"""Customer authentication: register, login, refresh, logout.

This module knows nothing about HTTP. It raises AuthError subclasses, and the
API layer (app/api/errors.py) turns them into status codes. That keeps the same
logic reusable from the Telegram bot, background jobs and tests.
"""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)
from app.models.enums import CustomerStatus, DeviceTrustStatus, SessionStatus
from app.models.identity import Customer, CustomerSession, Device, LoginEvent
from app.schemas.auth import LoginRequest, RegisterRequest, TokenPair


# ---------- Errors ----------
class AuthError(Exception):
    code = "auth_error"
    message = "Authentication failed"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or type(self).message
        super().__init__(self.message)


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


def _hash_fingerprint(fingerprint: str) -> str:
    return hashlib.sha256(fingerprint.encode()).hexdigest()


@lru_cache(maxsize=1)
def _dummy_password_hash() -> str:
    return hash_password("jaga-timing-equaliser")


async def _hash_password(password: str) -> str:
    # bcrypt takes ~0.2 s of CPU. Running it in a thread keeps the event loop
    # free to serve other requests meanwhile.
    return await asyncio.to_thread(hash_password, password)


async def _verify_password(password: str, password_hash: str) -> bool:
    return await asyncio.to_thread(verify_password, password, password_hash)


def _token_pair(customer_id: int, refresh_token: str) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(customer_id, "customer"),
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

    fingerprint_hash = _hash_fingerprint(fingerprint)
    device = await db.scalar(
        select(Device).where(
            Device.customer_id == customer_id,
            Device.fingerprint_hash == fingerprint_hash,
        )
    )
    now = _now()
    if device is None:
        device = Device(
            customer_id=customer_id,
            fingerprint_hash=fingerprint_hash,
            user_agent=client.user_agent,
            trust_status=DeviceTrustStatus.UNKNOWN,
            first_seen_at=now,
            last_seen_at=now,
        )
        db.add(device)
        await db.flush()  # get device.id
        return device, True

    device.last_seen_at = now
    if client.user_agent:
        device.user_agent = client.user_agent
    return device, False


async def _open_session(
    db: AsyncSession,
    customer: Customer,
    device: Device | None,
    client: ClientInfo,
) -> tuple[CustomerSession, TokenPair]:
    refresh_token, refresh_hash = new_refresh_token()
    now = _now()
    session_row = CustomerSession(
        customer_id=customer.id,
        device_id=device.id if device else None,
        refresh_token_hash=refresh_hash,
        status=SessionStatus.ACTIVE,
        ip_address=client.ip_address,
        started_at=now,
        last_activity_at=now,
        expires_at=now + timedelta(days=settings.refresh_token_ttl_days),
    )
    db.add(session_row)
    await db.flush()  # get session_row.id
    return session_row, _token_pair(customer.id, refresh_token)


def _record_login(
    db: AsyncSession,
    *,
    email: str,
    succeeded: bool,
    client: ClientInfo,
    customer_id: int | None = None,
    device_id: int | None = None,
    session_id: int | None = None,
    failure_reason: str | None = None,
    is_new_device: bool = False,
) -> None:
    """Every attempt, good or bad, is evidence for the account-takeover detector."""
    db.add(
        LoginEvent(
            customer_id=customer_id,
            device_id=device_id,
            session_id=session_id,
            attempted_email=email,
            succeeded=succeeded,
            failure_reason=failure_reason,
            is_new_device=is_new_device,
            ip_address=client.ip_address,
            risk_signals={},
        )
    )


async def _find_session_for_update(db: AsyncSession, refresh_token: str) -> CustomerSession | None:
    # FOR UPDATE locks the row, so two refresh calls racing with the same token
    # can't both succeed.
    return await db.scalar(
        select(CustomerSession)
        .where(CustomerSession.refresh_token_hash == hash_refresh_token(refresh_token))
        .with_for_update()
    )


# ---------- Public API ----------
async def register(db: AsyncSession, data: RegisterRequest, client: ClientInfo) -> AuthResult:
    if await db.scalar(select(Customer.id).where(func.lower(Customer.email) == data.email)):
        raise EmailAlreadyRegistered()
    if await db.scalar(select(Customer.id).where(Customer.phone_number == data.phone_number)):
        raise PhoneAlreadyRegistered()

    customer = Customer(
        email=data.email,
        phone_number=data.phone_number,
        full_name=data.full_name,
        password_hash=await _hash_password(data.password),
        preferred_language=data.preferred_language,
        status=CustomerStatus.ACTIVE,
        failed_login_count=0,
    )
    db.add(customer)
    try:
        await db.flush()
    except IntegrityError as exc:
        # Two sign-ups with the same email at the same moment: both passed the
        # checks above, but the unique index lets only one in.
        await db.rollback()
        if "phone" in str(exc.orig):
            raise PhoneAlreadyRegistered() from exc
        raise EmailAlreadyRegistered() from exc

    device, is_new_device = await _resolve_device(db, customer.id, data.device_fingerprint, client)
    session_row, tokens = await _open_session(db, customer, device, client)
    customer.last_login_at = _now()
    _record_login(
        db,
        email=data.email,
        succeeded=True,
        client=client,
        customer_id=customer.id,
        device_id=device.id if device else None,
        session_id=session_row.id,
        is_new_device=is_new_device,
    )
    await db.commit()
    await db.refresh(customer)  # load server-side defaults such as created_at
    return AuthResult(customer=customer, tokens=tokens, is_new_device=is_new_device)


async def login(db: AsyncSession, data: LoginRequest, client: ClientInfo) -> AuthResult:
    customer = await db.scalar(select(Customer).where(func.lower(Customer.email) == data.email))

    if customer is None:
        # Spend the same ~0.2 s as a real check, so response time doesn't reveal
        # whether the email exists.
        await _verify_password(data.password, _dummy_password_hash())
        _record_login(
            db, email=data.email, succeeded=False, client=client, failure_reason="unknown_email"
        )
        await db.commit()
        raise InvalidCredentials()

    if not await _verify_password(data.password, customer.password_hash):
        # SQL-side increment: correct even if two failed logins happen at once.
        customer.failed_login_count = Customer.failed_login_count + 1
        _record_login(
            db,
            email=data.email,
            succeeded=False,
            client=client,
            customer_id=customer.id,
            failure_reason="wrong_password",
        )
        await db.commit()
        raise InvalidCredentials()

    # Status is checked only AFTER the password, so a stranger can't learn
    # that an account is frozen.
    if customer.status != CustomerStatus.ACTIVE:
        _record_login(
            db,
            email=data.email,
            succeeded=False,
            client=client,
            customer_id=customer.id,
            failure_reason=f"account_{customer.status.value}",
        )
        await db.commit()
        raise AccountNotActive()

    device, is_new_device = await _resolve_device(db, customer.id, data.device_fingerprint, client)
    if device is not None and device.trust_status == DeviceTrustStatus.BLOCKED:
        _record_login(
            db,
            email=data.email,
            succeeded=False,
            client=client,
            customer_id=customer.id,
            device_id=device.id,
            failure_reason="device_blocked",
        )
        await db.commit()
        raise DeviceBlocked()

    session_row, tokens = await _open_session(db, customer, device, client)
    customer.failed_login_count = 0
    customer.last_login_at = _now()
    _record_login(
        db,
        email=data.email,
        succeeded=True,
        client=client,
        customer_id=customer.id,
        device_id=device.id if device else None,
        session_id=session_row.id,
        is_new_device=is_new_device,
    )
    await db.commit()
    await db.refresh(customer)
    return AuthResult(customer=customer, tokens=tokens, is_new_device=is_new_device)


async def refresh(db: AsyncSession, refresh_token: str, client: ClientInfo) -> TokenPair:
    session_row = await _find_session_for_update(db, refresh_token)
    if session_row is None or session_row.status != SessionStatus.ACTIVE:
        raise InvalidRefreshToken()

    now = _now()
    if session_row.expires_at <= now:
        session_row.status = SessionStatus.EXPIRED
        await db.commit()
        raise InvalidRefreshToken()

    customer = await db.get(Customer, session_row.customer_id)
    if customer is None or customer.status != CustomerStatus.ACTIVE:
        # Kill switch: a frozen account can't get new access tokens.
        session_row.status = SessionStatus.REVOKED
        session_row.revoked_at = now
        session_row.revoke_reason = "account_not_active"
        await db.commit()
        raise InvalidRefreshToken()

    # Rotation: the old refresh token stops working the moment this commits.
    new_token, new_hash = new_refresh_token()
    session_row.refresh_token_hash = new_hash
    session_row.last_activity_at = now
    # Sliding expiry: the session lives 30 days after its LAST use.
    session_row.expires_at = now + timedelta(days=settings.refresh_token_ttl_days)
    if client.ip_address:
        session_row.ip_address = client.ip_address
    await db.commit()
    return _token_pair(customer.id, new_token)


async def logout(db: AsyncSession, refresh_token: str) -> None:
    """Revoke the session. Always succeeds, even for unknown tokens (nothing to leak)."""
    session_row = await _find_session_for_update(db, refresh_token)
    if session_row is not None and session_row.status == SessionStatus.ACTIVE:
        session_row.status = SessionStatus.REVOKED
        session_row.revoked_at = _now()
        session_row.revoke_reason = "logout"
        await db.commit()
