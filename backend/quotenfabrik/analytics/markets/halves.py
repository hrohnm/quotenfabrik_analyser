"""Group 4: goals per half (total and per team), half-time result, highest scoring half."""

import numpy as np

from quotenfabrik.analytics.markets.base import MarketProbability, Outcomes, over_under, over_under_outcomes
from quotenfabrik.analytics.prediction import MatchPrediction, total_goals_dist

GROUP = "halves"
LINES_1H = [0.5, 1.5, 2.5]
LINES_2H = [0.5, 1.5, 2.5, 3.5]
TEAM_LINES = [0.5, 1.5]


def probabilities(pred: MatchPrediction) -> list[MarketProbability]:
    d1, d2 = total_goals_dist(pred.h1), total_goals_dist(pred.h2)
    out = over_under("ou_1h", d1, LINES_1H) + over_under("ou_2h", d2, LINES_2H)
    out += over_under("ou_home_1h", pred.h1.sum(axis=1), TEAM_LINES)
    out += over_under("ou_away_1h", pred.h1.sum(axis=0), TEAM_LINES)
    out += over_under("ou_home_2h", pred.h2.sum(axis=1), TEAM_LINES)
    out += over_under("ou_away_2h", pred.h2.sum(axis=0), TEAM_LINES)

    i, j = np.indices(pred.h1.shape)
    out += [
        MarketProbability("ht_1x2", "H", None, float(pred.h1[i > j].sum())),
        MarketProbability("ht_1x2", "D", None, float(pred.h1[i == j].sum())),
        MarketProbability("ht_1x2", "A", None, float(pred.h1[i < j].sum())),
        MarketProbability("btts_1h", "yes", None, float(pred.h1[1:, 1:].sum())),
        MarketProbability("btts_2h", "yes", None, float(pred.h2[1:, 1:].sum())),
    ]
    # highest scoring half, halves assumed independent
    joint = np.outer(d1, d2)
    a, b = np.indices(joint.shape)
    out += [
        MarketProbability("highest_half", "1H", None, float(joint[a > b].sum())),
        MarketProbability("highest_half", "2H", None, float(joint[a < b].sum())),
        MarketProbability("highest_half", "equal", None, float(joint[a == b].sum())),
    ]
    return out


def outcomes(m) -> Outcomes:
    g1, g2 = m.hthg + m.htag, m.h2g + m.a2g
    res = over_under_outcomes("ou_1h", g1, LINES_1H) | over_under_outcomes("ou_2h", g2, LINES_2H)
    res |= over_under_outcomes("ou_home_1h", m.hthg, TEAM_LINES)
    res |= over_under_outcomes("ou_away_1h", m.htag, TEAM_LINES)
    res |= over_under_outcomes("ou_home_2h", m.h2g, TEAM_LINES)
    res |= over_under_outcomes("ou_away_2h", m.a2g, TEAM_LINES)
    res[("ht_1x2", "H", None)] = m.hthg > m.htag
    res[("ht_1x2", "D", None)] = m.hthg == m.htag
    res[("ht_1x2", "A", None)] = m.hthg < m.htag
    res[("btts_1h", "yes", None)] = m.hthg > 0 and m.htag > 0
    res[("btts_2h", "yes", None)] = m.h2g > 0 and m.a2g > 0
    res[("highest_half", "1H", None)] = g1 > g2
    res[("highest_half", "2H", None)] = g1 < g2
    res[("highest_half", "equal", None)] = g1 == g2
    return res
