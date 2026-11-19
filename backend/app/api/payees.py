"""Saved recipients. Transfers (step 6) send money to a payee, not to a raw number."""

from typing import Annotated, Any

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentCustomer, DbSession
from app.schemas.auth import ErrorResponse
from app.schemas.payee import (
    AccountNumber,
    PayeeCreate,
    PayeeOut,
    PayeeUpdate,
    RecipientOut,
)
from app.services import payees as payee_service

router = APIRouter(prefix="/payees", tags=["payees"])

OpenApiResponses = dict[int | str, dict[str, Any]]

LOOKUP_ERRORS: OpenApiResponses = {
    400: {"model": ErrorResponse, "description": "Invalid number, or your own account"},
    404: {"model": ErrorResponse, "description": "No Jaga account has this number"},
}
NOT_FOUND: OpenApiResponses = {
    404: {"model": ErrorResponse, "description": "Not found (or not yours)"}
}


@router.get("")
async def list_payees(customer: CurrentCustomer, db: DbSession) -> list[PayeeOut]:
    """Your saved payees, A to Z."""
    rows = await payee_service.list_payees(db, customer.id)
    return [PayeeOut.from_row(payee, account) for payee, account in rows]


@router.get("/lookup", responses=LOOKUP_ERRORS)
async def lookup_recipient(
    account_number: Annotated[AccountNumber, Query()],
    customer: CurrentCustomer,
    db: DbSession,
) -> RecipientOut:
    """Check an account number before saving it: shows the owner's masked name ("Ali b**")."""
    account = await payee_service.find_recipient(db, customer.id, account_number)
    return RecipientOut.from_account(account)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={
        **LOOKUP_ERRORS,
        409: {"model": ErrorResponse, "description": "Already one of your payees"},
    },
)
async def add_payee(body: PayeeCreate, customer: CurrentCustomer, db: DbSession) -> PayeeOut:
    """Save a new payee."""
    payee, account = await payee_service.add_payee(
        db, customer.id, body.account_number, body.nickname
    )
    return PayeeOut.from_row(payee, account)


@router.patch("/{payee_id}", responses=NOT_FOUND)
async def rename_payee(
    payee_id: int, body: PayeeUpdate, customer: CurrentCustomer, db: DbSession
) -> PayeeOut:
    """Change a payee's nickname."""
    payee, account = await payee_service.rename_payee(db, customer.id, payee_id, body.nickname)
    return PayeeOut.from_row(payee, account)


@router.delete("/{payee_id}", status_code=status.HTTP_204_NO_CONTENT, responses=NOT_FOUND)
async def remove_payee(payee_id: int, customer: CurrentCustomer, db: DbSession) -> None:
    """Remove a payee (soft delete). Past transfers to them are kept."""
    await payee_service.remove_payee(db, customer.id, payee_id)
