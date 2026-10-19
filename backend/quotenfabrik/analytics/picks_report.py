"""``qf picks report``: hit rates of the suggested picks (single and as a 3-pick combo) → Markdown report."""

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import Engine, text

from quotenfabrik.analytics.picks import ALLOWED, DEFAULT_PROFILE, PICKS_PER_FIXTURE, PROFILES, evaluate_picks
from quotenfabrik.analytics.service import MODEL_VERSION
from quotenfabrik.api.data import CHOSEN_RUNS_SQL
from quotenfabrik.api.labels import pick_label

# Typical Betano margin per selection in the pick markets (docs/11_betano_nebenmaerkte.md) – for the odds estimate
TYPICAL_MARGIN = 0.06

_SQL = f"""
    with runs as ({CHOSEN_RUNS_SQL.format(where="and f.league_id = :league")})
    select k.fixture_id, f.season, k.profile, k.rank, k.market, k.selection, k.line::float as line, k.probability,
           p.outcome, coalesce(jsonb_typeof(k.reasons) = 'array', false) as has_reason
    from analytics.picks k
    join runs on runs.model_run_id = k.model_run_id and runs.fixture_id = k.fixture_id
    join analytics.predictions p on p.id = k.prediction_id
    join core.fixtures f on f.id = k.fixture_id
    where f.league_id = :league and p.outcome is not null
"""


def load_settled(engine: Engine, league_id: int) -> pd.DataFrame:
    return pd.read_sql(text(_SQL), engine, params={"league": league_id})


def write_report(engine: Engine, league_id: int, validation_until: int, path: Path) -> None:
    data = load_settled(engine, league_id)
    periods = {
        "Validierung": data[data["season"] <= validation_until],
        "Test": data[data["season"] > validation_until],
    }
    results = {(name, prof): evaluate_picks(frame[frame["profile"] == prof])
               for name, frame in periods.items() for prof in PROFILES}  # fmt: skip
    full = {prof: evaluate_picks(data[data["profile"] == prof]) for prof in PROFILES}
    path.write_text(render(results, full, data, validation_until), encoding="utf-8")


def _pct(v, digits: int = 1) -> str:
    return "–" if v is None else f"{v * 100:.{digits}f} %".replace(".", ",")


def _odd(v) -> str:
    return "–" if v is None else f"{v:.2f}".replace(".", ",")


def _season(s: int) -> str:
    return f"{s}/{(s + 1) % 100:02d}"


def render(results: dict, full: dict, data: pd.DataFrame, validation_until: int) -> str:
    seasons = sorted(data["season"].unique())
    default = full[DEFAULT_PROFILE]
    test = {prof: results[("Test", prof)] for prof in PROFILES}
    markets = ", ".join(sorted(ALLOWED))
    lines = [
        "# 12 – 3 Tipps pro Spiel: Trefferquote einzeln und als Kombi",
        "",
        f"Automatisch erzeugt von `qf picks report` am {datetime.now(UTC):%d.%m.%Y %H:%M} UTC (Modell `{MODEL_VERSION}`, "
        f"Saisons {_season(seasons[0])} – {_season(seasons[-1])}, {data['fixture_id'].nunique()} Spiele).",
        "",
        "## So werden die Tipps gewählt",
        "",
        "1. **Kandidaten:** alle Modell-Prognosen eines Spiels in gängigen Märkten mit üblichen Linien "
        f"(`{markets}`) – keine Torschützen, Handicaps oder exotischen Linien.",
        "2. **Stärke:** Wahrscheinlichkeit im Fenster des Profils, bewertet mit *Wahrscheinlichkeit + Gewicht × "
        "(Wahrscheinlichkeit − Ligaschnitt)*. Der Ligaschnitt ist die Häufigkeit der letzten drei Saisons; Tipps, bei "
        "denen das Modell für *dieses* Spiel etwas Besonderes sieht, werden bevorzugt.",
        "3. **Streuung:** je Marktgruppe (Spielausgang, Tore gesamt, Team-Tore, Halbzeiten) nur der beste Kandidat, "
        f"davon die {PICKS_PER_FIXTURE} besten – nie zwei Tipps aus derselben Gruppe. Welche Gruppen zum Zug kommen, "
        "wechselt von Spiel zu Spiel.",
        "4. **Begründung:** Pattern mit auffälligem Signal, die denselben Tipp stützen, werden angehängt.",
        "",
        "Alles nur mit Informationen vor dem Spieltag (Walk-Forward-Prognosen, Ligaschnitt und Pattern vor dem Spieltag). "
        f"Profile und Gewichte wurden auf den Saisons bis {_season(validation_until)} festgelegt; die Testsaisons danach "
        "zeigen, ob die Quoten stabil bleiben.",
        "",
        "| Profil | Wahrscheinlichkeit je Tipp | Gewicht Ligaschnitt-Abstand |",
        "|---|---|---|",
        *[
            f"| {p.label} | {_pct(p.min_p, 0)} – {_pct(p.max_p, 0)} | {f'{p.lift_weight:g}'.replace('.', ',')} |"
            for p in PROFILES.values()
        ],
        "",
        "## Ergebnis",
        "",
        "| Profil | Zeitraum | Tipps | Trefferquote | erwartet | Kombis | Kombi getroffen | Kombi rechnerisch* | faire Kombi-Quote (Median) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for prof, p in PROFILES.items():
        for period in ("Validierung", "Test"):
            r = results[(period, prof)]
            s, c = r["singles"], r["combo"]
            lines.append(
                f"| {p.label} | {period} | {s['n']} | **{_pct(s['hit_rate'])}** | {_pct(s['expected'])} | {c.get('n', 0)} | "
                f"**{_pct(c.get('hit_rate'))}** | {_pct(c.get('expected_naive'))} | {_odd(c.get('fair_odd_median'))} |"
            )
    t = test[DEFAULT_PROFILE]
    lines += [
        "",
        "\\* Produkt der drei Einzelwahrscheinlichkeiten – so rechnet eine gewöhnliche Kombiwette. Die Kombi trifft "
        "**deutlich öfter**, weil die Tipps eines Spiels zusammenhängen (z. B. Heimsieg und „Gastteam unter 1,5 Tore“). "
        "Faire Kombi-Quote = 1 / rechnerische Wahrscheinlichkeit.",
        "",
        "## Einordnung",
        "",
        f"- **Die Einzeltipps sind verlässlich:** Die Trefferquote entspricht in Validierung und Test fast genau der "
        f"vorhergesagten Wahrscheinlichkeit (Profil Ausgewogen, Test: {_pct(t['singles']['hit_rate'])} getroffen bei "
        f"{_pct(t['singles']['expected'])} erwartet). Das Modell ist kalibriert – die Prozentwerte kann man wörtlich nehmen.",
        f"- **Die Kombi trifft öfter als gedacht:** {_pct(t['combo']['hit_rate'])} statt rechnerisch "
        f"{_pct(t['combo']['expected_naive'])}. Bei einer normalen Kombiwette (Quoten werden multipliziert) wäre das ein "
        "Vorteil. Innerhalb *eines* Spiels bieten Buchmacher Kombis aber meist nur als „Bet Builder“ an – dort wird der "
        "Zusammenhang eingepreist, die Quote liegt unter dem Produkt der Einzelquoten.",
        f"- **Trefferquote ist nicht Gewinn:** Bei Betano liegt auf jedem Tipp eine Marge von ≈ {TYPICAL_MARGIN * 100:.0f} % "
        "(siehe `11_betano_nebenmaerkte.md`). Ein Tipp mit 80 % Wahrscheinlichkeit wird also nicht zu 1,25, sondern eher zu "
        "≈ 1,18 angeboten. Die Tipps sind eine gut begründete Vorauswahl, keine Value-Wetten.",
        f"- **Pattern-Begründung:** Tipps mit stützendem Pattern trafen {_pct(default['reasons']['with']['hit_rate'])} "
        f"(erwartet {_pct(default['reasons']['with']['expected'])}, n = {default['reasons']['with']['n']}), ohne "
        f"{_pct(default['reasons']['without']['hit_rate'])} (erwartet {_pct(default['reasons']['without']['expected'])}). "
        "Pattern erklären den Tipp, verbessern ihn aber nicht messbar – das Modell kennt die Information bereits.",
        "",
        f"## Details Profil „{PROFILES[DEFAULT_PROFILE].label}“ (alle Saisons)",
        "",
        "### Wie viele der drei Tipps treffen?",
        "",
        "| Treffer | 0 von 3 | 1 von 3 | 2 von 3 | 3 von 3 (Kombi) |",
        "|---|---|---|---|---|",
        "| Anteil der Spiele | "
        + " | ".join(_pct(default["hits_distribution"][str(k)]) for k in range(4))
        + " |",
        "",
        "### Je Saison",
        "",
        "| Saison | Tipps | Trefferquote | erwartet | Kombi getroffen | Kombi rechnerisch |",
        "|---|---|---|---|---|---|",
        *[
            f"| {_season(s['season'])} | {s['n']} | {_pct(s['hit_rate'])} | {_pct(s['expected'])} | "
            f"{_pct(s['combo'].get('hit_rate'))} | {_pct(s['combo'].get('expected_naive'))} |"
            for s in default["per_season"]
        ],
        "",
        "### Je Tipp-Rang (1 = stärkster Tipp des Spiels)",
        "",
        "| Rang | Tipps | Trefferquote | erwartet |",
        "|---|---|---|---|",
        *[
            f"| {r['rank']} | {r['n']} | {_pct(r['hit_rate'])} | {_pct(r['expected'])} |"
            for r in default["per_rank"]
        ],
        "",
        "### Kalibrierung",
        "",
        "| Wahrscheinlichkeit | Tipps | Trefferquote | erwartet |",
        "|---|---|---|---|",
        *[
            f"| {b['bin']} | {b['n']} | {_pct(b['hit_rate'])} | {_pct(b['expected'])} |"
            for b in default["calibration"]
        ],
        "",
        "### Häufigste Tipps",
        "",
        "| Tipp | Anzahl | Trefferquote | erwartet |",
        "|---|---|---|---|",
        *[
            f"| {pick_label(m['market'], m['selection'], m['line'], 'Heimteam', 'Gastteam')} | {m['n']} | "
            f"{_pct(m['hit_rate'])} | {_pct(m['expected'])} |"
            for m in default["per_market"][:15]
        ],
    ]
    return "\n".join(lines) + "\n"
