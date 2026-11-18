"""Reads and writes for the customer_sessions table."""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SessionStatus
from app.models.identity import CustomerSession


# ---------- Read ----------
async def get(db: AsyncSession, session_id: int) -> CustomerSession | None:
    return await db.get(CustomerSession, session_id)


async def get_for_customer(
    db: AsyncSession, customer_id: int, session_id: int
) -> CustomerSession | None:
    """Only returns the session if it belongs to this customer."""
    return await db.scalar(
        select(CustomerSession).where(
            CustomerSession.id == session_id,
            CustomerSession.customer_id == customer_id,
        )
    )


async def get_by_refresh_hash_for_update(
    db: AsyncSession, refresh_token_hash: str
) -> CustomerSession | None:
    # FOR UPDATE locks the row until commit, so two requests using the same
    # refresh token at the same moment can't both succeed.
    return await db.scalar(
        select(CustomerSession)
        .where(CustomerSession.refresh_token_hash == refresh_token_hash)
        .with_for_update()
    )


async def list_active_for_customer(
    db: AsyncSession, customer_id: int
) -> Sequence[CustomerSession]:
    result = await db.scalars(
        select(CustomerSession)
        .where(
            CustomerSession.customer_id == customer_id,
            CustomerSession.status == SessionStatus.ACTIVE,
        )
        .order_by(CustomerSession.last_activity_at.desc(), CustomerSession.id.desc())
    )
    return result.all()


# ---------- Create ----------
async def create(
    db: AsyncSession,
    *,
    customer_id: int,
    device_id: int | None,
    refresh_token_hash: str,
    ip_address: str | None,
    now: datetime,
    expires_at: datetime,
) -> CustomerSession:
    session_row = CustomerSession(
        customer_id=customer_id,
        device_id=device_id,
        refresh_token_hash=refresh_token_hash,
        status=SessionStatus.ACTIVE,
        ip_address=ip_address,
        started_at=now,
        last_activity_at=now,
        expires_at=expires_at,
    )
    db.add(session_row)
    await db.flush()  # assigns session_row.id
    return session_row


# ---------- Update ----------
def rotate(
    session_row: CustomerSession,
    *,
    refresh_token_hash: str,
    now: datetime,
    expires_at: datetime,
    ip_address: str | None,
) -> None:
    session_row.refresh_token_hash = refresh_token_hash
    session_row.last_activity_at = now
    session_row.expires_at = expires_at
    if ip_address:
        session_row.ip_address = ip_address


def revoke(session_row: CustomerSession, *, reason: str, now: datetime) -> None:
    session_row.status = SessionStatus.REVOKED
    session_row.revoked_at = now
    session_row.revoke_reason = reason


def mark_expired(session_row: CustomerSession) -> None:
    session_row.status = SessionStatus.EXPIRED


async def revoke_all_for_customer(
    db: AsyncSession,
    customer_id: int,
    *,
    reason: str,
    now: datetime,
    except_session_id: int | None = None,
) -> int:
    """Revoke every active session of a customer in one UPDATE. Returns how many."""
    statement = (
        update(CustomerSession)
        .where(
            CustomerSession.customer_id == customer_id,
            CustomerSession.status == SessionStatus.ACTIVE,
        )
        .values(status=SessionStatus.REVOKED, revoked_at=now, revoke_reason=reason)
        .execution_options(synchronize_session=False)
    )
    if except_session_id is not None:
        statement = statement.where(CustomerSession.id != except_session_id)
    result = await db.execute(statement)
    assert isinstance(result, CursorResult)
    return result.rowcount


async def revoke_all_for_device(
    db: AsyncSession, device_id: int, *, reason: str, now: datetime
) -> int:
    result = await db.execute(
        update(CustomerSession)
        .where(
            CustomerSession.device_id == device_id,
            CustomerSession.status == SessionStatus.ACTIVE,
        )
        .values(status=SessionStatus.REVOKED, revoked_at=now, revoke_reason=reason)
        .execution_options(synchronize_session=False)
    )
    assert isinstance(result, CursorResult)
    return result.rowcount
