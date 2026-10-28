"""value tips frozen per day: analytics.value_tips

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-28 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "value_tips",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("fixture_id", sa.BigInteger(), nullable=False),
        sa.Column("market", sa.Text(), nullable=False),
        sa.Column("selection", sa.Text(), nullable=False),
        sa.Column("line", sa.Numeric(5, 2), nullable=True),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("p_model", sa.Float(), nullable=False),
        sa.Column("p_market", sa.Float(), nullable=True),
        sa.Column("odds", sa.Numeric(8, 2), nullable=False),
        sa.Column("edge", sa.Float(), nullable=False),
        sa.Column("frozen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="analytics",
    )
    op.create_index("ix_value_tips_day", "value_tips", ["day"], schema="analytics")
    op.create_index("ix_value_tips_fixture_id", "value_tips", ["fixture_id"], schema="analytics")
    op.execute(
        "create unique index ux_value_tips_selection on analytics.value_tips "
        "(fixture_id, market, selection, coalesce(line, -1))"
    )


def downgrade() -> None:
    op.drop_table("value_tips", schema="analytics")
