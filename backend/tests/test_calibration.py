"""Post-hoc calibration of the model probabilities (no database)."""

import numpy as np
import pandas as pd
import pytest

from quotenfabrik.analytics import calibration as cal


def test_fit_one_recovers_miscalibration():
    rng = np.random.default_rng(0)
    p = rng.uniform(0.3, 0.7, 20000)
    true = 1 / (1 + np.exp(-(0.2 + 1.3 * np.log(p / (1 - p)))))  # model too cautious and too low
    y = (rng.uniform(size=p.size) < true).astype(float)
    a, b = cal.fit_one(p, y)
    assert a == pytest.approx(0.2, abs=0.05) and b == pytest.approx(1.3, abs=0.1)


def test_fit_one_small_sample_stays_near_identity():
    a, b = cal.fit_one(np.array([0.6] * 20), np.array([1.0] * 20))
    assert abs(a) < 0.5 and abs(b - 1) < 0.5


def preds() -> pd.DataFrame:
    rows = [
        (1, "1x2", "H", None, 0.50), (1, "1x2", "D", None, 0.25), (1, "1x2", "A", None, 0.25),
        (1, "dc", "1X", None, 0.75), (1, "dc", "X2", None, 0.50), (1, "dc", "12", None, 0.75),
        (1, "dnb", "H", None, 0.667), (1, "dnb", "A", None, 0.333),
        (1, "ou_ft", "over", 2.5, 0.55), (1, "ou_ft", "under", 2.5, 0.45),
        (1, "btts_1h", "yes", None, 0.20), (1, "scorer_anytime", "123", None, 0.30),
    ]  # fmt: skip
    return pd.DataFrame(rows, columns=["fixture_id", "market", "selection", "line", "probability"])


def test_apply_keeps_markets_consistent():
    calibrators = {
        ("1x2", "H", None): (0.3, 1.0),
        ("ou_ft", "over", 2.5): (0.2, 1.1),
        ("btts_1h", "yes", None): (-0.1, 1.0),
    }
    d = preds()
    d["p"] = cal.apply(d, calibrators)
    get = lambda m, s: float(d.loc[(d["market"] == m) & (d["selection"] == s), "p"].iloc[0])  # noqa: E731
    assert get("1x2", "H") + get("1x2", "D") + get("1x2", "A") == pytest.approx(1)
    assert get("1x2", "H") > 0.5
    assert get("dc", "1X") == pytest.approx(get("1x2", "H") + get("1x2", "D"))
    assert get("dnb", "H") == pytest.approx(get("1x2", "H") / (get("1x2", "H") + get("1x2", "A")))
    assert get("ou_ft", "over") + get("ou_ft", "under") == pytest.approx(1)
    assert get("ou_ft", "over") > 0.55
    assert get("btts_1h", "yes") < 0.2
    assert get("scorer_anytime", "123") == pytest.approx(0.30)  # scorers untouched


def test_apply_without_calibrators_is_identity():
    d = preds()
    assert np.allclose(cal.apply(d, {}), d["probability"])


def test_walk_forward_uses_only_earlier_seasons():
    rng = np.random.default_rng(1)
    rows = []
    for season in (2020, 2021, 2022):
        for f in range(400):
            p = rng.uniform(0.3, 0.8)
            y = float(rng.uniform() < min(p + 0.1, 0.99))  # model 10 points too low
            fid = season * 1000 + f
            rows += [
                (fid, season, "ou_ft", "over", 2.5, p, y),
                (fid, season, "ou_ft", "under", 2.5, 1 - p, 1 - y),
            ]
    d = pd.DataFrame(
        rows, columns=["fixture_id", "season", "market", "selection", "line", "probability", "outcome"]
    )
    res = cal.walk_forward(d, [2020, 2021, 2022])
    assert set(res["season"]) == {2021, 2022}  # 2020 has no earlier season to learn from
    over = res[res["selection"] == "over"]
    assert over["calibrated"].mean() > over["probability"].mean() + 0.05
