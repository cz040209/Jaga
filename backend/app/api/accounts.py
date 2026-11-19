"""The logged-in customer's bank accounts, balances and transaction history."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentCustomer, DbSession
from app.schemas.account import AccountOut, TransactionOut, TransactionPage
from app.schemas.auth import ErrorResponse
from app.services import accounts as account_service

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("/me")
async def my_accounts(customer: CurrentCustomer, db: DbSession) -> list[AccountOut]:
    """Your open accounts with their balance (worked out from the ledger), primary first."""
    rows = await account_service.list_accounts(db, customer.id)
    return [
        AccountOut.model_validate(
            {
                "id": row.account.id,
                "account_number": row.account.account_number,
                "account_name": row.account.account_name,
                "account_type": row.account.account_type,
                "status": row.account.status,
                "currency": row.account.currency,
                "is_primary": row.account.is_primary,
                "balance": row.balance,
                "created_at": row.account.created_at,
            }
        )
        for row in rows
    ]


@router.get(
    "/me/transactions",
    responses={404: {"model": ErrorResponse, "description": "Not your account"}},
)
async def my_transactions(
    customer: CurrentCustomer,
    db: DbSession,
    account_id: Annotated[
        int | None, Query(description="Which account. Default: your primary account.")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    before: Annotated[
        int | None, Query(ge=1, description="next_cursor from the previous page")
    ] = None,
) -> TransactionPage:
    """Your statement: newest first, with the balance after each line."""
    page = await account_service.list_transactions(
        db, customer.id, account_id=account_id, limit=limit, before=before
    )
    return TransactionPage(
        account_id=page.account.id,
        items=[TransactionOut.from_row(row) for row in page.rows],
        next_cursor=page.next_cursor,
    )
