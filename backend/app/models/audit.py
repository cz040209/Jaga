from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    Base,
    EMPTY_JSON,
    IntegerPrimaryKeyMixin,
)


class AuditLog(Base, IntegerPrimaryKeyMixin):
    __tablename__ = "audit_logs"

    actor_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )
    actor_customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"),
    )
    actor_staff_id: Mapped[int | None] = mapped_column(
        ForeignKey("staff_users.id", ondelete="SET NULL"),
    )
    action: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    resource_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    resource_id: Mapped[int | None] = mapped_column(BigInteger)
    request_id: Mapped[str | None] = mapped_column(String(128))
    ip_address: Mapped[Any | None] = mapped_column(INET)
    previous_values: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=EMPTY_JSON,
    )
    new_values: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=EMPTY_JSON,
    )
    audit_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
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
        CheckConstraint(
            "actor_type IN ('customer', 'staff', 'system')",
            name="ck_audit_actor_type",
        ),
        Index(
            "ix_audit_resource",
            "resource_type",
            "resource_id",
        ),
        Index(
            "ix_audit_customer_time",
            "actor_customer_id",
            "occurred_at",
        ),
        Index(
            "ix_audit_staff_time",
            "actor_staff_id",
            "occurred_at",
        ),
        Index("ix_audit_time", "occurred_at"),
    )