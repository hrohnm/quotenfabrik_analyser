"""Evaluation with thin data (e.g. a league or cup without goalscorer data): metrics None, never NaN."""

import json
import math

import numpy as np
import pandas as pd

from quotenfabrik.analytics import evaluation as ev
from quotenfabrik.analytics import service
from quotenfabrik.analytics.poisson import PoissonParams
from quotenfabrik.analytics.scorers import ScorerParams
from quotenfabrik.json_utils import dumps, json_safe
from quotenfabrik.models import ModelRun

SCORER_COLUMNS = ["fixture_id", "player_id", "known", "p_model", "p_base", "outcome"]


def _no_nan(obj) -> bool:
    return json.loads(json.dumps(obj, allow_nan=False)) is not None  # raises on NaN / inf


def test_scorer_summary_without_any_rows():
    s = service._scorer_summary(pd.DataFrame(columns=SCORER_COLUMNS))
    assert s["overall"] == {"n": 0, "unknown_players": 0, "model": {"logloss": None, "brier": None},
                            "base": {"logloss": None, "brier": None}}  # fmt: skip
    assert s["calibration"].empty and _no_nan(s["overall"])


def test_scorer_summary_when_no_player_is_known():
    """League 43: scorer rows exist, but none survives the filter (unknown players / no probabilities)."""
    rows = pd.DataFrame({"fixture_id": [1, 1, 2], "player_id": [10, 11, 12], "known": [False, False, True],
                         "p_model": [np.nan, np.nan, np.nan], "p_base": [0.2, 0.1, np.nan],
                         "outcome": [1.0, 0.0, 0.0]})  # fmt: skip
    s = service._scorer_summary(rows)
    assert s["overall"]["n"] == 0 and s["overall"]["unknown_players"] == 2
    assert s["overall"]["model"] == {"logloss": None, "brier": None}
    assert _no_nan(s["overall"])


def test_scorer_summary_with_data_keeps_the_metrics():
    rows = pd.DataFrame(
        {"known": [True, True], "p_model": [0.3, 0.1], "p_base": [0.2, 0.2], "outcome": [1.0, 0.0]}
    )
    s = service._scorer_summary(rows)["overall"]
    assert s["n"] == 2 and math.isclose(s["model"]["brier"], ((0.3 - 1) ** 2 + 0.1**2) / 2)


def test_multiclass_metrics_without_fixtures():
    empty = pd.DataFrame(
        columns=["fixture_id", "market", "selection", "p_model", "p_base", "p_naive", "outcome"]
    )
    m = ev.multiclass_metrics(empty, "ht_1x2")
    assert m["n"] == 0 and m["rps_model"] is None and m["logloss_base"] is None


def test_report_shows_no_data_instead_of_failing():
    results = pd.DataFrame(columns=["fixture_id", "season", "market", "selection", "line", "p_model", "p_base",
                                    "p_naive", "outcome"])  # fmt: skip
    binary = pd.DataFrame(columns=["group", "market", "selection", "line", "n", "rate", "brier_model", "brier_base",
                                   "brier_naive", "skill_vs_base", "skill_vs_naive", "ece_model"])  # fmt: skip
    signals = pd.DataFrame(columns=["group", "pattern", "signal", "n", "rate", "baseline", "model", "lift",
                                    "residual", "label"])  # fmt: skip
    multi = {m: ev.multiclass_metrics(results, m) for m in ("1x2", "ht_1x2")}
    scorers = service._scorer_summary(pd.DataFrame(columns=SCORER_COLUMNS))
    text = service.render_report(1, [2025], PoissonParams(), ScorerParams(), binary, multi, scorers, signals,
                                 service._per_season(results), results)  # fmt: skip
    assert "Keine Daten" in text and "nan" not in text.lower()


def test_model_run_never_stores_nan():
    run = ModelRun(kind="evaluation", model_version="dc-v1", league_id=43,
                   params={"x": float("inf")}, summary={"scorers": {"model": {"logloss": float("nan")}},
                                                        "n": np.int64(3), "rps": np.float64(0.2)})  # fmt: skip
    assert run.summary == {"scorers": {"model": {"logloss": None}}, "n": 3, "rps": 0.2}
    assert run.params == {"x": None}


def test_json_helpers():
    assert json_safe([np.nan, (1, np.float32(0.5))]) == [None, [1, 0.5]]
    assert dumps({"a": float("-inf"), "b": np.array([1.0, np.nan])}) == '{"a": null, "b": [1.0, null]}'


def test_nan_summary_is_stored_in_postgres(session):
    """Before the fix PostgreSQL rejected the insert ("Token NaN is invalid")."""
    session.add(ModelRun(kind="evaluation", model_version="dc-v1", league_id=43, params={},
                         summary={"scorers": {"n": 0, "model": {"logloss": float("nan")}}}))  # fmt: skip
    session.commit()
    stored = session.query(ModelRun).filter_by(league_id=43, kind="evaluation").one()
    assert stored.summary["scorers"]["model"]["logloss"] is None
