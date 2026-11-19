"""Reads and writes for the payees table (a customer's saved recipients).

Payees are soft-deleted: every read below skips rows where deleted_at is set.
Reads return the payee together with the account it points at, because the
API always shows the target's (masked) name and number.
"""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.banking import BankAccount, Payee
from app.models.enums import PayeeCheckStatus

LIVE = Payee.deleted_at.is_(None)


# ---------- Read ----------
async def get_for_customer(
    db: AsyncSession, customer_id: int, payee_id: int
) -> tuple[Payee, BankAccount] | None:
    """Only if it belongs to this customer and isn't deleted."""
    row = await db.execute(
        select(Payee, BankAccount)
        .join(BankAccount, BankAccount.id == Payee.target_account_id)
        .where(Payee.id == payee_id, Payee.customer_id == customer_id, LIVE)
    )
    found = row.first()
    return (found[0], found[1]) if found else None


async def list_for_customer(
    db: AsyncSession, customer_id: int
) -> Sequence[tuple[Payee, BankAccount]]:
    rows = await db.execute(
        select(Payee, BankAccount)
        .join(BankAccount, BankAccount.id == Payee.target_account_id)
        .where(Payee.customer_id == customer_id, LIVE)
        .order_by(Payee.nickname, Payee.id)
    )
    return [(payee, account) for payee, account in rows]


async def exists_for_target(db: AsyncSession, customer_id: int, target_account_id: int) -> bool:
    found = await db.scalar(
        select(Payee.id).where(
            Payee.customer_id == customer_id,
            Payee.target_account_id == target_account_id,
            LIVE,
        )
    )
    return found is not None


# ---------- Create ----------
async def create(
    db: AsyncSession,
    *,
    customer_id: int,
    target_account_id: int,
    nickname: str,
) -> Payee:
    payee = Payee(
        customer_id=customer_id,
        target_account_id=target_account_id,
        nickname=nickname,
        check_status=PayeeCheckStatus.PENDING,  # the mule check arrives in Phase 2
        check_reasons=[],
    )
    db.add(payee)
    await db.flush()  # assigns payee.id; IntegrityError if already saved
    return payee


# ---------- Update ----------
def rename(payee: Payee, nickname: str) -> None:
    payee.nickname = nickname


# ---------- Delete ----------
def soft_delete(payee: Payee, now: datetime) -> None:
    """Hide the payee; the row stays, because past transfers point at it.

    Adding the same account again later creates a NEW payee row
    (the partial unique index ignores deleted rows).
    """
    payee.deleted_at = now
