"""German labels for markets and selections and media URLs (shared by API and frontend)."""

# API-Football media (logos, player photos): free of quota, but rate limited -> the frontend caches them.
MEDIA_BASE = "https://media.api-sports.io/football"


def league_logo(league_id: int) -> str:
    return f"{MEDIA_BASE}/leagues/{league_id}.png"


_ROUNDS = {
    "Final": "Finale", "Semi-finals": "Halbfinale", "Quarter-finals": "Viertelfinale",
    "Round of 16": "Achtelfinale", "8th Finals": "Achtelfinale", "Round of 32": "Sechzehntelfinale",
    "16th Finals": "Sechzehntelfinale", "Knockout Round Play-offs": "K.-o.-Play-offs",
    "Play-offs": "Play-offs", "Playoff round": "Play-offs", "1st Qualifying Round": "1. Qualifikationsrunde",
    "2nd Qualifying Round": "2. Qualifikationsrunde", "3rd Qualifying Round": "3. Qualifikationsrunde",
}  # fmt: skip


def round_label(round_name: str | None) -> str | None:
    """German label of an API-Football round ("League Stage - 3" -> "Ligaphase, 3. Spieltag")."""
    if not round_name:
        return None
    base, _, number = round_name.partition(" - ")
    if base in _ROUNDS and not number:
        return _ROUNDS[base]
    if base.startswith("Preliminary"):
        return "Vorrunde"
    stage = {"Regular Season": None, "League Stage": "Ligaphase", "Group Stage": "Gruppenphase"}.get(
        base, f"Gruppe {base[6:]}" if base.startswith("Group ") else base
    )
    if number.isdigit():
        return f"{stage}, {number}. Spieltag" if stage else f"{number}. Spieltag"
    return stage or round_name


def _line(line: float | None) -> str:
    return "" if line is None else f"{line:g}".replace(".", ",")


def pick_label(market: str, selection: str, line: float | None, home: str, away: str) -> str:
    """Readable German text of a pick, e.g. "Über 2,5 Tore" or "Bayern München trifft"."""
    side = "Über" if selection == "over" else "Unter"
    team_markets = {"ou_home": (home, ""), "ou_away": (away, ""), "ou_home_1h": (home, " in der 1. HZ"),
                    "ou_away_1h": (away, " in der 1. HZ"), "ou_home_2h": (home, " in der 2. HZ"),
                    "ou_away_2h": (away, " in der 2. HZ")}  # fmt: skip
    if market == "1x2":
        return {"H": f"Sieg {home}", "D": "Unentschieden", "A": f"Sieg {away}"}[selection]
    if market == "dc":
        return {"1X": f"{home} oder Remis", "X2": f"{away} oder Remis", "12": "Kein Remis"}[selection]
    if market == "ht_1x2":
        return {"H": f"Halbzeitführung {home}", "D": "Remis zur Halbzeit", "A": f"Halbzeitführung {away}"}[
            selection
        ]
    if market in {"btts", "btts_1h", "btts_2h"}:
        suffix = {"btts": "", "btts_1h": " in der 1. HZ", "btts_2h": " in der 2. HZ"}[market]
        return f"Beide Teams treffen{suffix}" if selection == "yes" else f"Nicht beide Teams treffen{suffix}"
    if market == "clean_sheet":
        return f"{home if selection == 'home' else away} spielt zu null"
    if market in team_markets:
        team, suffix = team_markets[market]
        if line == 0.5:
            return f"{team} trifft{suffix}" if selection == "over" else f"{team} trifft nicht{suffix}"
        return f"{team}: {side} {_line(line)} Tore{suffix}"
    if market in {"ou_ft", "ou_1h", "ou_2h"}:
        prefix = {"ou_ft": "", "ou_1h": "1. HZ: ", "ou_2h": "2. HZ: "}[market]
        return f"{prefix}{side} {_line(line)} Tore"
    label = f"{MARKET_LABELS.get(market, market)} {SELECTION_LABELS.get(selection, selection)}"
    return f"{label} {_line(line)}".strip()


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
