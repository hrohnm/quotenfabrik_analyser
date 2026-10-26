"""Match preview in plain German ("Einschätzung"), built by rules from the data the detail page already has.

Input is the fixture detail (markets with model probabilities and Betano prices, form, style, patterns, scorers,
picks); everything was known before kickoff. The rules only state what carries weight (thresholds below) and
add the caveats from our validation reports (form: no betting signal, ``docs/17_form.md``; underdog "value":
the model is less extreme than the market, ``docs/10_quoten_backtest.md``). Finished matches get a short
check of what came true.
"""

import math
import re

CLEAR_FAVOURITE = 0.60
SLIGHT_FAVOURITE = 0.45
SLIGHT_GAP = 0.15
MANY_GOALS = 3.2
FEW_GOALS = 2.3
MARKET_GAP = 0.05  # model vs. market (percentage points) worth mentioning
VALUE_EDGE = 0.05
UNDERDOG = 0.35
NUMBERS = {
    2: "zwei",
    3: "drei",
    4: "vier",
    5: "fünf",
    6: "sechs",
    7: "sieben",
    8: "acht",
    9: "neun",
    10: "zehn",
}


def _pct(p: float | None) -> str:
    return "–" if p is None else f"{round(p * 100):.0f}\u00a0%"  # no line break between number and %


def _num(x: float, digits: int = 1) -> str:
    return f"{x:.{digits}f}".replace(".", ",")


def _decimal_comma(text: str) -> str:
    """'Über 3.5 …' -> 'Über 3,5 …' (pattern labels use a decimal point)."""
    return re.sub(r"(\d)\.(\d)", r"\1,\2", text)


def _odd(x: float) -> str:
    return f"{x:.2f}".replace(".", ",")


class _Markets:
    def __init__(self, markets: list[dict]) -> None:
        self.sel: dict[tuple, dict] = {}
        for m in markets:
            for s in m["selections"]:
                self.sel[(m["market"], None if m["line"] is None else float(m["line"]), s["selection"])] = s

    def p(self, market: str, selection: str, line: float | None = None) -> float | None:
        s = self.sel.get((market, line, selection))
        return None if s is None else float(s["probability"])

    def get(self, market: str, selection: str, line: float | None = None) -> dict | None:
        return self.sel.get((market, line, selection))

    def goals(self, side: str) -> float | None:
        p0 = self.p(f"ou_{side}", "under", 0.5)
        return None if p0 is None or p0 <= 0 else -math.log(p0)


def _headline(home: str, away: str, ph: float, pa: float, total: float | None) -> str:
    if ph >= CLEAR_FAVOURITE:
        fav = f"{home} klar favorisiert"
    elif pa >= CLEAR_FAVOURITE:
        fav = f"{away} klar favorisiert"
    elif ph >= SLIGHT_FAVOURITE and ph - pa >= SLIGHT_GAP:
        fav = f"Leichte Vorteile für {home}"
    elif pa >= SLIGHT_FAVOURITE and pa - ph >= SLIGHT_GAP:
        fav = f"Leichte Vorteile für {away}"
    else:
        fav = "Offenes Spiel"
    if total is not None and total >= MANY_GOALS:
        return f"{fav}, torreiches Spiel erwartet"
    if total is not None and total <= FEW_GOALS:
        return f"{fav}, eher wenige Tore erwartet"
    return fav


def _streak(sequence: str) -> tuple[str, int]:
    if not sequence:
        return "", 0
    last = sequence[-1]
    n = len(sequence) - len(sequence.rstrip(last))
    return last, n


def _form_text(name: str, form: dict | None) -> str | None:
    if not form or not form.get("form") or not form["form"]["matches"]:
        return None
    f = form["form"]
    seq = f["sequence"]
    kind, n = _streak(seq)
    words = {"S": ("Sieg", "Siege"), "U": ("Remis", "Remis"), "N": ("Niederlage", "Niederlagen")}
    if n == len(seq) and n >= 3:
        text = f"{name}: {NUMBERS.get(n, n)} {words[kind][1]} in Folge"
    else:
        counts = [(seq.count(k), words[k]) for k in "SUN" if seq.count(k)]
        listed = [f"{c} {w[0] if c == 1 else w[1]}" for c, w in counts]
        joined = ", ".join(listed[:-1]) + f" und {listed[-1]}" if len(listed) > 1 else listed[0]
        text = f"{name}: {joined} aus den letzten {f['matches']} Spielen"
        if n >= 3:
            text += f", zuletzt {NUMBERS.get(n, n)} {words[kind][1]} in Folge"
    if f.get("residual") is not None and abs(f["residual"]) >= 0.5:
        direction = "mehr" if f["residual"] > 0 else "weniger"
        text += f" – {_num(abs(f['residual']))} Punkte pro Spiel {direction}, als das Modell erwartet hätte"
    notable = [m for m in form.get("matches", [])[:5] if abs(m["gf"] - m["ga"]) >= 3]
    if notable:
        text += (
            " (u. a. "
            + ", ".join(
                f"{m['gf']}:{m['ga']} {'gegen' if m['venue'] == 'home' else 'bei'} {m['opponent']['name']}"
                for m in notable[:2]
            )
            + ")"
        )
    return text + "."


def _competition(name: str) -> str:
    return name.replace("UEFA ", "").replace("Europa Conference League", "Conference League")


def _team_context(team: str, c: dict) -> list[str]:
    """Schedule and absences of one team (facts, not used by the model)."""
    out = []
    prev, nxt = c.get("prev"), c.get("next")
    if prev and prev["cup"] and prev["days"] <= 4.5:
        where = "gegen" if prev["home"] else "bei"
        score = f"{prev['score'][0]}:{prev['score'][1]} " if prev.get("score") else ""
        out.append(f"{team} kommt nach {round(prev['days'])} Tagen Pause aus der {_competition(prev['league'])} "
                   f"({score}{where} {prev['opponent']}).")  # fmt: skip
    elif prev and prev["days"] <= 3.5:
        out.append(f"{team} hatte nur {round(prev['days'])} Tage Pause.")
    if nxt and nxt["cup"] and nxt["days"] <= 4.5:
        where = "gegen" if nxt["home"] else "bei"
        out.append(f"{team} spielt in {round(nxt['days'])} Tagen {_competition(nxt['league'])} {where} "
                   f"{nxt['opponent']} – Rotation möglich.")  # fmt: skip
    absences = c.get("absences") or []
    regulars = [a for a in absences if a["type"] == "missing" and a["regular"]]
    others = [a for a in absences if a["type"] == "missing" and not a["regular"]]
    doubtful = [a for a in absences if a["type"] == "doubtful" and a["regular"]]
    if regulars:
        names = ", ".join(f"{a['name']} ({a['reason_label']})" for a in regulars)
        text = f"Bei {team} fehlen {len(regulars)} Stammspieler: {names}" if len(regulars) > 1 else (
            f"Bei {team} fehlt Stammspieler {names}")  # fmt: skip
        share = sum(a["attack_share"] for a in regulars)
        if share >= 0.2:
            text += f" – zusammen {_pct(share)} der Tore und Vorlagen der letzten 10 Spiele"
        if others:
            text += f"; dazu {len(others)} weitere{'r' if len(others) == 1 else ''} Spieler"
        out.append(text + ".")
    elif others:
        out.append(f"Bei {team} fehlen {len(others)} Spieler, aber kein Stammspieler." if len(others) > 1 else
                   f"Bei {team} fehlt {others[0]['name']}, kein Stammspieler.")  # fmt: skip
    if doubtful:
        out.append(f"Fraglich bei {team}: {', '.join(a['name'] for a in doubtful)}.")
    return out


def _context_text(home: str, away: str, context: dict | None) -> str | None:
    if not context:
        return None
    lines = _team_context(home, context.get("home") or {}) + _team_context(away, context.get("away") or {})
    if not lines:
        return None
    return " ".join(lines) + (" Im Backtest verändern Termine und Ausfälle die Ergebnisse kaum gegenüber dem "
                              "Modell (docs/22) – ein Hinweis, kein Wettsignal.")  # fmt: skip


def _style_text(home: str, away: str, style: dict | None) -> str | None:
    if not style:
        return None
    h = (style.get("home") or {}).get("labels") or []
    a = (style.get("away") or {}).get("labels") or []
    if not h and not a:
        return None
    parts = []
    if h:
        parts.append(f"{home}: {' · '.join(h)}.")
    if a:
        parts.append(f"{away}: {' · '.join(a)}.")
    open_h, open_a = "Lässt viele Chancen zu" in h, "Lässt viele Chancen zu" in a
    press_h, press_a = "Offensiv druckvoll" in h, "Offensiv druckvoll" in a
    if open_h and open_a:
        parts.append("Offene Defensiven auf beiden Seiten sprechen für Tore.")
    elif press_h and open_a:
        parts.append(f"Das Duell spricht für {home}: viel Offensivdruck gegen eine anfällige Abwehr.")
    elif press_a and open_h:
        parts.append(f"Das Duell spricht für {away}: viel Offensivdruck gegen eine anfällige Abwehr.")
    elif "Defensiv kompakt" in h and "Defensiv kompakt" in a:
        parts.append("Zwei kompakte Defensiven – eher ein enges Spiel.")
    return " ".join(parts)


def _patterns_text(patterns: list[dict]) -> str | None:
    flagged = [
        p for p in patterns if p.get("signal") and p["group"] != "scorers" and "goal_timing" not in p["key"]
    ]
    form_flag = any("form_vs_expectation" in p["key"] for p in flagged)
    rates = [
        p for p in flagged if p.get("baseline") is not None and p.get("value") is not None and p["value"] <= 1
    ]
    rates.sort(key=lambda p: -abs(p["value"] - p["baseline"]))
    items = [
        f"{_decimal_comma(p['label'])}: {_pct(p['value'])} (Ligaschnitt {_pct(p['baseline'])})"
        for p in rates[:4]
    ]
    if not items and not form_flag:
        return None
    text = "; ".join(items) + "." if items else ""
    if form_flag:
        text += (
            " " if text else ""
        ) + "Die Form ist im Backtest kein eigenes Wettsignal – das Modell kennt die Teamstärke bereits."
    return text


def _flow_text(m: _Markets, home: str, away: str, ph: float, pa: float) -> str | None:
    parts = []
    h1, h2 = m.p("highest_half", "1H"), m.p("highest_half", "2H")
    if h1 is not None and h2 is not None and abs(h2 - h1) >= 0.1:
        later, earlier = ("2. Halbzeit", h2) if h2 > h1 else ("1. Halbzeit", h1)
        parts.append(
            f"Die {later} dürfte torreicher werden ({_pct(earlier)}, andere Hälfte {_pct(min(h1, h2))})."
        )
    ht = {k: m.p("ht_1x2", k) for k in "HDA"}
    if all(v is not None for v in ht.values()):
        lead = max(ht, key=ht.get)
        if lead == "D":
            parts.append(f"Zur Pause ist ein Remis am wahrscheinlichsten ({_pct(ht['D'])}).")
        else:
            parts.append(
                f"Zur Pause führt {home if lead == 'H' else away} in {_pct(ht[lead])} der Fälle, Remis {_pct(ht['D'])}."
            )
    fav_side = "home" if ph >= pa else "away"
    cs = m.p("clean_sheet", fav_side)
    if cs is not None:
        fav = home if fav_side == "home" else away
        if cs <= 0.35:
            parts.append(f"Ein Spiel ohne Gegentor für {fav} ist eher unwahrscheinlich ({_pct(cs)}).")
        elif cs >= 0.5:
            parts.append(f"{fav} bleibt eher ohne Gegentor ({_pct(cs)}).")
    return " ".join(parts) or None


def _scorers_text(scorers: list[dict], home_id: int, away_id: int, home: str, away: str) -> str | None:
    parts = []
    for team_id, name in ((home_id, home), (away_id, away)):
        top = [
            s
            for s in scorers
            if s.get("team_id") == team_id and s.get("anytime") is not None and s.get("name")
        ]
        top.sort(key=lambda s: -s["anytime"])
        if top:
            parts.append(f"{name}: " + " und ".join(f"{s['name']} ({_pct(s['anytime'])})" for s in top[:2]))
    return ("Am ehesten treffen – " + "; ".join(parts) + ".") if parts else None


def _market_text(m: _Markets, home: str, away: str) -> str | None:
    parts = []
    for sel, name in (("H", home), ("A", away)):
        s = m.get("1x2", sel)
        if s and s.get("betano"):
            market = s.get("pinnacle") or 1 / s["betano"]
            gap = market - s["probability"]
            if gap >= MARKET_GAP:
                parts.append(
                    f"Der Markt sieht {name} noch stärker (Betano {_odd(s['betano'])}, rund {_pct(market)})."
                )
            elif gap <= -MARKET_GAP and s["probability"] >= UNDERDOG:
                parts.append(
                    f"Der Markt traut {name} weniger zu als das Modell (Betano {_odd(s['betano'])}, rund {_pct(market)})."
                )
    o = m.get("ou_ft", "over", 2.5)
    if o and o.get("betano"):
        market = o.get("pinnacle") or 1 / o["betano"]
        if market - o["probability"] >= MARKET_GAP:
            parts.append(
                f"Bei Über 2,5 Tore (Betano {_odd(o['betano'])}) erwartet der Markt mehr Tore als das Modell."
            )
        elif o["probability"] - market >= MARKET_GAP:
            parts.append(
                f"Bei Über 2,5 Tore (Betano {_odd(o['betano'])}) erwartet das Modell mehr Tore als der Markt."
            )
    labels = {("1x2", "H"): f"Sieg {home}", ("1x2", "D"): "Remis", ("1x2", "A"): f"Sieg {away}",
              ("dc", "1X"): f"{home} oder Remis", ("dc", "X2"): f"{away} oder Remis", ("dc", "12"): "kein Remis",
              ("btts", "yes"): "beide treffen", ("btts", "no"): "nicht beide treffen"}  # fmt: skip
    value = []
    for (market, sel), label in labels.items():
        s = m.get(market, sel)
        if s and s.get("edge") is not None and s["edge"] >= VALUE_EDGE:
            value.append((label, s))
    for line in (1.5, 2.5, 3.5):
        for sel in ("over", "under"):
            s = m.get("ou_ft", sel, line)
            if s and s.get("edge") is not None and s["edge"] >= VALUE_EDGE:
                value.append((f"{'Über' if sel == 'over' else 'Unter'} {_num(line)} Tore", s))
    if value:
        value.sort(key=lambda v: -v[1]["edge"])
        listed = ", ".join(f"{label} ({_odd(s['betano'])})" for label, s in value[:3])
        if all(s["probability"] < UNDERDOG for _, s in value[:3]):
            parts.append(f"Vorteil laut Modell nur bei Außenseiter-Tipps: {listed} – dort weicht das Modell erfahrungsgemäß "
                         "am häufigsten zu Unrecht vom Markt ab, also kein belastbarer Value.")  # fmt: skip
        else:
            parts.append(
                f"Vorteil laut Modell (mindestens 5 %): {listed}. Ein Vorteil im Modell ist noch kein bewiesener Vorteil."
            )
    return " ".join(parts) or None


def _picks_text(picks: list[dict]) -> str | None:
    if not picks:
        return None
    items = []
    for p in picks:
        odd = f", Betano {_odd(p['betano'])}" if p.get("betano") else ""
        items.append(f"{p['rank']}. {p['label']} ({_pct(p['probability'])}{odd})")
    return "\n".join(items)


def _result_text(
    fixture: dict, m: _Markets, ph: float, pd_: float, pa: float, picks: list[dict]
) -> str | None:
    if not fixture.get("finished"):
        return None
    hg, ag = fixture["score"]["ft"]
    if hg is None or ag is None:
        return None
    home, away = fixture["home"]["name"], fixture["away"]["name"]
    fav = max((("H", ph), ("D", pd_), ("A", pa)), key=lambda x: x[1])[0]
    actual = "H" if hg > ag else "A" if hg < ag else "D"
    fav_name = {"H": f"Sieg {home}", "D": "Remis", "A": f"Sieg {away}"}[fav]
    parts = [
        f"Endstand {hg}:{ag}. Wahrscheinlichster Ausgang ({fav_name}) {'eingetreten' if fav == actual else 'nicht eingetreten'}."
    ]
    o25 = m.p("ou_ft", "over", 2.5)
    if o25 is not None:
        expected = "über" if o25 >= 0.5 else "unter"
        happened = "über" if hg + ag > 2.5 else "unter"
        parts.append(f"Tore: {expected} 2,5 erwartet, {happened} 2,5 eingetreten.")
    settled = [p for p in picks if p.get("outcome") is not None]
    if settled:
        hits = sum(1 for p in settled if p["outcome"])
        parts.append(f"Tipps: {hits} von {len(settled)} getroffen.")
    return " ".join(parts)


def build(detail: dict, profile: str) -> dict | None:
    """``{"headline", "summary", "sections": [{"title", "text"}]}`` for the fixture detail, or None without
    predictions."""
    m = _Markets(detail.get("markets") or [])
    ph, pd_, pa = m.p("1x2", "H"), m.p("1x2", "D"), m.p("1x2", "A")
    if ph is None or pd_ is None or pa is None:
        return None
    f = detail["fixture"]
    home, away = f["home"]["name"], f["away"]["name"]
    gh, ga = m.goals("home"), m.goals("away")
    total = gh + ga if gh is not None and ga is not None else None

    summary = f"Das Modell sieht {home} mit {_pct(ph)} vorn (Remis {_pct(pd_)}, {away} {_pct(pa)})." if ph >= pa else (
        f"Das Modell sieht {away} mit {_pct(pa)} vorn (Remis {_pct(pd_)}, {home} {_pct(ph)}).")  # fmt: skip
    if total is not None:
        summary += f" Erwartet werden rund {_num(total)} Tore ({home} {_num(gh)}, {away} {_num(ga)})."
    o25, btts = m.p("ou_ft", "over", 2.5), m.p("btts", "yes")
    if o25 is not None and btts is not None:
        summary += f" Über 2,5 Tore: {_pct(o25)}, beide treffen: {_pct(btts)}."

    sections = []
    leg = f.get("first_leg")
    if leg and leg.get("finished") and leg.get("score"):
        sections.append({"title": "Rückspiel", "text": f"Das Hinspiel endete {leg['score'][0]}:{leg['score'][1]} aus Sicht von {home}. "
                                                        "Abgerechnet wird nur dieses Spiel nach 90 Minuten."})  # fmt: skip
    forms = detail.get("form") or {}
    form_lines = [t for t in (_form_text(home, forms.get("home")), _form_text(away, forms.get("away"))) if t]
    if form_lines:
        sections.append({"title": "Ausgangslage", "text": " ".join(form_lines)})
    for title, text in (
        ("Termine & Personal", _context_text(home, away, detail.get("context"))),
        ("Spielstil", _style_text(home, away, detail.get("style"))),
        ("Auffällig", _patterns_text(detail.get("patterns") or [])),
        ("Spielverlauf", _flow_text(m, home, away, ph, pa)),
        (
            "Torschützen",
            _scorers_text(detail.get("scorers") or [], f["home"]["id"], f["away"]["id"], home, away),
        ),
        ("Markt (Betano)", _market_text(m, home, away)),
    ):
        if text:
            sections.append({"title": title, "text": text})
    picks = (detail.get("picks") or {}).get(profile) or []
    if (text := _picks_text(picks)) is not None:
        sections.append({"title": "Unsere 3 Tipps", "text": text})
    if (text := _result_text(f, m, ph, pd_, pa, picks)) is not None:
        sections.append({"title": "Ergebnis", "text": text})
    return {"headline": _headline(home, away, ph, pa, total), "summary": summary, "sections": sections}
