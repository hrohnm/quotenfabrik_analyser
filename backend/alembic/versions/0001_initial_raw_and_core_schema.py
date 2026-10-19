"""initial raw and core schema

Revision ID: 0001
Revises:
Create Date: 2026-10-19 06:50:32.849626
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS raw")
    op.execute("CREATE SCHEMA IF NOT EXISTS core")
    op.create_table(
        "bet_types",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("market_group", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bet_types")),
        schema="core",
    )
    op.create_table(
        "bookmakers",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bookmakers")),
        schema="core",
    )
    op.create_table(
        "leagues",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("country", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_leagues")),
        schema="core",
    )
    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_players")),
        schema="core",
    )
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_teams")),
        schema="core",
    )
    op.create_table(
        "venues",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("city", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_venues")),
        schema="core",
    )
    op.create_table(
        "api_responses",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("quota_remaining", sa.Integer(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("payload_hash", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_api_responses")),
        schema="raw",
    )
    op.create_index(
        op.f("ix_api_responses_endpoint_fetched_at"),
        "api_responses",
        ["endpoint", "fetched_at"],
        unique=False,
        schema="raw",
    )
    op.create_index(
        op.f("ix_api_responses_params"),
        "api_responses",
        ["params"],
        unique=False,
        schema="raw",
        postgresql_using="gin",
    )
    op.create_table(
        "football_data_files",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("league_code", sa.Text(), nullable=False),
        sa.Column("season_code", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("sha256", sa.Text(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_football_data_files")),
        sa.UniqueConstraint(
            "league_code",
            "season_code",
            "sha256",
            name=op.f("uq_football_data_files_league_code_season_code_sha256"),
        ),
        schema="raw",
    )
    op.create_table(
        "fixtures",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("league_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("round", sa.Text(), nullable=True),
        sa.Column("matchday", sa.Integer(), nullable=True),
        sa.Column("kickoff_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("venue_id", sa.Integer(), nullable=True),
        sa.Column("referee", sa.Text(), nullable=True),
        sa.Column("home_team_id", sa.Integer(), nullable=False),
        sa.Column("away_team_id", sa.Integer(), nullable=False),
        sa.Column("ft_home", sa.Integer(), nullable=True),
        sa.Column("ft_away", sa.Integer(), nullable=True),
        sa.Column("ht_home", sa.Integer(), nullable=True),
        sa.Column("ht_away", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("details_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("half_stats_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["away_team_id"], ["core.teams.id"], name=op.f("fk_fixtures_away_team_id_teams")
        ),
        sa.ForeignKeyConstraint(
            ["home_team_id"], ["core.teams.id"], name=op.f("fk_fixtures_home_team_id_teams")
        ),
        sa.ForeignKeyConstraint(
            ["league_id"], ["core.leagues.id"], name=op.f("fk_fixtures_league_id_leagues")
        ),
        sa.ForeignKeyConstraint(["venue_id"], ["core.venues.id"], name=op.f("fk_fixtures_venue_id_venues")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fixtures")),
        schema="core",
    )
    op.create_index(
        op.f("ix_fixtures_league_id_season_kickoff_utc"),
        "fixtures",
        ["league_id", "season", "kickoff_utc"],
        unique=False,
        schema="core",
    )
    op.create_table(
        "team_aliases",
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("alias", sa.Text(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("matched_games", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["core.teams.id"], name=op.f("fk_team_aliases_team_id_teams")),
        sa.PrimaryKeyConstraint("source", "alias", name=op.f("pk_team_aliases")),
        schema="core",
    )
    op.create_table(
        "fixture_events",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("fixture_id", sa.BigInteger(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("minute", sa.Integer(), nullable=True),
        sa.Column("extra_minute", sa.Integer(), nullable=True),
        sa.Column("team_id", sa.Integer(), nullable=True),
        sa.Column("player_id", sa.Integer(), nullable=True),
        sa.Column("player_name", sa.Text(), nullable=True),
        sa.Column("assist_player_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["fixture_id"], ["core.fixtures.id"], name=op.f("fk_fixture_events_fixture_id_fixtures")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fixture_events")),
        schema="core",
    )
    op.create_index(
        op.f("ix_fixture_events_fixture_id"), "fixture_events", ["fixture_id"], unique=False, schema="core"
    )
    op.create_index(
        op.f("ix_fixture_events_player_id"), "fixture_events", ["player_id"], unique=False, schema="core"
    )
    op.create_table(
        "fixture_lineups",
        sa.Column("fixture_id", sa.BigInteger(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("formation", sa.Text(), nullable=True),
        sa.Column("coach_id", sa.Integer(), nullable=True),
        sa.Column("coach_name", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["fixture_id"], ["core.fixtures.id"], name=op.f("fk_fixture_lineups_fixture_id_fixtures")
        ),
        sa.ForeignKeyConstraint(
            ["team_id"], ["core.teams.id"], name=op.f("fk_fixture_lineups_team_id_teams")
        ),
        sa.PrimaryKeyConstraint("fixture_id", "team_id", name=op.f("pk_fixture_lineups")),
        schema="core",
    )
    op.create_table(
        "fixture_player_stats",
        sa.Column("fixture_id", sa.BigInteger(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("is_starter", sa.Boolean(), nullable=True),
        sa.Column("minutes", sa.Integer(), nullable=True),
        sa.Column("position", sa.Text(), nullable=True),
        sa.Column("grid", sa.Text(), nullable=True),
        sa.Column("rating", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column("captain", sa.Boolean(), nullable=True),
        sa.Column("shots_total", sa.Integer(), nullable=True),
        sa.Column("shots_on", sa.Integer(), nullable=True),
        sa.Column("goals", sa.Integer(), nullable=True),
        sa.Column("assists", sa.Integer(), nullable=True),
        sa.Column("penalties_scored", sa.Integer(), nullable=True),
        sa.Column("penalties_missed", sa.Integer(), nullable=True),
        sa.Column("penalties_won", sa.Integer(), nullable=True),
        sa.Column("key_passes", sa.Integer(), nullable=True),
        sa.Column("offsides", sa.Integer(), nullable=True),
        sa.Column("yellow", sa.Integer(), nullable=True),
        sa.Column("red", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["fixture_id"], ["core.fixtures.id"], name=op.f("fk_fixture_player_stats_fixture_id_fixtures")
        ),
        sa.ForeignKeyConstraint(
            ["team_id"], ["core.teams.id"], name=op.f("fk_fixture_player_stats_team_id_teams")
        ),
        sa.PrimaryKeyConstraint("fixture_id", "player_id", name=op.f("pk_fixture_player_stats")),
        schema="core",
    )
    op.create_index(
        op.f("ix_fixture_player_stats_player_id"),
        "fixture_player_stats",
        ["player_id"],
        unique=False,
        schema="core",
    )
    op.create_table(
        "fixture_team_stats",
        sa.Column("fixture_id", sa.BigInteger(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("period", sa.Text(), nullable=False),
        sa.Column("shots_total", sa.Integer(), nullable=True),
        sa.Column("shots_on", sa.Integer(), nullable=True),
        sa.Column("shots_off", sa.Integer(), nullable=True),
        sa.Column("shots_blocked", sa.Integer(), nullable=True),
        sa.Column("shots_inside", sa.Integer(), nullable=True),
        sa.Column("shots_outside", sa.Integer(), nullable=True),
        sa.Column("corners", sa.Integer(), nullable=True),
        sa.Column("fouls", sa.Integer(), nullable=True),
        sa.Column("offsides", sa.Integer(), nullable=True),
        sa.Column("possession", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("yellow", sa.Integer(), nullable=True),
        sa.Column("red", sa.Integer(), nullable=True),
        sa.Column("gk_saves", sa.Integer(), nullable=True),
        sa.Column("passes_total", sa.Integer(), nullable=True),
        sa.Column("passes_accurate", sa.Integer(), nullable=True),
        sa.Column("xg", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.CheckConstraint("period in ('FT','1H','2H')", name=op.f("ck_fixture_team_stats_period")),
        sa.ForeignKeyConstraint(
            ["fixture_id"], ["core.fixtures.id"], name=op.f("fk_fixture_team_stats_fixture_id_fixtures")
        ),
        sa.ForeignKeyConstraint(
            ["team_id"], ["core.teams.id"], name=op.f("fk_fixture_team_stats_team_id_teams")
        ),
        sa.PrimaryKeyConstraint("fixture_id", "team_id", "period", name=op.f("pk_fixture_team_stats")),
        schema="core",
    )
    op.create_table(
        "historical_matches",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("league_code", sa.Text(), nullable=False),
        sa.Column("season_code", sa.Text(), nullable=False),
        sa.Column("match_date", sa.Date(), nullable=False),
        sa.Column("kickoff_local", sa.Time(), nullable=True),
        sa.Column("home_alias", sa.Text(), nullable=False),
        sa.Column("away_alias", sa.Text(), nullable=False),
        sa.Column("fixture_id", sa.BigInteger(), nullable=True),
        sa.Column("ft_home", sa.Integer(), nullable=True),
        sa.Column("ft_away", sa.Integer(), nullable=True),
        sa.Column("ht_home", sa.Integer(), nullable=True),
        sa.Column("ht_away", sa.Integer(), nullable=True),
        sa.Column("hs", sa.Integer(), nullable=True),
        sa.Column("as_", sa.Integer(), nullable=True),
        sa.Column("hst", sa.Integer(), nullable=True),
        sa.Column("ast", sa.Integer(), nullable=True),
        sa.Column("hc", sa.Integer(), nullable=True),
        sa.Column("ac", sa.Integer(), nullable=True),
        sa.Column("hf", sa.Integer(), nullable=True),
        sa.Column("af", sa.Integer(), nullable=True),
        sa.Column("hy", sa.Integer(), nullable=True),
        sa.Column("ay", sa.Integer(), nullable=True),
        sa.Column("hr", sa.Integer(), nullable=True),
        sa.Column("ar", sa.Integer(), nullable=True),
        sa.Column("hxg", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("axg", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("b365_h", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("b365_d", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("b365_a", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("ps_h", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("ps_d", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("ps_a", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("avg_h", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("avg_d", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("avg_a", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("max_h", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("max_d", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("max_a", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("b365c_h", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("b365c_d", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("b365c_a", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("psc_h", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("psc_d", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("psc_a", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("avgc_h", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("avgc_d", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("avgc_a", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("b365_o25", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("b365_u25", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("ps_o25", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("ps_u25", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("avg_o25", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("avg_u25", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("b365c_o25", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("b365c_u25", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("psc_o25", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("psc_u25", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("avgc_o25", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("avgc_u25", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("raw_row", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["fixture_id"], ["core.fixtures.id"], name=op.f("fk_historical_matches_fixture_id_fixtures")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_historical_matches")),
        sa.UniqueConstraint(
            "league_code",
            "season_code",
            "match_date",
            "home_alias",
            "away_alias",
            name=op.f("uq_historical_matches_league_code_season_code_match_date_home_alias_away_alias"),
        ),
        schema="core",
    )
    op.create_index(
        op.f("ix_historical_matches_fixture_id"),
        "historical_matches",
        ["fixture_id"],
        unique=False,
        schema="core",
    )
    op.create_table(
        "injuries",
        sa.Column("fixture_id", sa.BigInteger(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("player_name", sa.Text(), nullable=True),
        sa.Column("type", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["fixture_id"], ["core.fixtures.id"], name=op.f("fk_injuries_fixture_id_fixtures")
        ),
        sa.PrimaryKeyConstraint("fixture_id", "player_id", name=op.f("pk_injuries")),
        schema="core",
    )
    op.create_table(
        "odds_snapshots",
        sa.Column("fixture_id", sa.BigInteger(), nullable=False),
        sa.Column("bookmaker_id", sa.Integer(), nullable=False),
        sa.Column("bet_id", sa.Integer(), nullable=False),
        sa.Column("selection", sa.Text(), nullable=False),
        sa.Column("handicap", sa.Text(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("odd", sa.Numeric(precision=8, scale=3), nullable=False),
        sa.Column("is_main", sa.Boolean(), nullable=True),
        sa.Column("suspended", sa.Boolean(), nullable=True),
        sa.Column("api_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["fixture_id"], ["core.fixtures.id"], name=op.f("fk_odds_snapshots_fixture_id_fixtures")
        ),
        sa.PrimaryKeyConstraint(
            "fixture_id",
            "bookmaker_id",
            "bet_id",
            "selection",
            "handicap",
            "captured_at",
            name=op.f("pk_odds_snapshots"),
        ),
        schema="core",
    )
    op.create_index(
        op.f("ix_odds_snapshots_fixture_id_captured_at"),
        "odds_snapshots",
        ["fixture_id", "captured_at"],
        unique=False,
        schema="core",
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_odds_snapshots_fixture_id_captured_at"), table_name="odds_snapshots", schema="core"
    )
    op.drop_table("odds_snapshots", schema="core")
    op.drop_table("injuries", schema="core")
    op.drop_index(op.f("ix_historical_matches_fixture_id"), table_name="historical_matches", schema="core")
    op.drop_table("historical_matches", schema="core")
    op.drop_table("fixture_team_stats", schema="core")
    op.drop_index(op.f("ix_fixture_player_stats_player_id"), table_name="fixture_player_stats", schema="core")
    op.drop_table("fixture_player_stats", schema="core")
    op.drop_table("fixture_lineups", schema="core")
    op.drop_index(op.f("ix_fixture_events_player_id"), table_name="fixture_events", schema="core")
    op.drop_index(op.f("ix_fixture_events_fixture_id"), table_name="fixture_events", schema="core")
    op.drop_table("fixture_events", schema="core")
    op.drop_table("team_aliases", schema="core")
    op.drop_index(op.f("ix_fixtures_league_id_season_kickoff_utc"), table_name="fixtures", schema="core")
    op.drop_table("fixtures", schema="core")
    op.drop_table("football_data_files", schema="raw")
    op.drop_index(
        op.f("ix_api_responses_params"), table_name="api_responses", schema="raw", postgresql_using="gin"
    )
    op.drop_index(op.f("ix_api_responses_endpoint_fetched_at"), table_name="api_responses", schema="raw")
    op.drop_table("api_responses", schema="raw")
    op.drop_table("venues", schema="core")
    op.drop_table("teams", schema="core")
    op.drop_table("players", schema="core")
    op.drop_table("leagues", schema="core")
    op.drop_table("bookmakers", schema="core")
    op.drop_table("bet_types", schema="core")
    op.execute("DROP SCHEMA IF EXISTS core")
    op.execute("DROP SCHEMA IF EXISTS raw")
