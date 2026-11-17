"""create audit tables

Audit log: who did what to which record, with before/after values.
Append-only: rows are never updated or deleted.

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: Union[str, Sequence[str], None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


EMPTY_JSON = sa.text("'{}'::jsonb")


def jsonb(name: str) -> sa.Column:
    return sa.Column(name, postgresql.JSONB(), nullable=False, server_default=EMPTY_JSON)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "audit_logs",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(start=1, increment=1),
            primary_key=True,
        ),
        sa.Column("actor_type", sa.String(30), nullable=False),
        sa.Column(
            "actor_customer_id",
            sa.BigInteger(),
            sa.ForeignKey("customers.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "actor_staff_id",
            sa.BigInteger(),
            sa.ForeignKey("staff_users.id", ondelete="SET NULL"),
        ),
        sa.Column("action", sa.String(150), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        # Not a foreign key on purpose: it can point to a row in ANY table.
        sa.Column("resource_id", sa.BigInteger()),
        sa.Column("request_id", sa.String(128)),
        sa.Column("ip_address", postgresql.INET()),
        jsonb("previous_values"),
        jsonb("new_values"),
        jsonb("metadata"),
        # datetime columns last
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "actor_type IN ('customer', 'staff', 'system')", name="ck_audit_actor_type"
        ),
    )
    op.create_index("ix_audit_resource", "audit_logs", ["resource_type", "resource_id"])
    op.create_index("ix_audit_customer_time", "audit_logs", ["actor_customer_id", "occurred_at"])
    op.create_index("ix_audit_staff_time", "audit_logs", ["actor_staff_id", "occurred_at"])
    op.create_index("ix_audit_time", "audit_logs", ["occurred_at"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("audit_logs")
