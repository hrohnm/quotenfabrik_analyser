"""Market groups. Each module exposes ``probabilities(pred)`` and ``outcomes(match)``.

``probabilities`` returns model probabilities per (market, selection, line); ``outcomes`` returns the actual
result (True/False) for a finished match with the same keys, used for evaluation and bet settlement.
"""

from quotenfabrik.analytics.markets import halves, match_result, team_totals, totals

GROUPS = {
    "1x2": match_result,
    "totals": totals,
    "team_totals": team_totals,
    "halves": halves,
}
