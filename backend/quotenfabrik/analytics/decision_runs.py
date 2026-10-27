"""Fitting, storing and applying the Tippschein decision model (``qf model decisions``).

``fit``: features of all fixtures of the shown competitions, per decision the penalty from the validation
seasons, walk-forward probabilities for every backtest season (stored for the backtest runs), the production
fit on all settled fixtures (``analytics.decision_models``) applied to the forecasts, and the report
(``docs/24_tippschein.md``). ``apply``: production models on forecasts without decision probabilities yet
(cron after the forecast, before the day is frozen).
"""

from datetime import UTC, datetime

import numpy as np
import pandas as pd
from sqlalchemy import Engine, delete, select, text
from sqlalchemy.orm import Session

from quotenfabrik import app_config
from quotenfabrik.analytics import decision_features as dfe
from quotenfabrik.analytics import decision_model as dm
from quotenfabrik.ingest.db_utils import upsert
from quotenfabrik.models import DecisionModel, DecisionProb

THRESHOLDS = (0, 30, 50, 60, 70, 80, 90)


def _leagues() -> tuple[list[int], list[int]]:
    return list(app_config.shown_league_ids()), [lg.id for lg in app_config.cup_leagues()]


def _rows(frame: pd.DataFrame, pred: pd.DataFrame, spec: dm.Spec) -> list[dict]:
    runs = frame.set_index("fixture_id")["model_run_id"]
    return [{"model_run_id": int(runs[r.fixture_id]), "fixture_id": int(r.fixture_id), "decision": spec.key,
             "probabilities": {c: round(float(getattr(r, c)), 6) for c in spec.classes},
             "confidence": None if pd.isna(r.confidence) else round(float(r.confidence), 1)}
            for r in pred.itertuples(index=False)]  # fmt: skip


def _store(engine: Engine, rows: list[dict], replace_runs: list[int] | None = None) -> None:
    with Session(engine) as session:
        if replace_runs:
            session.execute(delete(DecisionProb).where(DecisionProb.model_run_id.in_(replace_runs)))
        upsert(session, DecisionProb, rows)
        session.commit()


def _reference(
    seasons: pd.Series, y: np.ndarray, frame_seasons: pd.Series, frame_y: np.ndarray
) -> np.ndarray:
    """Hit of "always the class that was most frequent in the earlier seasons" (NaN without history)."""
    out = np.full(len(y), np.nan)
    for season in seasons.unique():
        before = frame_y[(frame_seasons < season).to_numpy() & (frame_y >= 0)]
        if len(before):
            most = np.bincount(before).argmax()
            mask = (seasons == season).to_numpy()
            out[mask] = (y[mask] == most).astype(float)
    return out


def evaluate_decision(frame: pd.DataFrame, spec: dm.Spec, pred: pd.DataFrame) -> dict:
    """Test seasons: log loss and hit rate against the goal model (paired bootstrap) and the hit rate by
    minimum confidence against the naive reference."""
    y_all = dm.labels(frame, spec)
    test = pred[(frame.loc[pred.index, "season"] >= dm.TEST_FROM).to_numpy() & (y_all[pred.index] >= 0)]
    if test.empty:
        return {}
    y = y_all[test.index]
    p_new = test[list(spec.classes)].to_numpy()
    p_raw = np.exp(dm.offsets(frame.loc[test.index], spec))
    d = dm.log_loss(p_raw, y) - dm.log_loss(p_new, y)
    rng = np.random.default_rng(0)
    boot = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(1000)]
    seasons = frame.loc[test.index, "season"]
    ref = _reference(seasons, y, frame["season"], y_all)
    hit = p_new.argmax(axis=1) == y
    conf = test["confidence"].to_numpy()
    curve = []
    for t in THRESHOLDS:
        m = conf >= t
        curve.append({"min_confidence": t, "share": float(m.mean()), "n": int(m.sum()),
                      "hit_rate": float(hit[m].mean()) if m.any() else None,
                      "reference": float(np.nanmean(ref[m])) if m.any() else None,
                      "expected": float(p_new.max(axis=1)[m].mean()) if m.any() else None})  # fmt: skip
    return {
        "n": int(len(y)),
        "log_loss_model": float(dm.log_loss(p_raw, y).mean()),
        "log_loss": float(dm.log_loss(p_new, y).mean()),
        "gain": float(d.mean()),
        "gain_ci": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
        "hit_model": float((p_raw.argmax(axis=1) == y).mean()),
        "hit": float(hit.mean()),
        "curve": curve,
    }


def fit(engine: Engine) -> dict:
    """Refit everything (walk-forward for the backtests, production models, forecasts); returns the report
    data."""
    leagues, cups = _leagues()
    frame = dfe.build(engine, leagues, cups)
    if frame.empty:
        return {"decisions": []}
    seasons = sorted(int(s) for s in frame["season"].unique())
    backtest = frame[frame["kind"] == "backtest"]
    forecast = frame[frame["kind"] == "forecast"]
    results, rows = [], []
    with Session(engine) as session:
        session.execute(delete(DecisionModel))
        session.commit()
    for spec in dm.SPECS:
        alpha, scores = dm.choose_alpha(backtest, spec)
        pred = dm.walk_forward(backtest, spec, alpha, seasons)
        table = dm.confidence_table(pred[list(spec.classes)].max(axis=1).to_numpy())
        pred["confidence"] = dm.confidence(pred[list(spec.classes)].max(axis=1).to_numpy(), table)
        rows += _rows(backtest, pred, spec)
        payload = dm.fit_production(frame, spec, alpha)
        payload["confidence"] = table
        result = {
            "decision": spec.key,
            "alpha": alpha,
            "alpha_scores": {str(k): v for k, v in scores.items()},
            **evaluate_decision(backtest, spec, pred),
        }
        payload["metrics"] = {k: v for k, v in result.items() if k != "alpha_scores"}
        with Session(engine) as session:
            session.merge(DecisionModel(decision=spec.key, payload=payload, fitted_at=datetime.now(UTC)))
            session.commit()
        if not forecast.empty:
            rows += _rows(forecast, dm.apply(forecast, payload), spec)
        results.append(result)
    _store(engine, rows, replace_runs=[int(r) for r in frame["model_run_id"].unique()])
    return {"fixtures": int(len(frame)), "seasons": seasons, "decisions": results,
            "min_confidence": app_config.get("decisions.min_confidence")}  # fmt: skip


def models(engine: Engine) -> dict[str, dict]:
    with Session(engine) as session:
        return {m.decision: m.payload for m in session.scalars(select(DecisionModel))}


def apply_new(engine: Engine) -> int:
    """Production models on forecast runs whose fixtures have no decision probabilities yet."""
    payloads = models(engine)
    if not payloads:
        return 0
    leagues, cups = _leagues()
    with engine.connect() as conn:
        ids = [int(r[0]) for r in conn.execute(text("""
            select distinct p.fixture_id from analytics.predictions p
            join analytics.model_runs r on r.id = p.model_run_id
            join core.fixtures f on f.id = p.fixture_id
            where r.kind = 'forecast' and f.kickoff_utc > now() and f.league_id = any(:leagues)
              and p.market = '1x2' and p.selection = 'H'
              and not exists (select 1 from analytics.decision_probs d
                              where d.model_run_id = p.model_run_id and d.fixture_id = p.fixture_id)"""),
            {"leagues": leagues})]  # fmt: skip
    if not ids:
        return 0
    frame = dfe.build(engine, leagues, cups, fixture_ids=ids)
    frame = frame[frame["kind"] == "forecast"]
    rows = []
    for spec in dm.SPECS:
        if spec.key in payloads and not frame.empty:
            rows += _rows(frame, dm.apply(frame, payloads[spec.key]), spec)
    _store(engine, rows)
    return len(frame)


def stacked(engine: Engine, where: str, **params) -> pd.DataFrame:
    """Decision model probabilities of the chosen run per fixture (``where`` filters the chosen runs, e.g.
    ``"and p.fixture_id = any(:ids)"``)."""
    from quotenfabrik.api.data import chosen_runs_cte

    sql = f"""with runs as ({chosen_runs_cte(where)})
              select d.fixture_id, d.decision, d.probabilities, d.confidence
              from analytics.decision_probs d
              join runs on runs.model_run_id = d.model_run_id and runs.fixture_id = d.fixture_id"""
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


# --------------------------------------------------------------------------- report


def _pct(x, digits: int = 1) -> str:
    return "–" if x is None else f"{x * 100:.{digits}f} %".replace(".", ",")


METHOD = (
    "Je Entscheidung (Sieger, Über 1,5, Über 2,5, Beide treffen, Tor 1. HZ, Tor 2. HZ) eine logistische "
    "Regression über der Wahrscheinlichkeit des Tor-Modells mit allem, was vor Anpfiff bekannt ist: "
    "Pattern der Liga-Historie (direkter Vergleich, Heim-/Auswärtsquoten, Tor- und Halbzeitquoten), Form "
    "beider Teams, Spielstil beider Teams (Schüsse, Schüsse aufs Tor, Strafraumanteil, Verwertung, "
    "Ballbesitz, Ertrag, Gegentore, Paraden), Termine (Ruhetage, Europapokal davor/danach, Spiele in "
    "14 Tagen) und gemeldete Ausfälle (ab 2021/22). Fehlende Werte werden aufgefüllt und markiert, eine "
    "L2-Strafe hält nutzlose Merkmale bei null (Stärke auf den Validierungssaisons {validation} gewählt)."
)
CONFIDENCE = (
    "Walk-forward: jede Saison mit einem Fit auf den Saisons davor, getestet ab {test}. **Konfidenz** "
    "(0–100) = Rang der Wahrscheinlichkeit der getippten Seite unter allen Spielen derselben Entscheidung "
    "(70 = sicherer als 70 % der Spiele). Getippt wird ab der Mindest-Konfidenz (Einstellung, derzeit "
    "{min_conf}), sonst „kein Tipp“."
)


def report(result: dict) -> str:
    from quotenfabrik.analytics.decisions import BY_KEY

    test = f"{dm.TEST_FROM}/{(dm.TEST_FROM + 1) % 100:02d}"
    lines = [
        "# Tippschein: 6 Entscheidungen pro Spiel", "",
        "_Automatisch erzeugt mit `qf model decisions`. Nicht von Hand bearbeiten._", "",
        "## Methode", "",
        METHOD.format(validation=", ".join(map(str, dm.VALIDATION))), "",
        CONFIDENCE.format(test=test, min_conf=result.get("min_confidence")), "",
        "## Gewinn durch die Zusatzinformationen (Testsaisons)", "",
        "| Entscheidung | Spiele | Log-Loss Tor-Modell | Log-Loss mit allem | Gewinn (95 %) "
        "| Treffer Tor-Modell | Treffer mit allem |",
        "|---|--:|--:|--:|--:|--:|--:|",
    ]  # fmt: skip
    for r in result["decisions"]:
        if not r.get("n"):
            continue
        lo, hi = r["gain_ci"]
        sig = " ✓" if lo > 0 else ""
        label = BY_KEY[r["decision"]].label
        lines.append(
            f"| {label} | {r['n']} | {r['log_loss_model']:.4f} | {r['log_loss']:.4f} "
            f"| {r['gain']:+.4f} [{lo:+.4f}; {hi:+.4f}]{sig} | {_pct(r['hit_model'])} | {_pct(r['hit'])} |"
        )
    lines += [
        "", "✓ = Verbesserung belastbar (Intervall über 0).", "",
        "## Trefferquote nach Mindest-Konfidenz (Testsaisons)", "",
        "Getippt = Anteil der Spiele mit Tipp. Vergleich = immer das Ergebnis, das in den Vorsaisons am "
        "häufigsten war, auf denselben Spielen.", "",
    ]  # fmt: skip
    for r in result["decisions"]:
        if not r.get("curve"):
            continue
        lines += [f"### {BY_KEY[r['decision']].label}", "",
                  "| Mindest-Konfidenz | getippt | Spiele | getroffen | erwartet | Vergleich |",
                  "|--:|--:|--:|--:|--:|--:|"]  # fmt: skip
        for c in r["curve"]:
            lines.append(
                f"| {c['min_confidence']} | {_pct(c['share'], 0)} | {c['n']} | {_pct(c['hit_rate'])} "
                f"| {_pct(c['expected'])} | {_pct(c['reference'])} |"
            )
        lines.append("")
    return "\n".join(lines)
