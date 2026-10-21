"""bankroll: app.bankroll_transactions, manual payout of bets

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-21 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bankroll_transactions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        # start = starting capital, deposit / withdrawal, reset = new evaluation period from here on
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.CheckConstraint("kind in ('start', 'deposit', 'withdrawal', 'reset')", name="kind"),
        sa.CheckConstraint("amount >= 0", name="amount"),
        schema="app",
    )
    op.create_index("ix_bankroll_transactions_at", "bankroll_transactions", ["at"], schema="app")
    # payout entered by hand (cash-out, boost, different settlement): not recomputed from stake × odds
    op.add_column(
        "bets",
        sa.Column("payout_manual", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        schema="app",
    )


def downgrade() -> None:
    op.drop_column("bets", "payout_manual", schema="app")
    op.drop_index("ix_bankroll_transactions_at", table_name="bankroll_transactions", schema="app")
    op.drop_table("bankroll_transactions", schema="app")
