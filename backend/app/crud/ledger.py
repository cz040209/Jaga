"""Writes for transactions + ledger_entries.

Plain inserts only. The rules (balanced, locked, enough money) live in
app/ledger/service.py; nothing else should call these directly.
Both tables are append-only: a posted row is never updated or deleted.
A mistake is fixed by posting a new REVERSAL transaction.
"""

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.banking import LedgerEntry, Transaction
from app.models.enums import Channel, LedgerDirection, TransactionStatus, TransactionType


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
        amount=amount,
        currency="MYR",
        description=description,
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


async def system_total(db: AsyncSession) -> Decimal:
    """Credits minus debits across EVERY account. Double-entry means this is always 0."""
    signed = case(
        (LedgerEntry.direction == LedgerDirection.CREDIT, LedgerEntry.amount),
        else_=-LedgerEntry.amount,
    )
    total = await db.scalar(select(func.coalesce(func.sum(signed), 0)))
    return Decimal(total or 0)
