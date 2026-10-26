"""Closing line value of the picks: summary, odds-matched baseline, evaluation and report (pure functions)."""

import math

import pandas as pd
import pytest

from quotenfabrik.analytics import clv

KICKOFF = pd.Timestamp("2026-05-02 13:30", tz="UTC")


def _rows(spec: list[tuple[int, float, float, float, bool]], **extra) -> pd.DataFrame:
    """(fixture_id, taken, close, fair_close, outcome) → priced rows like ``attach_prices`` returns."""
    df = pd.DataFrame(spec, columns=["fixture_id", "taken", "close", "fair_close", "outcome"])
    df["fair_taken"] = df["fair_close"]
    df["probability"] = 0.7
    df["clv"] = df["taken"] * df["fair_close"] - 1
    df["move"] = df["taken"] / df["close"] - 1
    df["shift"] = 0.0
    for k, v in extra.items():
        df[k] = v
    return df


def test_summarize_clv_moves_and_result():
    rows = _rows([(1, 1.5, 1.4, 0.7, True), (1, 1.3, 1.3, 0.75, False), (2, 2.0, 2.2, 0.5, True)])
    s = clv.summarize(rows)
    assert s["n"] == 3 and s["fixtures"] == 2
    assert s["clv"] == pytest.approx(((1.5 * 0.7 - 1) + (1.3 * 0.75 - 1) + 0) / 3)
    assert s["beat_close"] == pytest.approx(1 / 3) and s["worse_close"] == pytest.approx(1 / 3)
    assert s["roi"] == pytest.approx((0.5 - 1 + 1.0) / 3)
    assert s["hit_rate"] == pytest.approx(2 / 3)
    assert s["clv_se"] > 0


def test_summarize_without_pinnacle_close_keeps_odds_moves():
    rows = _rows([(1, 1.5, 1.4, math.nan, True), (2, 1.6, 1.6, math.nan, False)])
    s = clv.summarize(rows)
    assert s["clv"] is None and s["clv_n"] == 0 and s["beat_close"] == 0.5


def test_clustered_se_counts_fixtures_not_picks():
    """Three identical picks per fixture carry the information of one: the SE must not shrink by √3."""
    one = _rows([(1, 1.5, 1.5, 0.70, True), (2, 1.5, 1.5, 0.66, True), (3, 1.5, 1.5, 0.64, True)])
    triple = pd.concat([one, one, one], ignore_index=True)
    se1, se3 = clv.summarize(one)["clv_se"], clv.summarize(triple)["clv_se"]
    assert se3 == pytest.approx(se1, rel=1e-9)


def test_matched_baseline_weights_by_odds_of_the_picks():
    # favourites (odds 1.2) lose 2 % to the closing price, outsiders (odds 3.0) lose 10 %
    base = _rows([(i, 1.2, 1.2, 0.98 / 1.2, True) for i in range(10)]
                 + [(i, 3.0, 3.0, 0.90 / 3.0, False) for i in range(10)])  # fmt: skip
    picks = _rows([(i, 1.2, 1.2, 0.99 / 1.2, True) for i in range(4)])
    assert clv.matched_baseline(picks, base) == pytest.approx(-0.02)
    assert base["clv"].mean() == pytest.approx(-0.06)  # the unweighted mean would flatter short-odds picks


def test_evaluate_sections_and_report():
    picks = _rows(
        [(1, 1.5, 1.4, 0.7, True), (1, 1.3, 1.25, 0.78, True), (2, 1.4, 1.45, 0.7, False)],
        kind="backtest", profile="sicher", market_group="totals", league_id=78, lead_h=[30.0, 30.0, 5.0],
        kickoff_utc=KICKOFF,
    )  # fmt: skip
    base = _rows([(1, 1.5, 1.5, 0.64, True), (2, 1.4, 1.4, 0.68, False)], kind="backtest",
                 market_group="totals", league_id=78, lead_h=[30.0, 5.0])  # fmt: skip
    labels = {
        "profiles": {"sicher": "Sicher"},
        "groups": {"totals": "Tore gesamt"},
        "leagues": {78: "Bundesliga"},
    }
    result = clv.evaluate(picks, base, labels)
    assert result["picks"] == 3 and result["fixtures"] == 2
    assert result["total"]["delta"] == pytest.approx(result["total"]["clv"] - result["total"]["baseline"])
    assert [r["key"] for r in result["leads"]] == ["unter 6 h", "1–3 Tage"]
    assert result["leagues"][0]["label"] == "Bundesliga" and result["profiles"][0]["label"] == "Sicher"
    text = clv.report(result)
    assert text.startswith("# Closing Line Value") and "| Sicher |" in text and "Bundesliga" in text


def test_evaluate_without_picks():
    assert clv.evaluate(pd.DataFrame(), pd.DataFrame()) == {"picks": 0}
    assert "Noch keine Tipps" in clv.report({"picks": 0})
