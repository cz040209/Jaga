"""add soft delete

Adds deleted_at to the master-data tables that staff or customers can delete:
devices, staff_users, merchants, merchant_qr_codes, fraud_rules, case_notes,
watchlist_entries, scam_knowledge_chunks.

Deleting sets deleted_at instead of removing the row, so history and audit
survive. Unique rules on these tables now apply to live rows only (partial
unique indexes WHERE deleted_at IS NULL), so a deleted record never blocks
creating the same thing again.

Not changed on purpose:
- Append-only history is never deleted (ledger_entries, transactions,
  login_events, fraud_events, decisions, audit_logs, ...).
- Tables that already have a soft-delete field: payees.deleted_at,
  customers / bank_accounts (status 'closed' + closed_at), sessions (revoked_at),
  model_versions (retired_at), fraud_cases (status).

Convention: deleted_at is the LAST column of every table that has it.
ADD COLUMN always appends, so the new columns land after created_at/updated_at.
payees.deleted_at (created in 0002) sat before created_at/updated_at; Postgres
can't move a column, so it is rebuilt at the end with its values copied over.

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: Union[str, Sequence[str], None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SOFT_DELETE_TABLES = (
    "devices",
    "staff_users",
    "merchants",
    "merchant_qr_codes",
    "fraud_rules",
    "case_notes",
    "watchlist_entries",
    "scam_knowledge_chunks",
)

NOT_DELETED = sa.text("deleted_at IS NULL")


def _move_payees_deleted_at_to_end() -> None:
    """Rebuild payees.deleted_at as the last column, keeping every value."""
    op.add_column("payees", sa.Column("deleted_at_new", sa.DateTime(timezone=True)))
    op.execute("UPDATE payees SET deleted_at_new = deleted_at")
    # The partial unique index depends on the old column, so drop it first.
    op.drop_index("uq_payees_active_customer_target", table_name="payees")
    op.drop_column("payees", "deleted_at")
    op.alter_column("payees", "deleted_at_new", new_column_name="deleted_at")
    op.create_index(
        "uq_payees_active_customer_target",
        "payees",
        ["customer_id", "target_account_id"],
        unique=True,
        postgresql_where=NOT_DELETED,
    )


def upgrade() -> None:
    """Upgrade schema."""
    _move_payees_deleted_at_to_end()

    for table in SOFT_DELETE_TABLES:
        op.add_column(table, sa.Column("deleted_at", sa.DateTime(timezone=True)))

    # --- Unique indexes become "unique among live rows" ----------------------
    op.drop_index("uq_devices_customer_fingerprint", table_name="devices")
    op.create_index(
        "uq_devices_customer_fingerprint",
        "devices",
        ["customer_id", "fingerprint_hash"],
        unique=True,
        postgresql_where=NOT_DELETED,
    )

    op.drop_index("uq_staff_email_lower", table_name="staff_users")
    op.create_index(
        "uq_staff_email_lower",
        "staff_users",
        [sa.text("lower(email)")],
        unique=True,
        postgresql_where=NOT_DELETED,
    )

    # --- Unique constraints become partial unique indexes -------------------
    op.drop_constraint("merchants_registration_number_key", "merchants", type_="unique")
    op.create_index(
        "uq_merchants_registration_number",
        "merchants",
        ["registration_number"],
        unique=True,
        postgresql_where=NOT_DELETED,
    )

    op.drop_constraint("fraud_rules_rule_key_key", "fraud_rules", type_="unique")
    op.create_index(
        "uq_rules_rule_key",
        "fraud_rules",
        ["rule_key"],
        unique=True,
        postgresql_where=NOT_DELETED,
    )

    op.drop_constraint("uq_watchlist_entity_hash", "watchlist_entries", type_="unique")
    op.create_index(
        "uq_watchlist_entity_hash",
        "watchlist_entries",
        ["entity_type", "normalized_value_hash"],
        unique=True,
        postgresql_where=NOT_DELETED,
    )

    op.drop_constraint(
        "uq_knowledge_source_version_chunk", "scam_knowledge_chunks", type_="unique"
    )
    op.create_index(
        "uq_knowledge_source_version_chunk",
        "scam_knowledge_chunks",
        ["source_name", "document_version", "chunk_number"],
        unique=True,
        postgresql_where=NOT_DELETED,
    )


def downgrade() -> None:
    """Downgrade schema.

    Fails if a deleted row and a live row share a value that must be unique
    (e.g. a forgotten device that logged in again). That's correct: going back
    would break the old, stricter rule.
    """
    op.drop_index("uq_knowledge_source_version_chunk", table_name="scam_knowledge_chunks")
    op.create_unique_constraint(
        "uq_knowledge_source_version_chunk",
        "scam_knowledge_chunks",
        ["source_name", "document_version", "chunk_number"],
    )

    op.drop_index("uq_watchlist_entity_hash", table_name="watchlist_entries")
    op.create_unique_constraint(
        "uq_watchlist_entity_hash",
        "watchlist_entries",
        ["entity_type", "normalized_value_hash"],
    )

    op.drop_index("uq_rules_rule_key", table_name="fraud_rules")
    op.create_unique_constraint("fraud_rules_rule_key_key", "fraud_rules", ["rule_key"])

    op.drop_index("uq_merchants_registration_number", table_name="merchants")
    op.create_unique_constraint(
        "merchants_registration_number_key", "merchants", ["registration_number"]
    )

    op.drop_index("uq_staff_email_lower", table_name="staff_users")
    op.create_index(
        "uq_staff_email_lower", "staff_users", [sa.text("lower(email)")], unique=True
    )

    op.drop_index("uq_devices_customer_fingerprint", table_name="devices")
    op.create_index(
        "uq_devices_customer_fingerprint",
        "devices",
        ["customer_id", "fingerprint_hash"],
        unique=True,
    )

    for table in reversed(SOFT_DELETE_TABLES):
        op.drop_column(table, "deleted_at")

    # payees.deleted_at existed before this migration, so it is kept (now as the
    # last column). Column order has no effect on how the app behaves.
