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
                           coalesce(s.minutes, 0) as minutes,
                           coalesce(s.goals, 0) + coalesce(s.assists, 0) as ga,
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
    """Absence (with ``xi`` also rotation) features per row of ``fixtures`` (fixture_id, team_id, kickoff)."""
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


# --------------------------------------------------------------------------- context of one fixture (display)

REGULAR = 0.5  # start share from which a player counts as regular starter

REASONS = {
    "Knee Injury": "Knieverletzung", "Muscle Injury": "Muskelverletzung",
    "Ankle Injury": "Sprunggelenksverletzung",
    "Injury": "Verletzung", "Illness": "Krankheit", "Thigh Injury": "Oberschenkelverletzung",
    "Groin Injury": "Leistenverletzung", "Yellow Cards": "Gelbsperre", "Calf Injury": "Wadenverletzung",
    "Shoulder Injury": "Schulterverletzung", "Hip Injury": "Hüftverletzung", "Red Card": "Rotsperre",
    "Foot Injury": "Fußverletzung", "Achilles Tendon Injury": "Achillessehnenverletzung",
    "Back Injury": "Rückenverletzung", "Leg Injury": "Beinverletzung", "Knock": "Prellung",
    "Lacking Match Fitness": "fehlende Spielpraxis", "Jumpers knee": "Patellasehne",
    "National selection": "Nationalmannschaft", "Tendon Injury": "Sehnenverletzung",
    "Hamstring Injury": "Oberschenkel hinten", "Broken ankle": "Knöchelbruch",
    "Abdominal strain": "Bauchmuskelzerrung", "Concussion": "Gehirnerschütterung", "Broken Leg": "Beinbruch",
    "Toe Injury": "Zehenverletzung", "Inactive": "inaktiv", "International duty": "Länderspielreise",
    "Broken calfbone": "Wadenbeinbruch", "Finger Injury": "Fingerverletzung",
    "Muscle bruise": "Muskelprellung",
    "Head Injury": "Kopfverletzung", "Hand Injury": "Handverletzung", "Elbow Injury": "Ellenbogenverletzung",
    "Suspended": "gesperrt", "Surgery": "Operation", "Stomach Disorder": "Magenprobleme",
    "Wrist Injury": "Handgelenksverletzung", "Personal Reasons": "persönliche Gründe",
    "Contusion": "Prellung",
    "Health problems": "gesundheitliche Probleme", "Broken shinbone": "Schienbeinbruch",
    "Heart Problems": "Herzprobleme", "Wound": "Wunde",
}  # fmt: skip


def absence_reason(reason: str | None) -> str:
    if not isinstance(reason, str) or not reason:
        return "Grund unbekannt"
    return REASONS.get(reason, reason)


def neighbour_matches(schedule: pd.DataFrame, team_id: int, kickoff: pd.Timestamp) -> dict:
    """Previous and next match of the team (all competitions) with the days in between.

    ``schedule``: fixtures (fixture_id, kickoff, league_id, league, cup, home_id, away_id, home, away, hg,
    ag)."""
    t = schedule[(schedule["home_id"] == team_id) | (schedule["away_id"] == team_id)].sort_values("kickoff")
    out: dict = {"prev": None, "next": None}
    before, after = t[t["kickoff"] < kickoff].tail(1), t[t["kickoff"] > kickoff].head(1)
    for key, part in (("prev", before), ("next", after)):
        if part.empty:
            continue
        m = part.iloc[0]
        home = m["home_id"] == team_id
        score = None
        if key == "prev" and pd.notna(m["hg"]) and pd.notna(m["ag"]):
            score = [int(m["hg"]), int(m["ag"])] if home else [int(m["ag"]), int(m["hg"])]
        out[key] = {
            "fixture_id": int(m["fixture_id"]),
            "kickoff": m["kickoff"].isoformat(),
            "days": round(abs((kickoff - m["kickoff"]).total_seconds()) / 86400, 1),
            "league_id": int(m["league_id"]),
            "league": m["league"],
            "cup": bool(m["cup"]),
            "home": bool(home),
            "opponent": m["away"] if home else m["home"],
            "score": score,  # own goals first
        }
    return out


def missing_players(roles: pd.DataFrame, absences: pd.DataFrame, names: dict[int, str]) -> list[dict]:
    """Reported absences of a team with the player's role (``start_share``, ``attack_share``), regulars
    first."""
    out = []
    for a in absences.itertuples(index=False):
        role = roles.loc[a.player_id] if a.player_id in roles.index else None
        fallback = a.player_name if isinstance(a.player_name, str) else None
        out.append({
            "player_id": int(a.player_id),
            "name": names.get(int(a.player_id)) or fallback,
            "type": "doubtful" if a.type == "Questionable" else "missing",
            "reason": a.reason if isinstance(a.reason, str) else None,
            "reason_label": absence_reason(a.reason),
            "position": None if role is None else role["position"],
            "start_share": 0.0 if role is None else float(role["start_share"]),
            "attack_share": 0.0 if role is None else float(role["attack_share"]),
            "regular": role is not None and float(role["start_share"]) >= REGULAR,
        })  # fmt: skip
    return sorted(out, key=lambda p: (p["type"] != "missing", -p["start_share"], -p["attack_share"]))
