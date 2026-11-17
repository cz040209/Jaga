from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    Base,
    EMPTY_JSON,
    EMPTY_JSON_LIST,
    IntegerPrimaryKeyMixin,
    enum_type,
)
from app.models.enums import (
    Channel,
    DecisionAction,
    EventType,
    ScoringStatus,
)


class FraudEvent(Base, IntegerPrimaryKeyMixin):
    __tablename__ = "fraud_events"

    event_type: Mapped[EventType] = mapped_column(
        enum_type(EventType, "fraud_event_type"),
        nullable=False,
    )
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"),
    )
    device_id: Mapped[int | None] = mapped_column(
        ForeignKey("devices.id", ondelete="SET NULL"),
    )
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("customer_sessions.id", ondelete="SET NULL"),
    )
    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"),
    )
    channel: Mapped[Channel] = mapped_column(
        enum_type(Channel, "fraud_event_channel"),
        nullable=False,
    )
    scoring_status: Mapped[ScoringStatus] = mapped_column(
        enum_type(ScoringStatus, "fraud_scoring_status"),
        nullable=False,
        server_default=ScoringStatus.PENDING.value,
    )
    ip_address: Mapped[Any | None] = mapped_column(INET)
    country_code: Mapped[str | None] = mapped_column(String(2))
    city: Mapped[str | None] = mapped_column(String(120))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    behavioural_signals: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=EMPTY_JSON,
    )
    event_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=EMPTY_JSON,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    scored_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    scoring_error: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index(
            "ix_fraud_events_customer_time",
            "customer_id",
            "occurred_at",
        ),
        Index("ix_fraud_events_transaction", "transaction_id"),
        Index(
            "ix_fraud_events_type_time",
            "event_type",
            "occurred_at",
        ),
        Index(
            "ix_fraud_events_scoring",
            "scoring_status",
            "ingested_at",
        ),
    )


class Decision(Base, IntegerPrimaryKeyMixin):
    __tablename__ = "decisions"

    event_id: Mapped[int] = mapped_column(
        ForeignKey("fraud_events.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"),
    )
    final_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )
    action: Mapped[DecisionAction] = mapped_column(
        enum_type(DecisionAction, "decision_action"),
        nullable=False,
    )
    threshold_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=EMPTY_JSON,
    )
    feature_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=EMPTY_JSON,
    )
    top_reasons: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=EMPTY_JSON_LIST,
    )
    customer_reason_code: Mapped[str | None] = mapped_column(String(100))
    customer_explanation: Mapped[str | None] = mapped_column(Text)
    model_versions: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=EMPTY_JSON,
    )
    rule_versions: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=EMPTY_JSON,
    )
    latency_ms: Mapped[Decimal] = mapped_column(
        Numeric(10, 3),
        nullable=False,
    )
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "final_score BETWEEN 0 AND 100",
            name="ck_decisions_score_range",
        ),
        CheckConstraint(
            "latency_ms >= 0",
            name="ck_decisions_latency",
        ),
        Index(
            "ix_decisions_action_time",
            "action",
            "decided_at",
        ),
        Index(
            "ix_decisions_score_time",
            "final_score",
            "decided_at",
        ),
        Index("ix_decisions_transaction", "transaction_id"),
    )


class DetectorResult(Base, IntegerPrimaryKeyMixin):
    __tablename__ = "detector_results"

    decision_id: Mapped[int] = mapped_column(
        ForeignKey("decisions.id", ondelete="CASCADE"),
        nullable=False,
    )
    detector_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    detector_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )
    weight: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    reasons: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=EMPTY_JSON_LIST,
    )
    feature_contributions: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=EMPTY_JSON,
    )
    latency_ms: Mapped[Decimal] = mapped_column(
        Numeric(10, 3),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "score BETWEEN 0 AND 100",
            name="ck_detector_score",
        ),
        CheckConstraint(
            "weight IS NULL OR weight >= 0",
            name="ck_detector_weight",
        ),
        CheckConstraint(
            "latency_ms >= 0",
            name="ck_detector_latency",
        ),
        UniqueConstraint(
            "decision_id",
            "detector_name",
            name="uq_detector_decision_name",
        ),
        Index(
            "ix_detector_name_time",
            "detector_name",
            "created_at",
        ),
    )