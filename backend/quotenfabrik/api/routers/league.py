"""League details of a fixture's competition season: table, top scorers, league figures (tab "Liga")."""

import pandas as pd
from fastapi import APIRouter, HTTPException

from quotenfabrik.analytics import league_table
from quotenfabrik.api.data import df
from quotenfabrik.api.labels import league_logo

router = APIRouter(prefix="/api", tags=["league"])

FINISHED = ("FT", "AET", "PEN", "AWD", "WO")
TOP_SCORERS, TOP_ASSISTS, TEAM_SCORERS = 15, 10, 3


@router.get("/fixtures/{fixture_id}/league")
def fixture_league(fixture_id: int) -> dict:
    """Table (total, home, away and before kickoff), top scorers and assists, league figures of the season."""
    fx = df("select league_id, season, round, kickoff_utc, home_team_id, away_team_id from core.fixtures where id = :id",
            id=fixture_id)  # fmt: skip
    if fx.empty:
        raise HTTPException(404, "Spiel nicht gefunden")
    f = next(fx.itertuples())
    league = df("select id, name from core.leagues where id = :id", id=int(f.league_id))
    rows = df(
        """select id, round, kickoff_utc as kickoff, status, home_team_id as home_id, away_team_id as away_id,
                  ft_home, ft_away
           from core.fixtures where league_id = :l and season = :s""",
        l=int(f.league_id), s=int(f.season),
    )  # fmt: skip
    rows["kickoff"] = pd.to_datetime(rows["kickoff"], utc=True)
    rows["group"] = rows["round"].map(league_table.table_group)
    group = league_table.table_group(f.round)
    if group is None and (rows["group"] == "").any():
        group = ""  # knockout match of a cup with a league phase: show the league phase
    finished = rows[rows["status"].isin(FINISHED) & rows["ft_home"].notna() & rows["ft_away"].notna()]

    tables = None
    if group is not None:
        in_table = rows[rows["group"] == group]
        teams = sorted(set(in_table["home_id"]) | set(in_table["away_id"]))
        done = finished[finished["group"] == group]
        before = done[done["kickoff"] < pd.Timestamp(f.kickoff_utc)]
        tables = {
            scope: league_table.standings(done, teams, scope) for scope in ("total", "home", "away")
        } | {"before": league_table.standings(before, teams)}

    goals = df(
        """select e.player_id as scorer_id, coalesce(ps.name, e.player_name) as scorer_name,
                  e.assist_player_id as assist_id, pa.name as assist_name, e.team_id,
                  (e.detail = 'Penalty') as penalty
           from core.fixture_events e
           join core.fixtures f on f.id = e.fixture_id
           left join core.players ps on ps.id = e.player_id
           left join core.players pa on pa.id = e.assist_player_id
           where f.league_id = :l and f.season = :s and f.status = any(:finished)
             and e.type = 'Goal' and coalesce(e.detail, '') not in ('Own Goal', 'Missed Penalty')""",
        l=int(f.league_id), s=int(f.season), finished=list(FINISHED),
    )  # fmt: skip
    home, away = int(f.home_team_id), int(f.away_team_id)
    team_ids = {home, away} | {int(t) for t in goals["team_id"].dropna()}
    if tables:
        team_ids |= {r["team_id"] for r in tables["total"]}
    teams = df("select id, name, logo_url from core.teams where id = any(:ids)", ids=sorted(team_ids))
    return {
        "league": None if league.empty else {"id": int(league.id[0]), "name": league.name[0],
                                             "logo": league_logo(int(league.id[0]))},
        "season": int(f.season),
        "group": group or None,
        "teams": {int(t.id): {"id": int(t.id), "name": t.name, "logo": t.logo_url} for t in teams.itertuples()},
        "home_id": home,
        "away_id": away,
        "table": tables,
        "scorers": league_table.top_players(goals, "scorer", TOP_SCORERS),
        "assists": league_table.top_players(goals, "assist", TOP_ASSISTS),
        "team_scorers": {
            side: league_table.top_players(goals[goals["team_id"] == team], "scorer", TEAM_SCORERS)
            for side, team in (("home", home), ("away", away))
        },
        "figures": league_table.figures(finished),
    }  # fmt: skip
