"""One adapter per channel. Adding a channel = one new class here + one line in CHANNELS.

Every adapter turns a rendered message into a notifications row, inside the
caller's database transaction (never committing):

- In-app inbox: the row IS the delivery, so it's saved as 'delivered'.
- External channels (Telegram, Web Push, email, ... later): the row is saved
  as 'pending', and a background worker sends it AFTER the commit, then
  records sent / failed. That way a rolled-back transfer can never have sent
  a message, and a slow Telegram server can never slow down a transfer.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from app.models.enums import DeliveryStatus, NotificationChannel
from app.models.messaging import Notification


@dataclass(frozen=True)
class Outgoing:
    """A rendered message, ready for any channel."""

    customer_id: int
    template_key: str
    subject: str
    message: str
    language: str
    transaction_id: int | None
    action_payload: dict[str, Any]
    now: datetime


class ChannelAdapter(Protocol):
    channel: NotificationChannel

    def build(self, outgoing: Outgoing) -> Notification: ...


class InAppInbox:
    """The simulated SMS inbox inside the Jaga app (CLAUDE.md: no real SMS)."""

    channel = NotificationChannel.SMS_INBOX

    def build(self, outgoing: Outgoing) -> Notification:
        return Notification(
            customer_id=outgoing.customer_id,
            transaction_id=outgoing.transaction_id,
            channel=self.channel,
            status=DeliveryStatus.DELIVERED,
            template_key=outgoing.template_key,
            subject=outgoing.subject,
            message=outgoing.message,
            language=outgoing.language,
            action_payload=outgoing.action_payload,
            attempt_count=1,
            sent_at=outgoing.now,
            delivered_at=outgoing.now,
        )


# The channels every customer gets today. Later: per-customer preferences
# (e.g. Telegram only once they've linked it).
CHANNELS: tuple[ChannelAdapter, ...] = (InAppInbox(),)
