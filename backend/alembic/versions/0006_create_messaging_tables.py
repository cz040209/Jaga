"""create messaging tables

Customer challenges (OTP / scam questionnaire), notifications for every
channel, scam message checks, and the scam knowledge base (pgvector).

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# --- Postgres enum types -------------------------------------------------
challenge_type = postgresql.ENUM(
    "otp", "scam_questionnaire", "transaction_confirmation",
    name="challenge_type",
    create_type=False,
)
challenge_status = postgresql.ENUM(
    "pending", "passed", "failed", "expired", "cancelled",
    name="challenge_status",
    create_type=False,
)
notification_channel = postgresql.ENUM(
    "in_app", "sms_inbox", "telegram", "web_push", "email", "slack", "discord",
    name="notification_channel",
    create_type=False,
)
notification_delivery_status = postgresql.ENUM(
    "pending", "sent", "delivered", "failed", "read",
    name="notification_delivery_status",
    create_type=False,
)
scam_check_input_type = postgresql.ENUM(
    "text", "image", name="scam_check_input_type", create_type=False
)
scam_check_status = postgresql.ENUM(
    "pending", "completed", "failed", "disabled", name="scam_check_status", create_type=False
)

ALL_ENUMS = (
    challenge_type,
    challenge_status,
    notification_channel,
    notification_delivery_status,
    scam_check_input_type,
    scam_check_status,
)

EMPTY_JSON = sa.text("'{}'::jsonb")
EMPTY_JSON_LIST = sa.text("'[]'::jsonb")


def id_column() -> sa.Column:
    return sa.Column(
        "id",
        sa.BigInteger(),
        sa.Identity(start=1, increment=1),
        primary_key=True,
    )


def timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    ]


def jsonb(name: str, default: sa.TextClause = EMPTY_JSON) -> sa.Column:
    return sa.Column(name, postgresql.JSONB(), nullable=False, server_default=default)


def upgrade() -> None:
    """Upgrade schema."""
    # pgvector: adds the VECTOR column type used for AI embeddings.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    bind = op.get_bind()
    for enum in ALL_ENUMS:
        enum.create(bind, checkfirst=True)

    # --- customer_challenges (OTP + interactive scam check) -----------------
    op.create_table(
        "customer_challenges",
        id_column(),
        sa.Column(
            "customer_id",
            sa.BigInteger(),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "transaction_id",
            sa.BigInteger(),
            sa.ForeignKey("transactions.id", ondelete="CASCADE"),
        ),
        sa.Column("challenge_type", challenge_type, nullable=False),
        sa.Column("status", challenge_status, nullable=False, server_default="pending"),
        # The OTP is stored hashed, like a password, never in plain text.
        sa.Column("secret_hash", sa.String(128)),
        jsonb("questions", EMPTY_JSON_LIST),
        jsonb("answers"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("maximum_attempts", sa.Integer(), nullable=False, server_default="3"),
        # datetime columns last
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        *timestamp_columns(),
        sa.CheckConstraint("attempts >= 0", name="ck_challenges_attempts"),
        sa.CheckConstraint("maximum_attempts > 0", name="ck_challenges_max_attempts"),
    )
    op.create_index(
        "ix_challenges_customer_status", "customer_challenges", ["customer_id", "status"]
    )
    op.create_index("ix_challenges_transaction", "customer_challenges", ["transaction_id"])
    op.create_index("ix_challenges_expires", "customer_challenges", ["expires_at"])

    # --- notifications (one row per message per channel) --------------------
    op.create_table(
        "notifications",
        id_column(),
        sa.Column(
            "customer_id",
            sa.BigInteger(),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
        ),
        sa.Column(
            "staff_user_id",
            sa.BigInteger(),
            sa.ForeignKey("staff_users.id", ondelete="CASCADE"),
        ),
        sa.Column(
            "transaction_id",
            sa.BigInteger(),
            sa.ForeignKey("transactions.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "case_id",
            sa.BigInteger(),
            sa.ForeignKey("fraud_cases.id", ondelete="SET NULL"),
        ),
        sa.Column("channel", notification_channel, nullable=False),
        sa.Column(
            "status", notification_delivery_status, nullable=False, server_default="pending"
        ),
        sa.Column("template_key", sa.String(100)),
        sa.Column("subject", sa.String(255)),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        jsonb("action_payload"),
        sa.Column("provider_message_id", sa.String(255)),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_reason", sa.Text()),
        # datetime columns last
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        *timestamp_columns(),
        # Exactly one recipient: a customer OR a staff user, never both / neither.
        sa.CheckConstraint(
            "(customer_id IS NOT NULL AND staff_user_id IS NULL) "
            "OR (customer_id IS NULL AND staff_user_id IS NOT NULL)",
            name="ck_notifications_one_recipient",
        ),
        sa.CheckConstraint("attempt_count >= 0", name="ck_notifications_attempts"),
    )
    op.create_index(
        "ix_notifications_customer_status", "notifications", ["customer_id", "status"]
    )
    op.create_index(
        "ix_notifications_staff_status", "notifications", ["staff_user_id", "status"]
    )
    # The retry worker finds "failed, retry after X" messages with this index.
    op.create_index("ix_notifications_retry", "notifications", ["status", "next_attempt_at"])

    # --- scam_checks (customer forwards a suspicious text / screenshot) -----
    op.create_table(
        "scam_checks",
        id_column(),
        sa.Column(
            "customer_id",
            sa.BigInteger(),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("input_type", scam_check_input_type, nullable=False),
        sa.Column("status", scam_check_status, nullable=False, server_default="pending"),
        sa.Column("input_text", sa.Text()),
        sa.Column("image_storage_key", sa.Text()),
        sa.Column("scam_probability", sa.Numeric(5, 4)),
        sa.Column("verdict", sa.String(100)),
        sa.Column("explanation", sa.Text()),
        jsonb("indicators", EMPTY_JSON_LIST),
        sa.Column("llm_provider", sa.String(100)),
        sa.Column("llm_model", sa.String(150)),
        # true = answered by the template fallback because no LLM key was set.
        sa.Column("used_fallback", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("error_message", sa.Text()),
        # datetime columns last
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        *timestamp_columns(),
        sa.CheckConstraint(
            "(input_type = 'text' AND input_text IS NOT NULL) "
            "OR (input_type = 'image' AND image_storage_key IS NOT NULL)",
            name="ck_scam_checks_input",
        ),
        sa.CheckConstraint(
            "scam_probability IS NULL OR scam_probability BETWEEN 0 AND 1",
            name="ck_scam_checks_probability",
        ),
    )
    op.create_index("ix_scam_checks_customer_time", "scam_checks", ["customer_id", "created_at"])

    # --- scam_knowledge_chunks (RAG knowledge base with embeddings) ---------
    op.create_table(
        "scam_knowledge_chunks",
        id_column(),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("source_uri", sa.Text()),
        sa.Column("document_version", sa.String(100)),
        sa.Column("chunk_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("embedding", Vector()),
        jsonb("metadata"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *timestamp_columns(),
        sa.CheckConstraint("chunk_number >= 0", name="ck_knowledge_chunk_number"),
        sa.UniqueConstraint(
            "source_name",
            "document_version",
            "chunk_number",
            name="uq_knowledge_source_version_chunk",
        ),
    )
    op.create_index(
        "ix_knowledge_language_active", "scam_knowledge_chunks", ["language", "active"]
    )
    op.create_index("ix_knowledge_content_hash", "scam_knowledge_chunks", ["content_hash"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("scam_knowledge_chunks")
    op.drop_table("scam_checks")
    op.drop_table("notifications")
    op.drop_table("customer_challenges")

    bind = op.get_bind()
    for enum in reversed(ALL_ENUMS):
        enum.drop(bind, checkfirst=True)

    op.execute("DROP EXTENSION IF EXISTS vector")
