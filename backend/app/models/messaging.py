from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
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
    EMPTY_JSON_LIST,
    IntegerPrimaryKeyMixin,
    TimestampMixin,
    enum_type,
)
from app.models.enums import (
    ChallengeStatus,
    ChallengeType,
    DeliveryStatus,
    NotificationChannel,
    ScamCheckInputType,
    ScamCheckStatus,
)


class CustomerChallenge(
    Base,
    IntegerPrimaryKeyMixin,
    TimestampMixin,
):
    __tablename__ = "customer_challenges"

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"),
    )
    challenge_type: Mapped[ChallengeType] = mapped_column(
        enum_type(ChallengeType, "challenge_type"),
        nullable=False,
    )
    status: Mapped[ChallengeStatus] = mapped_column(
        enum_type(ChallengeStatus, "challenge_status"),
        nullable=False,
        server_default=ChallengeStatus.PENDING.value,
    )
    secret_hash: Mapped[str | None] = mapped_column(String(128))
    questions: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=EMPTY_JSON_LIST,
    )
    answers: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=EMPTY_JSON,
    )
    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    maximum_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="3",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    __table_args__ = (
        CheckConstraint(
            "attempts >= 0",
            name="ck_challenges_attempts",
        ),
        CheckConstraint(
            "maximum_attempts > 0",
            name="ck_challenges_max_attempts",
        ),
        Index(
            "ix_challenges_customer_status",
            "customer_id",
            "status",
        ),
        Index("ix_challenges_transaction", "transaction_id"),
        Index("ix_challenges_expires", "expires_at"),
    )


class Notification(Base, IntegerPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "notifications"

    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
    )
    staff_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("staff_users.id", ondelete="CASCADE"),
    )
    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"),
    )
    case_id: Mapped[int | None] = mapped_column(
        ForeignKey("fraud_cases.id", ondelete="SET NULL"),
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        enum_type(NotificationChannel, "notification_channel"),
        nullable=False,
    )
    status: Mapped[DeliveryStatus] = mapped_column(
        enum_type(
            DeliveryStatus,
            "notification_delivery_status",
        ),
        nullable=False,
        server_default=DeliveryStatus.PENDING.value,
    )
    template_key: Mapped[str | None] = mapped_column(String(100))
    subject: Mapped[str | None] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        server_default="en",
    )
    action_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=EMPTY_JSON,
    )
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    failure_reason: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            """
            (customer_id IS NOT NULL AND staff_user_id IS NULL)
            OR (customer_id IS NULL AND staff_user_id IS NOT NULL)
            """,
            name="ck_notifications_one_recipient",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="ck_notifications_attempts",
        ),
        Index(
            "ix_notifications_customer_status",
            "customer_id",
            "status",
        ),
        Index(
            "ix_notifications_staff_status",
            "staff_user_id",
            "status",
        ),
        Index(
            "ix_notifications_retry",
            "status",
            "next_attempt_at",
        ),
    )


class ScamCheck(Base, IntegerPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "scam_checks"

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    input_type: Mapped[ScamCheckInputType] = mapped_column(
        enum_type(
            ScamCheckInputType,
            "scam_check_input_type",
        ),
        nullable=False,
    )
    status: Mapped[ScamCheckStatus] = mapped_column(
        enum_type(ScamCheckStatus, "scam_check_status"),
        nullable=False,
        server_default=ScamCheckStatus.PENDING.value,
    )
    input_text: Mapped[str | None] = mapped_column(Text)
    image_storage_key: Mapped[str | None] = mapped_column(Text)
    scam_probability: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4)
    )
    verdict: Mapped[str | None] = mapped_column(String(100))
    explanation: Mapped[str | None] = mapped_column(Text)
    indicators: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=EMPTY_JSON_LIST,
    )
    llm_provider: Mapped[str | None] = mapped_column(String(100))
    llm_model: Mapped[str | None] = mapped_column(String(150))
    used_fallback: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    __table_args__ = (
        CheckConstraint(
            """
            (input_type = 'text' AND input_text IS NOT NULL)
            OR (input_type = 'image' AND image_storage_key IS NOT NULL)
            """,
            name="ck_scam_checks_input",
        ),
        CheckConstraint(
            "scam_probability IS NULL "
            "OR scam_probability BETWEEN 0 AND 1",
            name="ck_scam_checks_probability",
        ),
        Index(
            "ix_scam_checks_customer_time",
            "customer_id",
            "created_at",
        ),
    )


class ScamKnowledgeChunk(
    Base,
    IntegerPrimaryKeyMixin,
    TimestampMixin,
):
    __tablename__ = "scam_knowledge_chunks"

    source_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    source_uri: Mapped[str | None] = mapped_column(Text)
    document_version: Mapped[str | None] = mapped_column(String(100))
    chunk_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        server_default="en",
    )
    embedding: Mapped[Any | None] = mapped_column(Vector())
    knowledge_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=EMPTY_JSON,
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )

    __table_args__ = (
        CheckConstraint(
            "chunk_number >= 0",
            name="ck_knowledge_chunk_number",
        ),
        UniqueConstraint(
            "source_name",
            "document_version",
            "chunk_number",
            name="uq_knowledge_source_version_chunk",
        ),
        Index(
            "ix_knowledge_language_active",
            "language",
            "active",
        ),
        Index("ix_knowledge_content_hash", "content_hash"),
    )