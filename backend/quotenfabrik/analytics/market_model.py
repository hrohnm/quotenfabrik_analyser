"""Market-implied model (``mkt-v1``): goal expectations fitted to sharp (Pinnacle) prices of the main markets.

The fitted ``MatchPrediction`` prices every side market consistently (team totals, halves, exact goals, BTTS,
highest scoring half …). Those fair prices are then compared with Betano's prices of the same markets.

Parameters per match and point in time: expected goals home/away (full time), share of each team's goals in
the first half, Dixon-Coles rho. Halves are independent Poisson models (like ``dc-v1``).
"""

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from quotenfabrik.analytics.prediction import MatchPrediction

# Market keys: (market, line). Selections per market as used in ``price`` / ``outcome``.
HDA = ("H", "D", "A")
OVER_UNDER = ("over", "under")
YES_NO = ("yes", "no")

LINE_MARKETS = {  # over/under markets: matrix, team (None = both)
    "ou_ft": ("ft", None),
    "ou_home": ("ft", 0),
    "ou_away": ("ft", 1),
    "ou_1h": ("h1", None),
    "ou_2h": ("h2", None),
    "ou_home_1h": ("h1", 0),
    "ou_away_1h": ("h1", 1),
    "ou_home_2h": ("h2", 0),
    "ou_away_2h": ("h2", 1),
}
RESULT_MARKETS = {"1x2": "ft", "ht_1x2": "h1", "2h_1x2": "h2"}
BTTS_MARKETS = {"btts": "ft", "btts_1h": "h1", "btts_2h": "h2"}
EXACT_MARKETS = {"tg": None, "tg_home": 0, "tg_away": 1}  # exact goals full time: "k" or "k+"

# Pinnacle markets used for the fit (all others are derived).
FIT_MARKETS = (
    "1x2",
    "ou_ft",
    "ou_home",
    "ou_away",
    "ht_1x2",
    "ou_1h",
    "ou_home_1h",
    "ou_away_1h",
    "btts",
    "btts_1h",
)


def _goals(matrix: np.ndarray, team: int | None) -> np.ndarray:
    """Distribution of goals of one team (0 = home, 1 = away) or of both."""
    if team == 0:
        return matrix.sum(axis=1)
    if team == 1:
        return matrix.sum(axis=0)
    n = matrix.shape[0]
    dist = np.zeros(2 * n - 1)
    i, j = np.indices(matrix.shape)
    np.add.at(dist, (i + j).ravel(), matrix.ravel())
    return dist


def _hda(matrix: np.ndarray, handicap: float = 0) -> dict[str, float]:
    i, j = np.indices(matrix.shape)
    diff = i - j + handicap
    return {
        "H": float(matrix[diff > 0].sum()),
        "D": float(matrix[diff == 0].sum()),
        "A": float(matrix[diff < 0].sum()),
    }


def price(pred: MatchPrediction, market: str, line: float | None, selection: str) -> float | None:
    """Probability of a selection (None if the market is unknown). Draw no bet: conditional on no draw."""
    mats = {"ft": pred.ft, "h1": pred.h1, "h2": pred.h2}
    if market in RESULT_MARKETS:
        return _hda(mats[RESULT_MARKETS[market]])[selection]
    if market == "eh":
        return _hda(pred.ft, line)[selection]
    if market == "dc":
        p = _hda(pred.ft)
        return {"1X": p["H"] + p["D"], "X2": p["D"] + p["A"], "12": p["H"] + p["A"]}[selection]
    if market == "dnb":
        p = _hda(pred.ft)
        return p[selection] / (p["H"] + p["A"])
    if market in LINE_MARKETS:
        matrix, team = LINE_MARKETS[market]
        dist = _goals(mats[matrix], team)
        over = float(dist[np.arange(len(dist)) > line].sum())
        return over if selection == "over" else 1 - over
    if market in BTTS_MARKETS:
        m = mats[BTTS_MARKETS[market]]
        yes = float(m[1:, 1:].sum())
        return yes if selection == "yes" else 1 - yes
    if market == "highest_half":
        t1, t2 = _goals(pred.h1, None), _goals(pred.h2, None)
        joint = np.outer(t1, t2)
        i, j = np.indices(joint.shape)
        return float(joint[{"1H": i > j, "2H": i < j, "equal": i == j}[selection]].sum())
    if market in EXACT_MARKETS:
        dist = _goals(pred.ft, EXACT_MARKETS[market])
        k = int(selection.rstrip("+"))
        return float(dist[k:].sum() if selection.endswith("+") else dist[k] if k < len(dist) else 0.0)
    return None


def outcome(goals: dict[str, int], market: str, line: float | None, selection: str) -> bool | None:
    """Result of a selection (goals: hg, ag, h1, a1 = first half). None = void (draw no bet on a draw)."""
    hg, ag, h1, a1 = goals["hg"], goals["ag"], goals["h1"], goals["a1"]
    h2, a2 = hg - h1, ag - a1
    period = {"ft": (hg, ag), "h1": (h1, a1), "h2": (h2, a2)}

    def hda(h, a, handicap=0):
        d = h - a + handicap
        return "H" if d > 0 else "D" if d == 0 else "A"

    if market in RESULT_MARKETS:
        return hda(*period[RESULT_MARKETS[market]]) == selection
    if market == "eh":
        return hda(hg, ag, line) == selection
    if market == "dc":
        return hda(hg, ag) in {"1X": "HD", "X2": "DA", "12": "HA"}[selection]
    if market == "dnb":
        return None if hg == ag else hda(hg, ag) == selection
    if market in LINE_MARKETS:
        matrix, team = LINE_MARKETS[market]
        g = period[matrix]
        total = sum(g) if team is None else g[team]
        return (total > line) == (selection == "over")
    if market in BTTS_MARKETS:
        h, a = period[BTTS_MARKETS[market]]
        return (h > 0 and a > 0) == (selection == "yes")
    if market == "highest_half":
        t1, t2 = h1 + a1, h2 + a2
        return {"1H": t1 > t2, "2H": t1 < t2, "equal": t1 == t2}[selection]
    if market in EXACT_MARKETS:
        team = EXACT_MARKETS[market]
        total = hg + ag if team is None else (hg, ag)[team]
        k = int(selection.rstrip("+"))
        return total >= k if selection.endswith("+") else total == k
    return None


def prediction(params: Iterable[float]) -> MatchPrediction:
    lh, la, share_h, share_a, rho = params
    return MatchPrediction(
        0, 0, 0, lh, la, rho, lh * share_h, la * share_a, lh * (1 - share_h), la * (1 - share_a)
    )


@dataclass
class Target:
    """Margin-free probabilities of one market (selections in the same order as ``probs``)."""

    market: str
    line: float | None
    selections: tuple[str, ...]
    probs: np.ndarray


BOUNDS = [(0.1, 5.0), (0.1, 5.0), (0.2, 0.7), (0.2, 0.7), (-0.25, 0.15)]
START = [1.6, 1.3, 0.45, 0.45, -0.05]


def fit(targets: list[Target]) -> tuple[MatchPrediction, dict]:
    """Minimises the cross-entropy between the targets and the model prices (each market weighted equally).

    Without first-half targets the half shares stay at the start value (league average ≈ 45 %).
    """
    targets = [t for t in targets if t.market in FIT_MARKETS]
    has_halves = any(t.market in {"ht_1x2", "ou_1h", "ou_home_1h", "ou_away_1h", "btts_1h"} for t in targets)
    bounds = BOUNDS if has_halves else [*BOUNDS[:2], (START[2], START[2]), (START[3], START[3]), BOUNDS[4]]

    def loss(x):
        pred = prediction(x)
        total = 0.0
        for t in targets:
            p = np.array([price(pred, t.market, t.line, s) for s in t.selections])
            total -= float(t.probs @ np.log(np.clip(p, 1e-9, 1)))
        return total / max(len(targets), 1)

    res = minimize(loss, START, method="L-BFGS-B", bounds=bounds)
    pred = prediction(res.x)
    # mean absolute deviation between fitted and target probabilities (fit quality)
    errors = [
        abs(price(pred, t.market, t.line, s) - p)
        for t in targets
        for s, p in zip(t.selections, t.probs, strict=True)
    ]  # noqa: E501
    info = {
        "params": [float(v) for v in res.x],
        "markets": len(targets),
        "mae": float(np.mean(errors)) if errors else None,
    }  # noqa: E501
    return pred, info
