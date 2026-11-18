from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    Base,
    EMPTY_JSON,
    IntegerPrimaryKeyMixin,
    SoftDeleteMixin,
    TimestampMixin,
    enum_type,
)
from app.models.enums import (
    CasePriority,
    CaseStatus,
    LabelSource,
    LabelValue,
)


class FraudCase(Base, IntegerPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "fraud_cases"

    case_number: Mapped[str] = mapped_column(
        String(40),
        unique=True,
        nullable=False,
    )
    primary_customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"),
    )
    assigned_to_staff_id: Mapped[int | None] = mapped_column(
        ForeignKey("staff_users.id", ondelete="SET NULL"),
    )
    status: Mapped[CaseStatus] = mapped_column(
        enum_type(CaseStatus, "case_status"),
        nullable=False,
        server_default=CaseStatus.OPEN.value,
    )
    priority: Mapped[CasePriority] = mapped_column(
        enum_type(CasePriority, "case_priority"),
        nullable=False,
        server_default=CasePriority.MEDIUM.value,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    ai_summary: Mapped[str | None] = mapped_column(Text)
    ai_recommended_action: Mapped[str | None] = mapped_column(Text)
    ai_evidence: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=EMPTY_JSON,
    )
    ai_generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    resolution: Mapped[str | None] = mapped_column(Text)
    resolved_label: Mapped[LabelValue | None] = mapped_column(
        enum_type(LabelValue, "case_resolution_label"),
    )
    resolved_by_staff_id: Mapped[int | None] = mapped_column(
        ForeignKey("staff_users.id", ondelete="SET NULL"),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    __table_args__ = (
        Index("ix_cases_status_priority", "status", "priority"),
        Index(
            "ix_cases_assignee_status",
            "assigned_to_staff_id",
            "status",
        ),
        Index(
            "ix_cases_customer_time",
            "primary_customer_id",
            "created_at",
        ),
    )


class CaseEvent(Base, IntegerPrimaryKeyMixin):
    __tablename__ = "case_events"

    case_id: Mapped[int] = mapped_column(
        ForeignKey("fraud_cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_id: Mapped[int] = mapped_column(
        ForeignKey("fraud_events.id", ondelete="RESTRICT"),
        nullable=False,
    )
    link_reason: Mapped[str | None] = mapped_column(String(255))
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "case_id",
            "event_id",
            name="uq_case_events",
        ),
        Index("ix_case_events_event", "event_id"),
    )


class CaseNote(Base, IntegerPrimaryKeyMixin, SoftDeleteMixin):
    __tablename__ = "case_notes"

    case_id: Mapped[int] = mapped_column(
        ForeignKey("fraud_cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    staff_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("staff_users.id", ondelete="SET NULL"),
    )
    note: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_case_notes_case_time",
            "case_id",
            "created_at",
        ),
    )


class FraudLabel(Base, IntegerPrimaryKeyMixin):
    __tablename__ = "fraud_labels"

    case_id: Mapped[int | None] = mapped_column(
        ForeignKey("fraud_cases.id", ondelete="CASCADE"),
    )
    event_id: Mapped[int | None] = mapped_column(
        ForeignKey("fraud_events.id", ondelete="CASCADE"),
    )
    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"),
    )
    label: Mapped[LabelValue] = mapped_column(
        enum_type(LabelValue, "fraud_label_value"),
        nullable=False,
    )
    source: Mapped[LabelSource] = mapped_column(
        enum_type(LabelSource, "fraud_label_source"),
        nullable=False,
    )
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    reason: Mapped[str | None] = mapped_column(Text)
    labelled_by_staff_id: Mapped[int | None] = mapped_column(
        ForeignKey("staff_users.id", ondelete="SET NULL"),
    )
    labelled_by_customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "case_id IS NOT NULL "
            "OR event_id IS NOT NULL "
            "OR transaction_id IS NOT NULL",
            name="ck_fraud_labels_subject",
        ),
        CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 1",
            name="ck_fraud_labels_confidence",
        ),
        Index("ix_labels_transaction", "transaction_id"),
        Index("ix_labels_event", "event_id"),
        Index(
            "ix_labels_value_time",
            "label",
            "created_at",
        ),
    )