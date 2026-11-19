"""Payees: the people a customer saves so they can send them money.

Rules for adding one:
1. The account number must pass its check digit (catches typos).
2. It must be an open Jaga customer account.
3. It can't be your own account.
4. You can't save the same account twice.

The mule check (check_status) is filled in from Phase 2.
"""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.masking import mask_name
from app.crud import account as account_crud
from app.crud import payee as payee_crud
from app.models.banking import BankAccount, Payee
from app.models.enums import AccountStatus, AccountType
from app.services.accounts import is_valid_account_number
from app.services.errors import AccountNotFound, NotFound, ServiceError

PayeeWithAccount = tuple[Payee, BankAccount]


# ---------- Errors ----------
class InvalidAccountNumber(ServiceError):
    code = "invalid_account_number"
    message = "This account number isn't valid. Please check it and try again."


class OwnAccount(ServiceError):
    code = "own_account"
    message = "You can't add your own account as a payee"


class PayeeAlreadyExists(ServiceError):
    code = "payee_exists"
    message = "This account is already in your payees"


class PayeeNotFound(NotFound):
    code = "payee_not_found"
    message = "Payee not found"


def _now() -> datetime:
    return datetime.now(UTC)


# ---------- Lookup ----------
async def find_recipient(db: AsyncSession, customer_id: int, account_number: str) -> BankAccount:
    """Turn a typed account number into the account it belongs to, or explain why not.

    A closed account answers exactly like a missing one: nobody learns that
    an account used to exist.
    """
    if not is_valid_account_number(account_number):
        raise InvalidAccountNumber()
    account = await account_crud.get_by_number(db, account_number)
    if (
        account is None
        or account.account_type != AccountType.CUSTOMER
        or account.status == AccountStatus.CLOSED
    ):
        raise AccountNotFound("No Jaga account has this number")
    if account.customer_id == customer_id:
        raise OwnAccount()
    return account


# ---------- CRUD ----------
async def list_payees(db: AsyncSession, customer_id: int) -> Sequence[PayeeWithAccount]:
    return await payee_crud.list_for_customer(db, customer_id)


async def add_payee(
    db: AsyncSession, customer_id: int, account_number: str, nickname: str | None
) -> PayeeWithAccount:
    target = await find_recipient(db, customer_id, account_number)
    if await payee_crud.exists_for_target(db, customer_id, target.id):
        raise PayeeAlreadyExists()

    try:
        payee = await payee_crud.create(
            db,
            customer_id=customer_id,
            target_account_id=target.id,
            # No nickname given: use the masked owner name, e.g. "Ali b** A**".
            nickname=nickname or mask_name(target.account_name),
        )
    except IntegrityError as exc:
        # Same payee added twice at the same moment (double-tap): both passed
        # the check above, but uq_payees_active_customer_target lets one in.
        await db.rollback()
        raise PayeeAlreadyExists() from exc

    await db.commit()
    await db.refresh(payee)  # load server-side defaults such as created_at
    return payee, target


async def _get_own_payee(db: AsyncSession, customer_id: int, payee_id: int) -> PayeeWithAccount:
    found = await payee_crud.get_for_customer(db, customer_id, payee_id)
    if found is None:
        raise PayeeNotFound()
    return found


async def rename_payee(
    db: AsyncSession, customer_id: int, payee_id: int, nickname: str
) -> PayeeWithAccount:
    payee, target = await _get_own_payee(db, customer_id, payee_id)
    payee_crud.rename(payee, nickname)
    await db.commit()
    await db.refresh(payee)
    return payee, target


async def remove_payee(db: AsyncSession, customer_id: int, payee_id: int) -> None:
    payee, _ = await _get_own_payee(db, customer_id, payee_id)
    payee_crud.soft_delete(payee, _now())
    await db.commit()
