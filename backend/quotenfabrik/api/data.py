"""Shared database access helpers for the API."""

import threading
import time
from functools import lru_cache

import pandas as pd
from sqlalchemy import Engine, text

from quotenfabrik import app_config
from quotenfabrik.analytics.data import load_competitions, load_goal_events, load_matches, load_player_matches
from quotenfabrik.db import get_engine

CACHE_TTL_S = 600


def engine() -> Engine:
    return get_engine()


def df(sql: str, **params) -> pd.DataFrame:
    with engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


# Chosen prediction run per fixture: the latest forecast made before kickoff, otherwise the backtest.
CHOSEN_RUNS_SQL = """
    select distinct on (p.fixture_id) p.fixture_id, p.model_run_id, r.kind,
           coalesce(p.predicted_at, r.as_of) as predicted_at
    from analytics.predictions p
    join analytics.model_runs r on r.id = p.model_run_id
    join core.fixtures f on f.id = p.fixture_id
    where r.kind in ('forecast', 'backtest') and p.market = '1x2' and p.selection = 'H'
      and (r.kind = 'backtest' or coalesce(p.predicted_at, r.as_of) <= f.kickoff_utc) {where}
    order by p.fixture_id, (r.kind = 'forecast') desc, r.id desc
"""


def records(frame: pd.DataFrame) -> list[dict]:
    """DataFrame -> JSON-safe records (NaN/NaT -> None, timestamps -> ISO strings)."""
    out = []
    for row in frame.to_dict("records"):
        clean = {}
        for k, v in row.items():
            if isinstance(v, pd.Timestamp):
                v = None if pd.isna(v) else v.isoformat()
            elif v is pd.NaT or (isinstance(v, float) and v != v):
                v = None
            elif hasattr(v, "item") and not isinstance(v, list | dict):
                v = v.item()
            clean[k] = v
        out.append(clean)
    return out


def chosen_runs_cte(where: str = "") -> str:
    return CHOSEN_RUNS_SQL.format(where=where)


class _ModelData:
    """In-memory copy of match/player data for on-demand pattern computation (refreshed every 10 min)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._loaded: dict[int, tuple[float, tuple]] = {}

    def get(self, league_id: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        with self._lock:
            entry = self._loaded.get(league_id)
            if entry is None or time.time() - entry[0] > CACHE_TTL_S:
                e = engine()
                if app_config.is_cup(league_id):  # cups: all competitions (same data as the cup forecast)
                    _, players, goals = load_competitions(
                        e, app_config.league_ids(), [lg.id for lg in app_config.cup_leagues()]
                    )
                    data = (app_config.europe_pool(e), players, goals)
                else:
                    data = (
                        load_matches(e, league_id),
                        load_player_matches(e, league_id),
                        load_goal_events(e, league_id),
                    )
                self._loaded[league_id] = (time.time(), data)
            return self._loaded[league_id][1]


model_data = _ModelData()


class _StyleData:
    """Match statistics of all competitions with statistics (playing style), refreshed every 10 min."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._loaded: tuple[float, pd.DataFrame] | None = None

    def get(self) -> pd.DataFrame:
        from quotenfabrik.analytics import style

        with self._lock:
            if self._loaded is None or time.time() - self._loaded[0] > CACHE_TTL_S:
                ids = app_config.league_ids() + [lg.id for lg in app_config.cup_leagues()]
                self._loaded = (time.time(), style.load_stats(engine(), ids))
            return self._loaded[1]


style_data = _StyleData()


@lru_cache(maxsize=1)
def team_names() -> dict[int, str]:
    return {int(r.id): r.name for r in df("select id, name from core.teams").itertuples()}
