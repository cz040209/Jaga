"""Customer authentication: register, login, refresh, logout.

Business rules live here; every database read/write goes through app/crud.
This module knows nothing about HTTP: it raises ServiceError subclasses and
app/api/errors.py turns them into status codes, so the same logic can be
reused by the Telegram bot, background jobs and tests.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.masking import mask_account_number
from app.core.security import (
    create_access_token,
    hash_password,
    hash_password_async,
    hash_refresh_token,
    new_refresh_token,
    verify_password_async,
)
from app.crud import customer as customer_crud
from app.crud import customer_session as session_crud
from app.crud import device as device_crud
from app.crud import login_event as login_event_crud
from app.models.enums import CustomerStatus, DeviceTrustStatus, SessionStatus
from app.models.identity import Customer, CustomerSession, Device
from app.notify import Event, format_amount, format_time, notify
from app.schemas.auth import LoginRequest, RegisterRequest, TokenPair
from app.services import accounts as account_service
from app.services.errors import ServiceError


# ---------- Errors ----------
class AuthError(ServiceError):
    code = "auth_error"
    message = "Authentication failed"


class EmailAlreadyRegistered(AuthError):
    code = "email_taken"
    message = "This email is already registered"


class PhoneAlreadyRegistered(AuthError):
    code = "phone_taken"
    message = "This phone number is already registered"


class InvalidCredentials(AuthError):
    # Same message for "no such email" and "wrong password", so attackers
    # can't use the login form to find out which emails have accounts.
    code = "invalid_credentials"
    message = "Invalid email or password"


class AccountNotActive(AuthError):
    code = "account_not_active"
    message = "This account is frozen or closed. Contact support to restore access."


class DeviceBlocked(AuthError):
    code = "device_blocked"
    message = "This device has been blocked to protect your account"


class InvalidRefreshToken(AuthError):
    code = "invalid_refresh_token"
    message = "Your session has ended. Please log in again."


# ---------- Small value objects ----------
@dataclass(frozen=True)
class ClientInfo:
    """Where a request came from. Filled in by the API layer."""

    ip_address: str | None = None
    user_agent: str | None = None


@dataclass(frozen=True)
class AuthResult:
    customer: Customer
    tokens: TokenPair
    is_new_device: bool


# ---------- Helpers ----------
def _now() -> datetime:
    return datetime.now(UTC)


def _session_expiry(now: datetime) -> datetime:
    return now + timedelta(days=settings.refresh_token_ttl_days)


def hash_fingerprint(fingerprint: str) -> str:
    return hashlib.sha256(fingerprint.encode()).hexdigest()


@lru_cache(maxsize=1)
def _dummy_password_hash() -> str:
    return hash_password("jaga-timing-equaliser")


def _token_pair(customer_id: int, session_id: int, refresh_token: str) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(customer_id, "customer", session_id=session_id),
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_ttl_minutes * 60,
    )


async def _resolve_device(
    db: AsyncSession,
    customer_id: int,
    fingerprint: str | None,
    client: ClientInfo,
) -> tuple[Device | None, bool]:
    """Find or create the device. Returns (device, is_new_device).

    No fingerprint means we can't recognise the device, so it counts as new.
    """
    if not fingerprint:
        return None, True

    now = _now()
    fingerprint_hash = hash_fingerprint(fingerprint)
    device = await device_crud.get_by_fingerprint(db, customer_id, fingerprint_hash)
    if device is None:
        device = await device_crud.create(
            db,
            customer_id=customer_id,
            fingerprint_hash=fingerprint_hash,
            user_agent=client.user_agent,
            now=now,
        )
        return device, True

    device_crud.touch(device, user_agent=client.user_agent, now=now)
    return device, False


async def _open_session(
    db: AsyncSession,
    customer: Customer,
    device: Device | None,
    client: ClientInfo,
) -> tuple[CustomerSession, TokenPair]:
    refresh_token, refresh_hash = new_refresh_token()
    now = _now()
    session_row = await session_crud.create(
        db,
        customer_id=customer.id,
        device_id=device.id if device else None,
        refresh_token_hash=refresh_hash,
        ip_address=client.ip_address,
        now=now,
        expires_at=_session_expiry(now),
    )
    return session_row, _token_pair(customer.id, session_row.id, refresh_token)


# ---------- Public API ----------
async def register(db: AsyncSession, data: RegisterRequest, client: ClientInfo) -> AuthResult:
    if await customer_crud.email_exists(db, data.email):
        raise EmailAlreadyRegistered()
    if await customer_crud.phone_exists(db, data.phone_number):
        raise PhoneAlreadyRegistered()

    try:
        customer = await customer_crud.create(
            db,
            email=data.email,
            phone_number=data.phone_number,
            full_name=data.full_name,
            password_hash=await hash_password_async(data.password),
            preferred_language=data.preferred_language,
        )
    except IntegrityError as exc:
        # Two sign-ups with the same email at the same moment: both passed the
        # checks above, but the unique index lets only one in.
        await db.rollback()
        if "phone" in str(exc.orig):
            raise PhoneAlreadyRegistered() from exc
        raise EmailAlreadyRegistered() from exc

    # New savings account + RM 10,000 from JAGA-TREASURY. Same transaction as
    # everything else here: if any step fails, none of it is saved.
    account = await account_service.open_primary_account(db, customer)
    await notify(
        db,
        customer,
        Event.WELCOME,
        {
            "name": customer.full_name,
            "account": mask_account_number(account.account_number),
            "amount": format_amount(settings.opening_balance),
        },
    )

    device, is_new_device = await _resolve_device(db, customer.id, data.device_fingerprint, client)
    session_row, tokens = await _open_session(db, customer, device, client)
    customer_crud.record_successful_login(customer, _now())
    login_event_crud.create(
        db,
        attempted_email=data.email,
        succeeded=True,
        ip_address=client.ip_address,
        customer_id=customer.id,
        device_id=device.id if device else None,
        session_id=session_row.id,
        is_new_device=is_new_device,
    )
    await db.commit()
    await db.refresh(customer)  # load server-side defaults such as created_at
    return AuthResult(customer=customer, tokens=tokens, is_new_device=is_new_device)


async def login(db: AsyncSession, data: LoginRequest, client: ClientInfo) -> AuthResult:
    customer = await customer_crud.get_by_email(db, data.email)

    if customer is None:
        # Spend the same ~0.2 s as a real check, so response time doesn't
        # reveal whether the email exists.
        await verify_password_async(data.password, _dummy_password_hash())
        login_event_crud.create(
            db,
            attempted_email=data.email,
            succeeded=False,
            ip_address=client.ip_address,
            failure_reason="unknown_email",
        )
        await db.commit()
        raise InvalidCredentials()

    if not await verify_password_async(data.password, customer.password_hash):
        customer_crud.record_failed_login(customer)
        login_event_crud.create(
            db,
            attempted_email=data.email,
            succeeded=False,
            ip_address=client.ip_address,
            customer_id=customer.id,
            failure_reason="wrong_password",
        )
        await db.commit()
        raise InvalidCredentials()

    # Status is checked only AFTER the password, so a stranger can't learn
    # that an account is frozen.
    if customer.status != CustomerStatus.ACTIVE:
        login_event_crud.create(
            db,
            attempted_email=data.email,
            succeeded=False,
            ip_address=client.ip_address,
            customer_id=customer.id,
            failure_reason=f"account_{customer.status.value}",
        )
        await db.commit()
        raise AccountNotActive()

    device, is_new_device = await _resolve_device(db, customer.id, data.device_fingerprint, client)
    if device is not None and device.trust_status == DeviceTrustStatus.BLOCKED:
        login_event_crud.create(
            db,
            attempted_email=data.email,
            succeeded=False,
            ip_address=client.ip_address,
            customer_id=customer.id,
            device_id=device.id,
            failure_reason="device_blocked",
        )
        await db.commit()
        raise DeviceBlocked()

    session_row, tokens = await _open_session(db, customer, device, client)
    customer_crud.record_successful_login(customer, _now())
    login_event_crud.create(
        db,
        attempted_email=data.email,
        succeeded=True,
        ip_address=client.ip_address,
        customer_id=customer.id,
        device_id=device.id if device else None,
        session_id=session_row.id,
        is_new_device=is_new_device,
    )
    if is_new_device:
        # A login from an unknown device is the first step of most account
        # takeovers, so the real owner hears about it straight away.
        await notify(db, customer, Event.NEW_DEVICE_LOGIN, {"time": format_time(_now())})
    await db.commit()
    await db.refresh(customer)
    return AuthResult(customer=customer, tokens=tokens, is_new_device=is_new_device)


async def refresh(db: AsyncSession, refresh_token: str, client: ClientInfo) -> TokenPair:
    session_row = await session_crud.get_by_refresh_hash_for_update(
        db, hash_refresh_token(refresh_token)
    )
    if session_row is None or session_row.status != SessionStatus.ACTIVE:
        raise InvalidRefreshToken()

    now = _now()
    if session_row.expires_at <= now:
        session_crud.mark_expired(session_row)
        await db.commit()
        raise InvalidRefreshToken()

    customer = await customer_crud.get(db, session_row.customer_id)
    if customer is None or customer.status != CustomerStatus.ACTIVE:
        # Kill switch: a frozen account can't get new access tokens.
        session_crud.revoke(session_row, reason="account_not_active", now=now)
        await db.commit()
        raise InvalidRefreshToken()

    # Rotation: the old refresh token stops working the moment this commits.
    # Sliding expiry: the session lives 30 days after its LAST use.
    new_token, new_hash = new_refresh_token()
    session_crud.rotate(
        session_row,
        refresh_token_hash=new_hash,
        now=now,
        expires_at=_session_expiry(now),
        ip_address=client.ip_address,
    )
    await db.commit()
    return _token_pair(customer.id, session_row.id, new_token)


async def logout(db: AsyncSession, refresh_token: str) -> None:
    """Revoke the session. Always succeeds, even for unknown tokens (nothing to leak)."""
    session_row = await session_crud.get_by_refresh_hash_for_update(
        db, hash_refresh_token(refresh_token)
    )
    if session_row is not None and session_row.status == SessionStatus.ACTIVE:
        session_crud.revoke(session_row, reason="logout", now=_now())
        await db.commit()
