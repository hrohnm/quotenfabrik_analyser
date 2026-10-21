"""Matchday overview and fixture detail."""

import dataclasses
import math
import threading
import time
from datetime import date, datetime, timedelta

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from quotenfabrik import app_config
from quotenfabrik.analytics import bookmaker_odds, form, preview, style
from quotenfabrik.analytics.patterns import PatternContext, compute_patterns
from quotenfabrik.analytics.picks import default_profile
from quotenfabrik.api.data import chosen_runs_cte, df, model_data, style_data, team_names
from quotenfabrik.api.labels import (
    GROUP_LABELS,
    MARKET_LABELS,
    SELECTION_LABELS,
    league_logo,
    pick_label,
    round_label,
)
from quotenfabrik.db import get_engine

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
        "round_label": round_label(r.round),
        "cup": app_config.is_cup(int(r.league_id)),
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


def _first_legs(fixtures: list[dict]) -> dict[int, dict]:
    """Second legs of cup ties: the first leg (same competition, season and round, teams swapped, earlier)."""
    ids = [f["id"] for f in fixtures if f["cup"]]
    if not ids:
        return {}
    rows = df(
        """select f.id, g.id as first_id, g.ft_home, g.ft_away, g.status, g.kickoff_utc
           from core.fixtures f
           join core.fixtures g on g.league_id = f.league_id and g.season = f.season and g.round = f.round
                and g.home_team_id = f.away_team_id and g.away_team_id = f.home_team_id
                and g.kickoff_utc < f.kickoff_utc
           where f.id = any(:ids)""",
        ids=ids,
    )
    out = {}
    for r in rows.itertuples():
        played = r.status in FINISHED
        # from the perspective of the second leg: goals of its home team first
        out[int(r.id)] = {"fixture_id": int(r.first_id), "kickoff": _clean(r.kickoff_utc), "finished": played,
                          "score": [_clean(r.ft_away), _clean(r.ft_home)] if played else None}  # fmt: skip
    return out


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
    # Betano 1X2 odds (OddsPapi, last price before kickoff) with the model's edge
    prices = _bookmaker_prices(list(out)) if out else {}
    for fixture_id, entry in out.items():
        p = entry["probabilities"]
        entry["betano"] = {
            key: _prices(prices, fixture_id, "1x2", None, sel, p[key])
            for sel, key in (("H", "home"), ("D", "draw"), ("A", "away"))
            if key in p
        }
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
    prices = _bookmaker_prices(list(names)) if not rows.empty else {}
    out: dict[int, dict[str, list[dict]]] = {}
    for r in rows.itertuples():
        line = None if pd.isna(r.line) else float(r.line)
        out.setdefault(int(r.fixture_id), {}).setdefault(r.profile, []).append(
            {"rank": int(r.rank), "group": r.market_group, "market": r.market, "selection": r.selection, "line": line,
             "label": pick_label(r.market, r.selection, line, *names[int(r.fixture_id)]),
             "probability": float(r.probability), "fair_odd": _clean(r.fair_odd), "base_rate": _clean(r.base_rate),
             "outcome": None if pd.isna(r.outcome) else bool(r.outcome), "reasons": r.reasons or [],
             **_prices(prices, int(r.fixture_id), r.market, line, r.selection, float(r.probability))}
        )  # fmt: skip
    return out


PRICE_TTL_S = 300  # OddsPapi prices are fetched every 3 h; summaries, picks and detail share one lookup
_price_cache: dict[int, tuple[float, dict[tuple, dict]]] = {}
_price_lock = threading.Lock()


def _bookmaker_prices(fixture_ids: list[int]) -> dict[tuple, dict]:
    """Betano odds and Pinnacle fair probability per selection (OddsPapi, last price before kickoff),
    cached per fixture for a few minutes."""
    now = time.time()
    with _price_lock:
        missing = [f for f in fixture_ids if f not in _price_cache or now - _price_cache[f][0] > PRICE_TTL_S]
    if missing:
        fresh = bookmaker_odds.lookup(bookmaker_odds.odds_table(get_engine(), missing))
        per_fixture: dict[int, dict[tuple, dict]] = {f: {} for f in missing}
        for key, value in fresh.items():
            per_fixture.setdefault(key[0], {})[key] = value
        with _price_lock:
            if len(_price_cache) > 5000:  # keep the cache small
                _price_cache.clear()
            for f, entries in per_fixture.items():
                _price_cache[f] = (now, entries)
    out: dict[tuple, dict] = {}
    with _price_lock:
        for f in fixture_ids:
            out.update(_price_cache.get(f, (0, {}))[1])
    return out


def _prices(prices: dict, fixture_id: int, market: str, line: float | None, selection: str, p: float) -> dict:
    """``betano`` odds, ``pinnacle`` fair probability and ``edge`` = p × Betano odds − 1 (None if unknown)."""
    hit = prices.get((fixture_id, market, None if line is None else round(line, 2), selection))
    if not hit:
        return {"betano": None, "pinnacle": None, "edge": None}
    betano = hit["betano"]
    return {"betano": betano, "pinnacle": hit["fair"], "edge": None if betano is None else p * betano - 1}


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
        leagues=[league] if league else app_config.shown_league_ids(), f=date_from, t=date_to,
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
    profile: str | None = None,
) -> list[dict]:
    where, params = (
        ["f.league_id = any(:leagues)"],
        {"leagues": [league] if league else app_config.shown_league_ids()},
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
    profile = profile or default_profile()
    picks = _picks(items, profile)
    first_legs = _first_legs(items)
    for item in items:
        item["prediction"] = summaries.get(item["id"])
        item["picks"] = picks.get(item["id"], {}).get(profile, [])
        item["first_leg"] = first_legs.get(item["id"])
    return items


@router.get("/fixtures/{fixture_id}")
def fixture_detail(fixture_id: int) -> dict:
    rows = df(f"{FIXTURE_SQL} where f.id = :id", id=fixture_id)
    if rows.empty:
        raise HTTPException(404, "Spiel nicht gefunden")
    r = next(rows.itertuples())
    fixture = _fixture_dict(r)
    fixture["first_leg"] = _first_legs([fixture]).get(fixture_id)
    forms = _forms(r)

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
    prices = _bookmaker_prices([fixture_id])
    for (_, market, line), m in markets.items():
        for s in m["selections"]:
            s.update(_prices(prices, fixture_id, market, line, s["selection"], s["probability"]))
    betano_at = [v["betano_at"] for v in prices.values() if v["betano_at"]]
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
    detail = {
        "fixture": fixture,
        "prediction": source,
        "markets": market_list,
        "scorers": sorted(scorers.values(), key=lambda s: -s.get("anytime", 0)),
        "patterns": _patterns(r, forms),
        "form": forms,
        "style": _styles(r),
        "picks": _picks([fixture]).get(fixture_id, {}),
        "odds": {"betano_at": max(betano_at) if betano_at else None, "closing": fixture["finished"]},
        "stats": _stats(fixture_id, fixture),
        "goals": _goals(fixture_id),
        "events": _events(fixture_id, fixture),
    }
    detail["preview"] = preview.build(detail, default_profile())
    return detail


def _patterns(r, forms: dict) -> list[dict]:
    """Patterns of the fixture (cups: over all competitions) plus the form pattern of both teams."""
    matches, players, goals = model_data.get(int(r.league_id))
    kickoff = pd.Timestamp(r.kickoff_utc)
    ctx = PatternContext.build(matches, kickoff, goals, players)
    out = []
    for p in compute_patterns(ctx, int(r.home_team_id), int(r.away_team_id)):
        out.append({"group": p.group, "key": p.key, "label": p.label, "scope": p.scope, "value": _clean(p.value),
                    "n": p.n, "baseline": _clean(p.baseline), "signal": p.signal, "details": p.details or None})  # fmt: skip
    for scope, team_label in (("home", "Heimteam"), ("away", "Gastteam")):
        f = forms[scope]["form"]
        out.append({"group": "1x2", "key": f"{scope}_form_vs_expectation",
                    "label": f"Form {team_label}: Punkte über/unter Modell-Erwartung pro Spiel "
                             f"(letzte {form.FORM_N}, alle Wettbewerbe)",
                    "scope": scope, "value": f["residual"], "n": f["n_expected"], "baseline": None,
                    "signal": f["signal"], "details": {"sequence": f["sequence"], "ppg": f["ppg"],
                                                       "expected_ppg": f["expected_ppg"]}})  # fmt: skip
    return out


def _styles(r) -> dict:
    """Playing style of both teams before kickoff, ranked against the teams of the competition and season."""
    rows = style_data.get()
    league_id, kickoff = int(r.league_id), pd.Timestamp(r.kickoff_utc)
    peers = set(
        df("""select home_team_id as t from core.fixtures where league_id = :l and season = :s
              union select away_team_id from core.fixtures where league_id = :l and season = :s""",
           l=league_id, s=int(r.season))["t"].astype(int)
    )  # fmt: skip
    # leagues: league matches only; cups: all competitions of the teams (ranked among the cup's teams)
    base = rows if app_config.is_cup(league_id) else rows[rows["league_id"] == league_id]
    return {
        scope: style.team_style(base, team, kickoff, peers, fallback_rows=rows)
        for scope, team in (("home", int(r.home_team_id)), ("away", int(r.away_team_id)))
    }


def _forms(r) -> dict:
    """Last matches of both teams in all competitions (before kickoff) and their form."""
    home, away = int(r.home_team_id), int(r.away_team_id)
    rows = form.team_rows(form.load_history(get_engine(), pd.Timestamp(r.kickoff_utc), [home, away]))
    names = team_names()
    out = {}
    for scope, team in (("home", home), ("away", away)):
        t = rows[rows["team"] == team]
        recent = t.tail(form.LIST_N).iloc[::-1]
        out[scope] = {
            "form": dataclasses.asdict(form.team_form(t)),
            "matches": [
                {"fixture_id": int(m.fixture_id), "kickoff": m.kickoff.isoformat(),
                 "league": {"id": int(m.league_id), "name": m.league_name, "logo": league_logo(int(m.league_id))},
                 "round_label": round_label(m.round), "venue": m.venue,
                 "opponent": {"id": int(m.opp), "name": names.get(int(m.opp), str(m.opp))},
                 "gf": int(m.gf), "ga": int(m.ga), "result": m.result, "points": int(m.points),
                 "xpts": _clean(m.xpts)}
                for m in recent.itertuples(index=False)
            ],
        }  # fmt: skip
    return out


def _stats(fixture_id: int, fixture: dict) -> dict:
    rows = df("select * from core.fixture_team_stats where fixture_id = :id", id=fixture_id)
    out: dict = {"home": {}, "away": {}}
    for r in rows.to_dict("records"):
        side = "home" if r["team_id"] == fixture["home"]["id"] else "away"
        out[side][r["period"]] = {k: _clean(float(v) if v is not None and k in ("xg", "possession") else v)
                                  for k, v in r.items() if k not in ("fixture_id", "team_id", "period")}  # fmt: skip
    return out


def _events(fixture_id: int, fixture: dict) -> list[dict]:
    rows = df(
        """select e.minute, e.extra_minute, e.team_id, e.player_id, e.player_name, a.name as assist_name, e.type,
                  e.detail, e.comments
           from core.fixture_events e left join core.players a on a.id = e.assist_player_id
           where e.fixture_id = :id order by e.seq""",
        id=fixture_id,
    )
    return timeline(
        [{k: _clean(v) for k, v in r.items()} for r in rows.to_dict("records")], fixture["home"]["id"]
    )


def timeline(rows: list[dict], home_id: int) -> list[dict]:
    """Match events for the timeline: goals (with the score after them), cards, substitutions, VAR.

    ``rows`` in API order (seq). API-Football conventions (checked on our data): an own goal carries the team
    it counts for; for a substitution ``player`` leaves the pitch and ``assist`` comes on; a second yellow comes
    as a yellow and a red card (only "Gelb-Rot" is kept)."""
    yellows: set = set()  # (team, player) with a yellow card
    out = []
    for r in rows:
        detail = r.get("detail") or ""
        if r["type"] == "Goal":
            kind = {"Own Goal": "own_goal", "Penalty": "penalty", "Missed Penalty": "missed_penalty"}.get(
                detail, "goal"
            )
        elif r["type"] == "Card":
            if "Red" in detail:
                kind = "second_yellow" if (r["team_id"], r["player_id"]) in yellows else "red"
            else:
                kind = "yellow"
                yellows.add((r["team_id"], r["player_id"]))
        elif r["type"] in ("subst", "Var"):
            kind = "sub" if r["type"] == "subst" else "var"
        else:
            continue
        out.append({"minute": r.get("minute"), "extra_minute": r.get("extra_minute"),
                    "side": "home" if r["team_id"] == home_id else "away", "kind": kind, "player": r.get("player_name"),
                    "related": r.get("assist_name"), "detail": detail or None, "comments": r.get("comments"),
                    "_player": r.get("player_id")})  # fmt: skip
    second = {(e["_player"], e["minute"]) for e in out if e["kind"] == "second_yellow"}
    out = [e for e in out if not (e["kind"] == "yellow" and (e["_player"], e["minute"]) in second)]
    out.sort(key=lambda e: (e["minute"] or 0, e["extra_minute"] or 0))  # stable: same minute keeps API order
    score = [0, 0]
    for e in out:
        del e["_player"]
        if e["kind"] in ("goal", "penalty", "own_goal") and (e["minute"] or 0) <= 120:
            score[0 if e["side"] == "home" else 1] += 1
            e["score"] = list(score)
    return out


def _goals(fixture_id: int) -> list[dict]:
    rows = df(
        """select minute, extra_minute, team_id, player_id, player_name, detail, comments from core.fixture_events
           where fixture_id = :id and type = 'Goal' and detail <> 'Missed Penalty' order by seq""",
        id=fixture_id,
    )
    return [{k: _clean(v) for k, v in r.items()} for r in rows.to_dict("records")]
