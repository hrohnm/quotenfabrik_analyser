"""freeze the picks and combos of a day: analytics.frozen_runs, analytics.day_combos

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-26 08:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # forecast run shown and settled for a fixture once its day is frozen (later forecasts do not replace it)
    op.create_table(
        "frozen_runs",
        sa.Column("fixture_id", sa.BigInteger(), sa.ForeignKey("core.fixtures.id"), primary_key=True),
        sa.Column(
            "model_run_id",
            sa.BigInteger(),
            sa.ForeignKey("analytics.model_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("frozen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="analytics",
    )
    # daily combos as published on the day (legs with odds and probabilities at freezing time)
    op.create_table(
        "day_combos",
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("kind", sa.Text(), primary_key=True),
        sa.Column("frozen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("odds", sa.Numeric(8, 2), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("real_odds", sa.Boolean(), nullable=False),
        sa.Column("legs", JSONB(), nullable=False),
        schema="analytics",
    )


def downgrade() -> None:
    op.drop_table("day_combos", schema="analytics")
    op.drop_table("frozen_runs", schema="analytics")
