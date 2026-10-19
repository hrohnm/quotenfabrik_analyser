"""German labels for markets and selections (shared by API and frontend)."""

GROUP_LABELS = {
    "1x2": "Spielausgang",
    "totals": "Tore gesamt",
    "team_totals": "Tore pro Team",
    "halves": "Halbzeiten",
    "scorers": "Torschützen",
}

MARKET_LABELS = {
    "1x2": "1X2",
    "dc": "Doppelte Chance",
    "dnb": "Draw No Bet",
    "eh": "Europäisches Handicap",
    "ou_ft": "Über/Unter Tore",
    "btts": "Beide Teams treffen",
    "exact_goals": "Exakte Toranzahl",
    "ou_home": "Über/Unter Tore Heimteam",
    "ou_away": "Über/Unter Tore Gastteam",
    "clean_sheet": "Zu null",
    "ou_1h": "Über/Unter 1. Halbzeit",
    "ou_2h": "Über/Unter 2. Halbzeit",
    "ou_home_1h": "Heimteam 1. Halbzeit",
    "ou_away_1h": "Gastteam 1. Halbzeit",
    "ou_home_2h": "Heimteam 2. Halbzeit",
    "ou_away_2h": "Gastteam 2. Halbzeit",
    "ht_1x2": "Halbzeit-Ergebnis",
    "btts_1h": "Beide treffen 1. HZ",
    "btts_2h": "Beide treffen 2. HZ",
    "highest_half": "Torreichste Halbzeit",
    "scorer_anytime": "Torschütze (Anytime)",
    "scorer_first": "Erster Torschütze",
}

SELECTION_LABELS = {
    "H": "Heim",
    "D": "Unentschieden",
    "A": "Gast",
    "1X": "1X",
    "X2": "X2",
    "12": "12",
    "over": "Über",
    "under": "Unter",
    "yes": "Ja",
    "no": "Nein",
    "home": "Heimteam",
    "away": "Gastteam",
    "1H": "1. Halbzeit",
    "2H": "2. Halbzeit",
    "equal": "Gleich",
}

# Markets whose selections (per line) are mutually exclusive and exhaustive -> "pick" = most likely selection.
PICK_SETS = {
    "1x2", "ht_1x2", "eh", "ou_ft", "ou_home", "ou_away", "ou_1h", "ou_2h", "ou_home_1h", "ou_away_1h",
    "ou_home_2h", "ou_away_2h", "btts", "exact_goals", "highest_half", "dnb",
}  # fmt: skip
