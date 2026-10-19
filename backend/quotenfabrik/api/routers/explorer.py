"""Data explorer: model probabilities of one market selection across many (past and upcoming) fixtures."""

from typing import Literal

import numpy as np
import pandas as pd
from fastapi import APIRouter, Query

from quotenfabrik import app_config
from quotenfabrik.api.data import chosen_runs_cte, df
from quotenfabrik.api.routers.fixtures import FINISHED, _clean

router = APIRouter(prefix="/api", tags=["explorer"])


@router.get("/explorer")
def explorer(
    market: str = "1x2",
    selection: str = "H",
    line: float | None = None,
    league: int | None = None,
    season: int | None = None,
    team: int | None = None,
    venue: Literal["any", "home", "away"] = "any",
    min_p: float = Query(0.0, ge=0, le=1),
    max_p: float = Query(1.0, ge=0, le=1),
    status: Literal["all", "finished", "upcoming"] = "all",
    outcome: Literal["all", "hit", "miss"] = "all",
    sort: Literal["kickoff_desc", "kickoff_asc", "probability_desc", "probability_asc"] = "kickoff_desc",
    limit: int = Query(100, le=500),
    offset: int = 0,
) -> dict:
    where = ["p.market = :market", "p.selection = :selection", "f.league_id = any(:leagues)",
             "p.probability between :min_p and :max_p"]  # fmt: skip
    params: dict = {"market": market, "selection": selection, "min_p": min_p, "max_p": max_p,
                    "leagues": [league] if league else app_config.league_ids()}  # fmt: skip
    where.append("p.line is null" if line is None else "p.line = :line")
    if line is not None:
        params["line"] = line
    if season:
        where.append("f.season = :season")
        params["season"] = season
    if team:
        params["team"] = team
        where.append({"home": "f.home_team_id = :team", "away": "f.away_team_id = :team"}.get(
            venue, "(f.home_team_id = :team or f.away_team_id = :team)"))  # fmt: skip
    if status == "finished":
        where.append("f.status in ('FT','AET','PEN','AWD','WO')")
    elif status == "upcoming":
        where.append("f.status not in ('FT','AET','PEN','AWD','WO')")
    if outcome == "hit":
        where.append("p.outcome is true")
    elif outcome == "miss":
        where.append("p.outcome is false")
    order = {"kickoff_desc": "f.kickoff_utc desc", "kickoff_asc": "f.kickoff_utc asc",
             "probability_desc": "p.probability desc", "probability_asc": "p.probability asc"}[sort]  # fmt: skip

    rows = df(
        f"""with runs as ({chosen_runs_cte()})
            select f.id, f.season, f.matchday, f.kickoff_utc, f.status, f.home_team_id, h.name as home_name,
                   f.away_team_id, a.name as away_name, f.ft_home, f.ft_away, f.ht_home, f.ht_away,
                   p.probability, p.fair_odd, p.outcome, runs.kind
            from analytics.predictions p
            join runs on runs.model_run_id = p.model_run_id and runs.fixture_id = p.fixture_id
            join core.fixtures f on f.id = p.fixture_id
            join core.teams h on h.id = f.home_team_id join core.teams a on a.id = f.away_team_id
            where {" and ".join(where)} order by {order}, f.id""",
        **params,
    )
    settled = rows[rows["outcome"].notna()]
    y = settled["outcome"].astype(float).to_numpy()
    p = settled["probability"].to_numpy(float)
    summary = {
        "n": int(len(rows)),
        "settled": int(len(settled)),
        "avg_probability": float(rows["probability"].mean()) if len(rows) else None,
        "observed_rate": float(y.mean()) if len(y) else None,
        "expected_rate": float(p.mean()) if len(p) else None,
        "brier": float(np.mean((p - y) ** 2)) if len(y) else None,
    }
    page = rows.iloc[offset : offset + limit]
    items = [
        {
            "id": int(r.id), "season": int(r.season), "matchday": _clean(r.matchday), "kickoff": _clean(r.kickoff_utc),
            "status": r.status, "finished": r.status in FINISHED,
            "home": {"id": int(r.home_team_id), "name": r.home_name},
            "away": {"id": int(r.away_team_id), "name": r.away_name},
            "score": {"ft": [_clean(r.ft_home), _clean(r.ft_away)], "ht": [_clean(r.ht_home), _clean(r.ht_away)]},
            "probability": float(r.probability), "fair_odd": None if pd.isna(r.fair_odd) else float(r.fair_odd),
            "outcome": None if pd.isna(r.outcome) else bool(r.outcome), "source": r.kind,
        }
        for r in page.itertuples()
    ]  # fmt: skip
    return {"summary": summary, "rows": items, "offset": offset, "limit": limit}
