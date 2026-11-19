"""Accounts + double-entry ledger: opening balance, invariants, locking, atomicity."""

import asyncio
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.crud import account as account_crud
from app.crud import ledger as ledger_crud
from app.ledger import service as ledger
from app.models.banking import BankAccount, LedgerEntry, Transaction
from app.models.enums import (
    AccountStatus,
    Channel,
    LedgerDirection,
    TransactionStatus,
    TransactionType,
)
from app.services.accounts import is_valid_account_number, luhn_check_digit

PASSWORD = "S3cure-pass!"
OPENING = Decimal("10000.00")


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def register(client: AsyncClient, n: int) -> dict[str, Any]:
    response = await client.post(
        "/auth/register",
        json={
            "full_name": f"Customer {n}",
            "email": f"customer{n}@jaga.my",
            "phone_number": f"01{n:08d}",
            "password": PASSWORD,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def my_account(client: AsyncClient, token: str) -> dict[str, Any]:
    response = await client.get("/accounts/me", headers=bearer(token))
    assert response.status_code == 200, response.text
    accounts = response.json()
    assert len(accounts) == 1
    return accounts[0]


# ---------- Account numbers ----------
def test_account_numbers_have_a_check_digit() -> None:
    assert luhn_check_digit("7992739871") == "3"  # textbook Luhn example
    valid = "88123456789" + luhn_check_digit("88123456789")
    assert is_valid_account_number(valid)
    typo = valid[:-1] + str((int(valid[-1]) + 1) % 10)  # one digit wrong
    assert not is_valid_account_number(typo)
    swapped = valid[:3] + valid[4] + valid[3] + valid[5:]  # two neighbours swapped
    assert not is_valid_account_number(swapped)


# ---------- Registration opens a funded account ----------
async def test_register_opens_account_with_opening_balance(
    client: AsyncClient, db: AsyncSession
) -> None:
    token = (await register(client, 1))["tokens"]["access_token"]
    account = await my_account(client, token)

    assert account["balance"] == "10000.00"  # a string, never a float
    assert account["is_primary"] is True
    assert account["status"] == "active"
    assert account["account_name"] == "Customer 1"
    assert is_valid_account_number(account["account_number"])
    assert account["masked_number"] == "•••• " + account["account_number"][-4:]

    # In the database: one posted transaction, two balanced lines.
    txn = await db.scalar(select(Transaction))
    assert txn is not None
    assert txn.transaction_type == TransactionType.OPENING_BALANCE
    assert txn.status == TransactionStatus.POSTED
    entries = (await db.scalars(select(LedgerEntry).order_by(LedgerEntry.sequence_number))).all()
    treasury = await account_crud.get_treasury(db)
    assert treasury is not None
    assert [(e.account_id, e.direction, e.amount) for e in entries] == [
        (treasury.id, LedgerDirection.DEBIT, OPENING),
        (account["id"], LedgerDirection.CREDIT, OPENING),
    ]


async def test_accounts_require_login(client: AsyncClient) -> None:
    assert (await client.get("/accounts/me")).status_code == 401


async def test_system_total_is_always_zero(client: AsyncClient, db: AsyncSession) -> None:
    for n in range(3):
        await register(client, n)

    assert await ledger_crud.system_total(db) == 0
    treasury = await account_crud.get_treasury(db)
    assert treasury is not None
    assert await account_crud.balance(db, treasury.id) == -3 * OPENING


async def test_concurrent_registrations_all_get_paid(
    client: AsyncClient, db: AsyncSession
) -> None:
    """Many sign-ups at the same moment: each gets exactly one opening balance."""
    await asyncio.gather(*(register(client, n) for n in range(8)))

    assert await db.scalar(select(func.count()).select_from(Transaction)) == 8
    assert await ledger_crud.system_total(db) == 0
    customer_accounts = (
        await db.scalars(select(BankAccount.id).where(BankAccount.customer_id.is_not(None)))
    ).all()
    balances = await account_crud.balances(db, customer_accounts)
    assert set(balances.values()) == {OPENING}


# ---------- Ledger rules ----------
async def _two_customer_accounts(client: AsyncClient, db: AsyncSession) -> tuple[int, int]:
    await register(client, 1)
    await register(client, 2)
    ids = (
        await db.scalars(
            select(BankAccount.id)
            .where(BankAccount.customer_id.is_not(None))
            .order_by(BankAccount.id)
        )
    ).all()
    return ids[0], ids[1]


async def _move(db: AsyncSession, source: int, destination: int, amount: str, key: str) -> None:
    await ledger.transfer(
        db,
        source_account_id=source,
        destination_account_id=destination,
        amount=Decimal(amount),
        transaction_type=TransactionType.TRANSFER,
        channel=Channel.API,
        idempotency_key=key,
    )


async def test_transfer_moves_money_and_keeps_total_zero(
    client: AsyncClient, db: AsyncSession
) -> None:
    a, b = await _two_customer_accounts(client, db)
    await _move(db, a, b, "2500.50", "t1")
    await db.commit()

    assert await account_crud.balances(db, [a, b]) == {
        a: Decimal("7499.50"),
        b: Decimal("12500.50"),
    }
    assert await ledger_crud.system_total(db) == 0


async def test_customer_balance_never_goes_negative(
    client: AsyncClient, db: AsyncSession
) -> None:
    a, b = await _two_customer_accounts(client, db)
    with pytest.raises(ledger.InsufficientFunds):
        await _move(db, a, b, "10000.01", "too-much")
    await db.rollback()

    # Spending exactly everything is fine.
    await _move(db, a, b, "10000.00", "all-of-it")
    await db.commit()
    assert await account_crud.balance(db, a) == 0


@pytest.mark.parametrize("amount", ["0", "-5", "10.001", "NaN"])
async def test_bad_amounts_are_rejected(
    client: AsyncClient, db: AsyncSession, amount: str
) -> None:
    a, b = await _two_customer_accounts(client, db)
    with pytest.raises(ledger.InvalidAmount):
        await _move(db, a, b, amount, "bad")
    await db.rollback()


async def test_unbalanced_entries_are_refused(client: AsyncClient, db: AsyncSession) -> None:
    a, b = await _two_customer_accounts(client, db)
    with pytest.raises(ledger.UnbalancedTransaction):
        await ledger.post_transaction(
            db,
            transaction_type=TransactionType.ADJUSTMENT,
            channel=Channel.SYSTEM,
            source_account_id=a,
            destination_account_id=b,
            amount=Decimal("100.00"),
            entries=[
                ledger.Entry(a, LedgerDirection.DEBIT, Decimal("100.00")),
                ledger.Entry(b, LedgerDirection.CREDIT, Decimal("150.00")),  # 50 from nowhere
            ],
            idempotency_key="unbalanced",
        )
    await db.rollback()
    assert await ledger_crud.system_total(db) == 0


async def test_frozen_account_can_receive_but_not_send(
    client: AsyncClient, db: AsyncSession
) -> None:
    a, b = await _two_customer_accounts(client, db)
    frozen = await account_crud.get(db, a)
    assert frozen is not None
    frozen.status = AccountStatus.FROZEN
    await db.commit()

    with pytest.raises(ledger.AccountUnavailable):
        await _move(db, a, b, "1.00", "from-frozen")
    await db.rollback()

    await _move(db, b, a, "1.00", "to-frozen")
    await db.commit()
    assert await account_crud.balance(db, a) == Decimal("10001.00")


async def test_failed_step_saves_nothing(client: AsyncClient, db: AsyncSession) -> None:
    """All-or-nothing: a transfer followed by a failure in the same transaction leaves no trace."""
    a, b = await _two_customer_accounts(client, db)
    before = await db.scalar(select(func.count()).select_from(LedgerEntry))

    await _move(db, a, b, "500.00", "first-half")
    with pytest.raises(ledger.InsufficientFunds):
        await _move(db, a, b, "9600.00", "second-half")  # only 9,500 left
    await db.rollback()

    assert await db.scalar(select(func.count()).select_from(LedgerEntry)) == before
    assert await account_crud.balance(db, a) == OPENING


async def test_concurrent_spending_cannot_double_spend(
    client: AsyncClient, db: AsyncSession
) -> None:
    """Two RM 6,000 transfers from a RM 10,000 account at the same moment: only one wins.

    Without the row lock, both would read 10,000, both would pass the check,
    and the account would end at -2,000.
    """
    a, b = await _two_customer_accounts(client, db)

    async def spend(key: str) -> bool:
        async with SessionLocal() as session:
            try:
                await _move(session, a, b, "6000.00", key)
                await asyncio.sleep(0.05)  # hold the lock a moment, so the other one waits
                await session.commit()
                return True
            except ledger.InsufficientFunds:
                await session.rollback()
                return False

    results = await asyncio.gather(spend("race-1"), spend("race-2"))

    assert sorted(results) == [False, True]
    assert await account_crud.balance(db, a) == Decimal("4000.00")
    assert await ledger_crud.system_total(db) == 0
