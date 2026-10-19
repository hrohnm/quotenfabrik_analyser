"""Match prediction: full-time Dixon-Coles plus separate Poisson models per half."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from quotenfabrik.analytics.poisson import FittedPoisson, PoissonParams, fit_poisson, score_matrix


@dataclass
class MatchPrediction:
    fixture_id: int
    home_id: int
    away_id: int
    lh: float  # expected home goals (full time)
    la: float
    rho: float
    lh_1h: float
    la_1h: float
    lh_2h: float
    la_2h: float

    def __post_init__(self) -> None:
        self.ft = score_matrix(self.lh, self.la, self.rho)
        self.h1 = score_matrix(self.lh_1h, self.la_1h)
        self.h2 = score_matrix(self.lh_2h, self.la_2h)


@dataclass
class MatchModel:
    """The three fitted models used for one prediction date."""

    ft: FittedPoisson
    first_half: FittedPoisson
    second_half: FittedPoisson

    def predict(self, fixture_id: int, home: int, away: int) -> MatchPrediction:
        lh, la = self.ft.lambdas(home, away)
        h1 = self.first_half.lambdas(home, away)
        h2 = self.second_half.lambdas(home, away)
        return MatchPrediction(fixture_id, home, away, lh, la, self.ft.rho, *h1, *h2)


def fit_match_model(
    matches: pd.DataFrame,
    as_of: pd.Timestamp,
    params: PoissonParams,
    current_teams: set[int],
    team_league: dict[int, int] | None = None,
) -> MatchModel:
    """``matches`` with a ``league_id`` column of several leagues -> joint model (``team_league``: current
    league per team)."""
    half_params = PoissonParams(
        **{**params.__dict__, "reg": params.half_reg, "fit_rho": False, "xg_weight": 0.0}
    )
    tl = team_league
    return MatchModel(
        ft=fit_poisson(matches, as_of, params, "hg", "ag", current_teams, "hxg", "axg", tl),
        first_half=fit_poisson(matches, as_of, half_params, "hthg", "htag", current_teams, team_league=tl),
        second_half=fit_poisson(matches, as_of, half_params, "h2g", "a2g", current_teams, team_league=tl),
    )


def total_goals_dist(matrix: np.ndarray) -> np.ndarray:
    """P(total goals = k) from a score matrix."""
    n = matrix.shape[0]
    dist = np.zeros(2 * n - 1)
    for i in range(n):
        for j in range(n):
            dist[i + j] += matrix[i, j]
    return dist
