"""Match-day context the goal model does not see: schedule (rest, upcoming European cup match) and
availability (reported absences, rotation in the confirmed line-up).

One row per fixture and team, built only from information available before kickoff:

* schedule – the fixture list of all competitions in the database (dates are published in advance):
  ``rest_days`` since the team's previous match, ``prev_cup`` (European cup match ≤ 4 days before),
  ``next_cup`` (European cup match ≤ 4 days after), ``games_14d`` (matches in the 14 days before).
  Domestic cups (DFB-Pokal) are not in the database and therefore not covered.
* absences – ``core.injuries`` of the fixture (``Missing Fixture``), weighted with the player's role in the
  team's last ``WINDOW`` matches with player data (all competitions): ``miss_starters`` = sum of start shares
  (≈ number of regular starters missing), ``miss_attack`` = share of the team's goals + assists,
  ``miss_defense`` = start shares of goalkeepers and defenders, ``doubtful`` = start shares of "Questionable".
* rotation – confirmed starting XI (published 20–40 minutes before kickoff): ``rotated`` = start shares of
  regular starters who are neither in the XI nor reported absent.
"""

import numpy as np
import pandas as pd
from sqlalchemy import Engine, text

WINDOW = 10  # matches with player data that define a player's role
CUP_GAP_DAYS = 4.5  # "European cup match on Tuesday/Wednesday/Thursday next to a weekend league match"
REST_CAP = 14.0
NOT_PLAYED = ("PST", "CANC", "ABD")

FEATURES = {
    "schedule": ["short_rest", "prev_cup", "next_cup", "games_14d"],
    "absences": ["miss_starters", "miss_attack", "miss_defense", "doubtful"],
    "rotation": ["rotated"],
}


def load_schedule(engine: Engine, cup_league_ids: list[int]) -> pd.DataFrame:
    """All fixtures of all competitions (one row per fixture and team)."""
    with engine.connect() as conn:
        f = pd.read_sql(
            text("""select id as fixture_id, league_id, kickoff_utc as kickoff, home_team_id, away_team_id
                    from core.fixtures where status <> all(:skip)"""),
            conn,
            params={"skip": list(NOT_PLAYED)},
        )
    f["kickoff"] = pd.to_datetime(f["kickoff"], utc=True)
    f["cup"] = f["league_id"].isin(cup_league_ids)
    home = f.rename(columns={"home_team_id": "team_id"}).drop(columns="away_team_id")
    away = f.rename(columns={"away_team_id": "team_id"}).drop(columns="home_team_id")
    return pd.concat([home, away], ignore_index=True).sort_values(["team_id", "kickoff"], ignore_index=True)


def schedule_features(schedule: pd.DataFrame) -> pd.DataFrame:
    """Schedule features per (fixture_id, team_id) for every fixture in ``schedule``."""
    s = schedule.sort_values(["team_id", "kickoff"]).copy()
    g = s.groupby("team_id")
    days = lambda a, b: (a - b).dt.total_seconds() / 86400  # noqa: E731
    prev_kick, next_kick = g["kickoff"].shift(1), g["kickoff"].shift(-1)
    s["rest_days"] = days(s["kickoff"], prev_kick).clip(upper=REST_CAP).fillna(REST_CAP)
    s["prev_cup"] = g["cup"].shift(1).fillna(False).astype(bool) & (
        days(s["kickoff"], prev_kick) <= CUP_GAP_DAYS
    )
    s["next_cup"] = g["cup"].shift(-1).fillna(False).astype(bool) & (
        days(next_kick, s["kickoff"]) <= CUP_GAP_DAYS
    )
    s["short_rest"] = (s["rest_days"] <= 3.5).astype(float)
    counts = []
    for _, t in s.groupby("team_id", sort=False):
        k = t["kickoff"].dt.tz_convert(None).to_numpy()
        lo = np.searchsorted(k, k - np.timedelta64(14, "D"), side="left")
        counts.append(pd.Series(np.arange(len(k)) - lo, index=t.index))
    s["games_14d"] = pd.concat(counts).clip(upper=5).astype(float)
    s["prev_cup"] = s["prev_cup"].astype(float)
    s["next_cup"] = s["next_cup"].astype(float)
    return s[["fixture_id", "team_id", "rest_days", *FEATURES["schedule"]]]


def load_player_roles(engine: Engine) -> pd.DataFrame:
    """Player rows of all fixtures with player data (starts, minutes, goals, assists, position)."""
    with engine.connect() as conn:
        p = pd.read_sql(
            text("""select s.fixture_id, f.kickoff_utc as kickoff, s.team_id, s.player_id, s.is_starter,
                           coalesce(s.minutes, 0) as minutes, coalesce(s.goals, 0) + coalesce(s.assists, 0) as ga,
                           s.position
                    from core.fixture_player_stats s join core.fixtures f on f.id = s.fixture_id
                    where s.is_starter is not null"""),
            conn,
        )
    p["kickoff"] = pd.to_datetime(p["kickoff"], utc=True)
    return p.sort_values(["team_id", "kickoff"], ignore_index=True)


def load_absences(engine: Engine) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text("select fixture_id, team_id, player_id, type from core.injuries"), conn)


def load_starting_xi(engine: Engine) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(
            text("select fixture_id, team_id, player_id from core.fixture_lineup_players where is_starter"),
            conn,
        )


def roles_before(
    players: pd.DataFrame, team_id: int, kickoff: pd.Timestamp, window: int = WINDOW
) -> pd.DataFrame:
    """Role of each player in the team's last ``window`` matches before ``kickoff``: ``start_share``,
    ``attack_share`` (share of the team's goals + assists) and the latest ``position``."""
    t = players[(players["team_id"] == team_id) & (players["kickoff"] < kickoff)]
    recent = t["fixture_id"].drop_duplicates().tail(window)
    t = t[t["fixture_id"].isin(recent)]
    if t.empty:
        return pd.DataFrame(columns=["start_share", "attack_share", "position"])
    n = len(recent)
    total_ga = max(float(t["ga"].sum()), 1.0)
    out = t.groupby("player_id").agg(
        starts=("is_starter", "sum"), ga=("ga", "sum"), position=("position", "last")
    )
    out["start_share"] = out["starts"] / n
    out["attack_share"] = out["ga"] / total_ga
    return out[["start_share", "attack_share", "position"]]


def availability_features(
    fixtures: pd.DataFrame, players: pd.DataFrame, absences: pd.DataFrame, xi: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Absence (and, with ``xi``, rotation) features per row of ``fixtures`` (fixture_id, team_id, kickoff)."""
    by_team = {t: g for t, g in players.groupby("team_id")}
    absent = {k: g for k, g in absences.groupby(["fixture_id", "team_id"])}
    starters = {
        k: set(g["player_id"]) for k, g in (xi.groupby(["fixture_id", "team_id"]) if xi is not None else [])
    }
    rows = []
    for f in fixtures.itertuples(index=False):
        roles = roles_before(by_team.get(f.team_id, players.iloc[0:0]), f.team_id, f.kickoff)
        a = absent.get((f.fixture_id, f.team_id))
        missing = set(a.loc[a["type"] != "Questionable", "player_id"]) if a is not None else set()
        doubtful = set(a.loc[a["type"] == "Questionable", "player_id"]) if a is not None else set()
        m = roles[roles.index.isin(missing)]
        row = {
            "fixture_id": f.fixture_id,
            "team_id": f.team_id,
            "has_roles": not roles.empty,
            "miss_starters": float(m["start_share"].sum()),
            "miss_attack": float(m["attack_share"].sum()),
            "miss_defense": float(m.loc[m["position"].isin(["G", "D"]), "start_share"].sum()),
            "doubtful": float(roles.loc[roles.index.isin(doubtful), "start_share"].sum()),
        }
        if xi is not None:
            xi_players = starters.get((f.fixture_id, f.team_id))
            if xi_players is None:
                row["rotated"] = np.nan
            else:
                regular = roles[(roles["start_share"] >= 0.5) & ~roles.index.isin(missing)]
                row["rotated"] = float(regular.loc[~regular.index.isin(xi_players), "start_share"].sum())
        rows.append(row)
    return pd.DataFrame(rows)
