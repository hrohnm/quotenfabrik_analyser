"""line-up players: core.fixture_lineup_players (starting XI and bench), team colours of the line-up

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-21 16:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("fixture_lineups", sa.Column("colors", JSONB(), nullable=True), schema="core")
    op.create_table(
        "fixture_lineup_players",
        sa.Column("fixture_id", sa.BigInteger(), sa.ForeignKey("core.fixtures.id"), primary_key=True),
        sa.Column("player_id", sa.Integer(), primary_key=True),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("core.teams.id"), nullable=False),
        sa.Column("player_name", sa.Text(), nullable=True),
        sa.Column("number", sa.Integer(), nullable=True),
        sa.Column("pos", sa.Text(), nullable=True),  # G / D / M / F
        sa.Column("grid", sa.Text(), nullable=True),  # "row:col", starting XI only
        sa.Column("is_starter", sa.Boolean(), nullable=False),
        sa.Column("sort", sa.Integer(), nullable=False),  # order within the API list
        schema="core",
    )
    op.create_index("ix_fixture_lineup_players_team_id", "fixture_lineup_players", ["team_id"], schema="core")
    # backfill from the raw match details (newest response per fixture), no API requests
    op.execute(
        """
        with items as (
            select r.id as raw_id, (item->'fixture'->>'id')::bigint as fixture_id, item
            from raw.api_responses r, jsonb_array_elements(r.payload->'response') item
            where r.endpoint = 'fixtures' and r.params ? 'ids'
              and jsonb_array_length(coalesce(item->'lineups', '[]'::jsonb)) > 0
        ), latest as (
            select distinct on (fixture_id) fixture_id, item from items order by fixture_id, raw_id desc
        ), entries as (
            select l.fixture_id, (lu->'team'->>'id')::int as team_id, lu->'team'->'colors' as colors,
                   p.entry->'player' as player, p.is_starter, p.ord
            from latest l, jsonb_array_elements(l.item->'lineups') lu,
            lateral (
                select e as entry, true as is_starter, o as ord
                from jsonb_array_elements(coalesce(lu->'startXI', '[]'::jsonb)) with ordinality s(e, o)
                union all
                select e, false, 100 + o
                from jsonb_array_elements(coalesce(lu->'substitutes', '[]'::jsonb)) with ordinality s(e, o)
            ) p
        )
        insert into core.fixture_lineup_players
            (fixture_id, player_id, team_id, player_name, number, pos, grid, is_starter, sort)
        select distinct on (e.fixture_id, (e.player->>'id')::int)
               e.fixture_id, (e.player->>'id')::int, e.team_id, e.player->>'name',
               (e.player->>'number')::int, e.player->>'pos', case when e.is_starter then e.player->>'grid' end,
               e.is_starter, e.ord
        from entries e
        join core.fixtures f on f.id = e.fixture_id
        join core.teams t on t.id = e.team_id
        where e.player->>'id' is not null
        order by e.fixture_id, (e.player->>'id')::int, e.ord
        """
    )
    op.execute(
        """
        update core.fixture_lineups fl set colors = x.colors
        from (
            select distinct on (fixture_id, team_id) fixture_id, team_id, colors from (
                select r.id as raw_id, (item->'fixture'->>'id')::bigint as fixture_id,
                       (lu->'team'->>'id')::int as team_id, lu->'team'->'colors' as colors
                from raw.api_responses r, jsonb_array_elements(r.payload->'response') item,
                     jsonb_array_elements(coalesce(item->'lineups', '[]'::jsonb)) lu
                where r.endpoint = 'fixtures' and r.params ? 'ids'
            ) s order by fixture_id, team_id, raw_id desc
        ) x
        where fl.fixture_id = x.fixture_id and fl.team_id = x.team_id and jsonb_typeof(x.colors) = 'object'
        """
    )


def downgrade() -> None:
    op.drop_index("ix_fixture_lineup_players_team_id", table_name="fixture_lineup_players", schema="core")
    op.drop_table("fixture_lineup_players", schema="core")
    op.drop_column("fixture_lineups", "colors", schema="core")
