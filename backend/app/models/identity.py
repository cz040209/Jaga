from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)

from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    Base,
    EMPTY_JSON,
    NOT_DELETED,
    IntegerPrimaryKeyMixin,
    SoftDeleteMixin,
    TimestampMixin,
    enum_type,
)

from app.models.enums import (
    CustomerStatus,
    DeviceTrustStatus,
    SessionStatus,
    StaffRole,
    StaffStatus,
)

class Customer(Base, IntegerPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "customers"

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    phone_number: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    preferred_language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        server_default="en",
    )
    telegram_chat_id: Mapped[int | None] = mapped_column(
        BigInteger,
        unique=True,
    )
    status: Mapped[CustomerStatus] = mapped_column(
        enum_type(CustomerStatus, "customer_status"),
        nullable=False,
        server_default=CustomerStatus.ACTIVE.value,
    )
    failed_login_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    frozen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    freeze_reason: Mapped[str | None] = mapped_column(Text)
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    __table_args__ = (
        Index(
            "uq_customers_email_lower",
            func.lower(email),
            unique=True,
        ),
        Index("ix_customers_status", "status"),
    )

class Device(Base, IntegerPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "devices"

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    fingerprint_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    display_name: Mapped[str | None] = mapped_column(String(120))
    user_agent: Mapped[str | None] = mapped_column(Text)
    operating_system: Mapped[str | None] = mapped_column(String(100))
    browser: Mapped[str | None] = mapped_column(String(100))
    trust_status: Mapped[DeviceTrustStatus] = mapped_column(
        enum_type(DeviceTrustStatus, "device_trust_status"),
        nullable=False,
        server_default=DeviceTrustStatus.UNKNOWN.value,
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    trusted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    blocked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    __table_args__ = (
        Index(
            "uq_devices_customer_fingerprint",
            "customer_id",
            "fingerprint_hash",
            unique=True,
            postgresql_where=NOT_DELETED,
        ),
        Index("ix_devices_fingerprint", "fingerprint_hash"),
        Index(
            "ix_devices_customer_trust",
            "customer_id",
            "trust_status",
        ),
    )

class CustomerSession(Base, IntegerPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "customer_sessions"

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    device_id: Mapped[int | None] = mapped_column(
        ForeignKey("devices.id", ondelete="SET NULL"),
    )
    refresh_token_hash: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
    )
    status: Mapped[SessionStatus] = mapped_column(
        enum_type(SessionStatus, "customer_session_status"),
        nullable=False,
        server_default=SessionStatus.ACTIVE.value,
    )
    ip_address: Mapped[Any | None] = mapped_column(INET)
    country_code: Mapped[str | None] = mapped_column(String(2))
    city: Mapped[str | None] = mapped_column(String(120))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    revoke_reason: Mapped[str | None] = mapped_column(String(255))

    __table_args__ = (
        Index(
            "ix_customer_sessions_customer_status",
            "customer_id",
            "status",
        ),
        Index("ix_customer_sessions_expires", "expires_at"),
    )


class LoginEvent(Base, IntegerPrimaryKeyMixin):
    __tablename__ = "login_events"

    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"),
    )
    device_id: Mapped[int | None] = mapped_column(
        ForeignKey("devices.id", ondelete="SET NULL"),
    )
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("customer_sessions.id", ondelete="SET NULL"),
    )
    attempted_email: Mapped[str | None] = mapped_column(String(320))
    succeeded: Mapped[bool] = mapped_column(Boolean, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(255))
    is_new_device: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    ip_address: Mapped[Any | None] = mapped_column(INET)
    country_code: Mapped[str | None] = mapped_column(String(2))
    city: Mapped[str | None] = mapped_column(String(120))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    risk_signals: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=EMPTY_JSON,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_login_events_customer_time",
            "customer_id",
            "occurred_at",
        ),
        Index(
            "ix_login_events_ip_time",
            "ip_address",
            "occurred_at",
        ),
    )


class StaffUser(Base, IntegerPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "staff_users"

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[StaffRole] = mapped_column(
        enum_type(StaffRole, "staff_role"),
        nullable=False,
    )
    status: Mapped[StaffStatus] = mapped_column(
        enum_type(StaffStatus, "staff_status"),
        nullable=False,
        server_default=StaffStatus.ACTIVE.value,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    __table_args__ = (
        Index(
            "uq_staff_email_lower",
            func.lower(email),
            unique=True,
            postgresql_where=NOT_DELETED,
        ),
        Index("ix_staff_role_status", "role", "status"),
    )


class StaffSession(Base, IntegerPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "staff_sessions"

    staff_user_id: Mapped[int] = mapped_column(
        ForeignKey("staff_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    refresh_token_hash: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
    )
    status: Mapped[SessionStatus] = mapped_column(
        enum_type(SessionStatus, "staff_session_status"),
        nullable=False,
        server_default=SessionStatus.ACTIVE.value,
    )
    ip_address: Mapped[Any | None] = mapped_column(INET)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    __table_args__ = (
        Index(
            "ix_staff_sessions_user_status",
            "staff_user_id",
            "status",
        ),
        Index("ix_staff_sessions_expires", "expires_at"),
    )