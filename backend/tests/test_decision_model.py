"""Tippschein decision model: no leakage, walk-forward, fit, confidence and stored models."""

import numpy as np
import pandas as pd
import pytest

from quotenfabrik.analytics import decision_features as dfe
from quotenfabrik.analytics import decision_model as dm
from quotenfabrik.analytics import decisions as dc

T = pd.Timestamp


def test_team_values_are_taken_strictly_before_kickoff():
    fixtures = pd.DataFrame({"fixture_id": [10, 11], "kickoff": [T("2024-03-02 15:30", tz="UTC")] * 2,
                             "home_id": [1, 3], "away_id": [2, 1]})  # fmt: skip
    values = pd.DataFrame({
        "team": [1, 1, 2],
        "kickoff": [T("2024-02-20", tz="UTC"), T("2024-03-02 15:30", tz="UTC"), T("2024-02-25", tz="UTC")],
        "form_ppg": [1.0, 3.0, 2.0],  # the value of the match itself (same kickoff) must not be used
    })  # fmt: skip
    out = dfe._asof(fixtures, values, ["form_ppg"], "").set_index("fixture_id")
    assert out.loc[10, "home_form_ppg"] == 1.0 and out.loc[10, "away_form_ppg"] == 2.0
    assert out.loc[11, "away_form_ppg"] == 1.0 and np.isnan(out.loc[11, "home_form_ppg"])


def _synthetic(n_per_season: int = 400, seasons=range(2017, 2025), effect: float = 1.2) -> pd.DataFrame:
    """Binary decision o25 where the feature ``home_style_shots`` shifts the true probability."""
    rng = np.random.default_rng(3)
    rows = []
    for season in seasons:
        for i in range(n_per_season):
            p_model = rng.uniform(0.35, 0.7)
            x = rng.normal()
            true = 1 / (1 + np.exp(-(np.log(p_model / (1 - p_model)) + effect * x)))
            rows.append({"fixture_id": season * 10000 + i, "season": season, "p_o25": p_model,
                         "home_style_shots": x, "pat_noise": rng.normal(), "y_o25": float(rng.random() < true)})  # fmt: skip
    return pd.DataFrame(rows)


def test_fit_learns_a_real_feature_and_ignores_noise():
    frame = _synthetic()
    spec = dm.BY_KEY["o25"]
    prep = dm.Prep.fit(frame, dm.feature_columns(frame))
    model = dm.fit(prep.transform(frame), dm.offsets(frame, spec), dm.labels(frame, spec), alpha=0.01)
    cols = dm.feature_columns(frame)
    w = dict(zip(cols, -model.w[: len(cols), 1], strict=True))  # class 0 = over; weights of class 1 = under
    assert w["home_style_shots"] > 0.8
    assert abs(w["pat_noise"]) < 0.15
    assert model.b == pytest.approx(1.0, abs=0.25)


def test_walk_forward_uses_only_earlier_seasons(monkeypatch):
    frame = _synthetic(n_per_season=50)
    seen = []
    original = dm.Prep.fit

    def spy(cls, train, columns):
        seen.append(set(train["season"]))
        return original.__func__(cls, train, columns)

    monkeypatch.setattr(dm.Prep, "fit", classmethod(spy))
    pred = dm.walk_forward(frame, dm.BY_KEY["o25"], 0.1, [2019, 2020])
    assert seen == [{2017, 2018}, {2017, 2018, 2019}]
    assert set(frame.loc[pred.index, "season"]) == {2019, 2020}


def test_stacked_model_beats_the_goal_model_out_of_sample():
    frame = _synthetic()
    spec = dm.BY_KEY["o25"]
    pred = dm.walk_forward(frame, spec, 0.1, [2023, 2024])
    y = dm.labels(frame, spec)[pred.index]
    new = dm.log_loss(pred[list(spec.classes)].to_numpy(), y).mean()
    raw = dm.log_loss(np.exp(dm.offsets(frame.loc[pred.index], spec)), y).mean()
    assert new < raw - 0.05


def test_winner_is_multinomial_and_payload_roundtrip():
    rng = np.random.default_rng(5)
    p = rng.dirichlet([4, 2.5, 3], size=600)
    won = np.array([rng.choice(3, p=q) for q in p])
    frame = pd.DataFrame({"fixture_id": range(600), "season": [2020 + i // 200 for i in range(600)],
                          "p_home": p[:, 0], "p_draw": p[:, 1], "p_away": p[:, 2],
                          "y_home": (won == 0).astype(float), "y_draw": (won == 1).astype(float),
                          "y_away": (won == 2).astype(float), "home_form_ppg": rng.normal(size=600)})  # fmt: skip
    payload = dm.fit_production(frame, dm.BY_KEY["winner"], 0.3)
    payload["confidence"] = dm.confidence_table(np.linspace(0.3, 0.8, 101))
    out = dm.apply(frame, payload)
    assert np.allclose(out[["H", "D", "A"]].sum(axis=1), 1)
    assert out["confidence"].between(0, 100).all()


def test_confidence_is_the_rank_among_past_predictions():
    table = dm.confidence_table(np.linspace(0.5, 1.0, 1001))
    assert dm.confidence(np.array([0.5, 0.75, 1.0]), table) == pytest.approx([0, 50, 100], abs=0.5)
    assert np.isnan(dm.confidence(np.array([0.7]), [])).all()


def test_decide_uses_the_decision_model_and_the_minimum_confidence():
    preds = pd.DataFrame([
        {"fixture_id": 1, "market": "ou_ft", "selection": "over", "line": 2.5, "probability": 0.52, "outcome": True},
        {"fixture_id": 1, "market": "ou_ft", "selection": "under", "line": 2.5, "probability": 0.48, "outcome": False},
        {"fixture_id": 1, "market": "btts", "selection": "yes", "line": None, "probability": 0.6, "outcome": False},
        {"fixture_id": 1, "market": "btts", "selection": "no", "line": None, "probability": 0.4, "outcome": True},
    ])  # fmt: skip
    stacked = pd.DataFrame([
        {"fixture_id": 1, "decision": "o25", "probabilities": {"over": 0.45, "under": 0.55}, "confidence": 72.0},
        {"fixture_id": 1, "decision": "btts", "probabilities": {"yes": 0.58, "no": 0.42}, "confidence": 20.0},
    ])  # fmt: skip
    rows = dc.decide(preds, stacked, 50).set_index("decision")
    assert rows.loc["o25", "pick"] == "under" and rows.loc["o25", "model_probability"] == 0.48
    assert bool(rows.loc["o25", "tipped"]) and not bool(rows.loc["btts", "tipped"])
    result = dc.evaluate(rows.reset_index().assign(season=2024))
    assert result["tipped"]["n"] == 1 and result["tipped"]["hit_rate"] == 0.0
