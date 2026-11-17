"""create arena tables

Scam Arena attempts: each attack on the demo victim, whether the engine
detected it, and how much money moved. Bypasses become training data.

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


arena_decision_action = postgresql.ENUM(
    "approve", "step_up", "hold", "block", name="arena_decision_action", create_type=False
)


def upgrade() -> None:
    """Upgrade schema."""
    arena_decision_action.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "arena_attempts",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(start=1, increment=1),
            primary_key=True,
        ),
        sa.Column(
            "attacker_customer_id",
            sa.BigInteger(),
            sa.ForeignKey("customers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "victim_customer_id",
            sa.BigInteger(),
            sa.ForeignKey("customers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "transaction_id",
            sa.BigInteger(),
            sa.ForeignKey("transactions.id", ondelete="SET NULL"),
            unique=True,
        ),
        sa.Column("attempted_amount", sa.Numeric(19, 2), nullable=False),
        sa.Column("amount_moved", sa.Numeric(19, 2), nullable=False, server_default="0"),
        sa.Column("detected", sa.Boolean(), nullable=False),
        sa.Column("decision_action", arena_decision_action, nullable=False),
        sa.Column("risk_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("attack_notes", sa.Text()),
        sa.Column(
            "learning_payload",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        # datetime columns last
        sa.Column(
            "attempted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "attacker_customer_id <> victim_customer_id", name="ck_arena_different_players"
        ),
        sa.CheckConstraint("attempted_amount > 0", name="ck_arena_attempted_amount"),
        sa.CheckConstraint(
            "amount_moved BETWEEN 0 AND attempted_amount", name="ck_arena_amount_moved"
        ),
        sa.CheckConstraint("risk_score BETWEEN 0 AND 100", name="ck_arena_risk_score"),
    )
    # Leaderboard: attempts per attacker over time.
    op.create_index(
        "ix_arena_attacker_time", "arena_attempts", ["attacker_customer_id", "attempted_at"]
    )
    op.create_index("ix_arena_detected_time", "arena_attempts", ["detected", "attempted_at"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("arena_attempts")
    arena_decision_action.drop(op.get_bind(), checkfirst=True)
