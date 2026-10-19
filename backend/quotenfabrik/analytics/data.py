"""Loads match data for the models (regular-season fixtures of a league) as pandas DataFrames."""

import pandas as pd
from sqlalchemy import Engine, text

_MATCHES_SQL = text(
    """
    select f.id as fixture_id, f.season, f.matchday, f.kickoff_utc as kickoff, f.status,
           f.home_team_id as home_id, f.away_team_id as away_id,
           f.ft_home as hg, f.ft_away as ag, f.ht_home as hthg, f.ht_away as htag,
           sh.xg as hxg, sa.xg as axg, sh.shots_total as hs, sa.shots_total as as_, sh.shots_on as hst,
           sa.shots_on as ast
    from core.fixtures f
    left join core.fixture_team_stats sh
           on sh.fixture_id = f.id and sh.team_id = f.home_team_id and sh.period = 'FT'
    left join core.fixture_team_stats sa
           on sa.fixture_id = f.id and sa.team_id = f.away_team_id and sa.period = 'FT'
    where f.league_id = :league and f.round like 'Regular Season%'
    order by f.kickoff_utc, f.id
    """
)

FINISHED = ("FT", "AET", "PEN", "AWD", "WO")


def league_name(engine: Engine, league_id: int) -> str:
    with engine.connect() as conn:
        name = conn.execute(text("select name from core.leagues where id = :id"), {"id": league_id}).scalar()
    return name or f"Liga {league_id}"


def with_league(markdown: str, name: str) -> str:
    """Adds the league to the report title (first line)."""
    title, _, rest = markdown.partition("\n")
    return f"{title} · {name}\n{rest}"


def load_matches(engine: Engine, league_id: int) -> pd.DataFrame:
    """All regular-season fixtures (finished and upcoming). Goal columns are NaN for unplayed fixtures."""
    df = pd.read_sql(_MATCHES_SQL, engine, params={"league": league_id})
    df["kickoff"] = pd.to_datetime(df["kickoff"], utc=True)
    df["finished"] = df["status"].isin(FINISHED) & df["hg"].notna() & df["hthg"].notna()
    df["h2g"] = df["hg"] - df["hthg"]
    df["a2g"] = df["ag"] - df["htag"]
    for col in ("hxg", "axg"):
        df[col] = df[col].astype(float)
    return df


_PLAYERS_SQL = text(
    """
    select p.fixture_id, f.kickoff_utc as kickoff, f.season, p.team_id, p.player_id, pl.name,
           p.position, p.is_starter, coalesce(p.minutes, 0) as minutes, coalesce(p.goals, 0) as goals,
           coalesce(p.penalties_scored, 0) as pen_goals, coalesce(p.shots_total, 0) as shots,
           coalesce(p.shots_on, 0) as shots_on
    from core.fixture_player_stats p
    join core.fixtures f on f.id = p.fixture_id
    join core.players pl on pl.id = p.player_id
    where f.league_id = :league and f.round like 'Regular Season%'
    order by f.kickoff_utc
    """
)

_GOALS_SQL = text(
    """
    select e.fixture_id, e.team_id, e.player_id, e.minute, e.extra_minute, e.detail
    from core.fixture_events e
    join core.fixtures f on f.id = e.fixture_id
    where f.league_id = :league and f.round like 'Regular Season%'
      and e.type = 'Goal' and e.detail <> 'Missed Penalty' and e.minute <= 90
    """
)


_LEAGUE_TEAMS_SQL = text(
    """
    select distinct league_id, team_id from (
        select league_id, home_team_id as team_id from core.fixtures where round like 'Regular Season%'
        union select league_id, away_team_id from core.fixtures where round like 'Regular Season%'
    ) t where league_id = any(:leagues)
    """
)


def connected_leagues(engine: Engine, league_id: int, candidates: list[int]) -> list[int]:
    """Leagues among ``candidates`` linked to ``league_id`` by teams that played in both (directly or via
    further leagues), e.g. 1. and 2. Bundesliga through promoted and relegated teams."""
    pool = sorted(set(candidates) | {league_id})
    with engine.connect() as conn:
        rows = conn.execute(_LEAGUE_TEAMS_SQL, {"leagues": pool}).all()
    teams: dict[int, set[int]] = {}
    for lg, team in rows:
        teams.setdefault(lg, set()).add(team)
    found, todo = {league_id}, [league_id]
    while todo:
        cur = todo.pop()
        for lg, ts in teams.items():
            if lg not in found and ts & teams.get(cur, set()):
                found.add(lg)
                todo.append(lg)
    return sorted(found)


def load_leagues(engine: Engine, league_ids: list[int]) -> pd.DataFrame:
    """Regular-season matches of several leagues with a ``league_id`` column (input of the joint model)."""
    frames = [load_matches(engine, lg).assign(league_id=lg) for lg in league_ids]
    return pd.concat(frames, ignore_index=True).sort_values(["kickoff", "fixture_id"], ignore_index=True)


def season_leagues(matches: pd.DataFrame) -> dict[int, dict[int, int]]:
    """{season: {team: league}} from the fixture schedule (known before the season starts)."""
    out: dict[int, dict[int, int]] = {}
    if "league_id" not in matches.columns:
        return out
    for (season, league), g in matches.groupby(["season", "league_id"]):
        for t in set(g["home_id"]) | set(g["away_id"]):
            out.setdefault(int(season), {})[int(t)] = int(league)
    return out


def load_player_matches(engine: Engine, league_id: int) -> pd.DataFrame:
    df = pd.read_sql(_PLAYERS_SQL, engine, params={"league": league_id})
    df["kickoff"] = pd.to_datetime(df["kickoff"], utc=True)
    return df


def load_goal_events(engine: Engine, league_id: int) -> pd.DataFrame:
    return pd.read_sql(_GOALS_SQL, engine, params={"league": league_id})
