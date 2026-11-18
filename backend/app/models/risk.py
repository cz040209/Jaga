from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
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
    NOT_DELETED,
    IntegerPrimaryKeyMixin,
    SoftDeleteMixin,
    TimestampMixin,
    enum_type,
)
from app.models.enums import (
    ModelStatus,
    RuleStatus,
    WatchlistEntityType,
)


class FraudRule(Base, IntegerPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "fraud_rules"

    rule_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[RuleStatus] = mapped_column(
        enum_type(RuleStatus, "fraud_rule_status"),
        nullable=False,
        server_default=RuleStatus.DRAFT.value,
    )
    current_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="1",
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="100",
    )
    created_by_staff_id: Mapped[int | None] = mapped_column(
        ForeignKey("staff_users.id", ondelete="SET NULL"),
    )

    __table_args__ = (
        CheckConstraint(
            "current_version >= 1",
            name="ck_rules_version",
        ),
        Index("ix_rules_status_priority", "status", "priority"),
        Index(
            "uq_rules_rule_key",
            "rule_key",
            unique=True,
            postgresql_where=NOT_DELETED,
        ),
    )


class FraudRuleVersion(Base, IntegerPrimaryKeyMixin):
    __tablename__ = "fraud_rule_versions"

    rule_id: Mapped[int] = mapped_column(
        ForeignKey("fraud_rules.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    yaml_definition: Mapped[str] = mapped_column(Text, nullable=False)
    compiled_definition: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=EMPTY_JSON,
    )
    change_reason: Mapped[str | None] = mapped_column(Text)
    backtest_results: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=EMPTY_JSON,
    )
    created_by_staff_id: Mapped[int | None] = mapped_column(
        ForeignKey("staff_users.id", ondelete="SET NULL"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "version >= 1",
            name="ck_rule_versions_positive",
        ),
        UniqueConstraint(
            "rule_id",
            "version",
            name="uq_rule_versions",
        ),
    )


class ModelVersion(Base, IntegerPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "model_versions"

    model_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    detector_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    status: Mapped[ModelStatus] = mapped_column(
        enum_type(ModelStatus, "model_status"),
        nullable=False,
        server_default=ModelStatus.CANDIDATE.value,
    )
    artifact_uri: Mapped[str] = mapped_column(Text, nullable=False)
    training_dataset_reference: Mapped[str | None] = mapped_column(Text)
    feature_schema: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=EMPTY_JSON,
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=EMPTY_JSON,
    )
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=EMPTY_JSON,
    )
    trained_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    promoted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    retired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    promoted_by_staff_id: Mapped[int | None] = mapped_column(
        ForeignKey("staff_users.id", ondelete="SET NULL"),
    )

    __table_args__ = (
        UniqueConstraint(
            "model_name",
            "version",
            name="uq_model_name_version",
        ),
        Index(
            "ix_models_detector_status",
            "detector_name",
            "status",
        ),
        Index(
            "uq_models_active_name",
            "model_name",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )


class ModelMonitoringSnapshot(Base, IntegerPrimaryKeyMixin):
    __tablename__ = "model_monitoring_snapshots"

    model_version_id: Mapped[int] = mapped_column(
        ForeignKey("model_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    window_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    window_ended_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    sample_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=EMPTY_JSON,
    )
    drift_detected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    drift_details: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=EMPTY_JSON,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "window_ended_at > window_started_at",
            name="ck_monitoring_window",
        ),
        CheckConstraint(
            "sample_count >= 0",
            name="ck_monitoring_samples",
        ),
        Index(
            "ix_monitoring_model_window",
            "model_version_id",
            "window_ended_at",
        ),
    )


class WatchlistEntry(
    Base,
    IntegerPrimaryKeyMixin,
    TimestampMixin,
    SoftDeleteMixin,
):
    __tablename__ = "watchlist_entries"

    entity_type: Mapped[WatchlistEntityType] = mapped_column(
        enum_type(WatchlistEntityType, "watchlist_entity_type"),
        nullable=False,
    )
    normalized_value_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    display_value_masked: Mapped[str | None] = mapped_column(String(255))
    risk_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="high",
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(150), nullable=False)
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    created_by_staff_id: Mapped[int | None] = mapped_column(
        ForeignKey("staff_users.id", ondelete="SET NULL"),
    )

    __table_args__ = (
        Index(
            "uq_watchlist_entity_hash",
            "entity_type",
            "normalized_value_hash",
            unique=True,
            postgresql_where=NOT_DELETED,
        ),
        Index(
            "ix_watchlist_lookup",
            "entity_type",
            "normalized_value_hash",
            "active",
        ),
    )