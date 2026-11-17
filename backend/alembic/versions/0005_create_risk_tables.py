"""create risk tables

Fraud rules and their versions, ML model versions, model monitoring snapshots
and the watchlist (mule accounts, scam phone numbers, bad devices...).

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# --- Postgres enum types -------------------------------------------------
fraud_rule_status = postgresql.ENUM(
    "draft", "active", "disabled", "retired", name="fraud_rule_status", create_type=False
)
model_status = postgresql.ENUM(
    "candidate", "shadow", "active", "retired", "failed", name="model_status", create_type=False
)
watchlist_entity_type = postgresql.ENUM(
    "account", "phone", "email", "device", "ip_address", "merchant",
    name="watchlist_entity_type",
    create_type=False,
)

ALL_ENUMS = (fraud_rule_status, model_status, watchlist_entity_type)

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


def timestamp_columns() -> list[sa.Column]:
    return [
        created_at_column(),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    ]


def jsonb(name: str) -> sa.Column:
    return sa.Column(name, postgresql.JSONB(), nullable=False, server_default=EMPTY_JSON)


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

    # --- fraud_rules --------------------------------------------------------
    op.create_table(
        "fraud_rules",
        id_column(),
        sa.Column("rule_key", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", fraud_rule_status, nullable=False, server_default="draft"),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        staff_fk("created_by_staff_id"),
        *timestamp_columns(),
        sa.CheckConstraint("current_version >= 1", name="ck_rules_version"),
    )
    op.create_index("ix_rules_status_priority", "fraud_rules", ["status", "priority"])

    # --- fraud_rule_versions (immutable history of every rule edit) ---------
    op.create_table(
        "fraud_rule_versions",
        id_column(),
        sa.Column(
            "rule_id",
            sa.BigInteger(),
            sa.ForeignKey("fraud_rules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("yaml_definition", sa.Text(), nullable=False),
        jsonb("compiled_definition"),
        sa.Column("change_reason", sa.Text()),
        jsonb("backtest_results"),
        staff_fk("created_by_staff_id"),
        created_at_column(),
        sa.CheckConstraint("version >= 1", name="ck_rule_versions_positive"),
        sa.UniqueConstraint("rule_id", "version", name="uq_rule_versions"),
    )

    # --- model_versions -----------------------------------------------------
    op.create_table(
        "model_versions",
        id_column(),
        sa.Column("model_name", sa.String(150), nullable=False),
        sa.Column("version", sa.String(100), nullable=False),
        sa.Column("detector_name", sa.String(100), nullable=False),
        sa.Column("status", model_status, nullable=False, server_default="candidate"),
        sa.Column("artifact_uri", sa.Text(), nullable=False),
        sa.Column("training_dataset_reference", sa.Text()),
        jsonb("feature_schema"),
        jsonb("metrics"),
        jsonb("parameters"),
        staff_fk("promoted_by_staff_id"),
        # datetime columns last
        sa.Column("trained_at", sa.DateTime(timezone=True)),
        sa.Column("promoted_at", sa.DateTime(timezone=True)),
        sa.Column("retired_at", sa.DateTime(timezone=True)),
        *timestamp_columns(),
        sa.UniqueConstraint("model_name", "version", name="uq_model_name_version"),
    )
    op.create_index("ix_models_detector_status", "model_versions", ["detector_name", "status"])
    # Only ONE active version per model name (others can be shadow / retired).
    op.create_index(
        "uq_models_active_name",
        "model_versions",
        ["model_name"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    # --- model_monitoring_snapshots (drift monitoring) ----------------------
    op.create_table(
        "model_monitoring_snapshots",
        id_column(),
        sa.Column(
            "model_version_id",
            sa.BigInteger(),
            sa.ForeignKey("model_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        jsonb("metrics"),
        sa.Column("drift_detected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        jsonb("drift_details"),
        # datetime columns last
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_ended_at", sa.DateTime(timezone=True), nullable=False),
        created_at_column(),
        sa.CheckConstraint("window_ended_at > window_started_at", name="ck_monitoring_window"),
        sa.CheckConstraint("sample_count >= 0", name="ck_monitoring_samples"),
    )
    op.create_index(
        "ix_monitoring_model_window",
        "model_monitoring_snapshots",
        ["model_version_id", "window_ended_at"],
    )

    # --- watchlist_entries (mule list, scam numbers, bad devices) -----------
    op.create_table(
        "watchlist_entries",
        id_column(),
        sa.Column("entity_type", watchlist_entity_type, nullable=False),
        # Stored as a hash, so the raw account number / phone is never kept here.
        sa.Column("normalized_value_hash", sa.String(128), nullable=False),
        sa.Column("display_value_masked", sa.String(255)),
        sa.Column("risk_level", sa.String(20), nullable=False, server_default="high"),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("source", sa.String(150), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        staff_fk("created_by_staff_id"),
        # datetime columns last
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        *timestamp_columns(),
        sa.UniqueConstraint(
            "entity_type", "normalized_value_hash", name="uq_watchlist_entity_hash"
        ),
    )
    op.create_index(
        "ix_watchlist_lookup",
        "watchlist_entries",
        ["entity_type", "normalized_value_hash", "active"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("watchlist_entries")
    op.drop_table("model_monitoring_snapshots")
    op.drop_table("model_versions")
    op.drop_table("fraud_rule_versions")
    op.drop_table("fraud_rules")

    bind = op.get_bind()
    for enum in reversed(ALL_ENUMS):
        enum.drop(bind, checkfirst=True)
