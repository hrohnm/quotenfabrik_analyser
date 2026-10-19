"""oddspapi odds history

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-19 07:54:32.024678
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oddspapi_markets",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("market_type", sa.Text(), nullable=False),
        sa.Column("period", sa.Text(), nullable=False),
        sa.Column("handicap", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("player_prop", sa.Boolean(), nullable=False),
        sa.Column("market_group", sa.Text(), nullable=True),
        sa.Column("outcomes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_oddspapi_markets")),
        schema="core",
    )
    op.create_table(
        "oddspapi_players",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_oddspapi_players")),
        schema="core",
    )
    op.create_table(
        "oddspapi_responses",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("sha256", sa.Text(), nullable=False),
        sa.Column("content_gzip", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_oddspapi_responses")),
        schema="raw",
    )
    op.create_index(
        op.f("ix_oddspapi_responses_endpoint_fetched_at"),
        "oddspapi_responses",
        ["endpoint", "fetched_at"],
        unique=False,
        schema="raw",
    )
    op.create_table(
        "oddspapi_fixtures",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("season_id", sa.Integer(), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status_id", sa.Integer(), nullable=True),
        sa.Column("participant1_id", sa.Integer(), nullable=False),
        sa.Column("participant2_id", sa.Integer(), nullable=False),
        sa.Column("participant1_name", sa.Text(), nullable=True),
        sa.Column("participant2_name", sa.Text(), nullable=True),
        sa.Column("fixture_id", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("history_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("history_final", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(
            ["fixture_id"], ["core.fixtures.id"], name=op.f("fk_oddspapi_fixtures_fixture_id_fixtures")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_oddspapi_fixtures")),
        schema="core",
    )
    op.create_index(
        op.f("ix_oddspapi_fixtures_fixture_id"),
        "oddspapi_fixtures",
        ["fixture_id"],
        unique=False,
        schema="core",
    )
    op.create_index(
        op.f("ix_oddspapi_fixtures_tournament_id_start_time"),
        "oddspapi_fixtures",
        ["tournament_id", "start_time"],
        unique=False,
        schema="core",
    )
    op.create_table(
        "odds_history",
        sa.Column("oddspapi_fixture_id", sa.Text(), nullable=False),
        sa.Column("bookmaker", sa.Text(), nullable=False),
        sa.Column("market_id", sa.Integer(), nullable=False),
        sa.Column("outcome_id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price", sa.Numeric(precision=8, scale=3), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["oddspapi_fixture_id"],
            ["core.oddspapi_fixtures.id"],
            name=op.f("fk_odds_history_oddspapi_fixture_id_oddspapi_fixtures"),
        ),
        sa.PrimaryKeyConstraint(
            "oddspapi_fixture_id",
            "bookmaker",
            "market_id",
            "outcome_id",
            "player_id",
            "changed_at",
            name=op.f("pk_odds_history"),
        ),
        schema="core",
    )
    op.create_index(
        op.f("ix_odds_history_oddspapi_fixture_id_market_id"),
        "odds_history",
        ["oddspapi_fixture_id", "market_id"],
        unique=False,
        schema="core",
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_odds_history_oddspapi_fixture_id_market_id"), table_name="odds_history", schema="core"
    )
    op.drop_table("odds_history", schema="core")
    op.drop_index(
        op.f("ix_oddspapi_fixtures_tournament_id_start_time"), table_name="oddspapi_fixtures", schema="core"
    )
    op.drop_index(op.f("ix_oddspapi_fixtures_fixture_id"), table_name="oddspapi_fixtures", schema="core")
    op.drop_table("oddspapi_fixtures", schema="core")
    op.drop_index(
        op.f("ix_oddspapi_responses_endpoint_fetched_at"), table_name="oddspapi_responses", schema="raw"
    )
    op.drop_table("oddspapi_responses", schema="raw")
    op.drop_table("oddspapi_players", schema="core")
    op.drop_table("oddspapi_markets", schema="core")
