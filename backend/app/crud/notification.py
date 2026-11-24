"""Reads and writes for the notifications table.

The in-app inbox is the rows with channel = 'sms_inbox'.
"""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import DeliveryStatus, NotificationChannel
from app.models.messaging import Notification

INBOX = NotificationChannel.SMS_INBOX


# ---------- Create ----------
def add(db: AsyncSession, notification: Notification) -> Notification:
    db.add(notification)
    return notification


# ---------- Read ----------
async def list_inbox(
    db: AsyncSession, customer_id: int, *, limit: int, before_id: int | None = None
) -> Sequence[Notification]:
    """Newest first. Paged by id ("older than #57"), like the statement."""
    query = (
        select(Notification)
        .where(Notification.customer_id == customer_id, Notification.channel == INBOX)
        .order_by(Notification.id.desc())
        .limit(limit)
    )
    if before_id is not None:
        query = query.where(Notification.id < before_id)
    return (await db.scalars(query)).all()


async def unread_count(db: AsyncSession, customer_id: int) -> int:
    count = await db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.customer_id == customer_id,
            Notification.channel == INBOX,
            Notification.read_at.is_(None),
        )
    )
    return int(count or 0)


async def get_inbox_message(
    db: AsyncSession, customer_id: int, notification_id: int
) -> Notification | None:
    """Only if it's in this customer's inbox."""
    return await db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.customer_id == customer_id,
            Notification.channel == INBOX,
        )
    )


# ---------- Update ----------
def mark_read(notification: Notification, now: datetime) -> None:
    if notification.read_at is None:  # keep the FIRST time it was read
        notification.read_at = now
        notification.status = DeliveryStatus.READ


async def mark_all_read(db: AsyncSession, customer_id: int, now: datetime) -> int:
    """One UPDATE for every unread message. Returns how many changed."""
    result = await db.execute(
        update(Notification)
        .where(
            Notification.customer_id == customer_id,
            Notification.channel == INBOX,
            Notification.read_at.is_(None),
        )
        .values(read_at=now, status=DeliveryStatus.READ)
    )
    return int(getattr(result, "rowcount", 0) or 0)
