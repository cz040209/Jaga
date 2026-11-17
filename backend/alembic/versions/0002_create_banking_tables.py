"""create banking tables

Bank accounts, merchants, merchant QR codes, payees, transactions and the
double-entry ledger.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# --- Postgres enum types -------------------------------------------------
account_type = postgresql.ENUM(
    "customer", "merchant", "system", name="account_type", create_type=False
)
account_status = postgresql.ENUM(
    "active", "frozen", "closed", name="account_status", create_type=False
)
payee_check_status = postgresql.ENUM(
    "pending", "clear", "watchlisted", "blocked", "error",
    name="payee_check_status",
    create_type=False,
)
transaction_type = postgresql.ENUM(
    "opening_balance", "transfer", "merchant_payment", "qr_payment", "reversal", "adjustment",
    name="transaction_type",
    create_type=False,
)
transaction_status = postgresql.ENUM(
    "pending", "step_up_required", "held", "posted", "blocked", "failed", "reversed", "cancelled",
    name="transaction_status",
    create_type=False,
)
transaction_channel = postgresql.ENUM(
    "web", "pwa", "telegram", "api", "system", name="transaction_channel", create_type=False
)
ledger_direction = postgresql.ENUM(
    "debit", "credit", name="ledger_direction", create_type=False
)

ALL_ENUMS = (
    account_type,
    account_status,
    payee_check_status,
    transaction_type,
    transaction_status,
    transaction_channel,
    ledger_direction,
)

EMPTY_JSON = sa.text("'{}'::jsonb")
EMPTY_JSON_LIST = sa.text("'[]'::jsonb")


# --- Reusable column helpers (mirror the mixins in app/models/base.py) ----
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


def money(name: str, **kwargs) -> sa.Column:
    """RM amount: 17 digits before the decimal point, 2 after. Never use float for money."""
    return sa.Column(name, sa.Numeric(19, 2), **kwargs)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    for enum in ALL_ENUMS:
        enum.create(bind, checkfirst=True)

    # --- bank_accounts ----------------------------------------------------
    op.create_table(
        "bank_accounts",
        id_column(),
        sa.Column(
            "customer_id",
            sa.BigInteger(),
            sa.ForeignKey("customers.id", ondelete="RESTRICT"),
        ),
        sa.Column("account_number", sa.String(32), nullable=False, unique=True),
        sa.Column("account_name", sa.String(200), nullable=False),
        sa.Column("account_type", account_type, nullable=False),
        sa.Column("status", account_status, nullable=False, server_default="active"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="MYR"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("freeze_reason", sa.Text()),
        # datetime columns last
        sa.Column("frozen_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        *timestamp_columns(),
        sa.CheckConstraint("currency = 'MYR'", name="ck_accounts_currency_myr"),
        # Customer accounts must have an owner; merchant/system accounts may not.
        sa.CheckConstraint(
            "(account_type = 'customer' AND customer_id IS NOT NULL) "
            "OR account_type IN ('merchant', 'system')",
            name="ck_accounts_valid_owner",
        ),
    )
    op.create_index("ix_accounts_customer_status", "bank_accounts", ["customer_id", "status"])
    # Partial unique index: at most ONE open primary account per customer.
    op.create_index(
        "uq_accounts_primary_customer",
        "bank_accounts",
        ["customer_id"],
        unique=True,
        postgresql_where=sa.text(
            "is_primary = true AND customer_id IS NOT NULL AND status <> 'closed'"
        ),
    )

    # --- merchants --------------------------------------------------------
    op.create_table(
        "merchants",
        id_column(),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("registration_number", sa.String(100), unique=True),
        sa.Column(
            "settlement_account_id",
            sa.BigInteger(),
            sa.ForeignKey("bank_accounts.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("category_code", sa.String(10)),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("risk_level", sa.String(20), nullable=False, server_default="normal"),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=EMPTY_JSON),
        *timestamp_columns(),
    )
    op.create_index("ix_merchants_active_risk", "merchants", ["active", "risk_level"])

    # --- merchant_qr_codes ------------------------------------------------
    op.create_table(
        "merchant_qr_codes",
        id_column(),
        sa.Column(
            "merchant_id",
            sa.BigInteger(),
            sa.ForeignKey("merchants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("qr_reference", sa.String(128), nullable=False, unique=True),
        sa.Column("label", sa.String(120)),
        money("fixed_amount"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *timestamp_columns(),
        sa.CheckConstraint(
            "fixed_amount IS NULL OR fixed_amount > 0",
            name="ck_merchant_qr_amount_positive",
        ),
    )
    op.create_index(
        "ix_merchant_qr_merchant_active",
        "merchant_qr_codes",
        ["merchant_id", "active"],
    )

    # --- payees -----------------------------------------------------------
    op.create_table(
        "payees",
        id_column(),
        sa.Column(
            "customer_id",
            sa.BigInteger(),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_account_id",
            sa.BigInteger(),
            sa.ForeignKey("bank_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("nickname", sa.String(120), nullable=False),
        sa.Column("check_status", payee_check_status, nullable=False, server_default="pending"),
        sa.Column(
            "check_reasons",
            postgresql.JSONB(),
            nullable=False,
            server_default=EMPTY_JSON_LIST,
        ),
        # datetime columns last
        sa.Column("checked_at", sa.DateTime(timezone=True)),
        sa.Column("cooling_off_until", sa.DateTime(timezone=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        *timestamp_columns(),
    )
    op.create_index("ix_payees_customer_created", "payees", ["customer_id", "created_at"])
    # Soft delete: the same payee can be re-added after the old row is deleted.
    op.create_index(
        "uq_payees_active_customer_target",
        "payees",
        ["customer_id", "target_account_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # --- transactions -----------------------------------------------------
    op.create_table(
        "transactions",
        id_column(),
        sa.Column("reference", sa.String(40), nullable=False, unique=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("transaction_type", transaction_type, nullable=False),
        sa.Column("status", transaction_status, nullable=False, server_default="pending"),
        sa.Column("channel", transaction_channel, nullable=False),
        sa.Column(
            "initiated_by_customer_id",
            sa.BigInteger(),
            sa.ForeignKey("customers.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "source_account_id",
            sa.BigInteger(),
            sa.ForeignKey("bank_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "destination_account_id",
            sa.BigInteger(),
            sa.ForeignKey("bank_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "payee_id",
            sa.BigInteger(),
            sa.ForeignKey("payees.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "merchant_id",
            sa.BigInteger(),
            sa.ForeignKey("merchants.id", ondelete="SET NULL"),
        ),
        # Self-reference: a reversal points to the transaction it undoes (only once).
        sa.Column(
            "reversal_of_transaction_id",
            sa.BigInteger(),
            sa.ForeignKey("transactions.id", ondelete="RESTRICT"),
            unique=True,
        ),
        money("amount", nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="MYR"),
        sa.Column("description", sa.String(500)),
        sa.Column("customer_reference", sa.String(140)),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=EMPTY_JSON),
        sa.Column("failure_code", sa.String(100)),
        sa.Column("failure_message", sa.Text()),
        # datetime columns last
        sa.Column(
            "initiated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("posted_at", sa.DateTime(timezone=True)),
        sa.Column("held_until", sa.DateTime(timezone=True)),
        *timestamp_columns(),
        sa.CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
        sa.CheckConstraint("currency = 'MYR'", name="ck_transactions_currency_myr"),
        sa.CheckConstraint(
            "source_account_id <> destination_account_id",
            name="ck_transactions_different_accounts",
        ),
        # Same request sent twice (double tap, retry) can't create two transfers.
        sa.UniqueConstraint(
            "initiated_by_customer_id",
            "idempotency_key",
            name="uq_transactions_customer_idempotency",
        ),
    )
    op.create_index(
        "ix_transactions_source_time", "transactions", ["source_account_id", "initiated_at"]
    )
    op.create_index(
        "ix_transactions_destination_time",
        "transactions",
        ["destination_account_id", "initiated_at"],
    )
    op.create_index("ix_transactions_status_time", "transactions", ["status", "initiated_at"])
    op.create_index(
        "ix_transactions_customer_time",
        "transactions",
        ["initiated_by_customer_id", "initiated_at"],
    )

    # --- ledger_entries (append-only: no updated_at) -----------------------
    op.create_table(
        "ledger_entries",
        id_column(),
        sa.Column(
            "transaction_id",
            sa.BigInteger(),
            sa.ForeignKey("transactions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            sa.BigInteger(),
            sa.ForeignKey("bank_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("direction", ledger_direction, nullable=False),
        money("amount", nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="MYR"),
        sa.Column("sequence_number", sa.SmallInteger(), nullable=False),
        sa.Column("description", sa.String(500)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("amount > 0", name="ck_ledger_amount_positive"),
        sa.CheckConstraint("currency = 'MYR'", name="ck_ledger_currency_myr"),
        sa.UniqueConstraint(
            "transaction_id",
            "sequence_number",
            name="uq_ledger_transaction_sequence",
        ),
    )
    op.create_index("ix_ledger_account_time", "ledger_entries", ["account_id", "created_at"])
    op.create_index("ix_ledger_transaction", "ledger_entries", ["transaction_id"])


def downgrade() -> None:
    """Downgrade schema."""
    # Children before parents.
    op.drop_table("ledger_entries")
    op.drop_table("transactions")
    op.drop_table("payees")
    op.drop_table("merchant_qr_codes")
    op.drop_table("merchants")
    op.drop_table("bank_accounts")

    bind = op.get_bind()
    for enum in reversed(ALL_ENUMS):
        enum.drop(bind, checkfirst=True)
