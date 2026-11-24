"""Transfers: a customer sends money to one of their payees.

Flow of send_transfer():
1. Idempotency: if this key was already used, return that transfer again
   instead of paying twice (a double-tap or a retried request on bad mobile
   data must never send money twice).
2. Resolve the payee (must be yours and not removed) and your account.
3. Risk decision. Phase 1 always approves; Phase 2 plugs the real-time
   fraud engine in here (APPROVE / STEP-UP / HOLD / BLOCK).
4. Move the money with the ledger (locks, balance check, double entry).
5. Tell both people (in-app inbox now; Telegram / Web Push later).
6. Commit once: the money, the ledger lines and both messages are saved
   together, or nothing is. No "money sent" message for a failed transfer.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.masking import mask_name
from app.crud import account as account_crud
from app.crud import customer as customer_crud
from app.crud import ledger as ledger_crud
from app.crud import payee as payee_crud
from app.ledger import service as ledger
from app.models.banking import BankAccount, Payee, Transaction
from app.models.enums import Channel, DecisionAction, TransactionType
from app.notify import Event, format_amount, format_time, notify
from app.services.accounts import get_own_account
from app.services.errors import NotFound, ServiceError
from app.services.payees import PayeeNotFound

DEFAULT_DESCRIPTION = "Fund transfer"


# ---------- Errors ----------
class TransferNotFound(NotFound):
    code = "transfer_not_found"
    message = "Transfer not found"


class IdempotencyKeyReused(ServiceError):
    code = "idempotency_key_reused"
    message = (
        "This Idempotency-Key was already used for a different transfer. "
        "Use a new key for every new transfer."
    )


# ---------- Results ----------
@dataclass(frozen=True)
class Receipt:
    """A transfer as seen by one of the two customers involved."""

    transaction: Transaction
    direction: Literal["in", "out"]
    my_account: BankAccount
    counterparty: BankAccount
    payee: Payee | None  # only the sender sees their own payee nickname
    balance_after: Decimal


@dataclass(frozen=True)
class SendResult:
    receipt: Receipt
    replayed: bool  # True: this key was used before; nothing new was sent


def _stored_key(idempotency_key: str) -> str:
    # Namespaced so a customer's key can never collide with internal keys
    # such as "opening-balance" (the same unique index covers both).
    return f"transfer:{idempotency_key}"


def _same_request(existing: Transaction, payee_id: int, amount: Decimal) -> bool:
    return (
        existing.transaction_type == TransactionType.TRANSFER
        and existing.payee_id == payee_id
        and existing.amount == amount
    )


async def _risk_decision(
    db: AsyncSession, *, customer_id: int, source: BankAccount, target: BankAccount, amount: Decimal
) -> DecisionAction:
    """PHASE 2 HOOK: the real-time fraud engine (rules + ML, < 50 ms) goes here.

    It will look at the amount vs. the customer's normal, how new the payee
    and device are, the time of day, the target's mule score, ... and return
    APPROVE, STEP_UP (OTP / scam check), HOLD or BLOCK. Phase 1 approves all.
    """
    return DecisionAction.APPROVE


# ---------- Public API ----------
async def send_transfer(
    db: AsyncSession,
    customer_id: int,
    *,
    payee_id: int,
    amount: Decimal,
    note: str | None,
    idempotency_key: str,
    channel: Channel = Channel.API,
) -> SendResult:
    """Send money to a payee. Commits. Safe to call twice with the same key.

    Takes customer_id (an int), not the Customer object: after a rollback
    every ORM object in the session is expired, and touching one again
    would trigger a database load at an unexpected moment.
    """
    key = _stored_key(idempotency_key)

    # 1. Seen this key before? Return the earlier result, send nothing.
    existing = await ledger_crud.get_by_idempotency_key(db, customer_id, key)
    if existing is not None:
        return await _replay(db, customer_id, existing, payee_id, amount)

    # 2. Who pays whom.
    amount = ledger.check_amount(amount)
    found = await payee_crud.get_for_customer(db, customer_id, payee_id)
    if found is None:
        raise PayeeNotFound()
    payee, target = found
    source = await get_own_account(db, customer_id)  # primary account

    # 3. Risk decision (Phase 2 makes this real).
    decision = await _risk_decision(
        db, customer_id=customer_id, source=source, target=target, amount=amount
    )
    if decision != DecisionAction.APPROVE:  # pragma: no cover - Phase 2
        raise NotImplementedError(f"Decision {decision} is handled from Phase 2")

    # 4-6. Move the money, queue the messages, then commit everything in one go.
    try:
        transaction = await ledger.transfer(
            db,
            source_account_id=source.id,
            destination_account_id=target.id,
            amount=amount,
            transaction_type=TransactionType.TRANSFER,
            channel=channel,
            idempotency_key=key,
            initiated_by_customer_id=customer_id,
            description=note or DEFAULT_DESCRIPTION,
            payee_id=payee.id,
            customer_reference=note,
        )
        transaction_id = transaction.id
        await _notify_both_sides(db, transaction, source=source, target=target)
        await db.commit()
    except IntegrityError:
        # The same key arrived twice at the same moment (double-tap): both
        # passed step 1, the second waited on the account lock, and the
        # unique index refused its insert. The first one paid; answer with it.
        await db.rollback()
        existing = await ledger_crud.get_by_idempotency_key(db, customer_id, key)
        if existing is None:
            raise
        return await _replay(db, customer_id, existing, payee_id, amount)
    except ServiceError:
        await db.rollback()  # e.g. insufficient funds: release the locks now
        raise

    receipt = await get_receipt(db, customer_id, transaction_id)
    return SendResult(receipt=receipt, replayed=False)


async def _notify_both_sides(
    db: AsyncSession, transaction: Transaction, *, source: BankAccount, target: BankAccount
) -> None:
    """'RM 50.00 sent to Ali b**' for the sender, 'You received ...' for the recipient."""
    common = {
        "amount": format_amount(transaction.amount),
        "reference": transaction.reference,
        "time": format_time(transaction.posted_at or transaction.initiated_at),
    }
    sender = await customer_crud.get(db, source.customer_id) if source.customer_id else None
    recipient = await customer_crud.get(db, target.customer_id) if target.customer_id else None
    if sender is not None:
        await notify(
            db,
            sender,
            Event.TRANSFER_SENT,
            {**common, "recipient": mask_name(target.account_name)},
            transaction_id=transaction.id,
        )
    if recipient is not None:
        await notify(
            db,
            recipient,
            Event.TRANSFER_RECEIVED,
            {**common, "sender": mask_name(source.account_name)},
            transaction_id=transaction.id,
        )


async def _replay(
    db: AsyncSession, customer_id: int, existing: Transaction, payee_id: int, amount: Decimal
) -> SendResult:
    # Same key but a different request is a client bug; refuse loudly rather
    # than guess which one was meant.
    if not _same_request(existing, payee_id, amount):
        raise IdempotencyKeyReused()
    receipt = await get_receipt(db, customer_id, existing.id)
    return SendResult(receipt=receipt, replayed=True)


async def get_receipt(db: AsyncSession, customer_id: int, transaction_id: int) -> Receipt:
    """A transfer, from the point of view of the sender OR the recipient.

    Anyone else gets the same 404 as a transfer that doesn't exist.
    """
    transaction = await ledger_crud.get_transaction(db, transaction_id)
    if transaction is None or transaction.transaction_type != TransactionType.TRANSFER:
        raise TransferNotFound()

    my_accounts = {a.id: a for a in await account_crud.list_for_customer(db, customer_id)}
    if transaction.source_account_id in my_accounts:
        direction: Literal["in", "out"] = "out"
        mine, other_id = transaction.source_account_id, transaction.destination_account_id
    elif transaction.destination_account_id in my_accounts:
        direction = "in"
        mine, other_id = transaction.destination_account_id, transaction.source_account_id
    else:
        raise TransferNotFound()

    counterparty = await account_crud.get(db, other_id)
    assert counterparty is not None  # foreign key guarantees it

    payee = None
    if direction == "out" and transaction.payee_id is not None:
        payee = await payee_crud.get_including_deleted(db, transaction.payee_id)

    return Receipt(
        transaction=transaction,
        direction=direction,
        my_account=my_accounts[mine],
        counterparty=counterparty,
        payee=payee,
        balance_after=await ledger_crud.balance_after(db, mine, transaction.id),
    )

