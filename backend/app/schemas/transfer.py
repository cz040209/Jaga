"""Request / response shapes for /transfers."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field

from app.core.masking import mask_account_number, mask_name
from app.models.enums import TransactionStatus
from app.schemas.account import Counterparty
from app.services.transfers import Receipt


def _clean_text(value: object) -> object:
    """Collapse repeated spaces and trim; an empty note becomes no note."""
    if isinstance(value, str):
        return " ".join(value.split()) or None
    return value


# ---------- Request ----------
class TransferCreate(BaseModel):
    payee_id: int = Field(gt=0)
    # Send money as a string ("250.50") to be exact; a JSON number also works.
    amount: Decimal = Field(gt=0, max_digits=17, decimal_places=2, examples=["250.50"])
    note: Annotated[str | None, BeforeValidator(_clean_text), Field(max_length=140)] = None


# ---------- Response ----------
class PayeeRef(BaseModel):
    id: int
    nickname: str


class TransferOut(BaseModel):
    """A transfer receipt, from YOUR side: 'out' if you sent it, 'in' if you received it."""

    id: int
    reference: str
    status: TransactionStatus
    direction: Literal["in", "out"]
    amount: Decimal
    note: str | None
    counterparty: Counterparty  # always masked
    payee: PayeeRef | None  # your saved payee (sender only)
    from_account: str  # your account, masked
    balance_after: Decimal  # your balance right after this transfer
    posted_at: datetime

    @classmethod
    def from_receipt(cls, receipt: Receipt) -> "TransferOut":
        txn = receipt.transaction
        return cls(
            id=txn.id,
            reference=txn.reference,
            status=txn.status,
            direction=receipt.direction,
            amount=txn.amount,
            note=txn.customer_reference,
            counterparty=Counterparty(
                name=mask_name(receipt.counterparty.account_name),
                masked_number=mask_account_number(receipt.counterparty.account_number),
            ),
            payee=(
                PayeeRef(id=receipt.payee.id, nickname=receipt.payee.nickname)
                if receipt.payee
                else None
            ),
            from_account=mask_account_number(receipt.my_account.account_number),
            balance_after=receipt.balance_after,
            posted_at=txn.posted_at or txn.initiated_at,
        )
