"""picks

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-19 13:39:13.578852
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "picks",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("model_run_id", sa.BigInteger(), nullable=False),
        sa.Column("prediction_id", sa.BigInteger(), nullable=False),
        sa.Column("fixture_id", sa.BigInteger(), nullable=False),
        sa.Column("profile", sa.Text(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("market_group", sa.Text(), nullable=False),
        sa.Column("market", sa.Text(), nullable=False),
        sa.Column("selection", sa.Text(), nullable=False),
        sa.Column("line", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("base_rate", sa.Float(), nullable=True),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(
            ["fixture_id"], ["core.fixtures.id"], name=op.f("fk_picks_fixture_id_fixtures")
        ),
        sa.ForeignKeyConstraint(
            ["model_run_id"],
            ["analytics.model_runs.id"],
            name=op.f("fk_picks_model_run_id_model_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["prediction_id"],
            ["analytics.predictions.id"],
            name=op.f("fk_picks_prediction_id_predictions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_picks")),
        schema="analytics",
    )
    op.create_index(op.f("ix_picks_fixture_id"), "picks", ["fixture_id"], unique=False, schema="analytics")
    op.create_index(
        op.f("ix_picks_model_run_id_profile"),
        "picks",
        ["model_run_id", "profile"],
        unique=False,
        schema="analytics",
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_picks_model_run_id_profile"), table_name="picks", schema="analytics")
    op.drop_index(op.f("ix_picks_fixture_id"), table_name="picks", schema="analytics")
    op.drop_table("picks", schema="analytics")
