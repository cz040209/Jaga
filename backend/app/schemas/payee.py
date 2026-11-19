"""Request / response shapes for /payees."""

from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, BeforeValidator, Field

from app.core.masking import mask_account_number, mask_name
from app.models.banking import BankAccount, Payee
from app.models.enums import PayeeCheckStatus


def _clean_text(value: object) -> object:
    """Collapse repeated spaces and trim, before length checks run."""
    return " ".join(value.split()) if isinstance(value, str) else value


def normalize_account_number(value: str) -> str:
    """People paste numbers like '8847 2193 0556' or '8847-2193-0556'."""
    return value.replace(" ", "").replace("-", "")


AccountNumber = Annotated[
    str,
    Field(min_length=1, max_length=40, examples=["884721930556"]),
    AfterValidator(normalize_account_number),
]
Nickname = Annotated[str, BeforeValidator(_clean_text), Field(min_length=1, max_length=120)]


# ---------- Requests ----------
class PayeeCreate(BaseModel):
    account_number: AccountNumber
    nickname: Nickname | None = None  # default: the owner's masked name


class PayeeUpdate(BaseModel):
    nickname: Nickname


# ---------- Responses ----------
class RecipientOut(BaseModel):
    """What a lookup reveals: enough to confirm it's the right person, nothing more."""

    masked_name: str
    masked_number: str

    @classmethod
    def from_account(cls, account: BankAccount) -> "RecipientOut":
        return cls(
            masked_name=mask_name(account.account_name),
            masked_number=mask_account_number(account.account_number),
        )


class PayeeOut(BaseModel):
    id: int
    nickname: str
    recipient: RecipientOut
    check_status: PayeeCheckStatus
    created_at: datetime

    @classmethod
    def from_row(cls, payee: Payee, account: BankAccount) -> "PayeeOut":
        return cls(
            id=payee.id,
            nickname=payee.nickname,
            recipient=RecipientOut.from_account(account),
            check_status=payee.check_status,
            created_at=payee.created_at,
        )
