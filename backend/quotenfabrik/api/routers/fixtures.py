"""Matchday overview and fixture detail."""

import math
from datetime import date, datetime, timedelta

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from quotenfabrik.analytics.patterns import PatternContext, compute_patterns
from quotenfabrik.analytics.picks import DEFAULT_PROFILE
from quotenfabrik.api.data import chosen_runs_cte, df, model_data
from quotenfabrik.api.labels import GROUP_LABELS, MARKET_LABELS, SELECTION_LABELS, league_logo, pick_label
from quotenfabrik.config import get_settings

router = APIRouter(prefix="/api", tags=["fixtures"])

FIXTURE_SQL = """
    select f.id, f.league_id, f.season, f.round, f.matchday, f.kickoff_utc, f.status, f.referee,
           f.home_team_id, h.name as home_name, h.logo_url as home_logo,
           f.away_team_id, a.name as away_name, a.logo_url as away_logo,
           f.ft_home, f.ft_away, f.ht_home, f.ht_away, v.name as venue, l.name as league_name
    from core.fixtures f
    join core.leagues l on l.id = f.league_id
    join core.teams h on h.id = f.home_team_id
    join core.teams a on a.id = f.away_team_id
    left join core.venues v on v.id = f.venue_id
"""

SUMMARY_KEYS = {
    ("1x2", "H", None): "home",
    ("1x2", "D", None): "draw",
    ("1x2", "A", None): "away",
    ("ou_ft", "over", 2.5): "over25",
    ("btts", "yes", None): "btts",
}
FINISHED = {"FT", "AET", "PEN", "AWD", "WO"}


def _clean(v):
    """JSON-safe value: numpy scalars -> Python, NaN/NaT -> None, timestamps -> ISO strings."""
    if v is None or v is pd.NaT:
        return None
    if hasattr(v, "item") and not isinstance(v, pd.Timestamp):
        v = v.item()
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, pd.Timestamp | datetime):
        return v.isoformat()
    return v


def _fixture_dict(r) -> dict:
    return {
        "id": int(r.id),
        "league_id": int(r.league_id),
        "league": {"id": int(r.league_id), "name": r.league_name, "logo": league_logo(int(r.league_id))},
        "season": int(r.season),
        "round": r.round,
        "matchday": _clean(r.matchday),
        "kickoff": _clean(r.kickoff_utc),
        "status": r.status,
        "finished": r.status in FINISHED,
        "venue": _clean(r.venue),
        "referee": _clean(r.referee),
        "home": {"id": int(r.home_team_id), "name": r.home_name, "logo": r.home_logo},
        "away": {"id": int(r.away_team_id), "name": r.away_name, "logo": r.away_logo},
        "score": {"ft": [_clean(r.ft_home), _clean(r.ft_away)], "ht": [_clean(r.ht_home), _clean(r.ht_away)]},
    }


def _summaries(fixture_ids: list[int]) -> dict[int, dict]:
    if not fixture_ids:
        return {}
    rows = df(
        f"""with runs as ({chosen_runs_cte("and p.fixture_id = any(:ids)")})
            select p.fixture_id, p.market, p.selection, p.line, p.probability, p.outcome, runs.kind
            from analytics.predictions p join runs on runs.model_run_id = p.model_run_id and runs.fixture_id = p.fixture_id
            where p.market in ('1x2', 'ou_ft', 'btts') and p.fixture_id = any(:ids)""",
        ids=fixture_ids,
    )
    out: dict[int, dict] = {}
    for r in rows.itertuples():
        key = SUMMARY_KEYS.get((r.market, r.selection, None if pd.isna(r.line) else float(r.line)))
        if key:
            entry = out.setdefault(int(r.fixture_id), {"source": r.kind, "probabilities": {}, "outcomes": {}})
            entry["probabilities"][key] = float(r.probability)
            entry["outcomes"][key] = None if pd.isna(r.outcome) else bool(r.outcome)
    for entry in out.values():
        p = entry["probabilities"]
        if {"home", "draw", "away"} <= p.keys():
            pick = max(("home", "draw", "away"), key=lambda k: p[k])
            entry["pick_1x2"] = pick
            entry["pick_1x2_hit"] = entry["outcomes"].get(pick)
    return out


def _picks(fixtures: list[dict], profile: str | None = None) -> dict[int, dict[str, list[dict]]]:
    """Picks of the chosen prediction run per fixture: {fixture_id: {profile: [pick, ...]}}."""
    if not fixtures:
        return {}
    names = {f["id"]: (f["home"]["name"], f["away"]["name"]) for f in fixtures}
    rows = df(
        f"""with runs as ({chosen_runs_cte("and p.fixture_id = any(:ids)")})
            select k.fixture_id, k.profile, k.rank, k.market_group, k.market, k.selection, k.line, k.probability,
                   k.base_rate, k.reasons, p.fair_odd, p.outcome
            from analytics.picks k
            join runs on runs.model_run_id = k.model_run_id and runs.fixture_id = k.fixture_id
            join analytics.predictions p on p.id = k.prediction_id
            where k.fixture_id = any(:ids) and (cast(:profile as text) is null or k.profile = :profile)
            order by k.fixture_id, k.profile, k.rank""",
        ids=list(names), profile=profile,
    )  # fmt: skip
    out: dict[int, dict[str, list[dict]]] = {}
    for r in rows.itertuples():
        line = None if pd.isna(r.line) else float(r.line)
        out.setdefault(int(r.fixture_id), {}).setdefault(r.profile, []).append(
            {"rank": int(r.rank), "group": r.market_group, "market": r.market, "selection": r.selection, "line": line,
             "label": pick_label(r.market, r.selection, line, *names[int(r.fixture_id)]),
             "probability": float(r.probability), "fair_odd": _clean(r.fair_odd), "base_rate": _clean(r.base_rate),
             "outcome": None if pd.isna(r.outcome) else bool(r.outcome), "reasons": r.reasons or []}
        )  # fmt: skip
    return out


@router.get("/days")
def days(
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    league: int | None = None,
) -> list[dict]:
    """Days with fixtures (Europe/Berlin calendar days) and the number of fixtures per day."""
    today = date.today()
    date_from = date_from or today - timedelta(days=60)
    date_to = date_to or today + timedelta(days=60)
    rows = df(
        """select (f.kickoff_utc at time zone 'Europe/Berlin')::date as day, count(*) as fixtures,
                  count(*) filter (where f.status in ('FT','AET','PEN','AWD','WO')) as finished
           from core.fixtures f where f.league_id = any(:leagues)
             and (f.kickoff_utc at time zone 'Europe/Berlin')::date between :f and :t
           group by 1 order by 1""",
        leagues=[league] if league else get_settings().leagues, f=date_from, t=date_to,
    )  # fmt: skip
    return [
        {"date": r.day.isoformat(), "fixtures": int(r.fixtures), "finished": int(r.finished)}
        for r in rows.itertuples()
    ]


@router.get("/fixtures")
def fixtures(
    day: date | None = Query(None, alias="date"),
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    league: int | None = None,
    season: int | None = None,
    team: int | None = None,
    limit: int = Query(200, le=1000),
    profile: str = DEFAULT_PROFILE,
) -> list[dict]:
    where, params = (
        ["f.league_id = any(:leagues)"],
        {"leagues": [league] if league else get_settings().leagues},
    )
    local_day = "(f.kickoff_utc at time zone 'Europe/Berlin')::date"
    if day:
        where.append(f"{local_day} = :day")
        params["day"] = day
    if date_from:
        where.append(f"{local_day} >= :df")
        params["df"] = date_from
    if date_to:
        where.append(f"{local_day} <= :dt")
        params["dt"] = date_to
    if season:
        where.append("f.season = :season")
        params["season"] = season
    if team:
        where.append("(f.home_team_id = :team or f.away_team_id = :team)")
        params["team"] = team
    rows = df(
        f"{FIXTURE_SQL} where {' and '.join(where)} order by f.kickoff_utc, f.id limit {int(limit)}", **params
    )
    items = [_fixture_dict(r) for r in rows.itertuples()]
    summaries = _summaries([i["id"] for i in items])
    picks = _picks(items, profile)
    for item in items:
        item["prediction"] = summaries.get(item["id"])
        item["picks"] = picks.get(item["id"], {}).get(profile, [])
    return items


@router.get("/fixtures/{fixture_id}")
def fixture_detail(fixture_id: int) -> dict:
    rows = df(f"{FIXTURE_SQL} where f.id = :id", id=fixture_id)
    if rows.empty:
        raise HTTPException(404, "Spiel nicht gefunden")
    r = next(rows.itertuples())
    fixture = _fixture_dict(r)

    preds = df(
        f"""with runs as ({chosen_runs_cte("and p.fixture_id = :id")})
            select p.market_group, p.market, p.selection, p.line, p.probability, p.fair_odd, p.outcome,
                   runs.kind, runs.predicted_at
            from analytics.predictions p join runs on runs.model_run_id = p.model_run_id and runs.fixture_id = p.fixture_id
            where p.fixture_id = :id""",
        id=fixture_id,
    )
    names = df(
        """select pl.id::text as id, pl.name, coalesce(ps.team_id, last.team_id, 0) as team_id,
                  coalesce(ps.position, last.position) as position, ps.is_starter, ps.minutes, ps.goals
           from core.players pl
           left join core.fixture_player_stats ps on ps.player_id = pl.id and ps.fixture_id = :id
           left join lateral (
               select s.team_id, s.position from core.fixture_player_stats s join core.fixtures f on f.id = s.fixture_id
               where s.player_id = pl.id order by f.kickoff_utc desc limit 1
           ) last on true
           where pl.id::text = any(:ids)""",
        id=fixture_id, ids=preds.loc[preds["market"].str.startswith("scorer"), "selection"].unique().tolist(),
    ).set_index("id")  # fmt: skip

    markets: dict[tuple, dict] = {}
    scorers: dict[str, dict] = {}
    for p in preds.itertuples():
        line = None if pd.isna(p.line) else float(p.line)
        outcome = None if pd.isna(p.outcome) else bool(p.outcome)
        if p.market.startswith("scorer"):
            s = scorers.setdefault(p.selection, {"player_id": int(p.selection)})
            if p.selection in names.index:
                n = names.loc[p.selection]
                s.update(name=n["name"], team_id=int(n["team_id"]) or None, position=_clean(n["position"]),
                         is_starter=_clean(n["is_starter"]), goals=_clean(n["goals"]))  # fmt: skip
            key = "anytime" if p.market == "scorer_anytime" else "first"
            s[key] = float(p.probability)
            s[f"{key}_outcome"] = outcome
            continue
        m = markets.setdefault(
            (p.market_group, p.market, line),
            {"group": p.market_group, "group_label": GROUP_LABELS.get(p.market_group), "market": p.market,
             "label": MARKET_LABELS.get(p.market, p.market), "line": line, "selections": []},
        )  # fmt: skip
        m["selections"].append(
            {"selection": p.selection, "label": SELECTION_LABELS.get(p.selection, p.selection),
             "probability": float(p.probability), "fair_odd": None if pd.isna(p.fair_odd) else float(p.fair_odd),
             "outcome": outcome}
        )  # fmt: skip
    order = list(GROUP_LABELS)
    market_list = sorted(
        markets.values(), key=lambda m: (order.index(m["group"]), m["market"], m["line"] or 0)
    )
    for m in market_list:
        m["selections"].sort(key=lambda s: -s["probability"] if m["market"] == "exact_goals" else 0)

    source = (
        None
        if preds.empty
        else {"kind": preds["kind"].iloc[0], "predicted_at": _clean(preds["predicted_at"].iloc[0])}
    )
    return {
        "fixture": fixture,
        "prediction": source,
        "markets": market_list,
        "scorers": sorted(scorers.values(), key=lambda s: -s.get("anytime", 0)),
        "patterns": _patterns(r),
        "picks": _picks([fixture]).get(fixture_id, {}),
        "stats": _stats(fixture_id, fixture),
        "goals": _goals(fixture_id),
    }


def _patterns(r) -> list[dict]:
    matches, players, goals = model_data.get(int(r.league_id))
    kickoff = pd.Timestamp(r.kickoff_utc)
    ctx = PatternContext.build(matches, kickoff, goals, players)
    out = []
    for p in compute_patterns(ctx, int(r.home_team_id), int(r.away_team_id)):
        out.append({"group": p.group, "key": p.key, "label": p.label, "scope": p.scope, "value": _clean(p.value),
                    "n": p.n, "baseline": _clean(p.baseline), "signal": p.signal, "details": p.details or None})  # fmt: skip
    return out


def _stats(fixture_id: int, fixture: dict) -> dict:
    rows = df("select * from core.fixture_team_stats where fixture_id = :id", id=fixture_id)
    out: dict = {"home": {}, "away": {}}
    for r in rows.to_dict("records"):
        side = "home" if r["team_id"] == fixture["home"]["id"] else "away"
        out[side][r["period"]] = {k: _clean(float(v) if v is not None and k in ("xg", "possession") else v)
                                  for k, v in r.items() if k not in ("fixture_id", "team_id", "period")}  # fmt: skip
    return out


def _goals(fixture_id: int) -> list[dict]:
    rows = df(
        """select minute, extra_minute, team_id, player_id, player_name, detail, comments from core.fixture_events
           where fixture_id = :id and type = 'Goal' and detail <> 'Missed Penalty' order by seq""",
        id=fixture_id,
    )
    return [{k: _clean(v) for k, v in r.items()} for r in rows.to_dict("records")]
