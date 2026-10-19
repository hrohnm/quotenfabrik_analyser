"""Market catalog: which API-Football pre-match bet ids belong to which market group.

Only these bets are archived. Asian markets (Asian handicap, quarter/whole goal lines) are excluded on
purpose: Betano does not offer them in Germany.
"""

import re

MARKET_GROUPS: dict[str, dict[int, str]] = {
    "1x2": {
        1: "Match Winner",
        2: "Home/Away",
        12: "Double Chance",
        9: "Handicap Result",
    },
    "totals": {
        5: "Goals Over/Under",
        8: "Both Teams Score",
        38: "Exact Goals Number",
    },
    "team_totals": {
        16: "Total - Home",
        17: "Total - Away",
        40: "Home Team Exact Goals Number",
        41: "Away Team Exact Goals Number",
        27: "Clean Sheet - Home",
        28: "Clean Sheet - Away",
        43: "Home Team Score a Goal",
        44: "Away Team Score a Goal",
    },
    "halves": {
        6: "Goals Over/Under First Half",
        26: "Goals Over/Under - Second Half",
        105: "Home Team Total Goals(1st Half)",
        106: "Away Team Total Goals(1st Half)",
        107: "Home Team Total Goals(2nd Half)",
        108: "Away Team Total Goals(2nd Half)",
        13: "First Half Winner",
        3: "Second Half Winner",
        11: "Highest Scoring Half",
        34: "Both Teams Score - First Half",
        35: "Both Teams To Score - Second Half",
        46: "Exact Goals Number - First Half",
        42: "Second Half Exact Goals Number",
    },
    "scorers": {
        92: "Anytime Goal Scorer",
        93: "First Goal Scorer",
        94: "Last Goal Scorer",
        95: "To Score Two or More Goals",
        231: "Home Anytime Goal Scorer",
        218: "Away Anytime Goal Scorer",
        232: "Home First Goal Scorer",
        219: "Away First Goal Scorer",
    },
}

BET_ID_TO_GROUP: dict[int, str] = {bet_id: group for group, bets in MARKET_GROUPS.items() for bet_id in bets}

# Bets whose selections carry a goal line ("Over 2.5"); only x.5 lines are kept.
LINE_BETS = {5, 6, 26, 16, 17, 105, 106, 107, 108}

_LINE_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*$")


def is_tracked_selection(bet_id: int, selection: str, handicap: str | None = None) -> bool:
    """True if the selection belongs to a tracked market and is not an Asian (x.0/x.25/x.75) line."""
    if bet_id not in BET_ID_TO_GROUP:
        return False
    if bet_id in LINE_BETS:
        match = _LINE_RE.search(selection)
        line = float(match.group(1)) if match else (float(handicap) if handicap else None)
        if line is None or abs(line % 1 - 0.5) > 1e-9:
            return False
    return True
