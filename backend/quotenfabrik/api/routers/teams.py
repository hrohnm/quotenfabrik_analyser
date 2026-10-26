"""Team page: header (competitions, venue, coach, form), statistics, squad; search for teams."""

from collections import Counter
from datetime import UTC, datetime

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from quotenfabrik import app_config
from quotenfabrik.analytics import league_table, team_stats
from quotenfabrik.api.data import chosen_runs_cte, df
from quotenfabrik.api.labels import MEDIA_BASE, league_logo

router = APIRouter(prefix="/api", tags=["teams"])

FINISHED = ("FT", "AET", "PEN", "AWD", "WO")
POSITION_ORDER = {"G": 0, "D": 1, "M": 2, "F": 3}


def player_photo(player_id: int) -> str:
    return f"{MEDIA_BASE}/players/{player_id}.png"


def _clean(v):
    if v is None or (isinstance(v, float) and v != v):
        return None
    return v.item() if hasattr(v, "item") else v


def _team(team_id: int) -> dict:
    t = df("select id, name, logo_url from core.teams where id = :id", id=team_id)
    if t.empty:
        raise HTTPException(404, "Mannschaft nicht gefunden")
    return {"id": team_id, "name": t.name[0], "logo": t.logo_url[0]}


def _matches(team_id: int, season: int, leagues: list[int]) -> pd.DataFrame:
    """Fixtures of the team in the season (shown competitions), with results and half-time scores."""
    m = df(
        """select f.id as fixture_id, f.league_id, f.season, f.round, f.kickoff_utc as kickoff, f.status,
                  f.home_team_id as home_id, f.away_team_id as away_id, f.ft_home as hg, f.ft_away as ag,
                  f.ht_home as hthg, f.ht_away as htag, f.venue_id
           from core.fixtures f
           where (f.home_team_id = :t or f.away_team_id = :t) and f.season = :s and f.league_id = any(:leagues)
           order by f.kickoff_utc""",
        t=team_id, s=season, leagues=leagues,
    )  # fmt: skip
    m["kickoff"] = pd.to_datetime(m["kickoff"], utc=True)
    m["finished"] = m["status"].isin(FINISHED) & m["hg"].notna() & m["ag"].notna()
    return m


def _seasons(team_id: int, leagues: list[int]) -> list[int]:
    s = df(
        """select distinct season from core.fixtures
           where (home_team_id = :t or away_team_id = :t) and league_id = any(:leagues) order by season desc""",
        t=team_id, leagues=leagues,
    )  # fmt: skip
    return [int(x) for x in s["season"]]


def _current_season(team_id: int, leagues: list[int]) -> int | None:
    """Season of the team's latest match up to two weeks ahead (otherwise its latest season)."""
    s = df(
        """select season from core.fixtures
           where (home_team_id = :t or away_team_id = :t) and league_id = any(:leagues)
             and kickoff_utc <= now() + interval '14 days'
           order by kickoff_utc desc limit 1""",
        t=team_id, leagues=leagues,
    )  # fmt: skip
    if not s.empty:
        return int(s.season[0])
    seasons = _seasons(team_id, leagues)
    return seasons[0] if seasons else None


def _competitions(team_id: int, season: int, matches: pd.DataFrame) -> list[dict]:
    """Competitions of the season with the team's table position (league or league / group phase)."""
    leagues = df(
        "select id, name, flag_url from core.leagues where id = any(:ids)",
        ids=sorted(int(x) for x in matches["league_id"].unique()),
    ).set_index("id")
    out = []
    for league_id, own in matches.groupby("league_id"):
        all_rows = df(
            """select id as fixture_id, round, kickoff_utc as kickoff, status, home_team_id as home_id,
                      away_team_id as away_id, ft_home, ft_away
               from core.fixtures where league_id = :l and season = :s""",
            l=int(league_id), s=season,
        )  # fmt: skip
        all_rows["kickoff"] = pd.to_datetime(all_rows["kickoff"], utc=True)
        all_rows["group"] = all_rows["round"].map(league_table.table_group)
        groups = [g for g in own["round"].map(league_table.table_group) if g is not None]
        group = Counter(groups).most_common(1)[0][0] if groups else None
        entry = {
            "league": {"id": int(league_id), "name": leagues.loc[league_id, "name"], "logo": league_logo(int(league_id)),
                       "flag": _clean(leagues.loc[league_id, "flag_url"]), "cup": app_config.is_cup(int(league_id))},
            "played": int(own["finished"].sum()), "rank": None, "points": None, "teams": None,
            "group": group or None,
        }  # fmt: skip
        if group is not None:
            rows = all_rows[all_rows["group"] == group]
            done = rows[rows["status"].isin(FINISHED) & rows["ft_home"].notna() & rows["ft_away"].notna()]
            teams = sorted(set(rows["home_id"]) | set(rows["away_id"]))
            table = league_table.standings(done, teams)
            mine = next((r for r in table if r["team_id"] == team_id), None)
            if mine:
                entry.update(rank=mine["rank"], points=mine["points"], teams=len(table))
        out.append(entry)
    return sorted(out, key=lambda c: (c["league"]["cup"], -c["played"]))


@router.get("/teams/{team_id}")
def team_overview(team_id: int, season: int | None = None) -> dict:
    """Header of the team page: competitions with position, venue, coach, form, key figures, streaks."""
    team = _team(team_id)
    leagues = app_config.shown_league_ids()
    season = season or _current_season(team_id, leagues)
    if season is None:
        raise HTTPException(404, "Keine Spiele dieser Mannschaft in den angezeigten Wettbewerben")
    matches = _matches(team_id, season, leagues)
    venue = df(
        """select v.id, v.name, v.city from core.fixtures f join core.venues v on v.id = f.venue_id
           where f.home_team_id = :t and f.kickoff_utc <= now() order by f.kickoff_utc desc limit 1""",
        t=team_id,
    )
    coach = df(
        """select l.coach_id, l.coach_name from core.fixture_lineups l join core.fixtures f on f.id = l.fixture_id
           where l.team_id = :t and l.coach_name is not null order by f.kickoff_utc desc limit 1""",
        t=team_id,
    )
    done = matches[matches["finished"]]
    view = team_stats.team_view(done, team_id) if not done.empty else None
    opponents = df("select id, name, logo_url from core.teams where id = any(:ids)",
                   ids=sorted({int(x) for x in pd.concat([matches["home_id"], matches["away_id"]])}))  # fmt: skip
    names = {int(r.id): {"id": int(r.id), "name": r.name, "logo": r.logo_url} for r in opponents.itertuples()}
    form = []
    if view is not None:
        for r in view.tail(6).itertuples():
            form.append({"fixture_id": int(r.fixture_id), "result": r.result, "score": [int(r.gf), int(r.ga)],
                         "home": bool(r.home), "opponent": names.get(int(r.opponent_id)),
                         "league_id": int(r.league_id)})  # fmt: skip
    return {
        "team": team,
        "season": season,
        "seasons": _seasons(team_id, leagues),
        "competitions": _competitions(team_id, season, matches) if not matches.empty else [],
        "venue": None if venue.empty else {"id": int(venue.id[0]), "name": venue.name[0], "city": _clean(venue.city[0]),
                                           "image": f"{MEDIA_BASE}/venues/{int(venue.id[0])}.png"},
        "coach": None if coach.empty or pd.isna(coach.coach_name[0]) else {
            "id": _clean(coach.coach_id[0]), "name": coach.coach_name[0],
            "photo": f"{MEDIA_BASE}/coachs/{int(coach.coach_id[0])}.png" if pd.notna(coach.coach_id[0]) else None},
        "form": form,
        "totals": team_stats.split(view) if view is not None else {"played": 0},
        "streaks": team_stats.streaks(view) if view is not None else [],
        "expected_points": _expected_points(team_id, view) if view is not None else None,
    }  # fmt: skip


def _expected_points(team_id: int, view: pd.DataFrame) -> dict | None:
    probs = df(
        f"""with runs as ({chosen_runs_cte("and p.fixture_id = any(:ids)")})
            select p.fixture_id, p.selection, p.probability, f.home_team_id
            from analytics.predictions p
            join runs on runs.model_run_id = p.model_run_id and runs.fixture_id = p.fixture_id
            join core.fixtures f on f.id = p.fixture_id
            where p.market = '1x2' and p.fixture_id = any(:ids)""",
        ids=[int(x) for x in view["fixture_id"]],
    )  # fmt: skip
    if probs.empty:
        return None
    wide = probs.pivot_table(index=["fixture_id", "home_team_id"], columns="selection", values="probability")
    wide = wide.reset_index()
    home = wide["home_team_id"] == team_id
    frame = pd.DataFrame({"fixture_id": wide["fixture_id"], "p_draw": wide["D"],
                          "p_win": wide["H"].where(home, wide["A"])})  # fmt: skip
    return team_stats.expected_points(view, frame)


@router.get("/teams/{team_id}/stats")
def team_statistics(team_id: int, season: int, competition: int | None = None) -> dict:
    """Home / away splits, goal timing, streaks, match statistics against the league average."""
    leagues = [competition] if competition else app_config.shown_league_ids()
    matches = _matches(team_id, season, leagues)
    done = matches[matches["finished"]]
    if done.empty:
        return {"season": season, "competition": competition, "splits": None}
    view = team_stats.team_view(done, team_id)
    goals = df(
        """select e.fixture_id, e.minute, e.team_id as scoring_team
           from core.fixture_events e
           where e.fixture_id = any(:ids) and e.type = 'Goal' and coalesce(e.detail, '') <> 'Missed Penalty'""",
        ids=[int(x) for x in done["fixture_id"]],
    )  # fmt: skip
    with_events = goals["fixture_id"].nunique()
    # match statistics: the competition, by default the team's league (most matches among the full leagues)
    full = set(app_config.league_ids())
    counts = done[done["league_id"].isin(full)]["league_id"].value_counts()
    stats_league = competition or (int(counts.index[0]) if len(counts) else int(done["league_id"].iloc[0]))
    stats = df(
        """select s.fixture_id, s.team_id, s.shots_total, s.shots_on, s.xg::float as xg, s.possession::float as possession,
                  s.corners, s.fouls, s.yellow, s.passes_total, s.passes_accurate
           from core.fixture_team_stats s join core.fixtures f on f.id = s.fixture_id
           where s.period = 'FT' and f.league_id = :l and f.season = :s""",
        l=stats_league, s=season,
    )  # fmt: skip
    league_name = df("select name from core.leagues where id = :id", id=stats_league)
    return {
        "season": season,
        "competition": competition,
        "splits": team_stats.splits(view),
        "segments": team_stats.goal_segments(goals, team_id, int(with_events)) if with_events else [],
        "streaks": team_stats.streaks(view),
        "match_stats": {
            "league": {"id": stats_league, "name": None if league_name.empty else league_name.name[0]},
            "rows": team_stats.stat_averages(stats, team_id) if not stats.empty else [],
        },
        "expected_points": _expected_points(team_id, view),
    }


@router.get("/teams/{team_id}/squad")
def team_squad(team_id: int, season: int) -> dict:
    """Players of the season (all shown competitions): appearances, minutes, goals, assists, cards, rating,
    shirt number, current absence; most frequent starting XI and rotation between matches."""
    leagues = app_config.shown_league_ids()
    rows = df(
        """select s.fixture_id, f.kickoff_utc as kickoff, s.player_id, p.name, s.is_starter, s.minutes, s.goals,
                  s.assists, s.yellow, s.red, s.rating::float as rating, s.position, s.shots_total, s.key_passes
           from core.fixture_player_stats s
           join core.fixtures f on f.id = s.fixture_id join core.players p on p.id = s.player_id
           where s.team_id = :t and f.season = :s and f.league_id = any(:leagues)""",
        t=team_id, s=season, leagues=leagues,
    )  # fmt: skip
    if rows.empty:
        return {"season": season, "players": [], "common_xi": None, "rotation": None}
    rows["kickoff"] = pd.to_datetime(rows["kickoff"], utc=True)
    played = rows[(rows["minutes"].fillna(0) > 0) | rows["is_starter"].fillna(False)]
    numbers = df(
        """select distinct on (lp.player_id) lp.player_id, lp.number, lp.pos
           from core.fixture_lineup_players lp join core.fixtures f on f.id = lp.fixture_id
           where lp.team_id = :t order by lp.player_id, f.kickoff_utc desc""",
        t=team_id,
    ).set_index("player_id")  # fmt: skip
    absent = df(
        """select i.player_id, i.type, i.reason from core.injuries i
           where i.team_id = :t and i.fixture_id = (
               select f.id from core.fixtures f where (f.home_team_id = :t or f.away_team_id = :t)
                 and f.kickoff_utc > now() - interval '3 hours' order by f.kickoff_utc limit 1)""",
        t=team_id,
    ).set_index("player_id")  # fmt: skip
    from quotenfabrik.analytics.availability import absence_reason

    players = []
    for pid, g in played.groupby("player_id"):
        pid = int(pid)
        rated = g["rating"].dropna()
        position = g.sort_values("kickoff")["position"].dropna()
        status = None
        if pid in absent.index:
            a = absent.loc[pid]
            status = {"type": "doubtful" if a["type"] == "Questionable" else "missing",
                      "reason": absence_reason(_clean(a["reason"]))}  # fmt: skip
        players.append({
            "player_id": pid, "name": g["name"].iloc[0], "photo": player_photo(pid),
            "position": position.iloc[-1] if len(position) else _clean(numbers["pos"].get(pid)),
            "number": _clean(numbers["number"].get(pid)) if pid in numbers.index else None,
            "apps": len(g), "starts": int(g["is_starter"].fillna(False).sum()),
            "minutes": int(g["minutes"].fillna(0).sum()), "goals": int(g["goals"].fillna(0).sum()),
            "assists": int(g["assists"].fillna(0).sum()), "yellow": int(g["yellow"].fillna(0).sum()),
            "red": int(g["red"].fillna(0).sum()), "rating": float(rated.mean()) if len(rated) else None,
            "shots": int(g["shots_total"].fillna(0).sum()), "key_passes": int(g["key_passes"].fillna(0).sum()),
            "status": status,
        })  # fmt: skip
    players.sort(key=lambda p: (POSITION_ORDER.get(p["position"] or "", 4), -p["minutes"]))
    return {"season": season, "players": players, **_starting_xi(team_id, season, leagues)}


def _starting_xi(team_id: int, season: int, leagues: list[int]) -> dict:
    """Most frequent formation and starters of the season, and average changes to the XI between matches."""
    xi = df(
        """select lp.fixture_id, f.kickoff_utc as kickoff, lp.player_id, lp.player_name, lp.number, lp.pos,
                  l.formation
           from core.fixture_lineup_players lp
           join core.fixtures f on f.id = lp.fixture_id
           left join core.fixture_lineups l on l.fixture_id = lp.fixture_id and l.team_id = lp.team_id
           where lp.team_id = :t and lp.is_starter and f.season = :s and f.league_id = any(:leagues)
           order by f.kickoff_utc""",
        t=team_id, s=season, leagues=leagues,
    )  # fmt: skip
    if xi.empty:
        return {"common_xi": None, "rotation": None}
    per_match = xi.groupby("fixture_id", sort=False)
    sets = [set(g["player_id"]) for _, g in per_match]
    changes = [len(b - a) for a, b in zip(sets, sets[1:], strict=False)]
    formation = xi.drop_duplicates("fixture_id")["formation"].dropna()
    starts = xi.groupby("player_id").agg(name=("player_name", "last"), number=("number", "last"),
                                          pos=("pos", "last"), starts=("fixture_id", "nunique"))  # fmt: skip
    top = starts.sort_values("starts", ascending=False).head(11).reset_index()
    top["order"] = top["pos"].map(POSITION_ORDER).fillna(4)
    common = [{"player_id": int(r.player_id), "name": r.name, "number": _clean(r.number), "pos": r.pos,
               "starts": int(r.starts), "photo": player_photo(int(r.player_id))}
              for r in top.sort_values(["order", "starts"], ascending=[True, False]).itertuples()]  # fmt: skip
    return {
        "common_xi": {"formation": formation.mode().iloc[0] if len(formation) else None,
                      "matches": len(sets), "players": common},
        "rotation": {"avg_changes": float(sum(changes) / len(changes)) if changes else None, "matches": len(sets)},
    }  # fmt: skip


@router.get("/search")
def search(q: str = Query(..., min_length=2), limit: int = Query(8, le=20)) -> dict:
    """Teams of the shown competitions and players (with matches in the last two years) whose name contains
    ``q``."""
    teams = df(
        """select t.id, t.name, t.logo_url, max(f.kickoff_utc) as last, max(f.league_id) filter (
                   where f.league_id = any(:full)) as league_id
           from core.teams t
           join core.fixtures f on (f.home_team_id = t.id or f.away_team_id = t.id) and f.league_id = any(:shown)
           where t.name ilike :q
           group by t.id order by (t.name ilike :prefix) desc, last desc limit :n""",
        q=f"%{q}%", prefix=f"{q}%", n=limit, full=app_config.league_ids(), shown=app_config.shown_league_ids(),
    )  # fmt: skip
    players = df(
        """select p.id, p.name, (array_agg(s.team_id order by f.kickoff_utc desc))[1] as team_id,
                  sum(coalesce(s.minutes, 0)) as minutes
           from core.players p
           join core.fixture_player_stats s on s.player_id = p.id
           join core.fixtures f on f.id = s.fixture_id
           where p.name ilike :q and f.kickoff_utc > now() - interval '2 years'
           group by p.id order by (p.name ilike :prefix) desc, minutes desc limit :n""",
        q=f"%{q}%", prefix=f"{q}%", n=limit,
    )  # fmt: skip
    team_names = df("select id, name, logo_url from core.teams where id = any(:ids)",
                    ids=[int(x) for x in players["team_id"].dropna()]).set_index("id")  # fmt: skip
    now = datetime.now(UTC)
    return {
        "players": [{"id": int(r.id), "name": r.name, "photo": f"{MEDIA_BASE}/players/{int(r.id)}.png",
                     "team": None if r.team_id not in team_names.index else
                     {"id": int(r.team_id), "name": team_names.at[r.team_id, "name"],
                      "logo": team_names.at[r.team_id, "logo_url"]}}
                    for r in players.itertuples()],
        "teams": [{"id": int(r.id), "name": r.name, "logo": r.logo_url,
                   "league_id": _clean(r.league_id),
                   "active": bool(pd.notna(r.last) and (now - pd.Timestamp(r.last)).days < 400)}
                  for r in teams.itertuples()],
    }  # fmt: skip


@router.get("/teams/{team_id}/betting")
def team_betting(team_id: int, season: int) -> dict:
    """ "Wetten & Modell" for the team's matches of the season (all shown competitions)."""
    from quotenfabrik.api import betting_report

    matches = _matches(team_id, season, app_config.shown_league_ids())
    ids = matches["fixture_id"].astype(int).tolist()
    finished = matches.loc[matches["finished"], "fixture_id"].astype(int).tolist()
    return {"season": season, **betting_report.report(finished, "l.fixture_id = any(:ids)", ids=ids)}
