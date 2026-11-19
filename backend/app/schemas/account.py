"""Response shapes for /accounts."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, computed_field

from app.core.masking import mask_account_number, mask_name
from app.crud.ledger import HistoryRow
from app.models.enums import (
    AccountStatus,
    AccountType,
    LedgerDirection,
    TransactionStatus,
    TransactionType,
)


class AccountOut(BaseModel):
    """One of the customer's own accounts.

    The full account_number is included because the owner needs it to receive
    money (like the "copy account number" button in a bank app). Screens show
    masked_number by default; anything that isn't the owner (logs, LLM
    prompts, the ops dashboard) must use the masked form.

    Money is a JSON string ("10000.00"), never a float: floats can't hold
    0.10 exactly, and a bank can't lose cents to rounding.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    account_number: str
    account_name: str
    account_type: AccountType
    status: AccountStatus
    currency: str
    is_primary: bool
    balance: Decimal
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def masked_number(self) -> str:
        return mask_account_number(self.account_number)


# ---------- History ----------
class Counterparty(BaseModel):
    """Who the money came from / went to. Always masked: it's someone else's data."""

    name: str
    masked_number: str | None  # None for the bank itself


class TransactionOut(BaseModel):
    """One line of the statement."""

    id: int  # ledger entry id; also the paging cursor
    transaction_id: int
    reference: str
    type: TransactionType
    status: TransactionStatus
    direction: Literal["in", "out"]
    amount: Decimal
    balance_after: Decimal
    description: str | None
    counterparty: Counterparty
    posted_at: datetime

    @classmethod
    def from_row(cls, row: HistoryRow) -> "TransactionOut":
        if row.counterparty_type == AccountType.SYSTEM:
            counterparty = Counterparty(name="Jaga", masked_number=None)
        else:
            counterparty = Counterparty(
                name=mask_name(row.counterparty_name),
                masked_number=mask_account_number(row.counterparty_number),
            )
        return cls(
            id=row.entry_id,
            transaction_id=row.transaction_id,
            reference=row.reference,
            type=row.transaction_type,
            status=row.status,
            direction="in" if row.direction == LedgerDirection.CREDIT else "out",
            amount=row.amount,
            balance_after=row.balance_after,
            description=row.description,
            counterparty=counterparty,
            posted_at=row.posted_at,
        )


class TransactionPage(BaseModel):
    account_id: int
    items: list[TransactionOut]
    next_cursor: int | None  # send as ?before=<next_cursor> for older lines; null = no more
