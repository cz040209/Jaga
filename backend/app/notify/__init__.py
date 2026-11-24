"""Customer notifications: notify() + one adapter per channel (in-app inbox first)."""

from app.notify.service import notify
from app.notify.templates import Event, format_amount, format_time

__all__ = ["Event", "format_amount", "format_time", "notify"]
