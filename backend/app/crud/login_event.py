"""Writes for the login_events table (append-only: never updated or deleted)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identity import LoginEvent


def create(
    db: AsyncSession,
    *,
    attempted_email: str,
    succeeded: bool,
    ip_address: str | None,
    customer_id: int | None = None,
    device_id: int | None = None,
    session_id: int | None = None,
    failure_reason: str | None = None,
    is_new_device: bool = False,
) -> LoginEvent:
    event = LoginEvent(
        customer_id=customer_id,
        device_id=device_id,
        session_id=session_id,
        attempted_email=attempted_email,
        succeeded=succeeded,
        failure_reason=failure_reason,
        is_new_device=is_new_device,
        ip_address=ip_address,
        risk_signals={},
    )
    db.add(event)
    return event
