"""Tippschein: six decisions per fixture (more likely selection) and their evaluation."""

import pandas as pd
import pytest

from quotenfabrik.analytics import decisions as dc


def _fixture(fixture_id: int, season: int, probs: dict, won: set) -> list[dict]:
    """probs: (market, selection, line) -> probability; won: selections that came true."""
    return [{"fixture_id": fixture_id, "season": season, "market": m, "selection": s, "line": ln,
             "probability": p, "outcome": (m, s, ln) in won} for (m, s, ln), p in probs.items()]  # fmt: skip


PROBS = {
    ("1x2", "H", None): 0.5, ("1x2", "D", None): 0.27, ("1x2", "A", None): 0.23,
    ("ou_ft", "over", 1.5): 0.78, ("ou_ft", "under", 1.5): 0.22,
    ("ou_ft", "over", 2.5): 0.45, ("ou_ft", "under", 2.5): 0.55,
    ("btts", "yes", None): 0.52, ("btts", "no", None): 0.48,
    ("ou_1h", "over", 0.5): 0.7, ("ou_1h", "under", 0.5): 0.3,
    ("ou_2h", "over", 0.5): 0.8, ("ou_2h", "under", 0.5): 0.2,
    ("ou_1h", "over", 1.5): 0.4, ("ou_home", "over", 0.5): 0.8,  # not part of the sheet
}  # fmt: skip
# result 2:1, both goals in the 2nd half (1:0 at half time? no: 0:0, then 2:1)
WON = {("1x2", "H", None), ("ou_ft", "over", 1.5), ("ou_ft", "over", 2.5), ("btts", "yes", None),
       ("ou_1h", "under", 0.5), ("ou_2h", "over", 0.5)}  # fmt: skip


def test_decide_takes_the_more_likely_side():
    rows = dc.decide(pd.DataFrame(_fixture(1, 2024, PROBS, WON)))
    assert list(rows["decision"]) == ["winner", "o15", "o25", "btts", "goal_1h", "goal_2h"]
    assert list(rows["pick_label"]) == ["Heim", "Ja", "Nein", "Ja", "Ja", "Ja"]
    assert list(rows["hit"]) == [True, True, False, True, False, True]
    assert list(rows["actual"]) == ["H", "over", "over", "yes", "under", "over"]


def test_open_fixture_has_no_result():
    rows = dc.decide(pd.DataFrame(_fixture(1, 2024, PROBS, set())).assign(outcome=None))
    assert rows["hit"].isna().all() and len(rows) == 6


def test_evaluate_counts_correct_decisions_and_walk_forward_reference():
    data = pd.DataFrame(
        _fixture(1, 2023, PROBS, WON) + _fixture(2, 2024, PROBS, WON)
        + _fixture(3, 2024, PROBS, {("1x2", "A", None), ("ou_ft", "under", 1.5), ("ou_ft", "under", 2.5),
                                    ("btts", "no", None), ("ou_1h", "under", 0.5), ("ou_2h", "under", 0.5)})
    )  # fmt: skip
    result = dc.evaluate(dc.decide(data))
    assert result["fixtures"] == 3
    assert result["correct_per_fixture"]["4"] == pytest.approx(2 / 3)  # fixtures 1 and 2
    assert result["correct_per_fixture"]["1"] == pytest.approx(1 / 3)  # fixture 3: only "under 2.5" right
    winner = next(d for d in result["decisions"] if d["key"] == "winner")
    assert winner["n"] == 3 and winner["hit_rate"] == pytest.approx(2 / 3)
    assert winner["picked"] == {"Heim": 3, "Unentschieden": 0, "Gast": 0}
    # reference only from 2024 on (2023 = home win most frequent): fixtures 2 (home) and 3 (away)
    assert winner["reference"] == {"n": 2, "hit_rate": 0.5, "model": 0.5}
    assert [s["season"] for s in result["seasons"]] == [2023, 2024]


def test_betano_result_per_decision():
    rows = dc.decide(pd.DataFrame(_fixture(1, 2024, PROBS, WON)))
    rows["betano"] = [2.0, 1.2, None, 1.9, 1.3, 1.15]
    result = dc.evaluate(rows)
    o15 = next(d for d in result["decisions"] if d["key"] == "o15")
    assert o15["betano"]["roi"] == pytest.approx(0.2)
    assert result["betano"]["n"] == 5
    assert result["betano"]["roi"] == pytest.approx((1.0 + 0.2 + 0.9 - 1 + 0.15) / 5)
