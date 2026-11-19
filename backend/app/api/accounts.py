"""The logged-in customer's bank accounts and balances."""

from fastapi import APIRouter

from app.api.deps import CurrentCustomer, DbSession
from app.schemas.account import AccountOut
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
