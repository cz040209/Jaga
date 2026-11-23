"""Reads and writes for the bank_accounts table.

There is no balance column. A balance is always worked out from
ledger_entries (credits minus debits), so it can never drift out of sync
with the money history.
"""

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.banking import BankAccount, LedgerEntry
from app.models.enums import AccountStatus, AccountType, LedgerDirection

# Seeded by migration 0009. The app finds the Treasury by this number.
TREASURY_ACCOUNT_NUMBER = "JAGA-TREASURY"

CENTS = Decimal("0.01")

# +amount for a credit (money in), -amount for a debit (money out).
_SIGNED_AMOUNT = case(
    (LedgerEntry.direction == LedgerDirection.CREDIT, LedgerEntry.amount),
    else_=-LedgerEntry.amount,
)


# ---------- Read ----------
async def get(db: AsyncSession, account_id: int) -> BankAccount | None:
    return await db.get(BankAccount, account_id)


async def get_many(db: AsyncSession, account_ids: Sequence[int]) -> list[BankAccount]:
    result = await db.scalars(select(BankAccount).where(BankAccount.id.in_(account_ids)))
    return list(result.all())


async def get_treasury(db: AsyncSession) -> BankAccount | None:
    return await db.scalar(
        select(BankAccount).where(BankAccount.account_number == TREASURY_ACCOUNT_NUMBER)
    )


async def list_for_customer(db: AsyncSession, customer_id: int) -> Sequence[BankAccount]:
    """The customer's accounts that aren't closed, primary first."""
    result = await db.scalars(
        select(BankAccount)
        .where(
            BankAccount.customer_id == customer_id,
            BankAccount.status != AccountStatus.CLOSED,
        )
        .order_by(BankAccount.is_primary.desc(), BankAccount.id)
    )
    return result.all()


async def get_by_number(db: AsyncSession, account_number: str) -> BankAccount | None:
    return await db.scalar(
        select(BankAccount).where(BankAccount.account_number == account_number)
    )


async def account_number_exists(db: AsyncSession, account_number: str) -> bool:
    found = await db.scalar(
        select(BankAccount.id).where(BankAccount.account_number == account_number)
    )
    return found is not None


async def lock_many(db: AsyncSession, account_ids: Sequence[int]) -> list[BankAccount]:
    """SELECT ... FOR UPDATE, always in id order.

    The lock is held until the transaction commits or rolls back, so two
    transfers from the same account run one after the other, never both at
    once. Locking in the same (id) order everywhere means two transactions
    can't each hold one lock and wait forever for the other (a deadlock).

    populate_existing: rows already loaded in this session are refreshed with
    the values read under the lock, not the stale ones from earlier.
    """
    if not account_ids:
        return []
    result = await db.scalars(
        select(BankAccount)
        .where(BankAccount.id.in_(account_ids))
        .order_by(BankAccount.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return list(result.all())


# ---------- Balances ----------
async def balance(db: AsyncSession, account_id: int) -> Decimal:
    return (await balances(db, [account_id]))[account_id]


async def balances(db: AsyncSession, account_ids: Sequence[int]) -> dict[int, Decimal]:
    """Balance per account in one query. Accounts with no entries get 0.00."""
    rows = await db.execute(
        select(LedgerEntry.account_id, func.sum(_SIGNED_AMOUNT))
        .where(LedgerEntry.account_id.in_(account_ids))
        .group_by(LedgerEntry.account_id)
    )
    found = {account_id: total for account_id, total in rows}
    return {
        account_id: Decimal(found.get(account_id, 0)).quantize(CENTS)
        for account_id in account_ids
    }


# ---------- Create ----------
async def create(
    db: AsyncSession,
    *,
    customer_id: int,
    account_number: str,
    account_name: str,
    is_primary: bool,
) -> BankAccount:
    account = BankAccount(
        customer_id=customer_id,
        account_number=account_number,
        account_name=account_name,
        account_type=AccountType.CUSTOMER,
        status=AccountStatus.ACTIVE,
        currency="MYR",
        is_primary=is_primary,
    )
    db.add(account)
    await db.flush()  # assigns account.id
    return account


# ---------- Update ----------
def close(account: BankAccount, now: datetime) -> None:
    """Soft delete: the row stays, because ledger history points at it."""
    account.status = AccountStatus.CLOSED
    account.closed_at = now
