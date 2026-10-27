"""Joint probability of several picks of one fixture (same-game combo, Betano "Bet Builder").

The picks of a fixture are correlated ("Lazio scores" and "Lazio or draw" mostly come true together), so the
product of the single probabilities understates the chance of the combo, and the product of the Betano single
odds overstates the Bet Builder odds Betano offers.

The joint chance comes from the half models: goals per team and half are independent Poisson variables
(``MatchPrediction.h1`` / ``h2``), their rates follow exactly from the stored P(team scores no goal in the
half). On that grid every pick market is evaluated; the ratio joint / product of the grid marginals
(correlation factor) is applied to the stored single probabilities, so the combo stays consistent with the
probabilities shown.
"""

import math
from collections.abc import Iterable, Mapping

import numpy as np
from scipy.stats import poisson

MAX_GOALS = 10  # per team and half; P(more) is negligible
# stored predictions that give the four half rates: P(no goal) = exp(-λ)
HALF_KEYS = (("ou_home_1h", "under", 0.5), ("ou_away_1h", "under", 0.5),
             ("ou_home_2h", "under", 0.5), ("ou_away_2h", "under", 0.5))  # fmt: skip

_K = np.arange(MAX_GOALS + 1)
_H1, _A1, _H2, _A2 = np.meshgrid(_K, _K, _K, _K, indexing="ij")
_HG, _AG = _H1 + _H2, _A1 + _A2


def half_lambdas(probabilities: Mapping[tuple, float]) -> tuple[float, ...] | None:
    """(home 1H, away 1H, home 2H, away 2H) from the stored predictions of a fixture (None if one is
    missing)."""
    out = []
    for key in HALF_KEYS:
        p = probabilities.get(key)
        if p is None or not 0 < p < 1:
            return None
        out.append(-math.log(p))
    return tuple(out)


def _mask(market: str, selection: str, line: float | None) -> np.ndarray | None:
    """Pick outcome on the goal grid (``None``: market not supported)."""
    diff = _HG - _AG
    over_under = {
        "ou_ft": _HG + _AG, "ou_home": _HG, "ou_away": _AG, "ou_1h": _H1 + _A1, "ou_2h": _H2 + _A2,
        "ou_home_1h": _H1, "ou_away_1h": _A1, "ou_home_2h": _H2, "ou_away_2h": _A2,
    }  # fmt: skip
    if market in over_under and line is not None:
        goals = over_under[market]
        return goals > line if selection == "over" else goals < line if selection == "under" else None
    simple = {
        ("1x2", "H"): diff > 0, ("1x2", "D"): diff == 0, ("1x2", "A"): diff < 0,
        ("dc", "1X"): diff >= 0, ("dc", "X2"): diff <= 0, ("dc", "12"): diff != 0,
        ("ht_1x2", "H"): _H1 > _A1, ("ht_1x2", "D"): _H1 == _A1, ("ht_1x2", "A"): _H1 < _A1,
        ("btts", "yes"): (_HG > 0) & (_AG > 0), ("btts", "no"): (_HG == 0) | (_AG == 0),
        ("btts_1h", "yes"): (_H1 > 0) & (_A1 > 0), ("btts_1h", "no"): (_H1 == 0) | (_A1 == 0),
        ("clean_sheet", "home"): _AG == 0, ("clean_sheet", "away"): _HG == 0,
    }  # fmt: skip
    return simple.get((market, selection))


def correlation_factor(
    lambdas: Iterable[float], legs: Iterable[tuple[str, str, float | None]]
) -> float | None:
    """P(all legs) / product of P(leg) on the goal grid of the half rates (1 = independent, > 1 = the legs
    tend to come true together); None if a market is not supported."""
    masks = [_mask(m, s, None if line is None else float(line)) for m, s, line in legs]
    if any(m is None for m in masks):
        return None
    pmf = [poisson.pmf(_K, lam) for lam in lambdas]
    grid = np.einsum("a,b,c,d->abcd", *pmf)
    singles = [float(grid[m].sum()) for m in masks]
    if min(singles) <= 0:
        return None
    joint = float(grid[np.logical_and.reduce(masks)].sum())
    return joint / math.prod(singles)


def combo(probabilities: list[float], factor: float | None, betano: list[float | None] | None = None) -> dict:
    """Same-game combo of picks: naive product, joint probability (product × factor, at most the smallest
    single probability), fair odds and the estimated Bet Builder odds (product of the Betano single odds ÷
    factor: Betano prices the correlation in as well)."""
    naive = math.prod(probabilities)
    joint = None if factor is None else min(naive * factor, min(probabilities))
    odds = betano or []
    product = math.prod(odds) if odds and all(o is not None for o in odds) else None
    builder = None if product is None or factor is None else max(product / factor, 1.01)
    return {
        "naive": naive,
        "probability": joint,
        "factor": factor,
        "fair_odd": None if not joint else 1 / joint,
        "betano_product": product,
        "builder_odds": None if builder is None else round(builder, 2),
    }
