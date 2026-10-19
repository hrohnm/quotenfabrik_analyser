"""analytics schema

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-19 08:18:16.826177
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS analytics")
    op.create_table(
        "model_runs",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("league_id", sa.Integer(), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=True),
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_model_runs")),
        schema="analytics",
    )
    op.create_table(
        "evaluations",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("model_run_id", sa.BigInteger(), nullable=False),
        sa.Column("market_group", sa.Text(), nullable=False),
        sa.Column("market", sa.Text(), nullable=False),
        sa.Column("selection", sa.Text(), nullable=True),
        sa.Column("line", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("n", sa.Integer(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["model_run_id"],
            ["analytics.model_runs.id"],
            name=op.f("fk_evaluations_model_run_id_model_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evaluations")),
        schema="analytics",
    )
    op.create_index(
        op.f("ix_evaluations_model_run_id"), "evaluations", ["model_run_id"], unique=False, schema="analytics"
    )
    op.create_table(
        "pattern_results",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("model_run_id", sa.BigInteger(), nullable=False),
        sa.Column("fixture_id", sa.BigInteger(), nullable=False),
        sa.Column("market_group", sa.Text(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("n", sa.Integer(), nullable=True),
        sa.Column("baseline", sa.Float(), nullable=True),
        sa.Column("signal", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(
            ["fixture_id"], ["core.fixtures.id"], name=op.f("fk_pattern_results_fixture_id_fixtures")
        ),
        sa.ForeignKeyConstraint(
            ["model_run_id"],
            ["analytics.model_runs.id"],
            name=op.f("fk_pattern_results_model_run_id_model_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pattern_results")),
        schema="analytics",
    )
    op.create_index(
        op.f("ix_pattern_results_fixture_id_model_run_id"),
        "pattern_results",
        ["fixture_id", "model_run_id"],
        unique=False,
        schema="analytics",
    )
    op.create_table(
        "predictions",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("model_run_id", sa.BigInteger(), nullable=False),
        sa.Column("fixture_id", sa.BigInteger(), nullable=False),
        sa.Column("market_group", sa.Text(), nullable=False),
        sa.Column("market", sa.Text(), nullable=False),
        sa.Column("selection", sa.Text(), nullable=False),
        sa.Column("line", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("fair_odd", sa.Numeric(precision=10, scale=3), nullable=True),
        sa.ForeignKeyConstraint(
            ["fixture_id"], ["core.fixtures.id"], name=op.f("fk_predictions_fixture_id_fixtures")
        ),
        sa.ForeignKeyConstraint(
            ["model_run_id"],
            ["analytics.model_runs.id"],
            name=op.f("fk_predictions_model_run_id_model_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_predictions")),
        schema="analytics",
    )
    op.create_index(
        op.f("ix_predictions_fixture_id_model_run_id"),
        "predictions",
        ["fixture_id", "model_run_id"],
        unique=False,
        schema="analytics",
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_predictions_fixture_id_model_run_id"), table_name="predictions", schema="analytics"
    )
    op.drop_table("predictions", schema="analytics")
    op.drop_index(
        op.f("ix_pattern_results_fixture_id_model_run_id"), table_name="pattern_results", schema="analytics"
    )
    op.drop_table("pattern_results", schema="analytics")
    op.drop_index(op.f("ix_evaluations_model_run_id"), table_name="evaluations", schema="analytics")
    op.drop_table("evaluations", schema="analytics")
    op.drop_table("model_runs", schema="analytics")
    op.execute("DROP SCHEMA IF EXISTS analytics")
