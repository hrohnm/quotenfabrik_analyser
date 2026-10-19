from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class MarketProbability:
    market: str  # e.g. '1x2', 'ou_ft', 'ou_home_1h'
    selection: str  # e.g. 'H', 'over', 'yes'
    line: float | None
    probability: float

    @property
    def key(self) -> tuple[str, str, float | None]:
        return (self.market, self.selection, self.line)

    @property
    def fair_odd(self) -> float:
        return 1 / self.probability if self.probability > 0 else float("inf")


Outcomes = dict[tuple[str, str, float | None], bool]


def over_under(market: str, dist: np.ndarray, lines: list[float]) -> list[MarketProbability]:
    """Over/under probabilities from a goal-count distribution (x.5 lines only)."""
    cdf = np.cumsum(dist)
    out = []
    for line in lines:
        under = float(cdf[int(line)])  # P(goals <= floor(line))
        out += [
            MarketProbability(market, "over", line, 1 - under),
            MarketProbability(market, "under", line, under),
        ]
    return out


def over_under_outcomes(market: str, goals: float, lines: list[float]) -> Outcomes:
    res: Outcomes = {}
    for line in lines:
        res[(market, "over", line)] = goals > line
        res[(market, "under", line)] = goals < line
    return res
