"""The in-app SMS inbox: transfer alerts, security alerts, (later) OTP codes."""

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentCustomer, DbSession
from app.schemas.auth import ErrorResponse
from app.schemas.inbox import InboxOut, MarkedRead, MessageOut
from app.services import inbox as inbox_service

router = APIRouter(prefix="/inbox", tags=["inbox"])


@router.get("")
async def list_messages(
    customer: CurrentCustomer,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    before: Annotated[
        int | None, Query(ge=1, description="next_cursor from the previous page")
    ] = None,
) -> InboxOut:
    """Your messages, newest first, plus how many are unread."""
    page = await inbox_service.list_inbox(db, customer.id, limit=limit, before=before)
    return InboxOut(
        items=[MessageOut.from_row(row) for row in page.messages],
        unread_count=page.unread_count,
        next_cursor=page.next_cursor,
    )


@router.post("/read-all")
async def mark_all_read(customer: CurrentCustomer, db: DbSession) -> MarkedRead:
    """Mark every unread message as read."""
    return MarkedRead(marked=await inbox_service.mark_all_read(db, customer.id))


@router.post(
    "/{message_id}/read",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse, "description": "Not found (or not yours)"}},
)
async def mark_read(message_id: int, customer: CurrentCustomer, db: DbSession) -> None:
    """Mark one message as read (e.g. when the customer opens it)."""
    await inbox_service.mark_read(db, customer.id, message_id)
