"""Odds arithmetic and the odds backtest on synthetic data (no database)."""

import numpy as np
import pandas as pd
import pytest

from quotenfabrik.analytics import odds_backtest as ob
from quotenfabrik.analytics.value import (
    closing_line_value,
    expected_value,
    kelly,
    log_pool,
    overround,
    remove_margin,
)

ODDS = np.array([[1.50, 4.20, 6.50], [2.60, 3.30, 2.80]])


@pytest.mark.parametrize("method", ["shin", "power", "proportional"])
def test_remove_margin_gives_distributions(method):
    p = remove_margin(ODDS, method)
    assert np.allclose(p.sum(axis=1), 1)
    assert (p > 0).all()
    # without margin every method returns the implied probabilities
    fair = np.array([[2.0, 4.0, 4.0]])
    assert np.allclose(remove_margin(fair, method), [[0.5, 0.25, 0.25]], atol=1e-6)


def test_shin_and_power_take_more_margin_from_longshots():
    prop, shin, power = (remove_margin(ODDS[:1], m)[0] for m in ("proportional", "shin", "power"))
    assert shin[0] > prop[0] and shin[2] < prop[2]
    assert power[0] > prop[0] and power[2] < prop[2]


def test_invalid_rows_become_nan():
    p = remove_margin(np.array([[2.0, np.nan], [1.0, 3.0], [1.9, 1.9]]))
    assert np.isnan(p[0]).all() and np.isnan(p[1]).all()
    assert np.allclose(p[2], [0.5, 0.5])


def test_value_formulas():
    assert overround(np.array([[1.9, 1.9]]))[0] == pytest.approx(2 / 1.9 - 1)
    assert expected_value(0.55, 2.0) == pytest.approx(0.10)
    assert kelly(0.55, 2.0, fraction=1, cap=1) == pytest.approx(0.10)
    assert kelly(0.40, 2.0) == 0  # no bet without edge
    assert kelly(0.9, 2.0) == 0.02  # capped
    assert closing_line_value(2.2, 0.5) == pytest.approx(0.10)


def test_log_pool_weights():
    market, model = np.array([[0.6, 0.4]]), np.array([[0.4, 0.6]])
    assert np.allclose(log_pool(market, model, 1, 0), market)
    assert np.allclose(log_pool(market, model, 0, 1), model)
    assert np.allclose(log_pool(market, model, 0.5, 0.5), [[0.5, 0.5]])


def synthetic_market(seed: int = 3, n: int = 1200) -> ob.MarketData:
    """Two-way market: bookmaker odds with 5 % margin around the truth, model = noisy truth."""
    rng = np.random.default_rng(seed)
    truth = rng.uniform(0.3, 0.7, n)
    p_true = np.c_[truth, 1 - truth]
    outcome = rng.random(n) < truth
    y = np.c_[outcome, ~outcome].astype(float)
    model = np.clip(truth + rng.normal(0, 0.05, n), 0.05, 0.95)
    data = ob.MarketData(
        spec=ob.MARKETS[1],
        fixture_id=np.arange(n),
        season=np.repeat([2019, 2020, 2021, 2022], n // 4),
        date=pd.date_range("2019-08-01", periods=n, freq="D").to_numpy(),
        p_model=np.c_[model, 1 - model],
        y=y,
    )
    odds = 1 / (p_true * 1.05)
    for book in ob.BOOKS:
        data.odds[book] = {"open": odds.copy(), "close": odds.copy()}
    return data


def test_value_bets_one_bet_per_match_and_profit():
    data = synthetic_market()
    p_close = data.reference("close")
    bets = ob.value_bets(data, data.p_model, "b365", 0.0, np.ones(len(data), bool), p_close)
    assert bets["fixture_id"].is_unique
    assert (bets["edge"] > 0).all()
    won = bets["won"].to_numpy()
    assert np.allclose(bets["profit"][won], bets["odd"][won] - 1)
    assert (bets["profit"][~won] == -1).all()
    s = ob.summarize(bets)
    assert s["roi_low"] <= s["roi"] <= s["roi_high"]
    assert s["clv"] == pytest.approx(-0.05 / 1.05, abs=0.01)  # 5 % margin, odds never move


def test_choices_use_only_validation_seasons():
    data = synthetic_market()
    before = ob.analyse_market(data, validation_until=2021)
    test = data.season > 2021
    data.y[test] = 1 - data.y[test]  # flip every test outcome
    after = ob.analyse_market(data, validation_until=2021)
    assert before.blend == after.blend
    assert [s["threshold"] for s in before.strategies] == [s["threshold"] for s in after.strategies]
    assert before.quality["test"] != after.quality["test"]
