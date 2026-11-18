"""Request / response shapes for /customers/me (profile, password, sessions, devices)."""

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import DeviceTrustStatus
from app.schemas.auth import Language, check_password_strength


def _clean_text(value: object) -> object:
    """Collapse repeated spaces and trim, before length checks run."""
    return " ".join(value.split()) if isinstance(value, str) else value


# ---------- Profile ----------
class CustomerUpdate(BaseModel):
    """PATCH: send only the fields you want to change."""

    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    preferred_language: Language | None = None

    _clean_name = field_validator("full_name", mode="before")(_clean_text)

    @model_validator(mode="after")
    def _at_least_one_field(self) -> Self:
        changed = {k for k in self.model_fields_set if getattr(self, k) is not None}
        if not changed:
            raise ValueError("Provide at least one field to update")
        return self


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _strength(cls, value: str) -> str:
        return check_password_strength(value)


class CloseAccountRequest(BaseModel):
    """Closing an account is irreversible from the app, so the password is required."""

    password: str = Field(min_length=1, max_length=256)


class RevokedSessions(BaseModel):
    revoked_sessions: int


# ---------- Sessions ----------
class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int | None
    ip_address: str | None
    country_code: str | None
    city: str | None
    started_at: datetime
    last_activity_at: datetime
    expires_at: datetime
    is_current: bool = False

    @field_validator("ip_address", mode="before")
    @classmethod
    def _ip_to_text(cls, value: object) -> object:
        # Postgres INET comes back as an ipaddress object; send it as text.
        return str(value) if value is not None else None


# ---------- Devices ----------
class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str | None
    operating_system: str | None
    browser: str | None
    trust_status: DeviceTrustStatus
    first_seen_at: datetime
    last_seen_at: datetime
    is_current: bool = False


class DeviceUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)

    _clean_name = field_validator("display_name", mode="before")(_clean_text)
