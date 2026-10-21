"""Generated match preview (no database)."""

from quotenfabrik.analytics import preview


def sel(selection, p, betano=None, edge=None, pinnacle=None):
    return {"selection": selection, "probability": p, "betano": betano, "edge": edge, "pinnacle": pinnacle}


def detail(finished=False):
    markets = [
        {"market": "1x2", "line": None, "selections": [sel("H", 0.64, 1.40, -0.10, 0.71), sel("D", 0.19, 5.4, 0.03),
                                                       sel("A", 0.17, 6.6, 0.12)]},
        {"market": "ou_home", "line": 0.5, "selections": [sel("over", 0.907), sel("under", 0.093)]},
        {"market": "ou_away", "line": 0.5, "selections": [sel("over", 0.68), sel("under", 0.32)]},
        {"market": "ou_ft", "line": 2.5, "selections": [sel("over", 0.68, 1.29, -0.12, 0.77), sel("under", 0.32)]},
        {"market": "btts", "line": None, "selections": [sel("yes", 0.62), sel("no", 0.38)]},
        {"market": "highest_half", "line": None, "selections": [sel("1H", 0.30), sel("2H", 0.48), sel("equal", 0.22)]},
    ]  # fmt: skip
    form = {
        "form": {"matches": 6, "sequence": "NNNNNN", "residual": -1.26},
        "matches": [{"gf": 0, "ga": 5, "venue": "away", "opponent": {"name": "SC Freiburg"}}],
    }
    return {
        "fixture": {"home": {"id": 1, "name": "Stuttgart"}, "away": {"id": 2, "name": "Gladbach"}, "finished": finished,
                    "score": {"ft": [2, 1] if finished else [None, None]}, "first_leg": None},
        "markets": markets,
        "form": {"home": {"form": {"matches": 6, "sequence": "SNNSSN", "residual": -0.2}, "matches": []}, "away": form},
        "style": {"home": {"labels": ["Offensiv druckvoll"]}, "away": {"labels": ["Lässt viele Chancen zu"]}},
        "patterns": [{"group": "1x2", "key": "home_win_rate_home", "label": "Heimsiege (letzte 10)", "value": 0.7,
                      "baseline": 0.42, "signal": "high"}],
        "scorers": [{"name": "Undav", "team_id": 1, "anytime": 0.32}, {"name": "Demirović", "team_id": 1, "anytime": 0.36}],
        "picks": {"ausgewogen": [{"rank": 1, "label": "Stuttgart oder Remis", "probability": 0.84, "betano": 1.13,
                                  "outcome": True if finished else None}]},
    }  # fmt: skip


def test_headline_and_summary():
    p = preview.build(detail(), "ausgewogen")
    assert p["headline"] == "Stuttgart klar favorisiert, torreiches Spiel erwartet"
    assert "64\u00a0%" in p["summary"] and "3,5 Tore" in p["summary"]


def test_sections():
    p = preview.build(detail(), "ausgewogen")
    sections = {s["title"]: s["text"] for s in p["sections"]}
    assert "sechs Niederlagen in Folge" in sections["Ausgangslage"]
    assert "0:5 bei SC Freiburg" in sections["Ausgangslage"]
    assert "spricht für Stuttgart" in sections["Spielstil"]
    assert "70\u00a0% (Ligaschnitt 42\u00a0%)" in sections["Auffällig"]
    assert sections["Torschützen"].index("Demirović") < sections["Torschützen"].index(
        "Undav"
    )  # sorted by chance
    assert "noch stärker" in sections["Markt (Betano)"]  # market 71 % vs. model 64 %
    assert "Außenseiter" in sections["Markt (Betano)"]  # only value: away win at 17 %
    assert "Ergebnis" not in sections


def test_finished_match_gets_result_check():
    sections = {s["title"]: s["text"] for s in preview.build(detail(finished=True), "ausgewogen")["sections"]}
    assert "Endstand 2:1" in sections["Ergebnis"] and "eingetreten" in sections["Ergebnis"]
    assert "1 von 1 getroffen" in sections["Ergebnis"]


def test_no_prediction_no_preview():
    d = detail()
    d["markets"] = []
    assert preview.build(d, "ausgewogen") is None
