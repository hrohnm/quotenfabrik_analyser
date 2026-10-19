"""app config

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-19 15:42:07.603290
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS app")
    op.create_table(
        "jobs",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("status", sa.Text(), server_default="queued", nullable=False),
        sa.Column("steps", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
        schema="app",
    )
    op.create_table(
        "leagues",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("country", sa.Text(), nullable=True),
        sa.Column("fd_code", sa.Text(), nullable=True),
        sa.Column("oddspapi_tournament", sa.Integer(), nullable=True),
        sa.Column("first_season", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_leagues")),
        schema="app",
    )
    op.create_table(
        "settings",
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_settings")),
        schema="app",
    )

    _seed_leagues_from_environment()


def _seed_leagues_from_environment() -> None:
    """Existing installations keep their leagues: QF_LEAGUES & co. become rows of app.leagues."""
    from quotenfabrik.config import get_settings

    settings = get_settings()
    tournaments = dict(zip(settings.leagues, settings.oddspapi_tournaments, strict=False))
    for league_id, fd_code in zip(settings.leagues, settings.fd_leagues, strict=False):
        op.get_bind().execute(
            sa.text(
                """insert into app.leagues (id, name, country, fd_code, oddspapi_tournament, first_season, active)
                   select :id, coalesce(l.name, :fallback), l.country, :fd, :tournament, 2015, true
                   from (select 1) one left join core.leagues l on l.id = :id
                   on conflict (id) do nothing"""
            ),
            {
                "id": league_id,
                "fallback": f"Liga {league_id}",
                "fd": fd_code,
                "tournament": tournaments.get(league_id),
            },
        )


def downgrade() -> None:
    op.drop_table("settings", schema="app")
    op.drop_table("leagues", schema="app")
    op.drop_table("jobs", schema="app")
    op.execute("DROP SCHEMA IF EXISTS app")
