"""The customer's in-app SMS inbox: read messages, mark them read."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import notification as notification_crud
from app.models.messaging import Notification
from app.services.errors import NotFound


class MessageNotFound(NotFound):
    code = "message_not_found"
    message = "Message not found"


@dataclass(frozen=True)
class InboxPage:
    messages: Sequence[Notification]
    unread_count: int
    next_cursor: int | None


async def list_inbox(
    db: AsyncSession, customer_id: int, *, limit: int, before: int | None
) -> InboxPage:
    # One extra row tells us whether there's an older page.
    rows = await notification_crud.list_inbox(db, customer_id, limit=limit + 1, before_id=before)
    has_more = len(rows) > limit
    rows = rows[:limit]
    return InboxPage(
        messages=rows,
        unread_count=await notification_crud.unread_count(db, customer_id),
        next_cursor=rows[-1].id if has_more else None,
    )


async def mark_read(db: AsyncSession, customer_id: int, message_id: int) -> None:
    """Safe to call again: an already-read message keeps its first read time."""
    message = await notification_crud.get_inbox_message(db, customer_id, message_id)
    if message is None:
        raise MessageNotFound()
    notification_crud.mark_read(message, datetime.now(UTC))
    await db.commit()


async def mark_all_read(db: AsyncSession, customer_id: int) -> int:
    marked = await notification_crud.mark_all_read(db, customer_id, datetime.now(UTC))
    await db.commit()
    return marked
