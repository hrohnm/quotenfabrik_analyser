"""``qf value backtest``: runs the odds backtest per market, stores the summary and writes the Markdown report."""

import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from quotenfabrik.analytics.data import league_name, with_league
from quotenfabrik.analytics.odds_backtest import (
    BOOK_LABELS,
    MARKETS,
    THRESHOLDS,
    MarketResult,
    analyse_market,
    load_market,
    result_summary,
)
from quotenfabrik.analytics.service import MODEL_VERSION
from quotenfabrik.models import ModelRun

SOURCE_LABELS = {
    "model": "Modell",
    "open": "Markt (Eröffnung)",
    "blend": "Mischung",
    "close": "Markt (Schluss)",
}


def run_odds_backtest(
    engine: Engine,
    league_id: int,
    validation_until: int = 2021,
    method: str = "shin",
    report_path: Path | None = None,
) -> dict:
    results = [
        analyse_market(load_market(engine, league_id, spec), validation_until, method) for spec in MARKETS
    ]
    summary = json.loads(json.dumps([result_summary(r) for r in results], default=_json))
    with Session(engine) as session:
        run = ModelRun(
            kind="odds_backtest",
            model_version=MODEL_VERSION,
            league_id=league_id,
            params={
                "validation_until": validation_until,
                "margin_method": method,
                "thresholds": list(THRESHOLDS),
            },
            summary={"markets": summary},
        )
        session.add(run)
        session.commit()
        run_id = run.id
    if report_path:
        text = with_league(
            render_report(run_id, results, validation_until, method), league_name(engine, league_id)
        )
        report_path.write_text(text, encoding="utf-8")
    return {"model_run_id": run_id, **{r.spec.key: {"matches": r.n, "bets": len(r.bets)} for r in results}}


def _json(v):
    if hasattr(v, "item"):
        return v.item()
    return str(v)


def _pct(v, digits: int = 1) -> str:
    return "–" if v is None else f"{v * 100:.{digits}f} %".replace(".", ",")


def _signed(v, digits: int = 1) -> str:
    return "–" if v is None else f"{'+' if v >= 0 else '−'}{abs(v) * 100:.{digits}f} %".replace(".", ",")


def _num(v, digits: int = 4) -> str:
    return "–" if v is None else f"{v:.{digits}f}".replace(".", ",")


def _seasons(seasons: list[int]) -> str:
    return (
        f"{seasons[0]}/{(seasons[0] + 1) % 100:02d} – {seasons[-1]}/{(seasons[-1] + 1) % 100:02d}"
        if seasons
        else "–"
    )


def render_report(run_id: int, results: list[MarketResult], validation_until: int, method: str) -> str:
    lines = [
        "# 10 – Quoten-Backtest 1X2 und Über/Unter 2,5 (Phase 3, Schritt 1)",
        "",
        f"Automatisch erzeugt von `qf value backtest` am {datetime.now(UTC):%d.%m.%Y %H:%M} UTC "
        f"(Modell `{MODEL_VERSION}`, Lauf `analytics.model_runs.id = {run_id}`).",
        "",
        "**Daten:** rückwirkende Walk-Forward-Prognosen (`qf model backtest`) gegen die historischen Quoten von "
        "football-data.co.uk. *Eröffnung* = Quote beim Erstellen der CSV (≈ Freitag bzw. Dienstag vor dem Spiel, "
        "also etwa dann, wenn wir wetten würden), *Schluss* = Quote kurz vor Anpfiff.",
        "",
        f"**Margenentfernung:** {method.capitalize()}-Methode. Marktwahrscheinlichkeit = Pinnacle, sonst Marktschnitt.",
        "",
        f"**Validierung / Test:** Blend-Gewichte und Edge-Schwelle werden nur auf den Saisons bis {validation_until}/"
        f"{(validation_until + 1) % 100:02d} gewählt und danach einmalig auf den Testsaisons bewertet. "
        "Achtung: Die Modell-Hyperparameter wurden auf 2018–2021 gewählt – die Validierung ist für das Modell "
        "daher leicht geschönt, der Test nicht.",
        "",
        "**Wetten:** je Spiel höchstens eine Wette (Auswahl mit der größten Edge über der Schwelle), "
        "Einsatz 1 Einheit zur Eröffnungsquote. *ROI* = Gewinn / Einsatz mit 95-%-Bootstrap-Intervall, "
        "*CLV* = Eröffnungsquote × margenfreie Schluss-Wahrscheinlichkeit − 1 (positiv = Quote war besser als der "
        "Schlusskurs; der belastbarste Indikator für echten Value). Bet365 dient als Proxy für Betano (ähnliche Marge, "
        "für Betano gibt es keine historischen Quoten).",
        "",
        "## Fazit",
        "",
        *_conclusion(results),
    ]
    for r in results:
        lines += _market_section(r)
    return "\n".join(lines) + "\n"


def _conclusion(results: list[MarketResult]) -> list[str]:
    out = []
    for r in results:
        q = r.quality["test"]
        gap = q["model"]["log_loss"] - q["open"]["log_loss"]
        main = next(s for s in r.strategies if s["source"] == "model" and s["book"] == "b365")["test"]
        best_clv = max(s["test"].get("clv") or -1 for s in r.strategies)
        mv = r.movement["test"]
        out.append(
            f"- **{r.spec.label}:** Log-Loss Modell {_num(q['model']['log_loss'])} vs. Markt (Eröffnung) "
            f"{_num(q['open']['log_loss'])} → Modell {'schlechter' if gap > 0 else 'besser'} als der Markt. "
            f"Blend-Gewicht des Modells {_num(r.blend[1], 2)} "
            f"({'keine Zusatzinformation' if r.blend[1] <= 0.05 else 'Zusatzinformation'}). "
            f"Der Markt bewegt sich bei klaren Abweichungen nur in {_pct(mv['towards_model'], 0)} der Fälle "
            f"Richtung Modell (Korrelation {_num(mv['corr'], 2)}). Value-Wetten nach Modell @ Bet365: "
            f"{main.get('n', 0)} Wetten, Ø Quote {_num(main.get('avg_odd'), 2)}, ROI {_signed(main.get('roi'))}, "
            f"CLV {_signed(main.get('clv'))}; auch die beste der vier Varianten hat CLV {_signed(best_clv)}."
        )
    out += [
        "",
        "**Bewertung:** Das Modell ist zwar deutlich besser als einfache Vergleichswerte (Phase 2), aber "
        "schlechter als die Buchmacher. Value-Wetten nach Modell verlieren im Test ungefähr die Marge oder mehr, "
        "und der CLV ist negativ – die Quoten bewegen sich eher *vom* Modell weg. Bei 1X2 sind die „Value“-Tipps "
        "überwiegend Außenseiter: Das Modell ist dort weniger extrem als der Markt (Regularisierung zieht Teams zum "
        "Mittelwert), der Markt liegt richtig. Für 1X2 und Ü/U 2,5 gibt es mit "
        "`dc-v1` **keinen belastbaren Value**. Diese Hauptmärkte sind sehr effizient; Ansatzpunkte für Phase 3 "
        "sind daher (a) aus den Hauptmarkt-Quoten abgeleitete Wahrscheinlichkeiten für Nebenmärkte (Team-Tore, "
        "Halbzeiten, Torschützen), die Buchmacher oft weniger genau bepreisen (Hypothese, mit dem Betano-Archiv zu prüfen), und (b) Informationen, die das Modell "
        "noch nicht nutzt (Aufstellungen, Ausfälle, xG).",
    ]
    return out


def _market_section(r: MarketResult) -> list[str]:
    out = [
        "",
        f"## {r.spec.label}",
        "",
        f"{r.n} Spiele; Validierung {_seasons(r.validation_seasons)}, Test {_seasons(r.test_seasons)}. "
        "Ø Marge (Eröffnung, Test): "
        + ", ".join(f"{BOOK_LABELS[b]} {_pct(m)}" for b, m in r.margins.items())
        + ".",
        "",
        "### Prognosegüte (kleiner = besser)",
        "",
        "| Quelle | Log-Loss Validierung | Log-Loss Test | Brier Test"
        + (" | RPS Test |" if r.spec.key == "1x2" else " |"),
        "|---|---|---|---" + ("|---|" if r.spec.key == "1x2" else "|"),
    ]
    for source, label in SOURCE_LABELS.items():
        v, t = r.quality["validation"][source], r.quality["test"][source]
        row = f"| {label} | {_num(v['log_loss'])} | {_num(t['log_loss'])} | {_num(t['brier'])}"
        out.append(row + (f" | {_num(t['rps'])} |" if r.spec.key == "1x2" else " |"))
    n_val, n_test = r.quality["validation"]["model"]["n"], r.quality["test"]["model"]["n"]
    out += [
        "",
        f"Vergleich jeweils auf denselben Spielen mit vollständigen Quoten (Validierung {n_val}, Test {n_test}). "
        f"*Mischung* = logarithmische Mischung p ∝ Markt^{_num(r.blend[0], 2)} · Modell^{_num(r.blend[1], 2)} "
        "(Gewichte auf der Validierung geschätzt).",
        "",
        "### Value-Wetten (Test)",
        "",
        "| Wahrscheinlichkeit | Quote | Schwelle (Validierung) | Wetten | Treffer | Ø Quote | ROI | 95-%-Intervall | CLV | Max. Drawdown |",  # noqa: E501
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in r.strategies:
        t = s["test"]
        if not t.get("n"):
            out.append(
                f"| {SOURCE_LABELS[s['source']]} | {BOOK_LABELS[s['book']]} | Edge > {_pct(s['threshold'], 0)} | 0 | | | | | | |"
            )  # noqa: E501
            continue
        out.append(
            f"| {SOURCE_LABELS[s['source']]} | {BOOK_LABELS[s['book']]} | Edge > {_pct(s['threshold'], 0)} "
            f"(ROI {_signed(s['validation'].get('roi'))}) | {t['n']} | {_pct(t['hit_rate'])} | {_num(t['avg_odd'], 2)} | "
            f"**{_signed(t['roi'])}** | {_signed(t['roi_low'])} … {_signed(t['roi_high'])} | {_signed(t['clv'])} | "
            f"{_num(t['max_drawdown'], 1)} E |"
        )
    model_b365 = next(s for s in r.strategies if s["source"] == "model" and s["book"] == "b365")
    out += [
        "",
        "Alle Schwellen im Test (Modell @ Bet365) – zeigt, ob das Ergebnis an einer zufällig gewählten Schwelle hängt:",
        "",
        "| Edge > | Wetten | ROI | CLV |",
        "|---|---|---|---|",
    ]
    for t, g in model_b365["grid_test"].items():
        out.append(f"| {_pct(t, 0)} | {g.get('n', 0)} | {_signed(g.get('roi'))} | {_signed(g.get('clv'))} |")
    out += [
        "",
        "Je Testsaison (Modell @ Bet365):",
        "",
        "| Saison | Wetten | ROI | CLV |",
        "|---|---|---|---|",
    ]
    for season, g in model_b365["per_season"].items():
        out.append(
            f"| {season}/{(season + 1) % 100:02d} | {g['n']} | {_signed(g['roi'])} | {_signed(g.get('clv'))} |"
        )
    return out
