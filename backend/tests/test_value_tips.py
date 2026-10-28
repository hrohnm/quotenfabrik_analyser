"""Value tips: blend of our model and Pinnacle, selection and result at the odds taken (pure functions)."""

import numpy as np
import pandas as pd
import pytest

from quotenfabrik.analytics import value_tips as vt


def _rows(spec):
    """(fixture_id, market, selection, p_model, fair_taken, taken, close, outcome)"""
    df = pd.DataFrame(spec, columns=["fixture_id", "market", "selection", "p_model", "fair_taken", "taken", "close",
                                     "outcome"])  # fmt: skip
    df["probability"] = df["p_model"]
    df["line"] = np.nan
    df["clv"] = df["taken"] * df["fair_taken"] - 1  # simplification: no line move
    return df


def test_blend_anchors_on_the_market_and_skips_rows_without_pinnacle():
    rows = _rows(
        [(1, "1x2", "H", 0.60, 0.50, 2.10, 2.10, True), (1, "btts", "yes", 0.7, np.nan, 1.5, 1.5, True)]
    )
    b = vt.blend(rows, vt.ValueSettings(model_weight=0.25))
    assert len(b) == 1
    assert b["probability"].iloc[0] == pytest.approx(0.25 * 0.60 + 0.75 * 0.50)
    assert b["edge"].iloc[0] == pytest.approx(0.525 * 2.10 - 1)


def test_select_thresholds_and_per_fixture_limit():
    s = vt.ValueSettings(model_weight=1.0, min_edge=0.05, min_p=0.3, max_odds=4.0, per_fixture=1)
    rows = vt.blend(_rows([
        (1, "1x2", "H", 0.55, 0.5, 2.1, 2.0, True),      # edge +15.5 %
        (1, "ou_ft", "over", 0.60, 0.5, 1.9, 1.9, False),  # edge +14 % (second of fixture 1 -> dropped)
        (2, "1x2", "A", 0.25, 0.2, 5.0, 5.0, False),     # odds above 4, probability below 0.3
        (3, "1x2", "D", 0.30, 0.3, 3.4, 3.4, True),      # edge +2 % below 5 %
    ]), s)  # fmt: skip
    tips = vt.select(rows, s)
    assert list(zip(tips["fixture_id"], tips["market"], strict=True)) == [(1, "1x2")]


def test_summarize_result_at_the_odds_taken():
    s = vt.ValueSettings(model_weight=1.0, min_edge=0.0)
    tips = vt.blend(_rows([(1, "1x2", "H", 0.6, 0.55, 2.0, 1.9, True), (2, "1x2", "A", 0.5, 0.45, 2.4, 2.5, False),
                           (3, "1x2", "H", 0.6, 0.5, 2.0, 2.0, None)]), s)  # fmt: skip
    r = vt.summarize(tips)
    assert r["n"] == 2 and r["fixtures"] == 2
    assert r["roi"] == pytest.approx((1.0 - 1.0) / 2)
    assert r["hit_rate"] == 0.5 and r["beat_close"] == 0.5
    assert r["roi_ci"][0] <= r["roi"] <= r["roi_ci"][1]


def test_summarize_without_settled_tips():
    assert vt.summarize(pd.DataFrame()) == {"n": 0, "fixtures": 0}


def test_blend_drops_broken_probabilities_and_prices():
    rows = _rows([(1, "1x2", "H", np.nan, 0.5, 2.1, 2.1, True), (2, "1x2", "H", 0.6, 0.5, np.inf, 2.1, True),
                  (3, "1x2", "H", 0.6, 0.5, 1.0, 1.0, True), (4, "1x2", "H", 0.6, 0.5, 2.1, 2.1, True)])  # fmt: skip
    b = vt.blend(rows, vt.ValueSettings())
    assert list(b["fixture_id"]) == [4]


def test_json_safe_replaces_nan_and_numpy_values():
    from quotenfabrik.api.data import json_safe

    out = json_safe({"a": float("nan"), "b": [np.float64(1.5), np.int64(2), float("inf")], "c": {"d": None}})
    assert out == {"a": None, "b": [1.5, 2, None], "c": {"d": None}}
