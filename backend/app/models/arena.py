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
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    Base,
    EMPTY_JSON,
    IntegerPrimaryKeyMixin,
    enum_type,
)
from app.models.enums import DecisionAction


class ArenaAttempt(Base, IntegerPrimaryKeyMixin):
    __tablename__ = "arena_attempts"

    attacker_customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    victim_customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"),
        unique=True,
    )
    attempted_amount: Mapped[Decimal] = mapped_column(
        Numeric(19, 2),
        nullable=False,
    )
    amount_moved: Mapped[Decimal] = mapped_column(
        Numeric(19, 2),
        nullable=False,
        server_default="0",
    )
    detected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    decision_action: Mapped[DecisionAction] = mapped_column(
        enum_type(DecisionAction, "arena_decision_action"),
        nullable=False,
    )
    risk_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )
    attack_notes: Mapped[str | None] = mapped_column(Text)
    learning_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=EMPTY_JSON,
    )
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "attacker_customer_id <> victim_customer_id",
            name="ck_arena_different_players",
        ),
        CheckConstraint(
            "attempted_amount > 0",
            name="ck_arena_attempted_amount",
        ),
        CheckConstraint(
            "amount_moved BETWEEN 0 AND attempted_amount",
            name="ck_arena_amount_moved",
        ),
        CheckConstraint(
            "risk_score BETWEEN 0 AND 100",
            name="ck_arena_risk_score",
        ),
        Index(
            "ix_arena_attacker_time",
            "attacker_customer_id",
            "attempted_at",
        ),
        Index(
            "ix_arena_detected_time",
            "detected",
            "attempted_at",
        ),
    )