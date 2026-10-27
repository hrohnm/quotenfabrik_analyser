"""Same-game combo (Bet Builder): joint probability of correlated picks of one fixture."""

import math

import pytest

from quotenfabrik.analytics import same_game as sg

LAMBDAS = (0.34, 0.73, 0.82, 0.74)  # home 1H, away 1H, home 2H, away 2H


def test_half_lambdas_from_stored_predictions():
    probs = {key: math.exp(-lam) for key, lam in zip(sg.HALF_KEYS, LAMBDAS, strict=True)}
    assert sg.half_lambdas(probs) == pytest.approx(LAMBDAS)
    assert sg.half_lambdas({k: v for k, v in list(probs.items())[:3]}) is None


def test_independent_legs_have_factor_one():
    # different teams in different halves are independent in the model
    legs = [("ou_home_1h", "over", 0.5), ("ou_away_2h", "over", 0.5)]
    assert sg.correlation_factor(LAMBDAS, legs) == pytest.approx(1.0, abs=1e-6)


def test_correlated_legs_raise_the_joint_chance():
    # away team scores, away win or draw, goal in the 2nd half (Sassuolo – Lazio)
    legs = [("ou_away", "over", 0.5), ("dc", "X2", None), ("ou_2h", "over", 0.5)]
    factor = sg.correlation_factor(LAMBDAS, legs)
    assert factor > 1.15
    c = sg.combo([0.77, 0.70, 0.79], factor, [1.18, 1.35, 1.19])
    assert c["naive"] == pytest.approx(0.77 * 0.70 * 0.79)
    assert c["probability"] == pytest.approx(c["naive"] * factor)
    assert c["fair_odd"] == pytest.approx(1 / c["probability"])
    # Bet Builder: product of the Betano odds 1.90 corrected for the correlation (Betano offered 1.62)
    assert c["betano_product"] == pytest.approx(1.18 * 1.35 * 1.19)
    assert 1.45 < c["builder_odds"] < 1.75  # without legs: product ÷ model factor


def test_excluding_legs_lower_the_joint_chance():
    assert sg.correlation_factor(LAMBDAS, [("1x2", "H", None), ("1x2", "A", None)]) == 0.0
    assert sg.correlation_factor(LAMBDAS, [("ou_ft", "under", 1.5), ("btts", "yes", None)]) == 0.0


def test_grid_marginals_match_closed_form():
    grid_p = sg.correlation_factor(LAMBDAS, [("ou_home_1h", "over", 0.5)])
    assert grid_p == pytest.approx(1.0)  # a single leg is its own product
    assert sg._mask("ou_home_1h", "over", 0.5).shape == (sg.MAX_GOALS + 1,) * 4


def test_unsupported_market_and_cap():
    assert sg.correlation_factor(LAMBDAS, [("exact_goals", "2", None)]) is None
    c = sg.combo([0.9, 0.5], 5.0, [1.1, None])
    assert c["probability"] == 0.5  # never above the least likely leg
    assert c["builder_odds"] is None and c["betano_product"] is None
    assert sg.combo([0.9, 0.5], None)["probability"] is None


# real Betano Bet Builder prices (27.10.2026): legs, Betano single odds, model half rates (prior), Bet Builder
BUILDER_EXAMPLES = [
    ([("ou_away", "over", 0.5), ("dc", "X2", None), ("ou_2h", "over", 0.5)], [1.18, 1.35, 1.19], 1.62),
    ([("dc", "X2", None), ("ou_ft", "over", 1.5), ("ou_2h", "over", 0.5)], [1.08, 1.13, 1.13], 1.28),
    ([("ou_away", "over", 1.5), ("ou_away_1h", "over", 0.5), ("1x2", "A", None)], [1.65, 1.65, 2.07], 2.67),
    ([("dc", "X2", None), ("ou_away", "over", 1.5), ("ou_away_1h", "over", 0.5)], [1.05, 1.19, 1.31], 1.42),
]


@pytest.mark.parametrize(("legs", "odds", "actual"), BUILDER_EXAMPLES)
def test_builder_odds_close_to_real_bet_builder_prices(legs, odds, actual):
    estimate = sg.builder_odds(legs, odds, prior=(0.3, 0.6, 0.4, 0.8))  # away side stronger in all four
    assert estimate == pytest.approx(actual, rel=0.06)
    assert estimate < math.prod(odds)  # always below the product of the single odds


def test_fit_lambdas_reproduces_targets():
    legs = [("ou_home_1h", "over", 0.5), ("ou_away_2h", "over", 0.5)]
    lam = sg.fit_lambdas(legs, [1 - math.exp(-0.4), 1 - math.exp(-0.9)], prior=(0.5, 0.5, 0.5, 0.5))
    assert lam[0] == pytest.approx(0.4, rel=0.02) and lam[3] == pytest.approx(0.9, rel=0.02)


def test_combo_with_legs_uses_the_betano_fit():
    legs = BUILDER_EXAMPLES[2][0]
    c = sg.combo([0.75, 0.75, 0.73], 1.5, [1.65, 1.65, 2.07], legs, (0.3, 0.6, 0.4, 0.8))
    assert c["builder_odds"] == pytest.approx(2.67, rel=0.06)
    assert c["edge"] == pytest.approx(c["probability"] * c["builder_odds"] - 1)
