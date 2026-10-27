"""Tippschein decision model: analytics.decision_models, analytics.decision_probs

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-27 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "decision_models",
        sa.Column("decision", sa.Text(), primary_key=True),
        sa.Column("fitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        schema="analytics",
    )
    op.create_table(
        "decision_probs",
        sa.Column(
            "model_run_id",
            sa.BigInteger(),
            sa.ForeignKey("analytics.model_runs.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("fixture_id", sa.BigInteger(), primary_key=True),
        sa.Column("decision", sa.Text(), primary_key=True),
        sa.Column("probabilities", JSONB(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        schema="analytics",
    )
    op.create_index("ix_decision_probs_fixture", "decision_probs", ["fixture_id"], schema="analytics")


def downgrade() -> None:
    op.drop_table("decision_probs", schema="analytics")
    op.drop_table("decision_models", schema="analytics")
