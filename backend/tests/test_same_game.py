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
    assert 1.45 < c["builder_odds"] < 1.75


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
