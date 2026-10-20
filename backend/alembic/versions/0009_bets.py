"""bet tracking: app.bets and app.bet_legs

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-20 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bets",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("placed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "source", sa.Text(), server_default="manuell", nullable=False
        ),  # tageskombi | tipps | manuell
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("bookmaker", sa.Text(), server_default="Betano", nullable=False),
        sa.Column("stake", sa.Numeric(10, 2), nullable=False),
        sa.Column("odds", sa.Numeric(8, 3), nullable=False),
        sa.Column("probability", sa.Float(), nullable=True),  # model probability when placed (EV)
        sa.Column("status", sa.Text(), server_default="open", nullable=False),
        sa.Column("payout", sa.Numeric(10, 2), nullable=True),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint("status in ('open', 'won', 'lost', 'void')", name="status"),
        schema="app",
    )
    op.create_table(
        "bet_legs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "bet_id", sa.BigInteger(), sa.ForeignKey("app.bets.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("fixture_id", sa.BigInteger(), sa.ForeignKey("core.fixtures.id"), nullable=True),
        sa.Column("market", sa.Text(), nullable=True),
        sa.Column("selection", sa.Text(), nullable=True),
        sa.Column("line", sa.Numeric(5, 2), nullable=True),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("probability", sa.Float(), nullable=True),
        sa.Column("odds", sa.Numeric(8, 3), nullable=True),
        sa.Column("outcome", sa.Boolean(), nullable=True),
        schema="app",
    )
    op.create_index("ix_bet_legs_bet_id", "bet_legs", ["bet_id"], schema="app")


def downgrade() -> None:
    op.drop_table("bet_legs", schema="app")
    op.drop_table("bets", schema="app")
