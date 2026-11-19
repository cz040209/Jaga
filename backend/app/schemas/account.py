"""Response shapes for /accounts."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, computed_field

from app.models.enums import AccountStatus, AccountType


def mask_account_number(number: str) -> str:
    """'884721930556' -> '•••• 0556'. Use this anywhere the full number isn't needed."""
    return f"•••• {number[-4:]}"


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
