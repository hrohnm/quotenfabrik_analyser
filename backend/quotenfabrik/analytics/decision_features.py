"""Features of the Tippschein decision model: everything we know about a fixture before kickoff.

One row per fixture of the shown competitions with a prediction of the chosen run:

- model probabilities of the six decisions (``p_*``),
- patterns of the league history (head-to-head, home/away rates, goal and half rates; value minus league
  rate),
- form of both teams (points above the model's expectation, points per match, last 6 matches, all
  competitions),
- playing style of both teams (shots, shots on target, box share, conversion, possession, ...; last 12
  matches),
- schedule (rest days, European cup match before/after, matches in 14 days),
- reported absences weighted by the players' roles (from 2021/22 on).

All values only use information available before kickoff (profiles and form from earlier matches, patterns
from matches before the matchday). Missing values stay NaN; the model fills them and adds a missing flag per
group.
"""

import numpy as np
import pandas as pd
from sqlalchemy import Engine, text

from quotenfabrik.analytics import availability, form, style
from quotenfabrik.analytics.data import load_matches
from quotenfabrik.analytics.patterns import PatternContext, compute_patterns

PROBS = {  # feature -> (market, selection, line)
    "p_home": ("1x2", "H", None), "p_draw": ("1x2", "D", None), "p_away": ("1x2", "A", None),
    "p_o15": ("ou_ft", "over", 1.5), "p_o25": ("ou_ft", "over", 2.5), "p_btts": ("btts", "yes", None),
    "p_goal_1h": ("ou_1h", "over", 0.5), "p_goal_2h": ("ou_2h", "over", 0.5),
}  # fmt: skip
STYLE = ["shots", "shots_on", "inside_share", "conversion_on", "possession", "possession_yield", "goals",
         "goals_against", "shots_on_against", "save_rate"]  # fmt: skip
FORM = ["form_residual", "form_ppg"]
SCHEDULE = ["rest_days", *availability.FEATURES["schedule"]]
ABSENCES = availability.FEATURES["absences"]
ABSENCES_FROM = pd.Timestamp("2021-07-01", tz="UTC")  # absences are reported from then on
GROUPS = {"form": FORM, "style": STYLE, "schedule": SCHEDULE, "absences": ABSENCES}

_PREDICTIONS_SQL = """
    with runs as ({runs})
    select p.fixture_id, runs.model_run_id, runs.kind, f.league_id, f.season, f.kickoff_utc as kickoff,
           f.home_team_id as home_id, f.away_team_id as away_id, p.market, p.selection, p.line::float as line,
           p.probability, p.outcome
    from analytics.predictions p
    join runs on runs.model_run_id = p.model_run_id and runs.fixture_id = p.fixture_id
    join core.fixtures f on f.id = p.fixture_id
    where p.market in ('1x2', 'ou_ft', 'btts', 'ou_1h', 'ou_2h')
"""


def load_predictions(engine: Engine, leagues: list[int]) -> pd.DataFrame:
    """Chosen run per fixture: probability and outcome of the six decisions, one row per fixture."""
    from quotenfabrik.api.data import chosen_runs_cte

    sql = _PREDICTIONS_SQL.format(runs=chosen_runs_cte("and f.league_id = any(:leagues)"))
    with engine.connect() as conn:
        p = pd.read_sql(text(sql), conn, params={"leagues": list(leagues)})
    if p.empty:
        return pd.DataFrame()
    p["kickoff"] = pd.to_datetime(p["kickoff"], utc=True)
    keys = {v: k for k, v in PROBS.items()}
    p["feature"] = [keys.get((m, s, None if pd.isna(ln) else float(ln))) for m, s, ln in
                    zip(p["market"], p["selection"], p["line"], strict=True)]  # fmt: skip
    p = p[p["feature"].notna()]
    meta = ["fixture_id", "model_run_id", "kind", "league_id", "season", "kickoff", "home_id", "away_id"]
    wide = p.pivot_table(index=meta, columns="feature", values="probability").reset_index()
    out = p.pivot_table(index="fixture_id", columns="feature", values="outcome", aggfunc="first")
    out.columns = [c.replace("p_", "y_") for c in out.columns]
    return wide.merge(out, left_on="fixture_id", right_index=True, how="left")


def pattern_features(engine: Engine, fixtures: pd.DataFrame) -> pd.DataFrame:
    """Pattern values minus the league rate per fixture (league history before the matchday)."""
    rows = []
    for league_id, lf in fixtures.groupby("league_id"):
        matches = load_matches(engine, int(league_id))
        known = matches[["fixture_id", "matchday"]]
        lf = lf.merge(known, on="fixture_id", how="left")
        if lf["matchday"].isna().all():  # European cups: no matchdays, too little own history
            continue
        for _, md in lf.groupby(["season", "matchday"], dropna=True):
            ctx = PatternContext.build(matches, md["kickoff"].min())
            for f in md.itertuples(index=False):
                row = {"fixture_id": f.fixture_id}
                for p in compute_patterns(ctx, int(f.home_id), int(f.away_id)):
                    if p.value is not None and p.n:
                        row[f"pat_{p.key}"] = p.value - (p.baseline or 0.0)
                rows.append(row)
    return pd.DataFrame(rows)


def _asof(fixtures: pd.DataFrame, team_values: pd.DataFrame, cols: list[str], prefix: str) -> pd.DataFrame:
    """Latest team values strictly before kickoff for the home and the away team."""
    tv = team_values.dropna(subset=["kickoff"]).sort_values("kickoff")
    out = fixtures[["fixture_id", "kickoff", "home_id", "away_id"]].copy()
    for side in ("home", "away"):
        left = out[["fixture_id", "kickoff", f"{side}_id"]].rename(columns={f"{side}_id": "team"})
        left = left.sort_values("kickoff")
        merged = pd.merge_asof(left, tv[["kickoff", "team", *cols]], on="kickoff", by="team",
                               allow_exact_matches=False)  # fmt: skip
        merged = merged.rename(columns={c: f"{side}_{prefix}{c}" for c in cols})
        out = out.merge(merged.drop(columns=["kickoff", "team"]), on="fixture_id", how="left")
    return out.drop(columns=["kickoff", "home_id", "away_id"])


def form_features(engine: Engine, fixtures: pd.DataFrame) -> pd.DataFrame:
    """Form of both teams over their last matches (all competitions), as known before kickoff."""
    history = form.load_history(engine, fixtures["kickoff"].max() + pd.Timedelta(days=1))
    rows = form.team_rows(history).sort_values(["team", "kickoff", "fixture_id"])
    g = rows.groupby("team", sort=False)
    n = form.FORM_N
    # values *after* each match (window including it), taken strictly before the next kickoff
    rows["form_residual"] = g["residual"].transform(
        lambda s: s.rolling(n, min_periods=form.MIN_EXPECTED).mean()
    )
    rows["form_ppg"] = g["points"].transform(lambda s: s.rolling(n, min_periods=n).mean())
    return _asof(fixtures, rows, FORM, "")


def style_features(engine: Engine, fixtures: pd.DataFrame, leagues: list[int]) -> pd.DataFrame:
    """Style profile of both teams over their last 12 matches with statistics, before kickoff."""
    rows = style.load_stats(engine, leagues).sort_values(["team", "kickoff", "fixture_id"])
    if rows.empty:
        return fixtures[["fixture_id"]]
    rows = rows.reset_index(drop=True)
    g = rows.groupby("team", sort=False)
    sums = (
        rows[style._SUMS]
        .astype(float)
        .groupby(rows["team"])
        .transform(lambda s: s.rolling(style.WINDOW, min_periods=1).sum())
    )
    played = (g.cumcount() + 1).clip(upper=style.WINDOW).astype(float)
    prof = style.with_yield(style._derive(sums, played))
    prof.loc[played < style.MIN_MATCHES, style.METRIC_KEYS] = np.nan
    prof[["team", "kickoff"]] = rows[["team", "kickoff"]]
    return _asof(fixtures, prof, STYLE, "style_")


def schedule_and_absence_features(engine: Engine, fixtures: pd.DataFrame, cups: list[int]) -> pd.DataFrame:
    """Rest days, European cup before/after, matches in 14 days and weighted absences of both teams."""
    sched = availability.schedule_features(availability.load_schedule(engine, cups))
    sides = [
        fixtures[["fixture_id", "kickoff"]].assign(team_id=fixtures[side], side=side.split("_")[0])
        for side in ("home_id", "away_id")
    ]
    teams = pd.concat(sides, ignore_index=True)
    teams = teams.merge(sched, on=["fixture_id", "team_id"], how="left")
    recent = teams[teams["kickoff"] >= ABSENCES_FROM]
    if len(recent):
        avail = availability.availability_features(
            recent[["fixture_id", "team_id", "kickoff"]], availability.load_player_roles(engine),
            availability.load_absences(engine),
        )  # fmt: skip
        avail = avail[avail["has_roles"]].drop(columns="has_roles")
        teams = teams.merge(avail, on=["fixture_id", "team_id"], how="left")
    cols = [c for c in (*SCHEDULE, *ABSENCES) if c in teams]
    wide = teams.pivot_table(index="fixture_id", columns="side", values=cols, dropna=False)
    wide.columns = [f"{side}_{col}" for col, side in wide.columns]
    return wide.reset_index()


def build(
    engine: Engine, leagues: list[int], cups: list[int], fixture_ids: list[int] | None = None
) -> pd.DataFrame:
    """Feature table of all fixtures of ``leagues`` (incl. cups) with a prediction of the chosen run (or only
    ``fixture_ids``)."""
    base = load_predictions(engine, leagues)
    if fixture_ids is not None and not base.empty:
        base = base[base["fixture_id"].isin(fixture_ids)].reset_index(drop=True)
    if base.empty:
        return base
    parts = [
        pattern_features(engine, base),
        form_features(engine, base),
        style_features(engine, base, leagues),
        schedule_and_absence_features(engine, base, cups),
    ]
    for part in parts:
        if not part.empty:
            base = base.merge(part, on="fixture_id", how="left")
    base["cup"] = base["league_id"].isin(cups).astype(float)
    return base.sort_values(["kickoff", "fixture_id"], ignore_index=True)
