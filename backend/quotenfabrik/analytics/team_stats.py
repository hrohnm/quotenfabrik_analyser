"""Statistics of one team over a season (team page): results split home / away, goal timing, streaks,
match statistics against the league average and points against the model's expectation.

Pure functions on frames the API loads; everything is descriptive (no new prediction).
"""

import numpy as np
import pandas as pd

SEGMENTS = [(1, 15), (16, 30), (31, 45), (46, 60), (61, 75), (76, 90)]
STAT_COLUMNS = {
    "shots_total": "Schüsse",
    "shots_on": "Schüsse aufs Tor",
    "xg": "xG",
    "possession": "Ballbesitz %",
    "corners": "Ecken",
    "fouls": "Fouls",
    "yellow": "Gelbe Karten",
    "passes_accurate_pct": "Passquote %",
}


def team_view(matches: pd.DataFrame, team_id: int) -> pd.DataFrame:
    """Finished matches (``home_id``, ``away_id``, ``hg``, ``ag``, ``hthg``, ``htag``, ``kickoff``) from the
    team's perspective: ``gf``, ``ga``, ``ht_gf``, ``ht_ga``, ``home``, ``result`` (S/U/N), oldest first."""
    m = matches[(matches["home_id"] == team_id) | (matches["away_id"] == team_id)].sort_values("kickoff")
    home = m["home_id"] == team_id
    out = pd.DataFrame({
        "fixture_id": m["fixture_id"].to_numpy(),
        "kickoff": m["kickoff"].to_numpy(),
        "league_id": m["league_id"].to_numpy(),
        "home": home.to_numpy(),
        "opponent_id": np.where(home, m["away_id"], m["home_id"]),
        "gf": np.where(home, m["hg"], m["ag"]).astype(float),
        "ga": np.where(home, m["ag"], m["hg"]).astype(float),
        "ht_gf": np.where(home, m["hthg"], m["htag"]).astype(float),
        "ht_ga": np.where(home, m["htag"], m["hthg"]).astype(float),
    })  # fmt: skip
    out["result"] = np.where(out["gf"] > out["ga"], "S", np.where(out["gf"] == out["ga"], "U", "N"))
    return out


def _rate(mask: pd.Series) -> float | None:
    return float(mask.mean()) if len(mask) else None


def split(rows: pd.DataFrame) -> dict:
    """Key figures of a set of matches (team view)."""
    n = len(rows)
    if n == 0:
        return {"played": 0}
    total = rows["gf"] + rows["ga"]
    ht = rows.dropna(subset=["ht_gf", "ht_ga"])
    return {
        "played": n,
        "won": int((rows["result"] == "S").sum()),
        "drawn": int((rows["result"] == "U").sum()),
        "lost": int((rows["result"] == "N").sum()),
        "points_per_game": float(((rows["result"] == "S") * 3 + (rows["result"] == "U")).mean()),
        "gf_per_game": float(rows["gf"].mean()),
        "ga_per_game": float(rows["ga"].mean()),
        "over_1_5": _rate(total > 1.5),
        "over_2_5": _rate(total > 2.5),
        "over_3_5": _rate(total > 3.5),
        "btts": _rate((rows["gf"] > 0) & (rows["ga"] > 0)),
        "clean_sheet": _rate(rows["ga"] == 0),
        "failed_to_score": _rate(rows["gf"] == 0),
        "ht_lead": _rate(ht["ht_gf"] > ht["ht_ga"]) if len(ht) else None,
        "first_half_goals": float((ht["ht_gf"] + ht["ht_ga"]).mean()) if len(ht) else None,
        "second_half_goals": float((ht["gf"] + ht["ga"] - ht["ht_gf"] - ht["ht_ga"]).mean())
        if len(ht)
        else None,
    }


def splits(rows: pd.DataFrame) -> dict:
    return {"total": split(rows), "home": split(rows[rows["home"]]), "away": split(rows[~rows["home"]])}


def goal_segments(goals: pd.DataFrame, team_id: int, matches: int) -> list[dict]:
    """Goals scored / conceded per 15-minute segment (stoppage time counts to its half's last segment).

    ``goals``: one row per goal (``minute``, ``scoring_team``) of the team's matches, own goals already
    assigned to the team they count for."""
    out = []
    minute = goals["minute"].clip(upper=90)
    for lo, hi in SEGMENTS:
        in_seg = (minute >= lo) & (minute <= hi)
        out.append({
            "label": f"{lo}–{hi}",
            "scored": int((in_seg & (goals["scoring_team"] == team_id)).sum()),
            "conceded": int((in_seg & (goals["scoring_team"] != team_id)).sum()),
            "matches": matches,
        })  # fmt: skip
    return out


STREAKS = {
    "unbeaten": ("ohne Niederlage", lambda r: r["result"] != "N"),
    "wins": ("Siege in Folge", lambda r: r["result"] == "S"),
    "winless": ("ohne Sieg", lambda r: r["result"] != "S"),
    "scored": ("mit eigenem Tor", lambda r: r["gf"] > 0),
    "clean_sheets": ("ohne Gegentor", lambda r: r["ga"] == 0),
    "over_2_5": ("Über 2,5 Tore", lambda r: r["gf"] + r["ga"] > 2.5),
    "btts": ("beide treffen", lambda r: (r["gf"] > 0) & (r["ga"] > 0)),
}


def streaks(rows: pd.DataFrame, min_length: int = 2) -> list[dict]:
    """Current series (from the latest match backwards) of at least ``min_length`` matches."""
    out = []
    latest_first = rows.sort_values("kickoff", ascending=False)
    for key, (label, cond) in STREAKS.items():
        hits = cond(latest_first).to_numpy()
        length = int(np.argmin(hits)) if not hits.all() else len(hits)
        if length >= min_length:
            out.append({"key": key, "label": label, "length": length})
    return sorted(out, key=lambda s: -s["length"])


def stat_averages(stats: pd.DataFrame, team_id: int, league_teams: set[int] | None = None) -> list[dict]:
    """Average match statistics of the team (for / against) and the league average per team and match.

    ``stats``: full-time rows of ``core.fixture_team_stats`` (fixture_id, team_id, columns of
    ``STAT_COLUMNS``) for the competition season."""
    s = stats.copy()
    s["passes_accurate_pct"] = s["passes_accurate"] / s["passes_total"].replace(0, np.nan) * 100
    own = s[s["team_id"] == team_id]
    opp = s[s["fixture_id"].isin(own["fixture_id"]) & (s["team_id"] != team_id)]
    league = s[s["team_id"].isin(league_teams)] if league_teams else s
    out = []
    for col, label in STAT_COLUMNS.items():
        if own[col].notna().sum() == 0:
            continue
        out.append({
            "key": col, "label": label,
            "team": float(own[col].mean()),
            "against": float(opp[col].mean()) if opp[col].notna().any() else None,
            "league": float(league[col].mean()) if league[col].notna().any() else None,
            "matches": int(own[col].notna().sum()),
        })  # fmt: skip
    return out


def expected_points(rows: pd.DataFrame, probs: pd.DataFrame) -> dict | None:
    """Points against the model's expectation (chosen pre-match prediction): ``probs`` has fixture_id,
    p_win, p_draw from the team's perspective."""
    m = rows.merge(probs, on="fixture_id")
    if m.empty:
        return None
    points = (m["result"] == "S") * 3 + (m["result"] == "U")
    xpts = 3 * m["p_win"] + m["p_draw"]
    return {"matches": len(m), "points": int(points.sum()), "expected": float(xpts.sum()),
            "diff_per_game": float((points - xpts).mean())}  # fmt: skip
