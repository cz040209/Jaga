"""Message texts for every notification, in English, Malay and Chinese.

One template per event and language. The customer's preferred_language
picks the text; English is the fallback for anything missing.

Style follows real Malaysian bank SMS: short, starts with the bank name,
amount and reference up front, and a "not you?" line for anything a
fraudster could have done.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import StrEnum

# Malaysia has one time zone and no daylight saving, so a fixed +08:00 is
# exact (and needs no time-zone database inside the Docker image).
MALAYSIA_TIME = timezone(timedelta(hours=8), "MYT")

DEFAULT_LANGUAGE = "en"


class Event(StrEnum):
    """What happened. Stored as notifications.template_key."""

    WELCOME = "welcome"
    TRANSFER_SENT = "transfer_sent"
    TRANSFER_RECEIVED = "transfer_received"
    NEW_DEVICE_LOGIN = "new_device_login"
    PASSWORD_CHANGED = "password_changed"


@dataclass(frozen=True)
class Template:
    subject: str
    body: str


TEMPLATES: dict[Event, dict[str, Template]] = {
    Event.WELCOME: {
        "en": Template(
            "Welcome to Jaga",
            "Jaga: Welcome, {name}! Your account {account} is ready with RM {amount}. "
            "Jaga will never ask for your password or codes.",
        ),
        "ms": Template(
            "Selamat datang ke Jaga",
            "Jaga: Selamat datang, {name}! Akaun anda {account} sedia dengan RM {amount}. "
            "Jaga tidak akan meminta kata laluan atau kod anda.",
        ),
        "zh": Template(
            "欢迎使用 Jaga",
            "Jaga：欢迎您，{name}！您的账户 {account} 已开通，余额 RM {amount}。"
            "Jaga 绝不会向您索取密码或验证码。",
        ),
    },
    Event.TRANSFER_SENT: {
        "en": Template(
            "Money sent",
            "Jaga: RM {amount} sent to {recipient} on {time}. Ref {reference}. "
            "Not you? Contact Jaga immediately.",
        ),
        "ms": Template(
            "Wang dihantar",
            "Jaga: RM {amount} dihantar kepada {recipient} pada {time}. Rujukan {reference}. "
            "Bukan anda? Hubungi Jaga dengan segera.",
        ),
        "zh": Template(
            "转账成功",
            "Jaga：已于 {time} 向 {recipient} 转账 RM {amount}。参考编号 {reference}。"
            "不是您本人操作？请立即联系 Jaga。",
        ),
    },
    Event.TRANSFER_RECEIVED: {
        "en": Template(
            "Money received",
            "Jaga: You received RM {amount} from {sender} on {time}. Ref {reference}.",
        ),
        "ms": Template(
            "Wang diterima",
            "Jaga: Anda menerima RM {amount} daripada {sender} pada {time}. "
            "Rujukan {reference}.",
        ),
        "zh": Template(
            "收到款项",
            "Jaga：您已于 {time} 收到来自 {sender} 的 RM {amount}。参考编号 {reference}。",
        ),
    },
    Event.NEW_DEVICE_LOGIN: {
        "en": Template(
            "New device login",
            "Jaga: A new device logged in to your account on {time}. "
            "Not you? Change your password now and contact Jaga.",
        ),
        "ms": Template(
            "Log masuk peranti baharu",
            "Jaga: Peranti baharu telah log masuk ke akaun anda pada {time}. "
            "Bukan anda? Tukar kata laluan sekarang dan hubungi Jaga.",
        ),
        "zh": Template(
            "新设备登录",
            "Jaga：您的账户于 {time} 在新设备上登录。不是您本人？请立即更改密码并联系 Jaga。",
        ),
    },
    Event.PASSWORD_CHANGED: {
        "en": Template(
            "Password changed",
            "Jaga: Your password was changed on {time}. Your other devices were signed out. "
            "Not you? Contact Jaga immediately.",
        ),
        "ms": Template(
            "Kata laluan ditukar",
            "Jaga: Kata laluan anda telah ditukar pada {time}. Peranti lain telah dilog "
            "keluar. Bukan anda? Hubungi Jaga dengan segera.",
        ),
        "zh": Template(
            "密码已更改",
            "Jaga：您的密码已于 {time} 更改，其他设备已退出登录。不是您本人？请立即联系 Jaga。",
        ),
    },
}


# ---------- Formatting helpers (used for the {placeholders}) ----------
def format_amount(amount: Decimal) -> str:
    """Decimal('1250.5') -> '1,250.50'."""
    return f"{amount:,.2f}"


def format_time(moment: datetime) -> str:
    """Shown in Malaysia time, e.g. '19 Nov 2026, 3:58 PM'."""
    local = moment.astimezone(MALAYSIA_TIME)
    return f"{local.day} {local:%b %Y}, {local.hour % 12 or 12}:{local:%M %p}"


def render(event: Event, language: str, data: dict[str, str]) -> tuple[str, str, str]:
    """Returns (subject, message, language actually used)."""
    by_language = TEMPLATES[event]
    used = language if language in by_language else DEFAULT_LANGUAGE
    template = by_language[used]
    # str.format raises KeyError if a placeholder is missing: a bug the tests catch.
    return template.subject, template.body.format(**data), used
