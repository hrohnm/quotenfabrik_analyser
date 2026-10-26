"""Competition page (league or European cup): header with tables, table variants, statistics, players."""

import pandas as pd
from fastapi import APIRouter, HTTPException

from quotenfabrik import app_config
from quotenfabrik.analytics import competition_stats, league_table
from quotenfabrik.api.data import chosen_runs_cte, df
from quotenfabrik.api.labels import league_logo, round_label

router = APIRouter(prefix="/api", tags=["competitions"])

FINISHED = ("FT", "AET", "PEN", "AWD", "WO")
HISTORY_SEASONS = 3


def _clean(v):
    if v is None or (isinstance(v, float) and v != v):
        return None
    return v.item() if hasattr(v, "item") else v


def _league(league_id: int) -> dict:
    if league_id not in app_config.shown_league_ids():
        raise HTTPException(404, "Wettbewerb nicht gefunden")
    row = df("select id, name, country, flag_url from core.leagues where id = :id", id=league_id)
    if row.empty:
        raise HTTPException(404, "Wettbewerb nicht gefunden")
    return {"id": league_id, "name": row.name[0], "country": _clean(row.country[0]), "flag": _clean(row.flag_url[0]),
            "logo": league_logo(league_id), "cup": app_config.is_cup(league_id)}  # fmt: skip


def _season_rows(league_id: int, season: int) -> pd.DataFrame:
    m = df(
        """select id as fixture_id, round, matchday, kickoff_utc as kickoff, status, home_team_id as home_id,
                  away_team_id as away_id, ft_home, ft_away, ht_home, ht_away
           from core.fixtures where league_id = :l and season = :s order by kickoff_utc""",
        l=league_id, s=season,
    )  # fmt: skip
    m["kickoff"] = pd.to_datetime(m["kickoff"], utc=True)
    m["finished"] = m["status"].isin(FINISHED) & m["ft_home"].notna() & m["ft_away"].notna()
    m["group"] = m["round"].map(league_table.table_group)
    m["round_label"] = m["round"].map(round_label)
    return m


def _season(league_id: int, season: int | None) -> tuple[int, list[int]]:
    seasons = df(
        "select distinct season from core.fixtures where league_id = :l order by season desc", l=league_id
    )
    available = [int(s) for s in seasons["season"]]
    if not available:
        raise HTTPException(404, "Keine Spiele in diesem Wettbewerb")
    if season is None:
        current = df(
            """select season from core.fixtures where league_id = :l and kickoff_utc <= now() + interval '14 days'
               order by kickoff_utc desc limit 1""",
            l=league_id,
        )  # fmt: skip
        season = int(current.season[0]) if not current.empty else available[0]
    return season, available


def _teams(ids) -> dict[int, dict]:
    t = df(
        "select id, name, logo_url from core.teams where id = any(:ids)", ids=sorted({int(i) for i in ids})
    )
    return {int(r.id): {"id": int(r.id), "name": r.name, "logo": r.logo_url} for r in t.itertuples()}


def _tables(rows: pd.DataFrame) -> list[dict]:
    """Standings per table group (league: one table; cup: league phase or groups)."""
    out = []
    for group, g in rows[rows["group"].notna()].groupby("group", sort=True):
        teams = sorted(set(g["home_id"]) | set(g["away_id"]))
        out.append({"group": group or None, "rows": league_table.standings(g[g["finished"]], teams)})
    return out


@router.get("/competitions/{league_id}")
def competition_overview(league_id: int, season: int | None = None) -> dict:
    """Header and overview: progress of the season, table(s), knockout rounds of a cup, figures."""
    league = _league(league_id)
    season, seasons = _season(league_id, season)
    rows = _season_rows(league_id, season)
    done = rows[rows["finished"]]
    upcoming = rows[~rows["finished"] & ~rows["status"].isin(["PST", "CANC", "ABD"])]
    matchdays = rows["matchday"].dropna()
    played_md = done["matchday"].dropna()
    return {
        "league": league,
        "season": season,
        "seasons": seasons,
        "progress": {
            "matches": len(rows),
            "finished": len(done),
            "matchday": int(played_md.max()) if len(played_md) else None,
            "matchdays": int(matchdays.max()) if len(matchdays) else None,
            "next_kickoff": upcoming["kickoff"].min().isoformat() if len(upcoming) else None,
        },  # fmt: skip
        "tables": _tables(rows),
        "knockout": competition_stats.knockout_ties(rows) if league["cup"] else [],
        "figures": league_table.figures(done),
        "teams": _teams(pd.concat([rows["home_id"], rows["away_id"]])),
    }


def _probabilities(fixture_ids: list[int]) -> pd.DataFrame:
    probs = df(
        f"""with runs as ({chosen_runs_cte("and p.fixture_id = any(:ids)")})
            select p.fixture_id, p.selection, p.probability from analytics.predictions p
            join runs on runs.model_run_id = p.model_run_id and runs.fixture_id = p.fixture_id
            where p.market = '1x2' and p.fixture_id = any(:ids)""",
        ids=fixture_ids,
    )  # fmt: skip
    if probs.empty:
        return pd.DataFrame(columns=["fixture_id", "H", "D", "A"])
    return probs.pivot_table(index="fixture_id", columns="selection", values="probability").reset_index()


@router.get("/competitions/{league_id}/table")
def competition_table(league_id: int, season: int, group: str | None = None) -> dict:
    """Table variants of one table group: total, home, away, first / second half, last 5 matches, expected
    points from the model, and the position after every matchday."""
    _league(league_id)
    rows = _season_rows(league_id, season)
    groups = [g for g in rows["group"].dropna().unique()]
    if not groups:
        return {"season": season, "group": None, "groups": [], "tables": None}
    group = group if group in groups else ("" if "" in groups else sorted(groups)[0])
    g = rows[rows["group"] == group]
    done = g[g["finished"]]
    teams = sorted(set(g["home_id"]) | set(g["away_id"]))
    tables = {
        "total": league_table.standings(done, teams),
        "home": league_table.standings(done, teams, "home"),
        "away": league_table.standings(done, teams, "away"),
        "first_half": league_table.standings(competition_stats.half_matches(done, 1), teams),
        "second_half": league_table.standings(competition_stats.half_matches(done, 2), teams),
        "form": competition_stats.form_table(done, teams) if not done.empty else [],
    }
    return {
        "season": season,
        "group": group or None,
        "groups": sorted(x or "" for x in groups),
        "tables": tables,
        "expected": competition_stats.expected_table(
            done, _probabilities(done["fixture_id"].tolist()), teams
        ),
        "history": competition_stats.position_history(done, teams),
        "teams": _teams(teams),
    }


def _figures_with_extras(league_id: int, season: int) -> dict | None:
    rows = _season_rows(league_id, season)
    return league_table.figures(rows[rows["finished"]])


@router.get("/competitions/{league_id}/stats")
def competition_statistics(league_id: int, season: int) -> dict:
    """League figures (with the previous seasons for comparison), goal timing, halves, cards, penalties,
    own goals, and team rankings from the match statistics."""
    _league(league_id)
    rows = _season_rows(league_id, season)
    done = rows[rows["finished"]]
    ids = done["fixture_id"].tolist()
    events = df(
        """select e.fixture_id, e.minute, e.type, e.detail from core.fixture_events e
           where e.fixture_id = any(:ids) and e.type in ('Goal', 'Card')""",
        ids=ids,
    )
    goals = events[(events["type"] == "Goal") & (events["detail"] != "Missed Penalty")]
    with_events = int(events["fixture_id"].nunique())
    stats = df(
        """select s.fixture_id, s.team_id, s.shots_total, s.shots_on, s.xg::float as xg,
                  s.possession::float as possession, s.yellow, s.red, s.corners, s.fouls
           from core.fixture_team_stats s where s.period = 'FT' and s.fixture_id = any(:ids)""",
        ids=ids,
    )
    per_match = (
        stats.groupby("fixture_id")[["yellow", "red", "corners", "fouls", "shots_total"]].sum().mean()
        if not stats.empty
        else pd.Series(dtype=float)
    )
    halves = done.dropna(subset=["ht_home", "ht_away"])
    first = halves["ht_home"] + halves["ht_away"]
    second = halves["ft_home"] + halves["ft_away"] - first
    history = []
    for s in range(season - HISTORY_SEASONS, season):
        f = _figures_with_extras(league_id, s)
        if f:
            history.append({"season": s, **f})
    return {
        "season": season,
        "figures": league_table.figures(done),
        "history": history,
        "segments": competition_stats.goal_segments(goals, with_events) if with_events else [],
        "halves": None
        if halves.empty
        else {
            "first": float(first.mean()),
            "second": float(second.mean()),
            "matches": len(halves),
        },  # fmt: skip
        "events": {
            "matches": with_events,
            "penalties_scored": int((goals["detail"] == "Penalty").sum()),
            "penalties_missed": int(
                ((events["type"] == "Goal") & (events["detail"] == "Missed Penalty")).sum()
            ),
            "own_goals": int((goals["detail"] == "Own Goal").sum()),
            "red_cards": int(
                ((events["type"] == "Card") & events["detail"].fillna("").str.contains("Red")).sum()
            ),
        },
        "per_match": {k: (None if pd.isna(v) else float(v)) for k, v in per_match.items()},
        "teams_ranked": competition_stats.team_rankings(stats, done),
        "teams": _teams(pd.concat([rows["home_id"], rows["away_id"]])),
    }


@router.get("/competitions/{league_id}/players")
def competition_players(league_id: int, season: int) -> dict:
    """Player rankings of the season: goals, assists, scorer points, per 90 minutes, rating, cards."""
    _league(league_id)
    players = df(
        """select s.fixture_id, s.player_id, p.name, s.team_id, s.minutes, s.goals, s.assists, s.penalties_scored,
                  s.yellow, s.red, s.rating::float as rating, s.shots_total
           from core.fixture_player_stats s
           join core.fixtures f on f.id = s.fixture_id join core.players p on p.id = s.player_id
           where f.league_id = :l and f.season = :s and coalesce(s.minutes, 0) > 0""",
        l=league_id, s=season,
    )  # fmt: skip
    rankings = competition_stats.player_rankings(players)
    team_ids = {e["team_id"] for key, lst in rankings.items() if isinstance(lst, list) for e in lst}
    return {"season": season, "rankings": rankings, "teams": _teams(team_ids)}
