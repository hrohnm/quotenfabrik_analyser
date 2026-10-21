import json
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

DATA = Path(__file__).parent / "data"
BACKEND = Path(__file__).resolve().parents[1]


def load_json(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def engine():
    url = os.environ.get("QF_TEST_DATABASE_URL")
    if not url:
        pytest.skip("QF_TEST_DATABASE_URL not set")
    from alembic import command
    from alembic.config import Config

    eng = create_engine(url)
    with eng.begin() as conn:
        for schema in ("app", "analytics", "core", "raw"):
            conn.execute(text(f"drop schema if exists {schema} cascade"))
        conn.execute(text("drop table if exists public.alembic_version"))
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.attributes["database_url"] = url
    command.upgrade(cfg, "head")
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s
        s.rollback()
    with engine.begin() as conn:
        conn.execute(
            text(
                "truncate core.odds_snapshots, core.historical_matches, core.team_aliases, core.injuries,"
                " core.fixture_player_stats, core.fixture_lineup_players, core.fixture_lineups, core.fixture_events,"
                " core.fixture_team_stats, core.fixtures, core.players, core.venues, core.teams,"
                " core.leagues, core.bet_types, core.bookmakers, raw.api_responses,"
                " core.odds_history, core.oddspapi_fixtures, core.oddspapi_markets,"
                " core.oddspapi_players, raw.oddspapi_responses, analytics.model_runs,"
                " raw.football_data_files cascade"
            )
        )
