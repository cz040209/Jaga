"""notify(): the ONE function the rest of the app calls to tell a customer something.

    await notify(db, customer, Event.TRANSFER_SENT, {"amount": ..., ...})

The caller doesn't know or care which channels exist. notify() picks the
customer's language, renders the template, and hands it to every channel.
It never commits: the message is saved together with the action that caused
it, so a transfer that rolls back leaves no "money sent" message behind.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import notification as notification_crud
from app.models.identity import Customer
from app.models.messaging import Notification
from app.notify.channels import CHANNELS, Outgoing
from app.notify.templates import Event, render


async def notify(
    db: AsyncSession,
    customer: Customer,
    event: Event,
    data: dict[str, str],
    *,
    transaction_id: int | None = None,
    action_payload: dict[str, Any] | None = None,
) -> list[Notification]:
    """Queue a message for `customer` on every channel. Does NOT commit."""
    subject, message, language = render(event, customer.preferred_language, data)
    outgoing = Outgoing(
        customer_id=customer.id,
        template_key=event.value,
        subject=subject,
        message=message,
        language=language,
        transaction_id=transaction_id,
        action_payload=action_payload or {},
        now=datetime.now(UTC),
    )
    return [notification_crud.add(db, adapter.build(outgoing)) for adapter in CHANNELS]
