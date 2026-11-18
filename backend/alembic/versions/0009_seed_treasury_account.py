"""seed treasury account

Inserts the Jaga Treasury: the bank's own internal (system) account that
opening balances are paid from. Double-entry can't create money from nothing,
so every RM 10,000 opening balance is:

    debit  JAGA-TREASURY   10,000   (money out of the bank's pile)
    credit customer        10,000   (money into the customer's account)

The Treasury is the only account allowed to go negative: its balance is minus
the total money issued to all customers. No customer owns it (customer_id is
NULL), which ck_accounts_valid_owner allows for account_type = 'system'.

This is bootstrap data, not demo data: the bank cannot work without it.

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: Union[str, Sequence[str], None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Fixed values, written out here on purpose: a migration is frozen history and
# must not import app code that might change later. The app looks the Treasury
# up by this account number.
TREASURY_ACCOUNT_NUMBER = "JAGA-TREASURY"
TREASURY_ACCOUNT_NAME = "Jaga Treasury"


def upgrade() -> None:
    """Upgrade schema."""
    # ON CONFLICT DO NOTHING: safe even if the row was already created by hand.
    op.execute(
        sa.text(
            """
            INSERT INTO bank_accounts
                (customer_id, account_number, account_name, account_type,
                 status, currency, is_primary)
            VALUES
                (NULL, :number, :name, 'system', 'active', 'MYR', false)
            ON CONFLICT (account_number) DO NOTHING
            """
        ).bindparams(number=TREASURY_ACCOUNT_NUMBER, name=TREASURY_ACCOUNT_NAME)
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Only succeeds while no ledger entries or transactions point at the
    # Treasury (their foreign keys are ON DELETE RESTRICT). That's deliberate:
    # the bank's own account must never vanish while money history uses it.
    op.execute(
        sa.text("DELETE FROM bank_accounts WHERE account_number = :number").bindparams(
            number=TREASURY_ACCOUNT_NUMBER
        )
    )
