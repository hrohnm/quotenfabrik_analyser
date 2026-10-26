"""Statistics of one player (player page): season values, per-90 values, share in the team, scorer forecasts
against the outcome and absences. Pure functions on frames the API loads; descriptive only.
"""

import pandas as pd

COUNTS = ("goals", "assists", "shots_total", "shots_on", "key_passes", "yellow", "red", "penalties_scored",
          "penalties_missed")  # fmt: skip


def summary(rows: pd.DataFrame) -> dict:
    """Season values of the player (``rows``: one row per match he was in the squad sheet of)."""
    played = rows[(rows["minutes"].fillna(0) > 0) | rows["is_starter"].fillna(False)]
    if played.empty:
        return {"apps": 0}
    minutes = float(played["minutes"].fillna(0).sum())
    out = {
        "apps": len(played),
        "starts": int(played["is_starter"].fillna(False).sum()),
        "minutes": int(minutes),
        "rating": float(played["rating"].dropna().mean()) if played["rating"].notna().any() else None,
        **{c: int(played[c].fillna(0).sum()) for c in COUNTS},
    }
    per90 = 90 / minutes if minutes else 0
    keys = (
        ("goals", "goals"),
        ("assists", "assists"),
        ("shots", "shots_total"),
        ("key_passes", "key_passes"),
    )
    out["per90"] = {k: out[c] * per90 for k, c in keys}
    out["conversion"] = out["goals"] / out["shots_total"] if out["shots_total"] else None
    out["minutes_per_goal"] = minutes / out["goals"] if out["goals"] else None
    return out


def by_competition(rows: pd.DataFrame) -> list[dict]:
    out = []
    for league_id, g in rows.groupby("league_id"):
        s = summary(g)
        if s["apps"]:
            keys = ("apps", "starts", "minutes", "goals", "assists", "rating")
            out.append({"league_id": int(league_id), **{k: s[k] for k in keys}})
    return sorted(out, key=lambda c: -c["minutes"])


def team_share(player: dict, team: dict) -> dict:
    """Share of the team's goals, assists, shots and available minutes (``team``: sums over the same
    matches)."""
    share = lambda a, b: (a / b) if b else None  # noqa: E731
    return {
        "goals": share(player.get("goals", 0), team.get("goals", 0)),
        "assists": share(player.get("assists", 0), team.get("assists", 0)),
        "shots": share(player.get("shots_total", 0), team.get("shots", 0)),
        "minutes": share(player.get("minutes", 0), team.get("matches", 0) * 90),
    }


def scoring_track(rows: pd.DataFrame) -> dict | None:
    """Scorer forecast (``p_anytime``, chosen pre-match run) against the outcome (``goals``), oldest first:
    matches with a forecast, expected and actual matches with a goal, cumulative series."""
    m = rows.dropna(subset=["p_anytime"]).sort_values("kickoff")
    if m.empty:
        return None
    scored = (m["goals"].fillna(0) > 0).astype(int)
    return {
        "matches": len(m),
        "expected": float(m["p_anytime"].sum()),
        "actual": int(scored.sum()),
        "series": [{"fixture_id": int(f), "expected": float(e), "actual": int(a)}
                   for f, e, a in zip(m["fixture_id"], m["p_anytime"].cumsum(), scored.cumsum(),
                                      strict=True)],
    }  # fmt: skip


def absence_summary(absences: pd.DataFrame) -> dict:
    """Reported absences: number of missed matches, doubtful matches and the most frequent reasons."""
    missing = absences[absences["type"] != "Questionable"]
    reasons = missing["reason_label"].value_counts()
    return {
        "missed": len(missing),
        "doubtful": int((absences["type"] == "Questionable").sum()),
        "reasons": [{"reason": r, "matches": int(n)} for r, n in reasons.items()],
    }
