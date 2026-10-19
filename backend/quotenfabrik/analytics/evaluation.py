"""Walk-forward evaluation of the match models without odds.

For every matchday the models are fitted on matches strictly before its first kickoff (no leakage) and
the matchday is predicted. Each market selection is scored as a binary event and compared with two
baselines:

* ``base``  – league frequency of the outcome over the training window (last 3 seasons)
* ``naive`` – home team's last 10 home games and away team's last 10 away games (shrunk to ``base``)
"""

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from quotenfabrik.analytics.data import season_leagues
from quotenfabrik.analytics.markets import GROUPS
from quotenfabrik.analytics.poisson import PoissonParams, fit_poisson
from quotenfabrik.analytics.prediction import fit_match_model

NAIVE_WINDOW = 10
NAIVE_SHRINK = 5.0
BASE_WINDOW_DAYS = 3 * 365
EPS = 1e-12
# Markets whose selections are exhaustive for a given line (probabilities are normalised for baselines).
EXHAUSTIVE = {"1x2", "ht_1x2", "exact_goals", "highest_half", "eh"}
SKIP_MARKETS = {"dc", "dnb"}  # derived from 1x2, not evaluated separately


def market_group_of(market: str) -> str:
    for group, module in GROUPS.items():
        if market in getattr(module, "MARKETS", ()):
            return group
    if market in {"1x2", "eh"}:
        return "1x2"
    if market in {"ou_ft", "btts", "exact_goals"}:
        return "totals"
    if market in {"ou_home", "ou_away", "clean_sheet"}:
        return "team_totals"
    return "halves"


def outcome_table(matches: pd.DataFrame) -> pd.DataFrame:
    """Long table of actual outcomes (one row per finished match and market selection)."""
    rows = []
    for m in matches[matches["finished"]].itertuples(index=False):
        for module in GROUPS.values():
            for (market, selection, line), hit in module.outcomes(m).items():
                if market in SKIP_MARKETS:
                    continue
                rows.append(
                    (m.fixture_id, m.kickoff, m.home_id, m.away_id, market, selection, line, bool(hit))
                )
    df = pd.DataFrame(
        rows,
        columns=["fixture_id", "kickoff", "home_id", "away_id", "market", "selection", "line", "outcome"],
    )
    df["line"] = df["line"].astype(float)
    return df


def _baselines(outcomes: pd.DataFrame, fixtures: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame:
    """Base and naive probabilities for the fixtures of one matchday, from outcomes before ``as_of``."""
    hist = outcomes[
        (outcomes["kickoff"] < as_of) & (outcomes["kickoff"] >= as_of - pd.Timedelta(days=BASE_WINDOW_DAYS))
    ]
    keys = ["market", "selection", "line"]
    base = hist.groupby(keys, dropna=False)["outcome"].mean().rename("p_base").reset_index()

    rows = []
    for f in fixtures.itertuples(index=False):
        home_hist = hist[hist["home_id"] == f.home_id].sort_values("kickoff")
        away_hist = hist[hist["away_id"] == f.away_id].sort_values("kickoff")
        home_last = home_hist[home_hist["fixture_id"].isin(home_hist["fixture_id"].unique()[-NAIVE_WINDOW:])]
        away_last = away_hist[away_hist["fixture_id"].isin(away_hist["fixture_id"].unique()[-NAIVE_WINDOW:])]
        hs = home_last.groupby(keys, dropna=False)["outcome"].agg(["sum", "count"])
        as_ = away_last.groupby(keys, dropna=False)["outcome"].agg(["sum", "count"])
        b = base.set_index(keys)["p_base"]
        hs = hs.reindex(b.index).fillna(0)
        as_ = as_.reindex(b.index).fillna(0)
        naive = 0.5 * (
            (hs["sum"] + NAIVE_SHRINK * b) / (hs["count"] + NAIVE_SHRINK)
            + (as_["sum"] + NAIVE_SHRINK * b) / (as_["count"] + NAIVE_SHRINK)
        )
        part = pd.DataFrame({"p_base": b, "p_naive": naive}).reset_index()
        part["fixture_id"] = f.fixture_id
        rows.append(part)
    out = pd.concat(rows, ignore_index=True)
    for col in ("p_base", "p_naive"):
        mask = out["market"].isin(EXHAUSTIVE)
        sums = out[mask].groupby(["fixture_id", "market", "line"], dropna=False)[col].transform("sum")
        out.loc[mask, col] = out.loc[mask, col] / sums
    return out


def _matchdays(matches: pd.DataFrame, seasons: Iterable[int]) -> list[tuple[pd.Timestamp, pd.DataFrame]]:
    test = matches[matches["season"].isin(list(seasons)) & matches["finished"]]
    groups = []
    for _, md in test.groupby(["season", "matchday"]):
        groups.append((md["kickoff"].min(), md))
    return sorted(groups, key=lambda g: g[0])


def walk_forward(
    matches: pd.DataFrame,
    seasons: Iterable[int],
    params: PoissonParams,
    outcomes: pd.DataFrame | None = None,
    pool: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Predictions, baselines and outcomes per market selection for all finished matches in ``seasons``.

    ``pool``: matches the models are fitted on (default ``matches``; several leagues = joint model).
    """
    outcomes = outcome_table(matches) if outcomes is None else outcomes
    pool = matches if pool is None else pool
    pool_seasons = season_leagues(pool)
    keys = ["fixture_id", "market", "selection", "line"]
    frames = []
    for as_of, md in _matchdays(matches, seasons):
        season = md["season"].iloc[0]
        teams = set(matches.loc[matches["season"] == season, "home_id"])
        model = fit_match_model(pool, as_of, params, teams, pool_seasons.get(int(season)))
        rows = []
        for f in md.itertuples(index=False):
            pred = model.predict(f.fixture_id, f.home_id, f.away_id)
            for module in GROUPS.values():
                for p in module.probabilities(pred):
                    if p.market not in SKIP_MARKETS:
                        rows.append(
                            (f.fixture_id, season, as_of, p.market, p.selection, p.line, p.probability)
                        )
        preds = pd.DataFrame(
            rows, columns=["fixture_id", "season", "as_of", "market", "selection", "line", "p_model"]
        )
        preds["line"] = preds["line"].astype(float)
        base = _baselines(outcomes, md, as_of)
        base["line"] = base["line"].astype(float)
        frame = preds.merge(base, on=keys, how="left").merge(
            outcomes[[*keys, "outcome"]], on=keys, how="inner"
        )
        frames.append(frame)
    result = pd.concat(frames, ignore_index=True)
    result["group"] = result["market"].map(market_group_of)
    return result


# --------------------------------------------------------------------------- metrics


def _log_loss(p: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(p, EPS, 1 - EPS)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def _brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def _ece(p: np.ndarray, y: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges) - 1, 0, bins - 1)
    ece = 0.0
    for b in range(bins):
        mask = idx == b
        if mask.any():
            ece += mask.mean() * abs(p[mask].mean() - y[mask].mean())
    return float(ece)


def binary_metrics(results: pd.DataFrame) -> pd.DataFrame:
    """Log loss, Brier and calibration error per market selection for model and baselines."""
    rows = []
    for (group, market, selection, line), r in results.groupby(
        ["group", "market", "selection", "line"], dropna=False
    ):
        y = r["outcome"].to_numpy(float)
        row = {
            "group": group,
            "market": market,
            "selection": selection,
            "line": line,
            "n": len(r),
            "rate": y.mean(),
        }
        for name in ("model", "base", "naive"):
            p = r[f"p_{name}"].to_numpy(float)
            row[f"logloss_{name}"] = _log_loss(p, y)
            row[f"brier_{name}"] = _brier(p, y)
        row["ece_model"] = _ece(r["p_model"].to_numpy(float), y)
        row["skill_vs_base"] = 1 - row["brier_model"] / row["brier_base"] if row["brier_base"] else np.nan
        row["skill_vs_naive"] = 1 - row["brier_model"] / row["brier_naive"] if row["brier_naive"] else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def multiclass_metrics(results: pd.DataFrame, market: str) -> dict[str, float]:
    """Multi-class log loss and ranked probability score for 1x2-type markets (H/D/A)."""
    r = results[results["market"] == market].pivot_table(
        index="fixture_id",
        columns="selection",
        values=["p_model", "p_base", "p_naive", "outcome"],
        aggfunc="first",
    )
    order = ["H", "D", "A"]
    y = r["outcome"][order].to_numpy(float)
    out = {"n": len(r)}
    for name in ("model", "base", "naive"):
        p = r[f"p_{name}"][order].to_numpy(float)
        p = p / p.sum(axis=1, keepdims=True)
        out[f"logloss_{name}"] = float(-np.mean(np.log(np.clip((p * y).sum(axis=1), EPS, None))))
        cp, cy = np.cumsum(p, axis=1)[:, :2], np.cumsum(y, axis=1)[:, :2]
        out[f"rps_{name}"] = float(np.mean(np.sum((cp - cy) ** 2, axis=1) / 2))
    return out


def calibration_table(results: pd.DataFrame, market: str, selection: str, line: float | None, bins: int = 10):
    r = results[(results["market"] == market) & (results["selection"] == selection)]
    r = r[r["line"].isna()] if line is None else r[r["line"] == line]
    cut = pd.cut(r["p_model"], np.linspace(0, 1, bins + 1), include_lowest=True)
    return r.groupby(cut, observed=True).agg(
        n=("outcome", "size"), predicted=("p_model", "mean"), observed=("outcome", "mean")
    )


# --------------------------------------------------------------------------- tuning


@dataclass
class TuningResult:
    params: PoissonParams
    score: float  # mean of 1x2 log loss and O/U 2.5 log loss (lower is better)


def tune_full_time(
    matches: pd.DataFrame, seasons: Iterable[int], grid: list[PoissonParams]
) -> list[TuningResult]:
    """Grid search on the full-time model using 1X2 and O/U 2.5 log loss on validation seasons."""
    days = _matchdays(matches, seasons)
    results = []
    for params in grid:
        ll_1x2, ll_ou = [], []
        for as_of, md in days:
            season = md["season"].iloc[0]
            teams = set(matches.loc[matches["season"] == season, "home_id"])
            fitted = fit_poisson(matches, as_of, params, "hg", "ag", teams, "hxg", "axg")
            for f in md.itertuples(index=False):
                from quotenfabrik.analytics.poisson import score_matrix

                lh, la = fitted.lambdas(f.home_id, f.away_id)
                m = score_matrix(lh, la, fitted.rho)
                i, j = np.indices(m.shape)
                p = {"H": m[i > j].sum(), "D": m[i == j].sum(), "A": m[i < j].sum()}
                res = "H" if f.hg > f.ag else "D" if f.hg == f.ag else "A"
                ll_1x2.append(-np.log(max(p[res], EPS)))
                over = m[(i + j) > 2.5].sum()
                y = float(f.hg + f.ag > 2.5)
                ll_ou.append(-(y * np.log(max(over, EPS)) + (1 - y) * np.log(max(1 - over, EPS))))
        results.append(TuningResult(params, float(np.mean(ll_1x2) + np.mean(ll_ou)) / 2))
    return sorted(results, key=lambda r: r.score)


# --------------------------------------------------------------------------- goalscorers


def walk_forward_scorers(
    matches: pd.DataFrame,
    player_matches: pd.DataFrame,
    seasons: Iterable[int],
    params: PoissonParams,
    scorer_params=None,
    use_lineups: bool = True,
    pool: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Anytime-scorer predictions for every squad player (starters + bench) of every finished match.

    ``use_lineups``: starters/bench are known (lineups are published ~1 h before kickoff). Otherwise the
    start probability from recent matches is used. Baseline ``p_base``: training frequency of scoring by
    (position, starter).
    """
    from quotenfabrik.analytics.scorers import ScorerModel

    pool = matches if pool is None else pool
    pool_seasons = season_leagues(pool)
    frames = []
    for as_of, md in _matchdays(matches, seasons):
        season = int(md["season"].iloc[0])
        teams = set(matches.loc[matches["season"] == season, "home_id"])
        ft = fit_poisson(pool, as_of, params, "hg", "ag", teams, "hxg", "axg", pool_seasons.get(season))
        model = ScorerModel(scorer_params).fit(player_matches, matches, as_of)
        since = as_of - pd.Timedelta(days=BASE_WINDOW_DAYS)
        hist = player_matches[(player_matches["kickoff"] < as_of) & (player_matches["kickoff"] >= since)]
        base = hist.assign(scored=hist["goals"] > 0).groupby(["position", "is_starter"])["scored"].mean()
        squads = player_matches[player_matches["fixture_id"].isin(md["fixture_id"])]
        rows = []
        for f in md.itertuples(index=False):
            lh, la = ft.lambdas(f.home_id, f.away_id)
            squad = squads[(squads["fixture_id"] == f.fixture_id) & squads["position"].isin(["D", "M", "F"])]
            for s in squad.itertuples(index=False):
                team_lambda = lh if s.team_id == f.home_id else la
                starter = s.is_starter if use_lineups else None
                lam = model.player_lambda(s.player_id, s.team_id, team_lambda, starter)
                known = s.player_id in model.players
                rows.append(
                    (f.fixture_id, md["season"].iloc[0], s.player_id, s.position, s.is_starter, known,
                     float(1 - np.exp(-lam)) if known else np.nan,
                     float(base.get((s.position, s.is_starter), np.nan)), bool(s.goals > 0))
                )  # fmt: skip
        columns = ["fixture_id", "season", "player_id", "position", "is_starter", "known",
                   "p_model", "p_base", "outcome"]  # fmt: skip
        frames.append(pd.DataFrame(rows, columns=columns))
    return pd.concat(frames, ignore_index=True)


# --------------------------------------------------------------------------- pattern signals

# pattern key -> (market, selection, line) whose outcome the pattern points to
PATTERN_TARGETS: dict[str, tuple[str, str, float | None]] = {
    "home_win_rate_home": ("1x2", "H", None),
    "away_win_rate_away": ("1x2", "A", None),
    "home_draw_rate": ("1x2", "D", None),
    "away_draw_rate": ("1x2", "D", None),
    "home_o15": ("ou_ft", "over", 1.5),
    "away_o15": ("ou_ft", "over", 1.5),
    "combined_o15": ("ou_ft", "over", 1.5),
    "home_o25": ("ou_ft", "over", 2.5),
    "away_o25": ("ou_ft", "over", 2.5),
    "combined_o25": ("ou_ft", "over", 2.5),
    "home_o35": ("ou_ft", "over", 3.5),
    "away_o35": ("ou_ft", "over", 3.5),
    "combined_o35": ("ou_ft", "over", 3.5),
    "combined_btts": ("btts", "yes", None),
    "home_scored": ("ou_home", "over", 0.5),
    "home_2plus": ("ou_home", "over", 1.5),
    "away_conceded_away": ("ou_home", "over", 0.5),
    "away_conceded_2plus_away": ("ou_home", "over", 1.5),
    "away_scored": ("ou_away", "over", 0.5),
    "away_2plus": ("ou_away", "over", 1.5),
    "home_conceded_home": ("ou_away", "over", 0.5),
    "home_clean_sheet": ("clean_sheet", "home", None),
    "away_clean_sheet": ("clean_sheet", "away", None),
    "combined_o05_1h": ("ou_1h", "over", 0.5),
    "combined_o15_1h": ("ou_1h", "over", 1.5),
    "combined_o15_2h": ("ou_2h", "over", 1.5),
}


def evaluate_pattern_signals(
    matches: pd.DataFrame, results: pd.DataFrame, seasons: Iterable[int]
) -> pd.DataFrame:
    """Out-of-sample hit rates of pattern signals, compared with league base rate and model probability.

    ``results`` is the output of ``walk_forward`` for the same seasons (provides p_model, p_base, outcome).
    """
    from quotenfabrik.analytics.patterns import PatternContext, compute_patterns

    lookup = results.set_index(["fixture_id", "market", "selection", "line"])[
        ["p_model", "p_base", "outcome"]
    ]
    rows = []
    for as_of, md in _matchdays(matches, seasons):
        ctx = PatternContext.build(matches, as_of)
        for f in md.itertuples(index=False):
            for p in compute_patterns(ctx, f.home_id, f.away_id):
                target = PATTERN_TARGETS.get(p.key)
                if target is None or p.signal is None:
                    continue
                market, selection, line = target
                key = (f.fixture_id, market, selection, np.nan if line is None else float(line))
                try:
                    r = lookup.loc[key]
                except KeyError:
                    continue
                rows.append((p.group, p.key, p.signal, r["p_model"], r["p_base"], bool(r["outcome"])))
    df = pd.DataFrame(rows, columns=["group", "pattern", "signal", "p_model", "p_base", "outcome"])
    return (
        df.groupby(["group", "pattern", "signal"])
        .agg(
            n=("outcome", "size"),
            observed=("outcome", "mean"),
            base=("p_base", "mean"),
            model=("p_model", "mean"),
        )
        .reset_index()
        .assign(
            lift_vs_base=lambda d: d["observed"] - d["base"],
            residual_vs_model=lambda d: d["observed"] - d["model"],
        )
    )
