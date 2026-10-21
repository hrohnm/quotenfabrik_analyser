"""Playing style of a team ("Spielstil"): ball possession, attacking pressure, finishing, defence, intensity.

Profiles come from the match statistics of the last ``WINDOW`` matches before kickoff (no leakage) and are
ranked against the other teams of the same competition (percentile 0–1). Ratios (goals per shot, pass
accuracy, …) are computed from the sums over the window, not as mean of per-match ratios. ``qf model
style-eval`` checks whether the style carries information the model does not have yet (``docs/18_spielstil.md``).
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sqlalchemy import Engine, text

FINISHED = ("FT", "AET", "PEN", "AWD", "WO")
WINDOW = 12  # matches per profile
MIN_MATCHES = 5
PEER_DAYS = 365  # peers: teams with a match in the competition within this period


@dataclass(frozen=True)
class Metric:
    key: str
    label: str
    group: str
    unit: str  # 'pct' (0–1 shown as %), 'num' (per match), 'ratio' (0–1 shown as %)
    better: str  # 'high' / 'low' / '' (neutral, style only)


GROUPS = {
    "control": "Spielkontrolle",
    "attack": "Offensivdruck",
    "finishing": "Verwertung",
    "defence": "Defensive",
    "intensity": "Intensität",
}

METRICS = [
    Metric("possession", "Ballbesitz", "control", "pct", ""),
    Metric("passes", "Pässe pro Spiel", "control", "num", ""),
    Metric("pass_accuracy", "Passquote", "control", "ratio", "high"),
    Metric("shots", "Schüsse pro Spiel", "attack", "num", "high"),
    Metric("shots_on", "Schüsse aufs Tor pro Spiel", "attack", "num", "high"),
    Metric("inside_share", "Anteil Schüsse aus dem Strafraum", "attack", "ratio", "high"),
    Metric("corners", "Ecken pro Spiel", "attack", "num", "high"),
    Metric("xg", "xG pro Spiel", "attack", "num", "high"),
    Metric("shot_share", "Anteil an allen Schüssen im Spiel", "attack", "ratio", "high"),
    Metric(
        "possession_yield",
        "Ertrag des Ballbesitzes (Schussanteil ggü. Teams mit gleichem Ballbesitz)",
        "attack",
        "pp",
        "high",
    ),
    Metric("goals", "Tore pro Spiel", "finishing", "num", "high"),
    Metric("conversion", "Tore pro Schuss", "finishing", "ratio", "high"),
    Metric("conversion_on", "Tore pro Schuss aufs Tor", "finishing", "ratio", "high"),
    Metric("goals_minus_xg", "Tore minus xG pro Spiel", "finishing", "num", "high"),
    Metric("shots_against", "Zugelassene Schüsse pro Spiel", "defence", "num", "low"),
    Metric("shots_on_against", "Zugelassene Schüsse aufs Tor pro Spiel", "defence", "num", "low"),
    Metric("xg_against", "Zugelassene xG pro Spiel", "defence", "num", "low"),
    Metric("goals_against", "Gegentore pro Spiel", "defence", "num", "low"),
    Metric("save_rate", "Paradenquote (gehaltene Schüsse aufs Tor)", "defence", "ratio", "high"),
    Metric("fouls", "Fouls pro Spiel", "intensity", "num", ""),
    Metric("cards", "Karten pro Spiel", "intensity", "num", "low"),
]
METRIC_KEYS = [m.key for m in METRICS]

# summed per window; xg sums only over matches with xG
_SUMS = ["gf", "ga", "possession", "shots", "shots_on", "inside", "corners", "passes", "passes_acc", "fouls",
         "cards", "saves", "shots_a", "shots_on_a", "xg", "xg_a", "xg_gf", "xg_n"]  # fmt: skip


# --------------------------------------------------------------------------- data

_STATS_SQL = """
    select f.id as fixture_id, f.kickoff_utc as kickoff, f.league_id, f.season, f.home_team_id, f.away_team_id,
           f.ft_home, f.ft_away, s.team_id, s.possession::float as possession, s.shots_total as shots,
           s.shots_on, s.shots_inside as inside, s.corners, s.passes_total as passes,
           s.passes_accurate as passes_acc, s.fouls, coalesce(s.yellow, 0) + coalesce(s.red, 0) as cards,
           s.gk_saves as saves, s.xg::float as xg
    from core.fixture_team_stats s
    join core.fixtures f on f.id = s.fixture_id
    where s.period = 'FT' and f.status = any(:fin) and f.ft_home is not null and f.league_id = any(:leagues)
"""


def load_stats(engine: Engine, league_ids: list[int]) -> pd.DataFrame:
    """One row per team and finished match with its own and the opponent's statistics."""
    with engine.connect() as conn:
        s = pd.read_sql(text(_STATS_SQL), conn, params={"fin": list(FINISHED), "leagues": list(league_ids)})
    return team_rows(s)


def team_rows(s: pd.DataFrame) -> pd.DataFrame:
    if s.empty:
        return pd.DataFrame(columns=["fixture_id", "kickoff", "league_id", "season", "team", "opp", *_SUMS])
    s = s.copy()
    s["kickoff"] = pd.to_datetime(s["kickoff"], utc=True)
    home = s["team_id"] == s["home_team_id"]
    s["team"] = s["team_id"]
    s["opp"] = np.where(home, s["away_team_id"], s["home_team_id"])
    s["venue"] = np.where(home, "home", "away")
    s["gf"] = np.where(home, s["ft_home"], s["ft_away"])
    s["ga"] = np.where(home, s["ft_away"], s["ft_home"])
    opp = s[["fixture_id", "team_id", "shots", "shots_on", "xg"]].rename(
        columns={"team_id": "opp", "shots": "shots_a", "shots_on": "shots_on_a", "xg": "xg_a"}
    )
    rows = s.merge(opp, on=["fixture_id", "opp"], how="inner")  # both teams need statistics
    has_xg = rows["xg"].notna() & rows["xg_a"].notna()
    rows["xg_n"] = has_xg.astype(int)
    rows["xg_gf"] = rows["gf"].where(has_xg, 0)  # goals of matches with xG (for goals minus xG)
    for col in ("xg", "xg_a"):
        rows[col] = rows[col].where(has_xg, 0.0)
    cols = ["fixture_id", "kickoff", "league_id", "season", "team", "opp", "venue", *_SUMS]
    return rows[cols].sort_values(["kickoff", "fixture_id"], ignore_index=True)


# --------------------------------------------------------------------------- profiles


def _derive(sums: pd.DataFrame, n: pd.Series) -> pd.DataFrame:
    """Metrics from window sums (``n`` = matches in the window)."""
    sums = sums.astype(float)
    n = n.astype(float)
    xg_n = sums["xg_n"].replace(0, np.nan)
    shots_all = (sums["shots"] + sums["shots_a"]).replace(0, np.nan)
    out = pd.DataFrame(index=sums.index)
    out["possession"] = sums["possession"] / n / 100
    out["passes"] = sums["passes"] / n
    out["pass_accuracy"] = sums["passes_acc"] / sums["passes"].replace(0, np.nan)
    out["shots"] = sums["shots"] / n
    out["shots_on"] = sums["shots_on"] / n
    out["inside_share"] = sums["inside"] / sums["shots"].replace(0, np.nan)
    out["corners"] = sums["corners"] / n
    out["xg"] = sums["xg"] / xg_n
    out["shot_share"] = sums["shots"] / shots_all
    out["possession_yield"] = np.nan  # needs the peers: with_yield()
    out["goals"] = sums["gf"] / n
    out["conversion"] = sums["gf"] / sums["shots"].replace(0, np.nan)
    out["conversion_on"] = sums["gf"] / sums["shots_on"].replace(0, np.nan)
    out["goals_minus_xg"] = (sums["xg_gf"] - sums["xg"]) / xg_n
    out["shots_against"] = sums["shots_a"] / n
    out["shots_on_against"] = sums["shots_on_a"] / n
    out["xg_against"] = sums["xg_a"] / xg_n
    out["goals_against"] = sums["ga"] / n
    out["save_rate"] = 1 - sums["ga"] / sums["shots_on_a"].replace(0, np.nan)
    out["fouls"] = sums["fouls"] / n
    out["cards"] = sums["cards"] / n
    out["matches"] = n
    out["xg_matches"] = sums["xg_n"]
    return out


def profiles_at(rows: pd.DataFrame, as_of: pd.Timestamp, n: int = WINDOW) -> pd.DataFrame:
    """Profile of every team from its last ``n`` matches before ``as_of`` (index: team)."""
    before = rows[rows["kickoff"] < as_of]
    last = before.groupby("team", sort=False).tail(n)
    sums = last.groupby("team")[_SUMS].sum(min_count=1)
    count = last.groupby("team").size()
    prof = _derive(sums.fillna(0), count)
    prof["last_match"] = last.groupby("team")["kickoff"].max()
    return prof[prof["matches"] >= MIN_MATCHES]


def rolling_profiles(rows: pd.DataFrame, n: int = WINDOW) -> pd.DataFrame:
    """Profile of each team *before* every match (window of the previous ``n`` matches), one row per team-match."""
    rows = rows.sort_values(["team", "kickoff", "fixture_id"]).reset_index(drop=True)
    g = rows.groupby("team", sort=False)
    prev = g[_SUMS].shift(1).fillna(0).astype(float)
    played = g.cumcount().clip(upper=n).astype(float)
    sums = prev.groupby(rows["team"]).transform(lambda s: s.rolling(n, min_periods=1).sum())
    prof = _derive(sums, played.replace(0, np.nan))
    prof.loc[played < MIN_MATCHES, METRIC_KEYS] = np.nan
    prof = with_yield(prof)
    return pd.concat([rows[["fixture_id", "kickoff", "league_id", "season", "team", "opp", "venue", "gf", "ga"]],
                      prof], axis=1)  # fmt: skip


def with_yield(prof: pd.DataFrame) -> pd.DataFrame:
    """Possession yield: shot share minus the shot share teams with the same possession usually reach (linear fit
    over ``prof``). More possession naturally brings more shots, so the plain difference would punish every
    possession team."""
    prof = prof.copy()
    ok = prof["possession"].notna() & prof["shot_share"].notna()
    if ok.sum() >= 5:
        slope, intercept = np.polyfit(prof.loc[ok, "possession"], prof.loc[ok, "shot_share"], 1)
        prof["possession_yield"] = prof["shot_share"] - (intercept + slope * prof["possession"])
    return prof


def percentiles(peers: pd.DataFrame) -> pd.DataFrame:
    """Rank of every metric among ``peers`` (0 = lowest value, 1 = highest)."""
    return peers[METRIC_KEYS].rank(pct=True, method="average")


# --------------------------------------------------------------------------- style labels


def labels(pct: pd.Series) -> list[str]:
    """Readable style labels from the percentiles of one team."""

    def p(key: str) -> float:
        v = pct.get(key)
        return 0.5 if v is None or pd.isna(v) else float(v)

    out = []
    if p("possession") >= 0.7:
        out.append("Ballbesitzteam")
    elif p("possession") <= 0.3:
        out.append("Wenig Ballbesitz, Umschaltspiel")
    attack = (p("shots") + p("shots_on")) / 2
    if attack >= 0.7:
        out.append("Offensiv druckvoll")
    elif attack <= 0.3:
        out.append("Wenig Offensivdruck")
    if p("possession") >= 0.6 and p("possession_yield") <= 0.3:
        out.append("Steriler Ballbesitz")
    if p("possession") <= 0.4 and p("possession_yield") >= 0.7:
        out.append("Gefährlich trotz wenig Ballbesitz")
    if p("conversion_on") >= 0.75:
        out.append("Effizient im Abschluss")
    elif p("conversion_on") <= 0.25:
        out.append("Schwache Chancenverwertung")
    defence = (p("shots_against") + p("shots_on_against")) / 2
    if defence <= 0.3:
        out.append("Defensiv kompakt")
    elif defence >= 0.7:
        out.append("Lässt viele Chancen zu")
    if p("fouls") >= 0.75:
        out.append("Körperbetont (viele Fouls)")
    return out


def team_style(
    rows: pd.DataFrame,
    team: int,
    as_of: pd.Timestamp,
    peer_teams: set[int] | None = None,
    fallback_rows: pd.DataFrame | None = None,
) -> dict | None:
    """Profile, percentiles among the peers and labels of one team before ``as_of``.

    ``rows``: matches of the competition (profiles of the team and its peers); ``fallback_rows``: all
    competitions, used when the team has too few recent matches in ``rows`` (e.g. promoted teams)."""
    prof = profiles_at(rows, as_of)
    recent = prof[prof["last_match"] >= as_of - pd.Timedelta(days=PEER_DAYS)]
    peers = recent if peer_teams is None else recent[recent.index.isin(peer_teams)]
    if team not in recent.index and fallback_rows is not None:
        own = profiles_at(fallback_rows[fallback_rows["team"] == team], as_of)
        prof = pd.concat([prof.drop(index=team, errors="ignore"), own])
    if team not in prof.index:
        return None
    if team not in peers.index:
        peers = pd.concat([peers.drop(index=team, errors="ignore"), prof.loc[[team]]])
    peers = with_yield(peers)
    pct = percentiles(peers).loc[team]
    values = peers.loc[team]
    return {
        "matches": int(values["matches"]),
        "xg_matches": int(values["xg_matches"]),
        "peers": len(peers),
        "labels": labels(pct),
        "metrics": [
            {"key": m.key, "label": m.label, "group": m.group, "unit": m.unit, "better": m.better,
             "value": None if pd.isna(values[m.key]) else float(values[m.key]),
             "percentile": None if pd.isna(values[m.key]) else float(pct[m.key]),
             "league_avg": None if peers[m.key].isna().all() else float(peers[m.key].mean())}
            for m in METRICS
        ],
    }  # fmt: skip
