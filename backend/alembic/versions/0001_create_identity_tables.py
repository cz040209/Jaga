"""create identity tables

Customers, devices, customer sessions, login events, staff users and staff sessions.

Revision ID: 0001
Revises:
Create Date: 2026-11-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# --- Postgres enum types -------------------------------------------------
# create_type=False: we create/drop them explicitly below, so create_table()
# does not try to create them a second time.
customer_status = postgresql.ENUM(
    "active", "frozen", "closed", name="customer_status", create_type=False
)
device_trust_status = postgresql.ENUM(
    "unknown", "trusted", "blocked", name="device_trust_status", create_type=False
)
customer_session_status = postgresql.ENUM(
    "active", "revoked", "expired", name="customer_session_status", create_type=False
)
staff_role = postgresql.ENUM(
    "analyst", "risk_manager", "admin", name="staff_role", create_type=False
)
staff_status = postgresql.ENUM("active", "disabled", name="staff_status", create_type=False)
staff_session_status = postgresql.ENUM(
    "active", "revoked", "expired", name="staff_session_status", create_type=False
)

ALL_ENUMS = (
    customer_status,
    device_trust_status,
    customer_session_status,
    staff_role,
    staff_status,
    staff_session_status,
)


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


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    for enum in ALL_ENUMS:
        enum.create(bind, checkfirst=True)

    # --- customers ------------------------------------------------------
    op.create_table(
        "customers",
        id_column(),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("phone_number", sa.String(32), nullable=False, unique=True),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("preferred_language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("telegram_chat_id", sa.BigInteger(), unique=True),
        sa.Column("status", customer_status, nullable=False, server_default="active"),
        sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("freeze_reason", sa.Text()),
        # datetime columns last
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("password_changed_at", sa.DateTime(timezone=True)),
        sa.Column("frozen_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        *timestamp_columns(),
    )
    # Case-insensitive unique email: "Aisyah@x.com" and "aisyah@x.com" clash.
    op.create_index(
        "uq_customers_email_lower",
        "customers",
        [sa.text("lower(email)")],
        unique=True,
    )
    op.create_index("ix_customers_status", "customers", ["status"])

    # --- devices --------------------------------------------------------
    op.create_table(
        "devices",
        id_column(),
        sa.Column(
            "customer_id",
            sa.BigInteger(),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fingerprint_hash", sa.String(128), nullable=False),
        sa.Column("display_name", sa.String(120)),
        sa.Column("user_agent", sa.Text()),
        sa.Column("operating_system", sa.String(100)),
        sa.Column("browser", sa.String(100)),
        sa.Column("trust_status", device_trust_status, nullable=False, server_default="unknown"),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("trusted_at", sa.DateTime(timezone=True)),
        sa.Column("blocked_at", sa.DateTime(timezone=True)),
        *timestamp_columns(),
    )
    op.create_index(
        "uq_devices_customer_fingerprint",
        "devices",
        ["customer_id", "fingerprint_hash"],
        unique=True,
    )
    op.create_index("ix_devices_fingerprint", "devices", ["fingerprint_hash"])
    op.create_index("ix_devices_customer_trust", "devices", ["customer_id", "trust_status"])

    # --- customer_sessions ---------------------------------------------
    op.create_table(
        "customer_sessions",
        id_column(),
        sa.Column(
            "customer_id",
            sa.BigInteger(),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "device_id",
            sa.BigInteger(),
            sa.ForeignKey("devices.id", ondelete="SET NULL"),
        ),
        sa.Column("refresh_token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("status", customer_session_status, nullable=False, server_default="active"),
        sa.Column("ip_address", postgresql.INET()),
        sa.Column("country_code", sa.String(2)),
        sa.Column("city", sa.String(120)),
        sa.Column("latitude", sa.Numeric(9, 6)),
        sa.Column("longitude", sa.Numeric(9, 6)),
        sa.Column("revoke_reason", sa.String(255)),
        # datetime columns last
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_activity_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        *timestamp_columns(),
    )
    op.create_index(
        "ix_customer_sessions_customer_status",
        "customer_sessions",
        ["customer_id", "status"],
    )
    op.create_index("ix_customer_sessions_expires", "customer_sessions", ["expires_at"])

    # --- login_events (append-only: no updated_at) -----------------------
    op.create_table(
        "login_events",
        id_column(),
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
        sa.Column("attempted_email", sa.String(320)),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.Column("failure_reason", sa.String(255)),
        sa.Column("is_new_device", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("ip_address", postgresql.INET()),
        sa.Column("country_code", sa.String(2)),
        sa.Column("city", sa.String(120)),
        sa.Column("latitude", sa.Numeric(9, 6)),
        sa.Column("longitude", sa.Numeric(9, 6)),
        sa.Column(
            "risk_signals",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_login_events_customer_time",
        "login_events",
        ["customer_id", "occurred_at"],
    )
    op.create_index("ix_login_events_ip_time", "login_events", ["ip_address", "occurred_at"])

    # --- staff_users ------------------------------------------------------
    op.create_table(
        "staff_users",
        id_column(),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", staff_role, nullable=False),
        sa.Column("status", staff_status, nullable=False, server_default="active"),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        *timestamp_columns(),
    )
    op.create_index(
        "uq_staff_email_lower",
        "staff_users",
        [sa.text("lower(email)")],
        unique=True,
    )
    op.create_index("ix_staff_role_status", "staff_users", ["role", "status"])

    # --- staff_sessions -----------------------------------------------------
    op.create_table(
        "staff_sessions",
        id_column(),
        sa.Column(
            "staff_user_id",
            sa.BigInteger(),
            sa.ForeignKey("staff_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("refresh_token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("status", staff_session_status, nullable=False, server_default="active"),
        sa.Column("ip_address", postgresql.INET()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        *timestamp_columns(),
    )
    op.create_index(
        "ix_staff_sessions_user_status",
        "staff_sessions",
        ["staff_user_id", "status"],
    )
    op.create_index("ix_staff_sessions_expires", "staff_sessions", ["expires_at"])


def downgrade() -> None:
    """Downgrade schema."""
    # Reverse order: tables that point to others are dropped first.
    # Dropping a table also drops its indexes.
    op.drop_table("staff_sessions")
    op.drop_table("staff_users")
    op.drop_table("login_events")
    op.drop_table("customer_sessions")
    op.drop_table("devices")
    op.drop_table("customers")

    bind = op.get_bind()
    for enum in reversed(ALL_ENUMS):
        enum.drop(bind, checkfirst=True)
