"""create fraud tables

Fraud events (every scored customer action), decisions (final score + action)
and per-detector results. Together they form the audit trail for every decision.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# --- Postgres enum types -------------------------------------------------
fraud_event_type = postgresql.ENUM(
    "registration", "login", "login_failed", "password_changed", "device_added",
    "payee_added", "payee_changed", "transfer", "merchant_payment", "qr_payment",
    "account_frozen", "account_unfrozen", "scam_check",
    name="fraud_event_type",
    create_type=False,
)
fraud_event_channel = postgresql.ENUM(
    "web", "pwa", "telegram", "api", "system", name="fraud_event_channel", create_type=False
)
fraud_scoring_status = postgresql.ENUM(
    "pending", "processing", "completed", "failed",
    name="fraud_scoring_status",
    create_type=False,
)
decision_action = postgresql.ENUM(
    "approve", "step_up", "hold", "block", name="decision_action", create_type=False
)

ALL_ENUMS = (fraud_event_type, fraud_event_channel, fraud_scoring_status, decision_action)

EMPTY_JSON = sa.text("'{}'::jsonb")
EMPTY_JSON_LIST = sa.text("'[]'::jsonb")


def id_column() -> sa.Column:
    return sa.Column(
        "id",
        sa.BigInteger(),
        sa.Identity(start=1, increment=1),
        primary_key=True,
    )


def jsonb(name: str, default: sa.TextClause = EMPTY_JSON) -> sa.Column:
    return sa.Column(name, postgresql.JSONB(), nullable=False, server_default=default)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    for enum in ALL_ENUMS:
        enum.create(bind, checkfirst=True)

    # --- fraud_events -----------------------------------------------------
    op.create_table(
        "fraud_events",
        id_column(),
        sa.Column("event_type", fraud_event_type, nullable=False),
        sa.Column(
            "customer_id",
            sa.BigInteger(),
            sa.ForeignKey("customers.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "device_id",
            sa.BigInteger(),
            sa.ForeignKey("devices.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "session_id",
            sa.BigInteger(),
            sa.ForeignKey("customer_sessions.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "transaction_id",
            sa.BigInteger(),
            sa.ForeignKey("transactions.id", ondelete="SET NULL"),
        ),
        sa.Column("channel", fraud_event_channel, nullable=False),
        sa.Column("scoring_status", fraud_scoring_status, nullable=False, server_default="pending"),
        sa.Column("ip_address", postgresql.INET()),
        sa.Column("country_code", sa.String(2)),
        sa.Column("city", sa.String(120)),
        sa.Column("latitude", sa.Numeric(9, 6)),
        sa.Column("longitude", sa.Numeric(9, 6)),
        jsonb("behavioural_signals"),
        jsonb("event_payload"),
        sa.Column("scoring_error", sa.Text()),
        # datetime columns last
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("scored_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_fraud_events_customer_time", "fraud_events", ["customer_id", "occurred_at"])
    op.create_index("ix_fraud_events_transaction", "fraud_events", ["transaction_id"])
    op.create_index("ix_fraud_events_type_time", "fraud_events", ["event_type", "occurred_at"])
    # The scoring worker looks up "pending" events oldest-first with this index.
    op.create_index("ix_fraud_events_scoring", "fraud_events", ["scoring_status", "ingested_at"])

    # --- decisions --------------------------------------------------------
    op.create_table(
        "decisions",
        id_column(),
        sa.Column(
            "event_id",
            sa.BigInteger(),
            sa.ForeignKey("fraud_events.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,  # one decision per event
        ),
        sa.Column(
            "transaction_id",
            sa.BigInteger(),
            sa.ForeignKey("transactions.id", ondelete="SET NULL"),
        ),
        sa.Column("final_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("action", decision_action, nullable=False),
        jsonb("threshold_snapshot"),
        jsonb("feature_snapshot"),
        jsonb("top_reasons", EMPTY_JSON_LIST),
        sa.Column("customer_reason_code", sa.String(100)),
        sa.Column("customer_explanation", sa.Text()),
        jsonb("model_versions"),
        jsonb("rule_versions"),
        sa.Column("latency_ms", sa.Numeric(10, 3), nullable=False),
        # datetime columns last
        sa.Column(
            "decided_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("final_score BETWEEN 0 AND 100", name="ck_decisions_score_range"),
        sa.CheckConstraint("latency_ms >= 0", name="ck_decisions_latency"),
    )
    op.create_index("ix_decisions_action_time", "decisions", ["action", "decided_at"])
    op.create_index("ix_decisions_score_time", "decisions", ["final_score", "decided_at"])
    op.create_index("ix_decisions_transaction", "decisions", ["transaction_id"])

    # --- detector_results -------------------------------------------------
    op.create_table(
        "detector_results",
        id_column(),
        sa.Column(
            "decision_id",
            sa.BigInteger(),
            sa.ForeignKey("decisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("detector_name", sa.String(100), nullable=False),
        sa.Column("detector_version", sa.String(100), nullable=False),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column("weight", sa.Numeric(8, 6)),
        jsonb("reasons", EMPTY_JSON_LIST),
        jsonb("feature_contributions"),
        sa.Column("latency_ms", sa.Numeric(10, 3), nullable=False),
        # datetime columns last
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("score BETWEEN 0 AND 100", name="ck_detector_score"),
        sa.CheckConstraint("weight IS NULL OR weight >= 0", name="ck_detector_weight"),
        sa.CheckConstraint("latency_ms >= 0", name="ck_detector_latency"),
        sa.UniqueConstraint("decision_id", "detector_name", name="uq_detector_decision_name"),
    )
    op.create_index("ix_detector_name_time", "detector_results", ["detector_name", "created_at"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("detector_results")
    op.drop_table("decisions")
    op.drop_table("fraud_events")

    bind = op.get_bind()
    for enum in reversed(ALL_ENUMS):
        enum.drop(bind, checkfirst=True)
