"""League table, top scorers and league figures of a competition season (match page, tab "Liga").

Pure functions on result rows; the API loads the rows. Table order: points, goal difference, goals scored,
then name (head-to-head is not modelled). Cups: only the league or group phase forms a table.
"""

import pandas as pd

TABLE_ROUNDS = ("Regular Season", "League Stage", "Group")
FORM_N = 5


def table_group(round_name: str | None) -> str | None:
    """Table a round belongs to: None for knockout rounds, the group for group stages, "" otherwise."""
    if not round_name:
        return ""  # leagues without round names
    base = round_name.partition(" - ")[0]
    if base.startswith("Group"):
        return base
    return "" if base.startswith(TABLE_ROUNDS) else None


def standings(matches: pd.DataFrame, teams: list[int] | None = None, scope: str = "total") -> list[dict]:
    """Table from finished matches (``home_id``, ``away_id``, ``ft_home``, ``ft_away``, ``kickoff``).

    ``scope``: total, home or away. ``teams`` lists teams without a finished match yet (0 points)."""
    rows = []
    for m in matches.sort_values("kickoff").itertuples():
        sides = (("home", m.home_id, m.ft_home, m.ft_away), ("away", m.away_id, m.ft_away, m.ft_home))
        for side, team, gf, ga in sides:
            if scope in ("total", side):
                rows.append({"team_id": int(team), "gf": int(gf), "ga": int(ga)})
    frame = pd.DataFrame(rows, columns=["team_id", "gf", "ga"])
    pairs = zip(frame["gf"], frame["ga"], strict=True)
    frame["result"] = ["S" if g > a else "U" if g == a else "N" for g, a in pairs]
    out = {t: {"team_id": int(t), "played": 0, "won": 0, "drawn": 0, "lost": 0, "gf": 0, "ga": 0, "form": ""}
           for t in teams or []}  # fmt: skip
    for team, g in frame.groupby("team_id", sort=False):
        res = g["result"]
        out[int(team)] = {
            "team_id": int(team), "played": len(g), "won": int((res == "S").sum()),
            "drawn": int((res == "U").sum()), "lost": int((res == "N").sum()),
            "gf": int(g["gf"].sum()), "ga": int(g["ga"].sum()),
            "form": "".join(res.tail(FORM_N)),
        }  # fmt: skip
    table = []
    for r in out.values():
        r["gd"] = r["gf"] - r["ga"]
        r["points"] = 3 * r["won"] + r["drawn"]
        table.append(r)
    table.sort(key=lambda r: (-r["points"], -r["gd"], -r["gf"], r["team_id"]))
    for i, r in enumerate(table, start=1):
        r["rank"] = i
    return table


def top_players(goals: pd.DataFrame, key: str, n: int) -> list[dict]:
    """Top ``n`` players by goals (``key="scorer"``) or assists (``key="assist"``).

    ``goals``: one row per goal (``scorer_id``, ``scorer_name``, ``assist_id``, ``assist_name``, ``team_id``,
    ``penalty``), own goals excluded."""
    if goals.empty:
        return []
    id_col, name_col = f"{key}_id", f"{key}_name"
    rows = goals.dropna(subset=[id_col])
    agg = rows.groupby(id_col).agg(
        name=(name_col, "last"),
        team_id=("team_id", "last"),
        count=(id_col, "size"),
        penalties=("penalty", "sum"),
    )
    if key == "scorer":
        assists = goals.dropna(subset=["assist_id"]).groupby("assist_id").size()
        agg["other"] = agg.index.map(assists).fillna(0)
    else:
        scored = goals.groupby("scorer_id").size()
        agg["other"] = agg.index.map(scored).fillna(0)
    agg = agg.sort_values(["count", "other", "name"], ascending=[False, False, True]).head(n)
    out, rank, prev = [], 0, None
    for i, (pid, r) in enumerate(agg.iterrows(), start=1):
        if r["count"] != prev:
            rank, prev = i, r["count"]
        entry = {"rank": rank, "player_id": int(pid), "name": r["name"], "team_id": int(r["team_id"])}
        if key == "scorer":
            entry.update(goals=int(r["count"]), penalties=int(r["penalties"]), assists=int(r["other"]))
        else:
            entry.update(assists=int(r["count"]), goals=int(r["other"]))
        out.append(entry)
    return out


def figures(matches: pd.DataFrame) -> dict | None:
    """League figures of the finished matches: goals per match, result split, over 2.5, both teams score."""
    if matches.empty:
        return None
    h, a = matches["ft_home"], matches["ft_away"]
    total = h + a
    return {
        "matches": len(matches),
        "goals_per_match": float(total.mean()),
        "home_win": float((h > a).mean()),
        "draw": float((h == a).mean()),
        "away_win": float((h < a).mean()),
        "over_2_5": float((total > 2.5).mean()),
        "btts": float(((h > 0) & (a > 0)).mean()),
        "nil_nil": float((total == 0).mean()),
    }
