"""Model, market and pattern tests on synthetic data (no database)."""

import numpy as np
import pandas as pd
import pytest

from quotenfabrik.analytics import evaluation as ev
from quotenfabrik.analytics.markets import GROUPS
from quotenfabrik.analytics.patterns import PatternContext, compute_patterns, wilson
from quotenfabrik.analytics.poisson import PoissonParams, fit_poisson, score_matrix
from quotenfabrik.analytics.prediction import MatchPrediction, fit_match_model
from quotenfabrik.analytics.scorers import ScorerModel

TEAMS = [1, 2, 3, 4, 5, 6]
STRENGTH = {1: 0.5, 2: 0.3, 3: 0.0, 4: 0.0, 5: -0.3, 6: -0.5}


def synthetic_matches(seasons=(2020, 2021, 2022), seed=7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows, fid = [], 1
    for season in seasons:
        start = pd.Timestamp(f"{season}-08-15", tz="UTC")
        pairs = [(h, a) for h in TEAMS for a in TEAMS if h != a]
        for k, (h, a) in enumerate(pairs):
            kickoff = start + pd.Timedelta(days=7 * (k // 3))
            lh = np.exp(0.25 + 0.25 + STRENGTH[h] - (-STRENGTH[a]) * 0.5)
            la = np.exp(0.25 + STRENGTH[a] - (-STRENGTH[h]) * 0.5)
            h1, a1 = rng.poisson(lh * 0.45), rng.poisson(la * 0.45)
            h2, a2 = rng.poisson(lh * 0.55), rng.poisson(la * 0.55)
            rows.append(
                {"fixture_id": fid, "season": season, "matchday": k // 3 + 1, "kickoff": kickoff,
                 "status": "FT", "home_id": h, "away_id": a, "hg": h1 + h2, "ag": a1 + a2,
                 "hthg": h1, "htag": a1, "hxg": np.nan, "axg": np.nan, "finished": True}
            )  # fmt: skip
            fid += 1
    df = pd.DataFrame(rows)
    df["h2g"], df["a2g"] = df["hg"] - df["hthg"], df["ag"] - df["htag"]
    return df


@pytest.fixture(scope="module")
def matches() -> pd.DataFrame:
    return synthetic_matches()


def test_score_matrix_is_a_distribution():
    m = score_matrix(1.6, 1.1, rho=-0.08)
    assert m.shape == (11, 11)
    assert abs(m.sum() - 1) < 1e-9
    assert (m >= 0).all()


def test_fit_ranks_strong_teams_higher(matches):
    model = fit_poisson(matches, pd.Timestamp("2023-06-01", tz="UTC"), PoissonParams(reg=1.0))
    strength = {t: model.attack[t] + model.defence[t] for t in TEAMS}
    assert strength[1] > strength[3] > strength[6]
    assert model.home_adv > 0


def test_no_leakage_future_results_do_not_change_predictions(matches):
    as_of = pd.Timestamp("2022-01-01", tz="UTC")
    before = fit_match_model(matches, as_of, PoissonParams(), set(TEAMS)).predict(0, 1, 6)
    changed = matches.copy()
    future = changed["kickoff"] >= as_of
    changed.loc[future, ["hg", "ag", "hthg", "htag", "h2g", "a2g"]] = [9, 0, 5, 0, 4, 0]
    after = fit_match_model(changed, as_of, PoissonParams(), set(TEAMS)).predict(0, 1, 6)
    assert (before.lh, before.la, before.lh_1h, before.la_2h) == (
        after.lh,
        after.la,
        after.lh_1h,
        after.la_2h,
    )


def test_new_team_gets_promoted_prior(matches):
    model = fit_poisson(matches, pd.Timestamp("2023-06-01", tz="UTC"), PoissonParams(), current_teams={99})
    assert 99 in model.new_teams
    assert model.attack[99] < 0 and model.defence[99] < 0


def _prediction() -> MatchPrediction:
    return MatchPrediction(1, 1, 2, 1.7, 1.1, -0.06, 0.75, 0.5, 0.95, 0.6)


def test_market_probabilities_are_consistent():
    pred = _prediction()
    probs = {p.key: p.probability for module in GROUPS.values() for p in module.probabilities(pred)}
    assert abs(probs[("1x2", "H", None)] + probs[("1x2", "D", None)] + probs[("1x2", "A", None)] - 1) < 1e-9
    for market, line in (("ou_ft", 2.5), ("ou_home", 1.5), ("ou_1h", 0.5), ("ou_away_2h", 0.5)):
        assert abs(probs[(market, "over", line)] + probs[(market, "under", line)] - 1) < 1e-9
    assert probs[("ou_ft", "over", 1.5)] > probs[("ou_ft", "over", 2.5)] > probs[("ou_ft", "over", 3.5)]
    hh = [probs[("highest_half", s, None)] for s in ("1H", "2H", "equal")]
    assert abs(sum(hh) - 1) < 1e-9
    assert probs[("dnb", "H", None)] > probs[("1x2", "H", None)]


def test_outcomes_cover_every_predicted_market(matches):
    pred = _prediction()
    m = matches.iloc[0]
    for module in GROUPS.values():
        predicted = {p.key for p in module.probabilities(pred) if p.market not in {"dc", "dnb"}}
        outcome_keys = set(module.outcomes(m).keys())
        assert predicted <= outcome_keys | {k for k in predicted if k[0] in {"dc", "dnb"}}


def test_walk_forward_uses_only_past_data(matches):
    res = ev.walk_forward(matches, [2022], PoissonParams())
    assert (
        res["as_of"] <= matches.set_index("fixture_id").loc[res["fixture_id"], "kickoff"].to_numpy()
    ).all()
    assert res["p_model"].between(0, 1).all() and res["p_base"].notna().all()
    metrics = ev.binary_metrics(res)
    assert {"brier_model", "brier_base", "brier_naive", "ece_model"} <= set(metrics.columns)


def test_wilson_interval():
    low, high = wilson(8, 10)
    assert 0.6 < low < 0.8 < high < 0.95
    assert wilson(0, 0) == (0.0, 1.0)


def test_patterns_ignore_future_matches(matches):
    as_of = pd.Timestamp("2022-01-01", tz="UTC")
    a = compute_patterns(PatternContext.build(matches, as_of), 1, 6)
    changed = matches.copy()
    changed.loc[changed["kickoff"] >= as_of, ["hg", "ag"]] = [9, 9]
    b = compute_patterns(PatternContext.build(changed, as_of), 1, 6)
    assert [(p.key, p.value, p.signal) for p in a] == [(p.key, p.value, p.signal) for p in b]
    keys = {p.key for p in a}
    assert {"home_win_rate_home", "combined_o25", "home_scored", "combined_o05_1h"} <= keys


def test_scorer_model_uses_minutes_and_lineup():
    kick = pd.Timestamp("2022-01-01", tz="UTC")
    rows = []
    for i in range(20):
        day = kick - pd.Timedelta(days=7 * (i + 1))
        rows.append((i, day, 2021, 1, 10, "Striker", "F", True, 90, 1 if i % 2 == 0 else 0, 0, 3, 2))
        rows.append((i, day, 2021, 1, 11, "Defender", "D", True, 90, 1 if i == 0 else 0, 0, 1, 0))
    players = pd.DataFrame(rows, columns=["fixture_id", "kickoff", "season", "team_id", "player_id", "name",
                                          "position", "is_starter", "minutes", "goals", "pen_goals", "shots",
                                          "shots_on"])  # fmt: skip
    matches = pd.DataFrame(
        {
            "kickoff": players["kickoff"].unique(),
            "home_id": 1,
            "away_id": 2,
            "hg": 2,
            "ag": 1,
            "finished": True,
        }
    )
    model = ScorerModel().fit(players, matches, kick)
    striker_start = model.player_lambda(10, 1, 2.0, True)
    striker_bench = model.player_lambda(10, 1, 2.0, False)
    defender = model.player_lambda(11, 1, 2.0, True)
    assert striker_start > defender > 0
    assert striker_start > 3 * striker_bench


def test_hit_rate_picks():
    from quotenfabrik.api.routers.stats import picks

    rows = [
        # 1X2: pick = H (0.5), outcome D -> miss
        (1, "1x2", "H", np.nan, 0.5, False),
        (1, "1x2", "D", np.nan, 0.3, True),
        (1, "1x2", "A", np.nan, 0.2, False),
        # O/U 2.5: pick = over (0.6), outcome over -> hit
        (1, "ou_ft", "over", 2.5, 0.6, True), (1, "ou_ft", "under", 2.5, 0.4, False),
        # single-selection market: clean sheet home 30 % -> "no" call, outcome False -> hit
        (1, "clean_sheet", "home", np.nan, 0.3, False),
    ]  # fmt: skip
    data = pd.DataFrame(rows, columns=["fixture_id", "market", "selection", "line", "probability", "outcome"])
    data["market_group"], data["season"] = "x", 2025
    result = picks(data).set_index("market")
    assert not result.loc["1x2", "hit"] and result.loc["1x2", "selection"] == "H"
    assert result.loc["ou_ft", "hit"] and result.loc["ou_ft", "pick_probability"] == 0.6
    assert (
        result.loc["clean_sheet", "hit"] and abs(result.loc["clean_sheet", "pick_probability"] - 0.7) < 1e-9
    )
