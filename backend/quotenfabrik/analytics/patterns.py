"""Descriptive patterns per market group ("Analysepattern").

Every pattern is computed from matches strictly before ``as_of``. Rate patterns carry the sample size, the
league baseline and a signal ('high' / 'low') when the Wilson interval of the rate lies clearly above or
below the baseline.
"""

from dataclasses import dataclass, field
from math import sqrt

import numpy as np
import pandas as pd

WINDOW = 10  # last N matches (venue-specific where it matters)
FORM_WINDOW = 5
MIN_N = 6
SIGNAL_MARGIN = 0.05
Z = 1.0  # ~68 % Wilson interval: patterns are hints, not proofs
TIMING_BINS = [0, 15, 30, 45, 60, 75, 90]
TIMING_LABELS = ["1-15", "16-30", "31-45", "46-60", "61-75", "76-90"]


@dataclass
class PatternResult:
    group: str  # market group
    key: str
    label: str  # German description for the UI
    scope: str  # 'home', 'away' or 'match'
    value: float | None
    n: int | None = None
    baseline: float | None = None
    signal: str | None = None  # 'high' / 'low' / None
    details: dict = field(default_factory=dict)


def wilson(hits: float, n: int, z: float = Z) -> tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    p = hits / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return centre - half, centre + half


def _signal(hits: float, n: int, baseline: float | None) -> str | None:
    if baseline is None or n < MIN_N:
        return None
    low, high = wilson(hits, n)
    if low > baseline + SIGNAL_MARGIN:
        return "high"
    if high < baseline - SIGNAL_MARGIN:
        return "low"
    return None


def team_matches(matches: pd.DataFrame) -> pd.DataFrame:
    """One row per team and finished match from the team's perspective."""
    m = matches[matches["finished"]]
    common = ["fixture_id", "season", "kickoff"]
    home = m[common].assign(
        team=m["home_id"], opp=m["away_id"], venue="home", gf=m["hg"], ga=m["ag"], gf1=m["hthg"],
        ga1=m["htag"], gf2=m["h2g"], ga2=m["a2g"], xgf=m["hxg"], xga=m["axg"],
    )  # fmt: skip
    away = m[common].assign(
        team=m["away_id"], opp=m["home_id"], venue="away", gf=m["ag"], ga=m["hg"], gf1=m["htag"],
        ga1=m["hthg"], gf2=m["a2g"], ga2=m["h2g"], xgf=m["axg"], xga=m["hxg"],
    )  # fmt: skip
    tm = pd.concat([home, away], ignore_index=True).sort_values("kickoff")
    tm["points"] = np.select([tm["gf"] > tm["ga"], tm["gf"] == tm["ga"]], [3, 1], 0)
    tm["tg"] = tm["gf"] + tm["ga"]
    tm["tg1"] = tm["gf1"] + tm["ga1"]
    tm["tg2"] = tm["gf2"] + tm["ga2"]
    return tm


@dataclass
class PatternContext:
    """Precomputed history for computing patterns of fixtures up to ``as_of``."""

    as_of: pd.Timestamp
    tm: pd.DataFrame  # team_matches before as_of
    goals: pd.DataFrame | None  # goal events (fixture_id, team_id, minute) before as_of
    players: pd.DataFrame | None  # player matches before as_of
    league: dict[str, float]

    @classmethod
    def build(
        cls, matches, as_of, goal_events=None, player_matches=None, base_days=3 * 365
    ) -> "PatternContext":
        tm = team_matches(matches[matches["kickoff"] < as_of])
        recent = tm[tm["kickoff"] >= as_of - pd.Timedelta(days=base_days)]
        home = recent[recent["venue"] == "home"]
        league = {
            "home_win": float((home["points"] == 3).mean()),
            "draw": float((home["points"] == 1).mean()),
            "away_win": float((home["points"] == 0).mean()),
            "o15": float((home["tg"] > 1.5).mean()),
            "o25": float((home["tg"] > 2.5).mean()),
            "o35": float((home["tg"] > 3.5).mean()),
            "btts": float(((home["gf"] > 0) & (home["ga"] > 0)).mean()),
            "home_scored": float((home["gf"] > 0).mean()),
            "away_scored": float((home["ga"] > 0).mean()),
            "home_2plus": float((home["gf"] > 1).mean()),
            "away_2plus": float((home["ga"] > 1).mean()),
            "o05_1h": float((home["tg1"] > 0.5).mean()),
            "o15_1h": float((home["tg1"] > 1.5).mean()),
            "o15_2h": float((home["tg2"] > 1.5).mean()),
            "share_1h": float(home["tg1"].sum() / max(home["tg"].sum(), 1)),
            "goals_per_match": float(home["tg"].mean()),
        }
        fixture_ids = set(matches.loc[matches["kickoff"] < as_of, "fixture_id"])
        goals = goal_events[goal_events["fixture_id"].isin(fixture_ids)] if goal_events is not None else None
        players = player_matches[player_matches["kickoff"] < as_of] if player_matches is not None else None
        return cls(as_of, tm, goals, players, league)

    def last(self, team: int, venue: str | None = None, n: int = WINDOW) -> pd.DataFrame:
        t = self.tm[self.tm["team"] == team]
        if venue:
            t = t[t["venue"] == venue]
        return t.tail(n)


def _rate(group, key, label, scope, mask: pd.Series, baseline) -> PatternResult:
    n, hits = int(mask.size), float(mask.sum())
    return PatternResult(
        group, key, label, scope, hits / n if n else None, n, baseline, _signal(hits, n, baseline)
    )


def _mean(group, key, label, scope, values: pd.Series, baseline=None) -> PatternResult:
    v = values.dropna()
    return PatternResult(group, key, label, scope, float(v.mean()) if len(v) else None, int(len(v)), baseline)


def patterns_1x2(ctx: PatternContext, home: int, away: int) -> list[PatternResult]:
    g, lg = "1x2", ctx.league
    h, a = ctx.last(home, "home"), ctx.last(away, "away")
    hf, af = ctx.last(home, n=FORM_WINDOW), ctx.last(away, n=FORM_WINDOW)
    h2h = ctx.tm[(ctx.tm["team"] == home) & (ctx.tm["opp"] == away)].tail(6)
    return [
        _rate(g, "home_win_rate_home", "Heimsiege des Heimteams (letzte 10 Heimspiele)", "home", h["points"] == 3, lg["home_win"]),
        _rate(g, "away_win_rate_away", "Auswärtssiege des Gastteams (letzte 10 Auswärtsspiele)", "away", a["points"] == 3, lg["away_win"]),
        _rate(g, "home_draw_rate", "Remis des Heimteams (letzte 10 Heimspiele)", "home", h["points"] == 1, lg["draw"]),
        _rate(g, "away_draw_rate", "Remis des Gastteams (letzte 10 Auswärtsspiele)", "away", a["points"] == 1, lg["draw"]),
        _mean(g, "home_ppg_form", "Punkte pro Spiel Heimteam (letzte 5)", "home", hf["points"]),
        _mean(g, "away_ppg_form", "Punkte pro Spiel Gastteam (letzte 5)", "away", af["points"]),
        _mean(g, "home_goal_diff", "Tordifferenz pro Spiel Heimteam (letzte 10 Heimspiele)", "home", h["gf"] - h["ga"]),
        _mean(g, "away_goal_diff", "Tordifferenz pro Spiel Gastteam (letzte 10 Auswärtsspiele)", "away", a["gf"] - a["ga"]),
        _mean(g, "home_xg_diff", "xG-Differenz pro Spiel Heimteam (letzte 10)", "home", ctx.last(home)["xgf"] - ctx.last(home)["xga"]),
        _mean(g, "away_xg_diff", "xG-Differenz pro Spiel Gastteam (letzte 10)", "away", ctx.last(away)["xgf"] - ctx.last(away)["xga"]),
        _rate(g, "h2h_home_wins", "Siege des Heimteams im direkten Vergleich (letzte 6)", "match", h2h["points"] == 3, None),
    ]  # fmt: skip


def patterns_totals(ctx: PatternContext, home: int, away: int) -> list[PatternResult]:
    g, lg = "totals", ctx.league
    h, a = ctx.last(home, "home"), ctx.last(away, "away")
    both = pd.concat([h, a])
    out = []
    for line, key in ((1.5, "o15"), (2.5, "o25"), (3.5, "o35")):
        out += [
            _rate(g, f"home_{key}", f"Über {line} in Heimspielen des Heimteams (letzte 10)", "home", h["tg"] > line, lg[key]),
            _rate(g, f"away_{key}", f"Über {line} in Auswärtsspielen des Gastteams (letzte 10)", "away", a["tg"] > line, lg[key]),
            _rate(g, f"combined_{key}", f"Über {line} kombiniert (Heim- + Auswärtsserie)", "match", both["tg"] > line, lg[key]),
        ]  # fmt: skip
    out += [
        _rate(g, "combined_btts", "Beide Teams treffen kombiniert (letzte 10 + 10)", "match", (both["gf"] > 0) & (both["ga"] > 0), lg["btts"]),
        _mean(g, "combined_goals", "Tore pro Spiel kombiniert", "match", both["tg"], lg["goals_per_match"]),
        _mean(g, "combined_xg", "xG gesamt pro Spiel kombiniert", "match", both["xgf"] + both["xga"]),
    ]  # fmt: skip
    return out


def patterns_team_totals(ctx: PatternContext, home: int, away: int) -> list[PatternResult]:
    g, lg = "team_totals", ctx.league
    h, a = ctx.last(home, "home"), ctx.last(away, "away")
    return [
        _rate(g, "home_scored", "Heimteam traf (letzte 10 Heimspiele)", "home", h["gf"] > 0, lg["home_scored"]),
        _rate(g, "home_2plus", "Heimteam 2+ Tore (letzte 10 Heimspiele)", "home", h["gf"] > 1, lg["home_2plus"]),
        _rate(g, "away_conceded_away", "Gastteam kassierte auswärts (letzte 10)", "away", a["ga"] > 0, lg["home_scored"]),
        _rate(g, "away_conceded_2plus_away", "Gastteam kassierte auswärts 2+ (letzte 10)", "away", a["ga"] > 1, lg["home_2plus"]),
        _rate(g, "away_scored", "Gastteam traf (letzte 10 Auswärtsspiele)", "away", a["gf"] > 0, lg["away_scored"]),
        _rate(g, "away_2plus", "Gastteam 2+ Tore (letzte 10 Auswärtsspiele)", "away", a["gf"] > 1, lg["away_2plus"]),
        _rate(g, "home_conceded_home", "Heimteam kassierte zu Hause (letzte 10)", "home", h["ga"] > 0, lg["away_scored"]),
        _rate(g, "home_clean_sheet", "Heimteam zu null (letzte 10 Heimspiele)", "home", h["ga"] == 0, 1 - lg["away_scored"]),
        _rate(g, "away_clean_sheet", "Gastteam zu null (letzte 10 Auswärtsspiele)", "away", a["ga"] == 0, 1 - lg["home_scored"]),
        _mean(g, "home_goals_minus_xg", "Heimteam Tore minus xG pro Spiel (letzte 10)", "home", ctx.last(home)["gf"] - ctx.last(home)["xgf"]),
        _mean(g, "away_goals_minus_xg", "Gastteam Tore minus xG pro Spiel (letzte 10)", "away", ctx.last(away)["gf"] - ctx.last(away)["xgf"]),
    ]  # fmt: skip


def patterns_halves(ctx: PatternContext, home: int, away: int) -> list[PatternResult]:
    g, lg = "halves", ctx.league
    h, a = ctx.last(home, "home"), ctx.last(away, "away")
    both = pd.concat([h, a])
    out = [
        _rate(g, "combined_o05_1h", "1. HZ Über 0.5 kombiniert", "match", both["tg1"] > 0.5, lg["o05_1h"]),
        _rate(g, "combined_o15_1h", "1. HZ Über 1.5 kombiniert", "match", both["tg1"] > 1.5, lg["o15_1h"]),
        _rate(g, "combined_o15_2h", "2. HZ Über 1.5 kombiniert", "match", both["tg2"] > 1.5, lg["o15_2h"]),
        _rate(g, "home_scored_1h", "Heimteam traf in der 1. HZ (letzte 10 Heimspiele)", "home", h["gf1"] > 0, None),
        _rate(g, "away_scored_1h", "Gastteam traf in der 1. HZ (letzte 10 Auswärtsspiele)", "away", a["gf1"] > 0, None),
        PatternResult(g, "share_goals_1h", "Anteil der Tore in der 1. HZ (Spiele beider Teams)", "match",
                      float(both["tg1"].sum() / both["tg"].sum()) if both["tg"].sum() else None,
                      int(both["tg"].sum()), lg["share_1h"]),
    ]  # fmt: skip
    if ctx.goals is not None:
        for team, scope, rows in ((home, "home", h), (away, "away", a)):
            ev = ctx.goals[ctx.goals["fixture_id"].isin(rows["fixture_id"])]
            scored = ev[ev["team_id"] == team]
            hist = (
                pd.cut(scored["minute"], TIMING_BINS, labels=TIMING_LABELS)
                .value_counts()
                .reindex(TIMING_LABELS)
            )
            out.append(
                PatternResult(g, f"{scope}_goal_timing", f"Tor-Timing {'Heim' if scope == 'home' else 'Gast'}team (eigene Tore, 15-Min.-Intervalle)",
                              scope, None, int(len(scored)), None, None, {k: int(v) for k, v in hist.fillna(0).items()})
            )  # fmt: skip
    return out


def patterns_scorers(ctx: PatternContext, home: int, away: int, top: int = 5) -> list[PatternResult]:
    if ctx.players is None:
        return []
    out = []
    recent = ctx.players[ctx.players["kickoff"] >= ctx.as_of - pd.Timedelta(days=365)]
    for team, scope in ((home, "home"), (away, "away")):
        p = recent[recent["team_id"] == team]
        if p.empty:
            continue
        agg = p.groupby(["player_id", "name"]).agg(
            goals=("goals", "sum"), minutes=("minutes", "sum"), shots=("shots", "sum"),
            shots_on=("shots_on", "sum"), pen_goals=("pen_goals", "sum"), apps=("fixture_id", "nunique"),
            starts=("is_starter", "sum"),
        ).reset_index()  # fmt: skip
        team_goals = max(agg["goals"].sum(), 1)
        for r in agg.sort_values(["goals", "shots_on"], ascending=False).head(top).itertuples():
            per90 = 90 / r.minutes if r.minutes else 0
            out.append(
                PatternResult(
                    "scorers", f"{scope}_scorer_{r.player_id}", r.name, scope, r.goals * per90, int(r.apps), None, None,
                    {"goals": int(r.goals), "goals_per90": round(r.goals * per90, 2), "shots_per90": round(r.shots * per90, 2),
                     "shots_on_per90": round(r.shots_on * per90, 2), "share_team_goals": round(float(r.goals / team_goals), 3),
                     "penalty_goals": int(r.pen_goals), "start_rate": round(r.starts / r.apps, 2) if r.apps else 0,
                     "minutes": int(r.minutes)},
                )
            )  # fmt: skip
    return out


ALL = {
    "1x2": patterns_1x2,
    "totals": patterns_totals,
    "team_totals": patterns_team_totals,
    "halves": patterns_halves,
    "scorers": patterns_scorers,
}


def compute_patterns(ctx: PatternContext, home: int, away: int) -> list[PatternResult]:
    return [p for fn in ALL.values() for p in fn(ctx, home, away)]
