"""Group 3: goals per team (home / away) over/under, clean sheet, team to score."""

from quotenfabrik.analytics.markets.base import MarketProbability, Outcomes, over_under, over_under_outcomes
from quotenfabrik.analytics.prediction import MatchPrediction

GROUP = "team_totals"
LINES = [0.5, 1.5, 2.5, 3.5]


def probabilities(pred: MatchPrediction) -> list[MarketProbability]:
    home_dist = pred.ft.sum(axis=1)
    away_dist = pred.ft.sum(axis=0)
    out = over_under("ou_home", home_dist, LINES) + over_under("ou_away", away_dist, LINES)
    out += [
        MarketProbability("clean_sheet", "home", None, float(away_dist[0])),
        MarketProbability("clean_sheet", "away", None, float(home_dist[0])),
    ]
    return out


def outcomes(m) -> Outcomes:
    res = over_under_outcomes("ou_home", m.hg, LINES) | over_under_outcomes("ou_away", m.ag, LINES)
    res[("clean_sheet", "home", None)] = m.ag == 0
    res[("clean_sheet", "away", None)] = m.hg == 0
    return res
