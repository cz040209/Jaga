"""create case tables

Fraud cases (HOLD/BLOCK investigations), the events linked to each case,
analyst notes, and fraud labels used as training data.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# --- Postgres enum types -------------------------------------------------
LABEL_VALUES = ("fraud", "not_fraud", "suspicious", "inconclusive")

case_status = postgresql.ENUM(
    "open", "investigating", "awaiting_customer", "resolved", "closed",
    name="case_status",
    create_type=False,
)
case_priority = postgresql.ENUM(
    "low", "medium", "high", "critical", name="case_priority", create_type=False
)
# Same values (LabelValue), but your models give each column its own Postgres type.
case_resolution_label = postgresql.ENUM(
    *LABEL_VALUES, name="case_resolution_label", create_type=False
)
fraud_label_value = postgresql.ENUM(*LABEL_VALUES, name="fraud_label_value", create_type=False)
fraud_label_source = postgresql.ENUM(
    "analyst", "customer", "arena", "system", "model",
    name="fraud_label_source",
    create_type=False,
)

ALL_ENUMS = (
    case_status,
    case_priority,
    case_resolution_label,
    fraud_label_value,
    fraud_label_source,
)

EMPTY_JSON = sa.text("'{}'::jsonb")


def id_column() -> sa.Column:
    return sa.Column(
        "id",
        sa.BigInteger(),
        sa.Identity(start=1, increment=1),
        primary_key=True,
    )


def created_at_column() -> sa.Column:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )


def staff_fk(name: str) -> sa.Column:
    return sa.Column(
        name,
        sa.BigInteger(),
        sa.ForeignKey("staff_users.id", ondelete="SET NULL"),
    )


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    for enum in ALL_ENUMS:
        enum.create(bind, checkfirst=True)

    # --- fraud_cases --------------------------------------------------------
    op.create_table(
        "fraud_cases",
        id_column(),
        sa.Column("case_number", sa.String(40), nullable=False, unique=True),
        sa.Column(
            "primary_customer_id",
            sa.BigInteger(),
            sa.ForeignKey("customers.id", ondelete="SET NULL"),
        ),
        staff_fk("assigned_to_staff_id"),
        sa.Column("status", case_status, nullable=False, server_default="open"),
        sa.Column("priority", case_priority, nullable=False, server_default="medium"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("ai_summary", sa.Text()),
        sa.Column("ai_recommended_action", sa.Text()),
        sa.Column("ai_evidence", postgresql.JSONB(), nullable=False, server_default=EMPTY_JSON),
        sa.Column("resolution", sa.Text()),
        sa.Column("resolved_label", case_resolution_label),
        staff_fk("resolved_by_staff_id"),
        # datetime columns last
        sa.Column("ai_generated_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        created_at_column(),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_cases_status_priority", "fraud_cases", ["status", "priority"])
    op.create_index("ix_cases_assignee_status", "fraud_cases", ["assigned_to_staff_id", "status"])
    op.create_index(
        "ix_cases_customer_time", "fraud_cases", ["primary_customer_id", "created_at"]
    )

    # --- case_events (links a case to the fraud events that caused it) ------
    op.create_table(
        "case_events",
        id_column(),
        sa.Column(
            "case_id",
            sa.BigInteger(),
            sa.ForeignKey("fraud_cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "event_id",
            sa.BigInteger(),
            sa.ForeignKey("fraud_events.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("link_reason", sa.String(255)),
        # datetime columns last
        sa.Column(
            "linked_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("case_id", "event_id", name="uq_case_events"),
    )
    op.create_index("ix_case_events_event", "case_events", ["event_id"])

    # --- case_notes ---------------------------------------------------------
    op.create_table(
        "case_notes",
        id_column(),
        sa.Column(
            "case_id",
            sa.BigInteger(),
            sa.ForeignKey("fraud_cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        staff_fk("staff_user_id"),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("is_internal", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        created_at_column(),
    )
    op.create_index("ix_case_notes_case_time", "case_notes", ["case_id", "created_at"])

    # --- fraud_labels (training data for the ML models) ---------------------
    op.create_table(
        "fraud_labels",
        id_column(),
        sa.Column(
            "case_id",
            sa.BigInteger(),
            sa.ForeignKey("fraud_cases.id", ondelete="CASCADE"),
        ),
        sa.Column(
            "event_id",
            sa.BigInteger(),
            sa.ForeignKey("fraud_events.id", ondelete="CASCADE"),
        ),
        sa.Column(
            "transaction_id",
            sa.BigInteger(),
            sa.ForeignKey("transactions.id", ondelete="CASCADE"),
        ),
        sa.Column("label", fraud_label_value, nullable=False),
        sa.Column("source", fraud_label_source, nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4)),
        sa.Column("reason", sa.Text()),
        staff_fk("labelled_by_staff_id"),
        sa.Column(
            "labelled_by_customer_id",
            sa.BigInteger(),
            sa.ForeignKey("customers.id", ondelete="SET NULL"),
        ),
        created_at_column(),
        # A label must be about something: a case, an event or a transaction.
        sa.CheckConstraint(
            "case_id IS NOT NULL OR event_id IS NOT NULL OR transaction_id IS NOT NULL",
            name="ck_fraud_labels_subject",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 1",
            name="ck_fraud_labels_confidence",
        ),
    )
    op.create_index("ix_labels_transaction", "fraud_labels", ["transaction_id"])
    op.create_index("ix_labels_event", "fraud_labels", ["event_id"])
    op.create_index("ix_labels_value_time", "fraud_labels", ["label", "created_at"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("fraud_labels")
    op.drop_table("case_notes")
    op.drop_table("case_events")
    op.drop_table("fraud_cases")

    bind = op.get_bind()
    for enum in reversed(ALL_ENUMS):
        enum.drop(bind, checkfirst=True)
