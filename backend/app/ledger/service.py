"""Double-entry ledger: the ONLY way money moves in Jaga.

Every movement is one `transactions` row plus two or more `ledger_entries`
rows (debit = money out of an account, credit = money in). Three rules:

1. Balanced: total debits == total credits, so money is never created or
   destroyed. Summed over every account, the ledger is always exactly 0.
2. Locked: customer accounts involved are locked (SELECT ... FOR UPDATE)
   before their balance is checked, so two transfers at the same moment
   can't both spend the same RM 10,000.
3. All-or-nothing: these functions never commit. The caller commits once, so
   the business action (e.g. a new customer) and its ledger lines are saved
   together, or not at all.

Only system accounts (the Treasury) may go below zero.
"""

import secrets
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import account as account_crud
from app.crud import ledger as ledger_crud
from app.models.banking import BankAccount, Transaction
from app.models.enums import (
    AccountStatus,
    AccountType,
    Channel,
    LedgerDirection,
    TransactionType,
)
from app.services.errors import ServiceError

CENTS = Decimal("0.01")


# ---------- Errors ----------
class InvalidAmount(ServiceError):
    code = "invalid_amount"
    message = "Amount must be more than RM 0.00, with at most 2 decimal places"


class InsufficientFunds(ServiceError):
    code = "insufficient_funds"
    message = "Not enough money in the account"


class AccountUnavailable(ServiceError):
    code = "account_unavailable"
    message = "This account can't be used right now"


class UnbalancedTransaction(Exception):
    """A bug in our code, never the customer's fault, so not a ServiceError (-> 500)."""


# ---------- Value objects ----------
@dataclass(frozen=True)
class Entry:
    account_id: int
    direction: LedgerDirection
    amount: Decimal
    description: str | None = None


# ---------- Helpers ----------
def new_reference(now: datetime) -> str:
    """Human-friendly, unique id shown on receipts, e.g. JG2611180F3A9C1B27."""
    return f"JG{now:%y%m%d}{secrets.token_hex(5).upper()}"


def check_amount(amount: Decimal) -> Decimal:
    if not amount.is_finite() or amount <= 0 or amount != amount.quantize(CENTS):
        raise InvalidAmount()
    return amount.quantize(CENTS)


def _check_balanced(entries: Sequence[Entry], amount: Decimal) -> None:
    if len(entries) < 2:
        raise UnbalancedTransaction("A transaction needs at least 2 entries")
    debits = sum((e.amount for e in entries if e.direction == LedgerDirection.DEBIT), Decimal(0))
    credits = sum(
        (e.amount for e in entries if e.direction == LedgerDirection.CREDIT), Decimal(0)
    )
    if any(e.amount <= 0 for e in entries):
        raise UnbalancedTransaction("Every entry amount must be positive")
    if debits != credits:
        raise UnbalancedTransaction(f"Debits {debits} != credits {credits}")
    if debits != amount:
        raise UnbalancedTransaction(f"Entries move {debits}, transaction says {amount}")


def _net_change(entries: Sequence[Entry]) -> dict[int, Decimal]:
    """How much each account goes up (+) or down (-) in this transaction."""
    change: dict[int, Decimal] = defaultdict(Decimal)
    for e in entries:
        change[e.account_id] += e.amount if e.direction == LedgerDirection.CREDIT else -e.amount
    return dict(change)


async def _load_and_lock(db: AsyncSession, account_ids: Sequence[int]) -> dict[int, BankAccount]:
    accounts = {a.id: a for a in await account_crud.get_many(db, account_ids)}
    missing = set(account_ids) - accounts.keys()
    if missing:
        raise AccountUnavailable()

    # Lock customer/merchant accounts; their balance must never go negative.
    # The Treasury isn't locked: it may go negative, so there's nothing to
    # check, and locking it would make every sign-up queue behind each other.
    to_lock = [a.id for a in accounts.values() if a.account_type != AccountType.SYSTEM]
    for locked in await account_crud.lock_many(db, to_lock):
        accounts[locked.id] = locked
    return accounts


# ---------- Public API ----------
async def post_transaction(
    db: AsyncSession,
    *,
    transaction_type: TransactionType,
    channel: Channel,
    source_account_id: int,
    destination_account_id: int,
    amount: Decimal,
    entries: Sequence[Entry],
    idempotency_key: str,
    initiated_by_customer_id: int | None = None,
    description: str | None = None,
    payee_id: int | None = None,
    customer_reference: str | None = None,
) -> Transaction:
    """Post a balanced set of ledger entries as one transaction. Does NOT commit."""
    amount = check_amount(amount)
    _check_balanced(entries, amount)
    change = _net_change(entries)
    accounts = await _load_and_lock(db, list(change))

    for account_id, delta in change.items():
        account = accounts[account_id]
        if account.status == AccountStatus.CLOSED:
            raise AccountUnavailable()
        # A frozen account can still receive money, but can't send any.
        if delta < 0 and account.status != AccountStatus.ACTIVE:
            raise AccountUnavailable()

    # Balance check, read AFTER the locks are held, so it sees every transfer
    # that committed before us and none can sneak in until we commit.
    debited = [
        account_id
        for account_id, delta in change.items()
        if delta < 0 and accounts[account_id].account_type != AccountType.SYSTEM
    ]
    if debited:
        current = await account_crud.balances(db, debited)
        for account_id in debited:
            if current[account_id] + change[account_id] < 0:
                raise InsufficientFunds()

    now = datetime.now(UTC)
    transaction = await ledger_crud.create_posted_transaction(
        db,
        reference=new_reference(now),
        idempotency_key=idempotency_key,
        transaction_type=transaction_type,
        channel=channel,
        source_account_id=source_account_id,
        destination_account_id=destination_account_id,
        amount=amount,
        initiated_by_customer_id=initiated_by_customer_id,
        description=description,
        now=now,
        payee_id=payee_id,
        customer_reference=customer_reference,
    )
    ledger_crud.add_entries(
        db,
        transaction_id=transaction.id,
        entries=[(e.account_id, e.direction, e.amount, e.description) for e in entries],
        now=now,
    )
    await db.flush()
    return transaction


async def transfer(
    db: AsyncSession,
    *,
    source_account_id: int,
    destination_account_id: int,
    amount: Decimal,
    transaction_type: TransactionType,
    channel: Channel,
    idempotency_key: str,
    initiated_by_customer_id: int | None = None,
    description: str | None = None,
    payee_id: int | None = None,
    customer_reference: str | None = None,
) -> Transaction:
    """The common case: debit one account, credit another. Does NOT commit."""
    if source_account_id == destination_account_id:
        raise AccountUnavailable("You can't transfer to the same account")
    amount = check_amount(amount)
    return await post_transaction(
        db,
        transaction_type=transaction_type,
        channel=channel,
        source_account_id=source_account_id,
        destination_account_id=destination_account_id,
        amount=amount,
        entries=[
            Entry(source_account_id, LedgerDirection.DEBIT, amount, description),
            Entry(destination_account_id, LedgerDirection.CREDIT, amount, description),
        ],
        idempotency_key=idempotency_key,
        initiated_by_customer_id=initiated_by_customer_id,
        description=description,
        payee_id=payee_id,
        customer_reference=customer_reference,
    )
