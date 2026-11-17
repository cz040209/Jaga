"""Request / response shapes for the customer auth API.

Validation happens here, before any business logic runs: if a request reaches
the service layer, its email is lower-case, its phone number is normalised and
its password meets the rules.
"""

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import CustomerStatus

Language = Literal["en", "ms", "zh"]

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_BYTES = 72  # bcrypt ignores everything after 72 bytes


def normalize_my_mobile(value: str) -> str:
    """Turn '012-345 6789', '+60 12 345 6789' or '60123456789' into '+60123456789'."""
    digits = re.sub(r"[\s\-()]", "", value)
    if digits.startswith("+60"):
        digits = digits[3:]
    elif digits.startswith("60"):
        digits = digits[2:]
    elif digits.startswith("0"):
        digits = digits[1:]
    # Malaysian mobile numbers: 1x followed by 7-8 more digits.
    if not re.fullmatch(r"1\d{8,9}", digits):
        raise ValueError("Enter a valid Malaysian mobile number, e.g. 012-345 6789")
    return "+60" + digits


def check_password_strength(value: str) -> str:
    if len(value) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters")
    if len(value.encode()) > PASSWORD_MAX_BYTES:
        raise ValueError("Password is too long")
    if value.strip() != value:
        raise ValueError("Password cannot start or end with a space")
    return value


# ---------- Requests ----------
class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    phone_number: str
    password: str
    preferred_language: Language = "en"
    device_fingerprint: str | None = Field(default=None, min_length=8, max_length=256)

    @field_validator("full_name", mode="before")
    @classmethod
    def _clean_name(cls, value: object) -> object:
        # Collapse "  Aisyah   Rahman " to "Aisyah Rahman" before the length check runs.
        return " ".join(value.split()) if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def _lower_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("phone_number")
    @classmethod
    def _phone(cls, value: str) -> str:
        return normalize_my_mobile(value)

    @field_validator("password")
    @classmethod
    def _password(cls, value: str) -> str:
        return check_password_strength(value)


class LoginRequest(BaseModel):
    email: EmailStr
    # No strength rules on login: only "is it the right password?"
    password: str = Field(min_length=1, max_length=256)
    device_fingerprint: str | None = Field(default=None, min_length=8, max_length=256)

    @field_validator("email")
    @classmethod
    def _lower_email(cls, value: str) -> str:
        return value.lower()


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=200)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=200)


# ---------- Responses ----------
class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description="Access token lifetime in seconds")


class CustomerOut(BaseModel):
    """What a customer may see about themselves. Never includes password_hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    phone_number: str
    preferred_language: str
    status: CustomerStatus
    created_at: datetime


class AuthResponse(BaseModel):
    customer: CustomerOut
    tokens: TokenPair
    is_new_device: bool


class ErrorResponse(BaseModel):
    detail: str
    code: str
