"""Odds arithmetic: margin removal, expected value, Kelly stakes and closing line value.

All functions are vectorised over rows: ``odds`` has shape (n, k) with the k exclusive outcomes of a market
(e.g. home/draw/away or over/under). Probabilities are decimals 0–1, odds decimal odds.
"""

import numpy as np

METHODS = ("shin", "power", "proportional")


def overround(odds: np.ndarray) -> np.ndarray:
    """Bookmaker margin per row: ``Σ 1/odd − 1``."""
    return (1 / np.asarray(odds, dtype=float)).sum(axis=1) - 1


def remove_margin(odds: np.ndarray, method: str = "shin") -> np.ndarray:
    """Fair probabilities per row (sum 1). Rows with missing or invalid odds become NaN."""
    odds = np.atleast_2d(np.asarray(odds, dtype=float))
    out = np.full(odds.shape, np.nan)
    ok = np.isfinite(odds).all(axis=1) & (odds > 1).all(axis=1)
    if not ok.any():
        return out
    q = 1 / odds[ok]
    if method == "proportional":
        p = q / q.sum(axis=1, keepdims=True)
    elif method == "power":
        p = _power(q)
    elif method == "shin":
        p = _shin(q)
    else:
        raise ValueError(f"unknown method {method!r}, expected one of {METHODS}")
    out[ok] = p / p.sum(axis=1, keepdims=True)  # remove the remaining bisection error
    return out


def _bisect(f, lo: np.ndarray, hi: np.ndarray, iterations: int = 60) -> np.ndarray:
    """Vectorised bisection for a function that decreases in its argument (f(lo) > 0 > f(hi))."""
    for _ in range(iterations):
        mid = (lo + hi) / 2
        positive = f(mid) > 0
        lo = np.where(positive, mid, lo)
        hi = np.where(positive, hi, mid)
    return (lo + hi) / 2


def _power(q: np.ndarray) -> np.ndarray:
    """p_i = q_i^k with k chosen so that Σ p_i = 1 (longshots lose more of their margin)."""
    n = len(q)
    k = _bisect(lambda k: (q ** k[:, None]).sum(axis=1) - 1, np.ones(n), np.full(n, 10.0))
    return q ** k[:, None]


def _shin(q: np.ndarray) -> np.ndarray:
    """Shin (1993): margin explained by a share z of insider money; favourite-longshot bias built in."""
    total = q.sum(axis=1)

    def probs(z: np.ndarray) -> np.ndarray:
        z = z[:, None]
        return (np.sqrt(z**2 + 4 * (1 - z) * q**2 / total[:, None]) - z) / (2 * (1 - z))

    n = len(q)
    z = _bisect(lambda z: probs(z).sum(axis=1) - 1, np.zeros(n), np.full(n, 0.5))
    return probs(z)


def expected_value(p, odd):
    """Expected profit per unit stake: ``p × odd − 1`` (the edge)."""
    return np.asarray(p, dtype=float) * np.asarray(odd, dtype=float) - 1


def kelly(p, odd, fraction: float = 0.25, cap: float = 0.02):
    """Share of the bankroll: fractional Kelly ``(p × odd − 1) / (odd − 1)``, never negative, capped."""
    p, odd = np.asarray(p, dtype=float), np.asarray(odd, dtype=float)
    full = (p * odd - 1) / (odd - 1)
    return np.clip(full * fraction, 0, cap)


def closing_line_value(odd_taken, p_close):
    """Value of the taken odd measured against the margin-free closing probability: ``odd × p_close − 1``."""
    return np.asarray(odd_taken, dtype=float) * np.asarray(p_close, dtype=float) - 1


def log_pool(p_market: np.ndarray, p_model: np.ndarray, w_market: float, w_model: float) -> np.ndarray:
    """Logarithmic pooling ``p ∝ p_market^a · p_model^b`` per row (a, b fitted on a validation period)."""
    z = w_market * np.log(np.clip(p_market, 1e-9, 1)) + w_model * np.log(np.clip(p_model, 1e-9, 1))
    z = np.exp(z - z.max(axis=1, keepdims=True))
    return z / z.sum(axis=1, keepdims=True)
