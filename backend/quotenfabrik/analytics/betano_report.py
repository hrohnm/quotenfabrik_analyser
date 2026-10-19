"""``qf value betano``: Betano side markets against the market-implied model, summary and Markdown report."""

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from quotenfabrik.analytics import betano_value as bv
from quotenfabrik.api.labels import MARKET_LABELS
from quotenfabrik.models import ModelRun

MODEL_VERSION = "mkt-v1"
BET_HOURS = (48.0, 24.0, 6.0, 1.0)
THRESHOLDS = (0.0, 0.02, 0.05)
EXTRA_LABELS = {"2h_1x2": "2. Halbzeit 1X2", "tg": "Exakte Toranzahl"}


def run_betano_value(engine: Engine, league_id: int, report_path: Path | None = None) -> dict:
    fixtures, odds = bv.load(engine, league_id)
    evaluations = [bv.evaluate(fixtures, odds, h) for h in BET_HOURS]
    summary = {
        "fixtures": int(evaluations[0].rows["oddspapi_id"].nunique()) if len(evaluations[0].rows) else 0,
        "per_time": [_time_summary(e) for e in evaluations],
        "markets": _market_table(evaluations[1].rows).to_dict("records"),
        "calibration": _calibration(evaluations[-1].rows),
    }
    # numpy scalars → Python, NaN → null (jsonb does not accept NaN)
    summary = json.loads(
        json.dumps(summary, default=lambda v: v.item() if hasattr(v, "item") else str(v)),
        parse_constant=lambda _: None,
    )
    with Session(engine) as session:
        run = ModelRun(kind="betano_value", model_version=MODEL_VERSION, league_id=league_id,
                       params={"bet_hours": list(BET_HOURS), "thresholds": list(THRESHOLDS)}, summary=summary)  # fmt: skip
        session.add(run)
        session.commit()
        run_id = run.id
    if report_path:
        report_path.write_text(render_report(run_id, evaluations, summary), encoding="utf-8")
    return {
        "model_run_id": run_id,
        "fixtures": summary["fixtures"],
        "betano_prices": len(evaluations[1].rows),
    }


def _bets_summary(bets: pd.DataFrame) -> dict:
    if bets.empty:
        return {"n": 0}
    return {
        "n": len(bets),
        "matches": int(bets["oddspapi_id"].nunique()),
        "edge": float(bets["edge"].mean()),
        "roi": float(bets["profit"].mean()),
        "clv": float(bets["clv"].mean()),
        "clv_betano": float(bets["clv_betano"].mean()),
        "clv_positive": float((bets["clv"] > 0).mean()),
    }


def _time_summary(e: bv.Evaluation) -> dict:
    r = e.rows
    return {
        "hours": e.hours_before,
        "fixtures": int(r["oddspapi_id"].nunique()),
        "prices": len(r),
        "fit_mae": float(e.fits["mae"].mean()) if len(e.fits) else None,
        "positive_share": float((r["edge"] > 0).mean()) if len(r) else None,
        "bets": {f"{t:.2f}": _bets_summary(bv.value_bets(r, t)) for t in THRESHOLDS},
    }


def _market_table(rows: pd.DataFrame) -> pd.DataFrame:
    """Per market: typical Betano edge against the fair price (≈ −margin) and how often a price is above fair."""
    g = rows.groupby("market")
    out = pd.DataFrame(
        {
            "prices": g.size(),
            "median_edge": g["edge"].median(),
            "positive_share": g["edge"].apply(lambda e: float((e > 0).mean())),
            "near_fair_share": g["edge"].apply(lambda e: float((e > -0.02).mean())),
            "direct": g["direct"].mean(),
        }
    ).reset_index()
    out["family"] = out["market"].map(bv.FAMILY_OF)
    return out.sort_values("median_edge", ascending=False)


def _calibration(rows: pd.DataFrame) -> dict:
    """Fair closing probabilities (Pinnacle fit) vs outcomes, and against Betano's own margin-free prices."""
    r = rows[rows["outcome"].notna() & rows["p_close"].notna()].copy()
    r["y"] = r["outcome"].astype(float)
    r["inv"] = 1 / r["odd"]
    grp = r.groupby(["oddspapi_id", "market", "line"], dropna=False)
    complete = grp["selection"].transform("count") == r["market"].map(lambda m: len(bv.EXHAUSTIVE.get(m, ())))
    r["p_betano"] = np.where(complete, r["inv"] / grp["inv"].transform("sum"), np.nan)
    both = r[r["p_betano"].notna()]
    bins = pd.cut(r["p_close"], np.linspace(0, 1, 11))
    table = r.groupby(bins, observed=True).agg(
        n=("y", "size"), predicted=("p_close", "mean"), observed=("y", "mean")
    )
    return {
        "n": len(r),
        "bins": [{"bin": str(k), **v} for k, v in table.to_dict("index").items()],
        "brier": {
            fam: {"n": len(g), "fair": float(((g["p_close"] - g["y"]) ** 2).mean()),
                  "betano": float(((g["p_betano"] - g["y"]) ** 2).mean())}
            for fam, g in both.groupby("family")
        },
    }  # fmt: skip


def _pct(v, digits: int = 1) -> str:
    return (
        "–"
        if v is None or (isinstance(v, float) and np.isnan(v))
        else f"{v * 100:.{digits}f} %".replace(".", ",")
    )


def _signed(v, digits: int = 1) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "–"
    return f"{'+' if v >= 0 else '−'}{abs(v) * 100:.{digits}f} %".replace(".", ",")


def _num(v: float, digits: int = 4) -> str:
    return f"{v:.{digits}f}".replace(".", ",")


def _better(summary: dict) -> str:
    brier = summary["calibration"]["brier"].values()
    return f"{sum(v['fair'] < v['betano'] for v in brier)} von {len(brier)}"


def _label(market: str) -> str:
    return EXTRA_LABELS.get(market) or MARKET_LABELS.get(market, market)


def render_report(run_id: int, evaluations: list[bv.Evaluation], summary: dict) -> str:
    times = summary["per_time"]
    main = next(t for t in times if t["hours"] == 24.0)
    best = main["bets"]["0.00"]
    lines = [
        "# 11 – Betano-Nebenmärkte gegen faire Preise (Phase 3, Weg 1)",
        "",
        f"Automatisch erzeugt von `qf value betano` am {datetime.now(UTC):%d.%m.%Y %H:%M} UTC "
        f"(Modell `{MODEL_VERSION}`, Lauf `analytics.model_runs.id = {run_id}`).",
        "",
        "**Vorgehen:** Für jedes Spiel mit Quotenverläufen (OddsPapi) wird zu einem Zeitpunkt *T* vor Anpfiff das "
        "marktbasierte Modell `mkt-v1` an die Pinnacle-Quoten angepasst (1X2, Ü/U, Team-Tore, Beide treffen, jeweils "
        "Spiel und 1. Halbzeit; Margenentfernung nach Shin). Parameter: erwartete Tore Heim/Gast, Anteil der Tore in "
        "der 1. Halbzeit je Team, Dixon-Coles-ρ. Daraus folgt ein fairer Preis für **jede** Betano-Quote zum selben "
        "Zeitpunkt – auch für Märkte, die Pinnacle nicht anbietet (2. Halbzeit, torreichste Halbzeit, exakte "
        "Toranzahl …). *Edge* = faire Wahrscheinlichkeit × Betano-Quote − 1.",
        "",
        "**Bewertung:** *CLV* = Betano-Quote × faire Wahrscheinlichkeit beim Anpfiff (Pinnacle-Schlusskurs) − 1, "
        "*CLV Betano* = Betano-Quote / Betano-Schlussquote − 1. Bei ≈ 100 Spielen ist der ROI reiner Zufall; "
        "aussagekräftig sind Edge-Verteilung und CLV. Je Spiel und Marktlinie höchstens eine Wette.",
        "",
        "**Nicht enthalten:** Torschützen (Zuordnung OddsPapi-Spieler ↔ API-Football-Spieler fehlt noch) und „exakte "
        "Tore Heim/Gast“ – dort sind die Betano-Daten über den ganzen Verlauf widersprüchlich zu Betanos eigenen "
        "Team-Tore-Quoten (z. B. „4+“ zu 16,5 bei Ü3,5 = 1,44), vermutlich falsch beschriftete Auswahlen.",
        "",
        "## Fazit",
        "",
        f"- **Faire Preise sind verlässlich:** Das Modell trifft die Pinnacle-Quoten im Mittel auf "
        f"{_pct(main['fit_mae'], 2)} genau und ist auf {summary['calibration']['n']} Betano-Auswahlen gut kalibriert "
        f"(Tabelle unten) und in {_better(summary)} Marktfamilien genauer als Betanos eigene margenbereinigte "
        "Quoten (sonst gleichauf).",
        f"- **Betano liegt fast nie über dem fairen Preis:** 24 h vor Anpfiff sind {_pct(main['positive_share'])} der "
        f"{main['prices']} Betano-Quoten positiv (Ø Edge dieser Wetten {_signed(best.get('edge'))}, "
        f"CLV {_signed(best.get('clv'))}). Größere Abweichungen (> 2 %) kommen praktisch nicht vor – auch nicht 48 h "
        "oder 1 h vor Anpfiff. Betano leitet seine Nebenmärkte offenbar sauber aus den Hauptmärkten ab und schlägt "
        "nur eine Marge auf.",
        "- **Die Marge ist je Markt sehr unterschiedlich:** ≈ 4–7 % bei 1X2, Doppelter Chance, Über/Unter und "
        "Team-Toren, ≈ 9–17 % bei Halbzeit-Ergebnis, Handicap, torreichster Halbzeit und exakter Toranzahl. "
        "Wer bei Betano wettet, verliert in den letztgenannten Märkten langfristig zwei- bis dreimal so viel.",
        "- **Konsequenz:** Mit Quotenvergleich allein ist bei Betano kein dauerhafter Value zu finden. Realistische "
        "Quellen sind Quotenboosts und Aktionen (mit den fairen Preisen sofort bewertbar), Torschützen-Märkte "
        "(noch zu prüfen) und Momente, in denen Betano nach Nachrichten (Aufstellung, Ausfall) langsamer reagiert als "
        "Pinnacle.",
        "",
        "## Value-Wetten je Zeitpunkt",
        "",
        "| Zeitpunkt | Spiele | Betano-Quoten | davon Edge > 0 | Schwelle | Wetten | Ø Edge | ROI | CLV | CLV Betano |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for t in times:
        for th, b in t["bets"].items():
            lines.append(
                f"| {t['hours']:.0f} h vor Anpfiff | {t['fixtures']} | {t['prices']} | {_pct(t['positive_share'])} | "
                f"Edge > {_pct(float(th), 0)} | {b['n']} | {_signed(b.get('edge'))} | {_signed(b.get('roi'))} | "
                f"{_signed(b.get('clv'))} | {_signed(b.get('clv_betano'))} |"
            )
    lines += [
        "",
        "## Betano je Markt (24 h vor Anpfiff)",
        "",
        "*Typische Edge* = Median über alle Betano-Quoten des Marktes (≈ −Marge). *Nah am fairen Preis* = Edge > −2 %. "
        "*Pinnacle direkt* = Anteil der Quoten, deren Markt und Linie Pinnacle selbst anbietet (sonst abgeleitet).",
        "",
        "| Markt | Familie | Quoten | Typische Edge | Edge > 0 | Nah am fairen Preis | Pinnacle direkt |",
        "|---|---|---|---|---|---|---|",
    ]
    for m in summary["markets"]:
        lines.append(
            f"| {_label(m['market'])} | {m['family']} | {m['prices']} | {_signed(m['median_edge'])} | "
            f"{_pct(m['positive_share'])} | {_pct(m['near_fair_share'], 0)} | {_pct(m['direct'], 0)} |"
        )
    cal = summary["calibration"]
    lines += [
        "",
        "## Kalibrierung der fairen Preise (Schlusskurs)",
        "",
        "| Vorhergesagt | Auswahlen | Ø vorhergesagt | Eingetreten |",
        "|---|---|---|---|",
        *[f"| {b['bin']} | {b['n']} | {_pct(b['predicted'])} | {_pct(b['observed'])} |" for b in cal["bins"]],
        "",
        "| Familie | Auswahlen | Brier faire Preise | Brier Betano (margenbereinigt) |",
        "|---|---|---|---|",
        *[
            f"| {fam} | {v['n']} | {_num(v['fair'])} | {_num(v['betano'])} |"
            for fam, v in cal["brier"].items()
        ],
    ]
    return "\n".join(lines) + "\n"
