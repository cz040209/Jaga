"""Reads and writes for transactions + ledger_entries.

Plain inserts only. The rules (balanced, locked, enough money) live in
app/ledger/service.py; nothing else should call these directly.
Both tables are append-only: a posted row is never updated or deleted.
A mistake is fixed by posting a new REVERSAL transaction.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.banking import BankAccount, LedgerEntry, Transaction
from app.models.enums import (
    AccountType,
    Channel,
    LedgerDirection,
    TransactionStatus,
    TransactionType,
)

# +amount for a credit (money in), -amount for a debit (money out).
SIGNED_AMOUNT = case(
    (LedgerEntry.direction == LedgerDirection.CREDIT, LedgerEntry.amount),
    else_=-LedgerEntry.amount,
)


async def create_posted_transaction(
    db: AsyncSession,
    *,
    reference: str,
    idempotency_key: str,
    transaction_type: TransactionType,
    channel: Channel,
    source_account_id: int,
    destination_account_id: int,
    amount: Decimal,
    initiated_by_customer_id: int | None,
    description: str | None,
    now: datetime,
    payee_id: int | None = None,
    customer_reference: str | None = None,
) -> Transaction:
    transaction = Transaction(
        reference=reference,
        idempotency_key=idempotency_key,
        transaction_type=transaction_type,
        status=TransactionStatus.POSTED,
        channel=channel,
        initiated_by_customer_id=initiated_by_customer_id,
        source_account_id=source_account_id,
        destination_account_id=destination_account_id,
        payee_id=payee_id,
        amount=amount,
        currency="MYR",
        description=description,
        customer_reference=customer_reference,
        initiated_at=now,
        posted_at=now,
    )
    db.add(transaction)
    await db.flush()  # assigns transaction.id, needed by the entries
    return transaction


def add_entries(
    db: AsyncSession,
    *,
    transaction_id: int,
    entries: Sequence[tuple[int, LedgerDirection, Decimal, str | None]],
    now: datetime,
) -> list[LedgerEntry]:
    """entries: (account_id, direction, amount, description), numbered 1, 2, ..."""
    rows = [
        LedgerEntry(
            transaction_id=transaction_id,
            account_id=account_id,
            direction=direction,
            amount=amount,
            currency="MYR",
            sequence_number=number,
            description=description,
            created_at=now,
        )
        for number, (account_id, direction, amount, description) in enumerate(entries, start=1)
    ]
    db.add_all(rows)
    return rows


CENTS = Decimal("0.01")


def _money(value: object) -> Decimal:
    """DB result -> Decimal with exactly 2 places.

    Careful: `value or 0` would be a bug, because Decimal("0.00") is falsy,
    so a balance of exactly zero would turn into 0 and print as "0".
    """
    return Decimal(0 if value is None else str(value)).quantize(CENTS)


# ---------- Read ----------
@dataclass(frozen=True)
class HistoryRow:
    """One line of an account's statement."""

    entry_id: int
    direction: LedgerDirection
    amount: Decimal
    balance_after: Decimal
    transaction_id: int
    reference: str
    transaction_type: TransactionType
    status: TransactionStatus
    description: str | None
    posted_at: datetime
    counterparty_name: str
    counterparty_number: str
    counterparty_type: AccountType


async def history(
    db: AsyncSession, account_id: int, *, limit: int, before_entry_id: int | None = None
) -> list[HistoryRow]:
    """An account's ledger lines, newest first, with the balance after each one.

    Paging uses the entry id as a cursor ("give me lines older than #57"),
    not OFFSET: a new transfer arriving between page 1 and page 2 would
    shift an OFFSET by one and show a line twice.

    balance_after is a running total (SUM ... OVER ... ORDER BY id) computed
    over ALL the account's lines in the inner query, before the page is cut
    out, so it is correct on every page.
    """
    running = (
        select(
            LedgerEntry.id.label("entry_id"),
            func.sum(SIGNED_AMOUNT).over(order_by=LedgerEntry.id).label("balance_after"),
        )
        .where(LedgerEntry.account_id == account_id)
        .subquery()
    )

    # The other side of the transaction: if this account was the source, the
    # counterparty is the destination, and the other way round.
    counterparty = aliased(BankAccount)
    counterparty_id = case(
        (Transaction.source_account_id == account_id, Transaction.destination_account_id),
        else_=Transaction.source_account_id,
    )

    query = (
        select(LedgerEntry, Transaction, counterparty, running.c.balance_after)
        .join(running, running.c.entry_id == LedgerEntry.id)
        .join(Transaction, Transaction.id == LedgerEntry.transaction_id)
        .join(counterparty, counterparty.id == counterparty_id)
        .where(LedgerEntry.account_id == account_id)
        .order_by(LedgerEntry.id.desc())
        .limit(limit)
    )
    if before_entry_id is not None:
        query = query.where(LedgerEntry.id < before_entry_id)

    rows = await db.execute(query)
    return [
        HistoryRow(
            entry_id=entry.id,
            direction=entry.direction,
            amount=entry.amount,
            balance_after=_money(balance_after),
            transaction_id=txn.id,
            reference=txn.reference,
            transaction_type=txn.transaction_type,
            status=txn.status,
            description=txn.description,
            posted_at=txn.posted_at or entry.created_at,
            counterparty_name=other.account_name,
            counterparty_number=other.account_number,
            counterparty_type=other.account_type,
        )
        for entry, txn, other, balance_after in rows
    ]


async def get_transaction(db: AsyncSession, transaction_id: int) -> Transaction | None:
    return await db.get(Transaction, transaction_id)


async def get_by_idempotency_key(
    db: AsyncSession, customer_id: int, idempotency_key: str
) -> Transaction | None:
    """Uses uq_transactions_customer_idempotency, so it's a single index lookup."""
    return await db.scalar(
        select(Transaction).where(
            Transaction.initiated_by_customer_id == customer_id,
            Transaction.idempotency_key == idempotency_key,
        )
    )


async def balance_after(db: AsyncSession, account_id: int, transaction_id: int) -> Decimal:
    """The account's balance right after this transaction's line on it."""
    entry_id = (
        select(LedgerEntry.id)
        .where(
            LedgerEntry.transaction_id == transaction_id,
            LedgerEntry.account_id == account_id,
        )
        .scalar_subquery()
    )
    total = await db.scalar(
        select(func.coalesce(func.sum(SIGNED_AMOUNT), 0)).where(
            LedgerEntry.account_id == account_id, LedgerEntry.id <= entry_id
        )
    )
    return _money(total)


async def system_total(db: AsyncSession) -> Decimal:
    """Credits minus debits across EVERY account. Double-entry means this is always 0."""
    total = await db.scalar(select(func.coalesce(func.sum(SIGNED_AMOUNT), 0)))
    return _money(total)
