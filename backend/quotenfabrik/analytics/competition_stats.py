"""Season statistics of a competition (competition page): half-time tables, table positions per matchday,
expected-points table, goal timing, team rankings, player rankings and knockout ties.

Pure functions on frames the API loads; descriptive only.
"""

import numpy as np
import pandas as pd

from quotenfabrik.analytics import league_table
from quotenfabrik.analytics.team_stats import SEGMENTS

RANKED = ("shots", "shots_on", "xg", "possession", "goals", "conceded", "shots_against", "conversion")
MIN_MINUTES_SHARE = 0.3  # per-90 rankings: at least 30 % of the most-used player's minutes


def half_matches(matches: pd.DataFrame, half: int) -> pd.DataFrame:
    """Matches with the score of the first (``half=1``) or second half (``half=2``) as ``ft_*``."""
    m = matches.dropna(subset=["ht_home", "ht_away"]).copy()
    if half == 1:
        m["ft_home"], m["ft_away"] = m["ht_home"], m["ht_away"]
    else:
        m["ft_home"], m["ft_away"] = m["ft_home"] - m["ht_home"], m["ft_away"] - m["ht_away"]
    return m


def last_matches(matches: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """fixture_id per team for each team's last ``n`` finished matches."""
    rows = [
        matches[["fixture_id", "kickoff", side]].rename(columns={side: "team_id"})
        for side in ("home_id", "away_id")
    ]
    return pd.concat(rows).sort_values("kickoff").groupby("team_id").tail(n)


def form_table(matches: pd.DataFrame, teams: list[int], n: int = 5) -> list[dict]:
    """Table of each team's last ``n`` matches only."""
    last = last_matches(matches, n)
    out = []
    for team in teams:
        ids = set(last.loc[last["team_id"] == team, "fixture_id"])
        own = matches[matches["fixture_id"].isin(ids)]
        row = league_table.standings(own, [team])
        out.append(next(r for r in row if r["team_id"] == team))
    out.sort(key=lambda r: (-r["points"], -r["gd"], -r["gf"], r["team_id"]))
    for i, r in enumerate(out, start=1):
        r["rank"] = i
    return out


def position_history(matches: pd.DataFrame, teams: list[int]) -> dict:
    """Table position of every team after each matchday (leagues with matchdays)."""
    m = matches.dropna(subset=["matchday"])
    if m.empty:
        return {"matchdays": [], "positions": {}}
    days = sorted(int(d) for d in m["matchday"].unique())
    positions: dict[int, list[int | None]] = {t: [] for t in teams}
    for d in days:
        table = {r["team_id"]: r["rank"] for r in league_table.standings(m[m["matchday"] <= d], teams)}
        for t in teams:
            positions[t].append(table.get(t))
    return {"matchdays": days, "positions": positions}


def expected_table(matches: pd.DataFrame, probs: pd.DataFrame, teams: list[int]) -> list[dict]:
    """Points against the model's pre-match expectation per team (``probs``: fixture_id, H, D, A)."""
    m = matches.merge(probs, on="fixture_id")
    rows = {t: {"team_id": t, "matches": 0, "points": 0, "expected": 0.0} for t in teams}
    for r in m.itertuples(index=False):
        hp = 3 if r.ft_home > r.ft_away else 1 if r.ft_home == r.ft_away else 0
        ap = 3 if r.ft_away > r.ft_home else 1 if r.ft_home == r.ft_away else 0
        for team, pts, xp in ((r.home_id, hp, 3 * r.H + r.D), (r.away_id, ap, 3 * r.A + r.D)):
            if team in rows:
                rows[team]["matches"] += 1
                rows[team]["points"] += pts
                rows[team]["expected"] += xp
    out = [r | {"diff": r["points"] - r["expected"]} for r in rows.values()]
    out.sort(key=lambda r: -r["expected"])
    for i, r in enumerate(out, start=1):
        r["rank"] = i
    return out


def goal_segments(goals: pd.DataFrame, matches: int) -> list[dict]:
    """Goals per 15-minute segment over all matches (stoppage time counts to the half's last segment)."""
    minute = goals["minute"].clip(upper=90)
    return [{"label": f"{lo}–{hi}", "goals": int(((minute >= lo) & (minute <= hi)).sum()), "matches": matches}
            for lo, hi in SEGMENTS]  # fmt: skip


def team_rankings(stats: pd.DataFrame, matches: pd.DataFrame) -> list[dict]:
    """Per team and match: shots, shots on target, xG, possession, goals, conversion (goals per shot on
    target), shots against, goals conceded."""
    if stats.empty:
        return []
    s = stats.merge(matches[["fixture_id", "home_id", "away_id", "ft_home", "ft_away"]], on="fixture_id")
    s["goals"] = np.where(s["team_id"] == s["home_id"], s["ft_home"], s["ft_away"])
    s["conceded"] = np.where(s["team_id"] == s["home_id"], s["ft_away"], s["ft_home"])
    opp = s[["fixture_id", "team_id", "shots_total", "shots_on"]].rename(
        columns={"team_id": "opp_id", "shots_total": "shots_against", "shots_on": "on_target_against"}
    )
    s = s.merge(opp, on="fixture_id")
    s = s[s["team_id"] != s["opp_id"]]
    g = s.groupby("team_id").agg(
        matches=("fixture_id", "nunique"), shots=("shots_total", "mean"), shots_on=("shots_on", "mean"),
        xg=("xg", "mean"), possession=("possession", "mean"), goals=("goals", "mean"),
        conceded=("conceded", "mean"), shots_against=("shots_against", "mean"),
        goals_sum=("goals", "sum"), on_sum=("shots_on", "sum"),
    )  # fmt: skip
    g["conversion"] = g["goals_sum"] / g["on_sum"].replace(0, np.nan)
    out = []
    for team, r in g.iterrows():
        out.append({"team_id": int(team), **{k: (None if pd.isna(r[k]) else float(r[k])) for k in
                    RANKED},
                    "matches": int(r["matches"])})  # fmt: skip
    return out


def player_rankings(players: pd.DataFrame, n: int = 15) -> dict:
    """Player rankings of the season from per-match rows (player_id, name, team_id, minutes, goals, assists,
    penalties_scored, yellow, red, rating, shots_total)."""
    if players.empty:
        return {}
    p = players.copy()
    for col in ("minutes", "goals", "assists", "penalties_scored", "yellow", "red", "shots_total"):
        p[col] = p[col].fillna(0)
    agg = p.groupby("player_id").agg(
        name=("name", "last"), team_id=("team_id", "last"), apps=("fixture_id", "nunique"),
        minutes=("minutes", "sum"), goals=("goals", "sum"), assists=("assists", "sum"),
        penalties=("penalties_scored", "sum"), yellow=("yellow", "sum"), red=("red", "sum"),
        shots=("shots_total", "sum"), rating=("rating", "mean"),
    )  # fmt: skip
    agg["points"] = agg["goals"] + agg["assists"]
    min_minutes = MIN_MINUTES_SHARE * float(agg["minutes"].max())
    regular = agg[agg["minutes"] >= min_minutes].copy()
    regular["goals_per_90"] = regular["goals"] / regular["minutes"] * 90
    regular["points_per_90"] = regular["points"] / regular["minutes"] * 90

    def top(frame: pd.DataFrame, key: str, extra: list[str], ascending: bool = False) -> list[dict]:
        frame = frame[frame[key] > 0] if not ascending else frame
        frame = frame.sort_values([key, "minutes"], ascending=[ascending, True]).head(n)
        return [{"player_id": int(pid), "name": r["name"], "team_id": int(r["team_id"]),
                 "value": float(r[key]),
                 **{e: (None if pd.isna(r[e]) else float(r[e])) for e in extra}}
                for pid, r in frame.iterrows()]  # fmt: skip

    cards = agg.assign(cards=agg["yellow"] + 3 * agg["red"])
    return {
        "goals": top(agg, "goals", ["assists", "penalties", "minutes"]),
        "assists": top(agg, "assists", ["goals", "minutes"]),
        "points": top(agg, "points", ["goals", "assists", "minutes"]),
        "goals_per_90": top(regular, "goals_per_90", ["goals", "minutes"]),
        "points_per_90": top(regular, "points_per_90", ["goals", "assists", "minutes"]),
        "rating": top(regular.dropna(subset=["rating"]), "rating", ["apps", "minutes"]),
        "cards": top(cards, "cards", ["yellow", "red", "apps"]),
        "min_minutes": int(min_minutes),
    }


def knockout_ties(matches: pd.DataFrame) -> list[dict]:
    """Knockout rounds of a cup: ties (one or two legs) per round with the aggregate after 90 minutes.

    ``matches`` has fixture_id, round, round_label, kickoff, home_id, away_id, ft_home, ft_away, finished."""
    ko = matches[matches["round"].map(league_table.table_group).isna()].sort_values("kickoff")
    rounds = []
    for name, g in ko.groupby("round", sort=False):
        ties: dict[frozenset, dict] = {}
        for r in g.itertuples(index=False):
            key = frozenset((int(r.home_id), int(r.away_id)))
            tie = ties.setdefault(key, {"team_a": int(r.home_id), "team_b": int(r.away_id), "legs": []})
            a_home = int(r.home_id) == tie["team_a"]
            score = None
            if r.finished:
                score = [int(r.ft_home), int(r.ft_away)] if a_home else [int(r.ft_away), int(r.ft_home)]
            tie["legs"].append(
                {"fixture_id": int(r.fixture_id), "kickoff": r.kickoff.isoformat(), "score": score}
            )
        for tie in ties.values():
            done = [leg["score"] for leg in tie["legs"] if leg["score"]]
            tie["aggregate"] = [sum(s[0] for s in done), sum(s[1] for s in done)] if done else None
        rounds.append({"round": name, "label": g["round_label"].iloc[0],
                       "kickoff": g["kickoff"].min().isoformat(),
                       "ties": list(ties.values())})  # fmt: skip
    return rounds
