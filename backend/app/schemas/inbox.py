"""Response shapes for /inbox."""

from datetime import datetime

from pydantic import BaseModel

from app.models.messaging import Notification


class MessageOut(BaseModel):
    id: int
    event: str | None  # e.g. "transfer_received": lets the app pick an icon
    subject: str | None
    message: str
    language: str
    transaction_id: int | None  # tap through to GET /transfers/{id}
    read: bool
    received_at: datetime

    @classmethod
    def from_row(cls, row: Notification) -> "MessageOut":
        return cls(
            id=row.id,
            event=row.template_key,
            subject=row.subject,
            message=row.message,
            language=row.language,
            transaction_id=row.transaction_id,
            read=row.read_at is not None,
            received_at=row.delivered_at or row.created_at,
        )


class InboxOut(BaseModel):
    items: list[MessageOut]
    unread_count: int  # for the red badge on the inbox icon
    next_cursor: int | None  # send as ?before=<next_cursor> for older messages


class MarkedRead(BaseModel):
    marked: int
