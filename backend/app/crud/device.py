"""Reads and writes for the devices table."""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import DeviceTrustStatus
from app.models.identity import Device


# ---------- Read ----------
async def get_for_customer(db: AsyncSession, customer_id: int, device_id: int) -> Device | None:
    """Only returns the device if it belongs to this customer."""
    return await db.scalar(
        select(Device).where(Device.id == device_id, Device.customer_id == customer_id)
    )


async def get_by_fingerprint(
    db: AsyncSession, customer_id: int, fingerprint_hash: str
) -> Device | None:
    return await db.scalar(
        select(Device).where(
            Device.customer_id == customer_id,
            Device.fingerprint_hash == fingerprint_hash,
        )
    )


async def list_for_customer(db: AsyncSession, customer_id: int) -> Sequence[Device]:
    result = await db.scalars(
        select(Device)
        .where(Device.customer_id == customer_id)
        .order_by(Device.last_seen_at.desc(), Device.id.desc())
    )
    return result.all()


# ---------- Create ----------
async def create(
    db: AsyncSession,
    *,
    customer_id: int,
    fingerprint_hash: str,
    user_agent: str | None,
    now: datetime,
) -> Device:
    device = Device(
        customer_id=customer_id,
        fingerprint_hash=fingerprint_hash,
        user_agent=user_agent,
        trust_status=DeviceTrustStatus.UNKNOWN,
        first_seen_at=now,
        last_seen_at=now,
    )
    db.add(device)
    await db.flush()  # assigns device.id
    return device


# ---------- Update ----------
def touch(device: Device, *, user_agent: str | None, now: datetime) -> None:
    device.last_seen_at = now
    if user_agent:
        device.user_agent = user_agent


def rename(device: Device, display_name: str) -> None:
    device.display_name = display_name


# ---------- Delete ----------
async def delete(db: AsyncSession, device: Device) -> None:
    # Foreign keys from sessions, login_events and fraud_events are ON DELETE SET NULL,
    # so their history is kept; it just no longer points at this device.
    await db.delete(device)
    await db.flush()
