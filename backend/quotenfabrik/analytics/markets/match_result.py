"""Group 1: 1X2 incl. double chance, draw no bet and European handicap."""

import numpy as np

from quotenfabrik.analytics.markets.base import MarketProbability, Outcomes
from quotenfabrik.analytics.prediction import MatchPrediction

GROUP = "1x2"
EUROPEAN_HANDICAPS = [-2, -1, 1, 2]  # handicap applied to the home team


def _hda(matrix: np.ndarray, handicap: int = 0) -> tuple[float, float, float]:
    i, j = np.indices(matrix.shape)
    diff = i - j + handicap
    return float(matrix[diff > 0].sum()), float(matrix[diff == 0].sum()), float(matrix[diff < 0].sum())


def probabilities(pred: MatchPrediction) -> list[MarketProbability]:
    h, d, a = _hda(pred.ft)
    out = [
        MarketProbability("1x2", "H", None, h),
        MarketProbability("1x2", "D", None, d),
        MarketProbability("1x2", "A", None, a),
        MarketProbability("dc", "1X", None, h + d),
        MarketProbability("dc", "X2", None, d + a),
        MarketProbability("dc", "12", None, h + a),
        # draw no bet: stake returned on a draw -> probability conditional on no draw
        MarketProbability("dnb", "H", None, h / (h + a)),
        MarketProbability("dnb", "A", None, a / (h + a)),
    ]
    for hc in EUROPEAN_HANDICAPS:
        eh, ed, ea = _hda(pred.ft, hc)
        out += [
            MarketProbability("eh", "H", hc, eh),
            MarketProbability("eh", "D", hc, ed),
            MarketProbability("eh", "A", hc, ea),
        ]
    return out


def outcomes(m) -> Outcomes:
    diff = m.hg - m.ag
    res: Outcomes = {
        ("1x2", "H", None): diff > 0,
        ("1x2", "D", None): diff == 0,
        ("1x2", "A", None): diff < 0,
        ("dc", "1X", None): diff >= 0,
        ("dc", "X2", None): diff <= 0,
        ("dc", "12", None): diff != 0,
        # draw no bet: None = stake returned
        ("dnb", "H", None): None if diff == 0 else diff > 0,
        ("dnb", "A", None): None if diff == 0 else diff < 0,
    }
    for hc in EUROPEAN_HANDICAPS:
        res[("eh", "H", hc)] = diff + hc > 0
        res[("eh", "D", hc)] = diff + hc == 0
        res[("eh", "A", hc)] = diff + hc < 0
    return res
