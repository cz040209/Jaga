"""Bank accounts: opening a customer's account and reading balances."""

import secrets
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.crud import account as account_crud
from app.ledger import service as ledger
from app.models.banking import BankAccount
from app.models.enums import Channel, TransactionType
from app.models.identity import Customer

ACCOUNT_NUMBER_PREFIX = "88"  # every Jaga account number starts with 88
OPENING_BALANCE_KEY = "opening-balance"


# ---------- Account numbers ----------
def luhn_check_digit(digits: str) -> str:
    """The last digit of the account number, computed from the others.

    Same check as credit card numbers: one mistyped digit (or two swapped
    neighbours) makes the number invalid, so typos are caught before a
    transfer goes to the wrong person.
    """
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 0:  # every second digit, starting next to the check digit
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return str((10 - total % 10) % 10)


def is_valid_account_number(number: str) -> bool:
    return (
        len(number) == 12
        and number.isdigit()
        and number.startswith(ACCOUNT_NUMBER_PREFIX)
        and luhn_check_digit(number[:-1]) == number[-1]
    )


def new_account_number() -> str:
    """12 digits: '88' + 9 random digits + 1 check digit, e.g. 884721930556."""
    body = ACCOUNT_NUMBER_PREFIX + "".join(secrets.choice("0123456789") for _ in range(9))
    return body + luhn_check_digit(body)


async def _unused_account_number(db: AsyncSession) -> str:
    # 1,000,000,000 possible numbers, so a clash is very unlikely; the unique
    # index on account_number is the final guard either way.
    for _ in range(10):
        number = new_account_number()
        if not await account_crud.account_number_exists(db, number):
            return number
    raise RuntimeError("Could not find a free account number")


# ---------- Public API ----------
@dataclass(frozen=True)
class AccountWithBalance:
    account: BankAccount
    balance: Decimal


async def open_primary_account(db: AsyncSession, customer: Customer) -> BankAccount:
    """Open the customer's first account and pay in the opening balance.

    Called inside register(), in the same database transaction: a customer
    is never saved without an account, and an account never without its
    opening money. Does NOT commit.
    """
    account = await account_crud.create(
        db,
        customer_id=customer.id,
        account_number=await _unused_account_number(db),
        account_name=customer.full_name,
        is_primary=True,
    )

    treasury = await account_crud.get_treasury(db)
    if treasury is None:
        raise RuntimeError("JAGA-TREASURY is missing. Run: uv run alembic upgrade head")

    if settings.opening_balance > 0:
        await ledger.transfer(
            db,
            source_account_id=treasury.id,
            destination_account_id=account.id,
            amount=settings.opening_balance,
            transaction_type=TransactionType.OPENING_BALANCE,
            channel=Channel.SYSTEM,
            # Unique per customer (uq_transactions_customer_idempotency), so the
            # database itself refuses a second opening balance for anyone.
            idempotency_key=OPENING_BALANCE_KEY,
            initiated_by_customer_id=customer.id,
            description="Welcome to Jaga: opening balance",
        )
    return account


async def list_accounts(db: AsyncSession, customer_id: int) -> list[AccountWithBalance]:
    accounts = await account_crud.list_for_customer(db, customer_id)
    totals = await account_crud.balances(db, [a.id for a in accounts])
    return [AccountWithBalance(account=a, balance=totals[a.id]) for a in accounts]
