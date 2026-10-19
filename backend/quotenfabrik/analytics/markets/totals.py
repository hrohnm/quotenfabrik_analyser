"""Group 2: total goals over/under, both teams to score, exact goals."""

from quotenfabrik.analytics.markets.base import MarketProbability, Outcomes, over_under, over_under_outcomes
from quotenfabrik.analytics.prediction import MatchPrediction, total_goals_dist

GROUP = "totals"
LINES = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]


def probabilities(pred: MatchPrediction) -> list[MarketProbability]:
    dist = total_goals_dist(pred.ft)
    btts = float(pred.ft[1:, 1:].sum())
    out = over_under("ou_ft", dist, LINES)
    out += [MarketProbability("btts", "yes", None, btts), MarketProbability("btts", "no", None, 1 - btts)]
    out += [MarketProbability("exact_goals", str(k), None, float(dist[k])) for k in range(6)]
    out.append(MarketProbability("exact_goals", "6+", None, float(dist[6:].sum())))
    return out


def outcomes(m) -> Outcomes:
    goals = m.hg + m.ag
    res = over_under_outcomes("ou_ft", goals, LINES)
    res[("btts", "yes", None)] = m.hg > 0 and m.ag > 0
    res[("btts", "no", None)] = not (m.hg > 0 and m.ag > 0)
    for k in range(6):
        res[("exact_goals", str(k), None)] = goals == k
    res[("exact_goals", "6+", None)] = goals >= 6
    return res
