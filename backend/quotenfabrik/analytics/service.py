"""Forecast and evaluation runs: fit models, compute probabilities and patterns, persist to ``analytics``."""

import dataclasses
import math
from collections.abc import Iterable
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from quotenfabrik.analytics import evaluation as ev
from quotenfabrik.analytics.data import (
    league_name,
    load_competitions,
    load_goal_events,
    load_matches,
    load_player_matches,
    season_leagues,
    with_league,
)
from quotenfabrik.analytics.markets import GROUPS
from quotenfabrik.analytics.patterns import PatternContext, compute_patterns
from quotenfabrik.analytics.poisson import PoissonParams
from quotenfabrik.analytics.prediction import fit_match_model
from quotenfabrik.analytics.scorers import ScorerModel, ScorerParams
from quotenfabrik.app_config import europe_pool, is_cup, model_params, model_pool
from quotenfabrik.ingest.db_utils import upsert
from quotenfabrik.models import Evaluation, ModelRun, PatternResultRow, Prediction

MODEL_VERSION = "dc-v1"
SQUAD_RECENCY_DAYS = 60
MIN_SCORER_PROBABILITY = 0.02


def _line(value: float | None) -> Decimal | None:
    return None if value is None or (isinstance(value, float) and math.isnan(value)) else Decimal(str(value))


def _fair(p: float) -> Decimal | None:
    return Decimal(str(round(1 / p, 3))) if p > 0.001 else None


def _squad(
    player_matches: pd.DataFrame, model: ScorerModel, team_id: int, as_of: pd.Timestamp
) -> pd.DataFrame:
    """Likely squad before lineups are known: outfield players of the team seen in recent matches."""
    recent = player_matches[
        (player_matches["kickoff"] >= as_of - pd.Timedelta(days=SQUAD_RECENCY_DAYS))
        & (player_matches["kickoff"] < as_of)
    ]
    ids = set(recent.loc[recent["team_id"] == team_id, "player_id"])
    rows = [
        (pid, team_id, None)
        for pid in ids
        if pid in model.players
        and model.players[pid].team_id == team_id
        and model.players[pid].position != "G"
    ]
    return pd.DataFrame(rows, columns=["player_id", "team_id", "is_starter"])


def _pool_leagues(pool: pd.DataFrame, league_id: int) -> list[int]:
    """Leagues the model was fitted on (several = joint model), stored with the model run."""
    return (
        sorted(int(lg) for lg in pool["league_id"].unique()) if "league_id" in pool.columns else [league_id]
    )


def run_forecast(
    engine: Engine,
    league_id: int,
    days_ahead: int = 10,
    params: PoissonParams | None = None,
    scorer_params: ScorerParams | None = None,
    as_of: pd.Timestamp | None = None,
) -> dict:
    """Predicts all regular-season fixtures in the next ``days_ahead`` days and stores the results."""
    if is_cup(league_id):
        return run_cup_forecast(engine, league_id, days_ahead, params, as_of)
    params = params or model_params()
    as_of = as_of or pd.Timestamp(datetime.now(UTC))
    matches = load_matches(engine, league_id)
    players = load_player_matches(engine, league_id)
    goals = load_goal_events(engine, league_id)
    upcoming = matches[
        ~matches["finished"]
        & (matches["kickoff"] >= as_of)
        & (matches["kickoff"] <= as_of + pd.Timedelta(days=days_ahead))
    ]
    if upcoming.empty:
        return {"fixtures": 0}
    season = int(upcoming["season"].iloc[0])
    teams = set(matches.loc[matches["season"] == season, "home_id"])
    pool = model_pool(engine, league_id)
    model = fit_match_model(pool, as_of, params, teams, season_leagues(pool).get(season))
    scorer_model = ScorerModel(scorer_params).fit(players, matches, as_of)
    ctx = PatternContext.build(matches, as_of, goals, players)

    with Session(engine) as session:
        run = ModelRun(
            kind="forecast",
            model_version=MODEL_VERSION,
            league_id=league_id,
            as_of=as_of.to_pydatetime(),
            params={
                "poisson": dataclasses.asdict(params),
                "scorers": dataclasses.asdict(scorer_model.params),
                "leagues": _pool_leagues(pool, league_id),
            },
        )
        session.add(run)
        session.flush()
        predictions, patterns = [], []
        for f in upcoming.itertuples(index=False):
            pred = model.predict(f.fixture_id, f.home_id, f.away_id)
            for group, module in GROUPS.items():
                for p in module.probabilities(pred):
                    predictions.append(_prediction_row(run.id, f.fixture_id, group, p))
            squad = pd.concat(
                [
                    _squad(players, scorer_model, f.home_id, as_of),
                    _squad(players, scorer_model, f.away_id, as_of),
                ]
            )
            for p in scorer_model.probabilities(squad, pred.lh, pred.la, f.home_id):
                if p.probability >= MIN_SCORER_PROBABILITY or p.market == "scorer_first":
                    predictions.append(_prediction_row(run.id, f.fixture_id, "scorers", p))
            for p in compute_patterns(ctx, f.home_id, f.away_id):
                patterns.append(
                    {
                        "model_run_id": run.id, "fixture_id": f.fixture_id, "market_group": p.group, "key": p.key,
                        "label": p.label, "scope": p.scope, "value": p.value, "n": p.n, "baseline": p.baseline,
                        "signal": p.signal, "details": p.details or None,
                    }
                )  # fmt: skip
        for row in predictions:
            row["predicted_at"] = as_of.to_pydatetime()
        upsert(session, Prediction, predictions, update=False)
        upsert(session, PatternResultRow, patterns, update=False)
        run.summary = {"fixtures": len(upcoming), "predictions": len(predictions), "patterns": len(patterns)}
        session.commit()
        return {"model_run_id": run.id, **run.summary}


def _prediction_row(run_id: int, fixture_id: int, group: str, p) -> dict:
    return {
        "model_run_id": run_id,
        "fixture_id": fixture_id,
        "market_group": group,
        "market": p.market,
        "selection": p.selection,
        "line": _line(p.line),
        "probability": float(p.probability),
        "fair_odd": _fair(p.probability),
    }


# --------------------------------------------------------------------------- evaluation


def run_evaluation(
    engine: Engine,
    league_id: int,
    seasons: Iterable[int],
    params: PoissonParams | None = None,
    scorer_params: ScorerParams | None = None,
    report_path: Path | None = None,
) -> dict:
    params = params or model_params()
    scorer_params = scorer_params or ScorerParams()
    seasons = list(seasons)
    matches = load_matches(engine, league_id)
    players = load_player_matches(engine, league_id)
    outcomes = ev.outcome_table(matches)
    pool = model_pool(engine, league_id)

    results = ev.walk_forward(matches, seasons, params, outcomes, pool=pool)
    binary = ev.binary_metrics(results)
    multi = {m: ev.multiclass_metrics(results, m) for m in ("1x2", "ht_1x2")}
    scorers = ev.walk_forward_scorers(matches, players, seasons, params, scorer_params, pool=pool)
    scorer_summary = _scorer_summary(scorers)
    signals = ev.evaluate_pattern_signals(matches, results, seasons)
    per_season = _per_season(results)

    with Session(engine) as session:
        run = ModelRun(
            kind="evaluation",
            model_version=MODEL_VERSION,
            league_id=league_id,
            params={"poisson": dataclasses.asdict(params), "scorers": dataclasses.asdict(scorer_params),
                    "seasons": seasons},
            summary={"multiclass": multi, "scorers": scorer_summary["overall"]},
        )  # fmt: skip
        session.add(run)
        session.flush()
        rows = []
        for r in binary.itertuples(index=False):
            metrics = {
                k: _num(getattr(r, k))
                for k in binary.columns
                if k not in {"group", "market", "selection", "line", "n"}
            }
            rows.append({"model_run_id": run.id, "market_group": r.group, "market": r.market, "selection": r.selection,
                         "line": _line(r.line), "n": int(r.n), "metrics": metrics})  # fmt: skip
        upsert(session, Evaluation, rows, update=False)
        session.commit()
        run_id = run.id

    if report_path:
        report_path.write_text(
            with_league(render_report(run_id, seasons, params, scorer_params, binary, multi, scorer_summary, signals, per_season, results), league_name(engine, league_id)),
            encoding="utf-8",
        )  # fmt: skip
    return {
        "model_run_id": run_id,
        "selections": len(binary),
        "matches": int(results["fixture_id"].nunique()),
    }


def _num(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return float(v)


def _per_season(results: pd.DataFrame) -> pd.DataFrame:
    key = results[
        (results["market"] == "ou_ft") & (results["line"] == 2.5) & (results["selection"] == "over")
    ]
    rows = []
    for season, r in results[results["market"] == "1x2"].groupby("season"):
        m = ev.multiclass_metrics(r, "1x2")
        k = key[key["season"] == season]
        y = k["outcome"].to_numpy(float)
        rows.append(
            {"season": season, "matches": m["n"], "rps_model": m["rps_model"], "rps_base": m["rps_base"],
             "rps_naive": m["rps_naive"],
             "brier_o25_model": float(np.mean((k["p_model"] - y) ** 2)),
             "brier_o25_base": float(np.mean((k["p_base"] - y) ** 2))}
        )  # fmt: skip
    return pd.DataFrame(rows)


def _scorer_summary(scorers: pd.DataFrame) -> dict:
    k = scorers[scorers["known"] & scorers["p_model"].notna() & scorers["p_base"].notna()]
    y = k["outcome"].to_numpy(float)

    def metrics(p):
        p = np.clip(p, 1e-9, 1 - 1e-9)
        return {
            "logloss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
            "brier": float(np.mean((p - y) ** 2)),
        }

    bins = [0, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.6, 1]
    calib = (
        k.assign(bin=pd.cut(k["p_model"], bins))
        .groupby("bin", observed=True)
        .agg(n=("outcome", "size"), predicted=("p_model", "mean"), observed=("outcome", "mean"))
        .reset_index()
    )
    return {
        "overall": {"n": int(len(k)), "unknown_players": int((~scorers["known"]).sum()),
                    "model": metrics(k["p_model"].to_numpy(float)), "base": metrics(k["p_base"].to_numpy(float))},
        "calibration": calib,
    }  # fmt: skip


# --------------------------------------------------------------------------- report (German)

GROUP_TITLES = {
    "1x2": "1. Spielausgang (1X2)",
    "totals": "2. Über/Unter Tore gesamt",
    "team_totals": "3. Über/Unter Tore pro Team",
    "halves": "4. Über/Unter Tore pro Halbzeit",
}
MARKET_LABELS = {
    "1x2": "1X2", "eh": "Europ. Handicap (Heim)", "ou_ft": "Tore gesamt", "btts": "Beide treffen",
    "exact_goals": "Exakte Toranzahl", "ou_home": "Tore Heimteam", "ou_away": "Tore Gastteam",
    "clean_sheet": "Zu null", "ou_1h": "Tore 1. HZ", "ou_2h": "Tore 2. HZ", "ou_home_1h": "Heimteam 1. HZ",
    "ou_away_1h": "Gastteam 1. HZ", "ou_home_2h": "Heimteam 2. HZ", "ou_away_2h": "Gastteam 2. HZ",
    "ht_1x2": "Halbzeit-Ergebnis", "btts_1h": "Beide treffen 1. HZ", "btts_2h": "Beide treffen 2. HZ",
    "highest_half": "Torreichste Halbzeit",
}  # fmt: skip


def _pct(v: float) -> str:
    return f"{v * 100:.1f} %"


def _signed_pct(v: float) -> str:
    return f"{v * 100:+.1f} %"


def render_report(
    run_id, seasons, params, scorer_params, binary, multi, scorer_summary, signals, per_season, results
) -> str:
    lines = [
        "# 09 – Modell-Evaluation (Phase 2, ohne Quoten)",
        "",
        f"Automatisch erzeugt von `qf model evaluate` am {datetime.now(UTC):%d.%m.%Y %H:%M} UTC "
        f"(Modell `{MODEL_VERSION}`, Lauf `analytics.model_runs.id = {run_id}`).",
        "",
        f"**Testzeitraum:** Saisons {', '.join(f'{s}/{(s + 1) % 100:02d}' for s in seasons)} – "
        f"{results['fixture_id'].nunique()} Spiele, Walk-Forward je Spieltag (Training nur mit Spielen vor dem Spieltag).",
        "",
        "**Vergleichswerte:** *Liga* = Häufigkeit des Ereignisses in den letzten 3 Saisons; "
        "*Form* = letzte 10 Heimspiele des Heimteams und letzte 10 Auswärtsspiele des Gastteams (geschrumpft zum Ligaschnitt).",
        "",
        "**Kennzahlen:** Brier-Score (mittlerer quadratischer Fehler der Wahrscheinlichkeit, kleiner = besser), "
        "*Skill* = relative Verbesserung des Brier-Scores gegenüber dem Vergleichswert, *ECE* = mittlerer "
        "Kalibrierungsfehler (|vorhergesagt − eingetreten| über 10 Klassen).",
        "",
        "**Parameter:** "
        f"Zeitgewichtung ξ = {params.xi}/Tag, Regularisierung {params.reg} (Halbzeiten {params.half_reg}), "
        f"Fenster {params.window_days} Tage, Aufsteiger-Prior {params.promoted_attack}/{params.promoted_defence}; "
        f"Torschützen: Shrinkage {scorer_params.shrink_90s} × 90 Min., Team-Faktor-Exponent {scorer_params.team_ratio_power}.",
        "",
        "## Überblick",
        "",
        "| Markt | Modell | Liga | Form | Bewertung |",
        "|---|---|---|---|---|",
    ]  # fmt: skip
    m = multi["1x2"]
    lines.append(
        f"| 1X2 (RPS) | {m['rps_model']:.4f} | {m['rps_base']:.4f} | {m['rps_naive']:.4f} | "
        f"{_signed_pct(1 - m['rps_model'] / m['rps_base'])} ggü. Liga |"
    )
    m = multi["ht_1x2"]
    lines.append(
        f"| Halbzeit-Ergebnis (RPS) | {m['rps_model']:.4f} | {m['rps_base']:.4f} | {m['rps_naive']:.4f} | "
        f"{_signed_pct(1 - m['rps_model'] / m['rps_base'])} ggü. Liga |"
    )
    for group in GROUP_TITLES:
        g = binary[(binary["group"] == group) & binary["selection"].isin(["over", "yes", "H", "home"])]
        if g.empty:
            continue
        w = g["n"]
        lines.append(
            f"| {GROUP_TITLES[group]} (Ø Brier, {len(g)} Auswahlen) | {np.average(g['brier_model'], weights=w):.4f} | "
            f"{np.average(g['brier_base'], weights=w):.4f} | {np.average(g['brier_naive'], weights=w):.4f} | "
            f"Skill {_signed_pct(np.average(g['skill_vs_base'], weights=w))} ggü. Liga |"
        )
    s = scorer_summary["overall"]
    lines.append(
        f"| 5. Torschützen Anytime (Brier, {s['n']} Spieler-Einsätze) | {s['model']['brier']:.5f} | "
        f"{s['base']['brier']:.5f} | – | Skill {_signed_pct(1 - s['model']['brier'] / s['base']['brier'])} ggü. Positions-Schnitt |"
    )
    lines += ["", "## Saison für Saison (1X2-RPS und Über 2.5-Brier)", "",
              "| Saison | Spiele | RPS Modell | RPS Liga | RPS Form | Brier Ü2.5 Modell | Brier Ü2.5 Liga |",
              "|---|---|---|---|---|---|---|"]  # fmt: skip
    for r in per_season.itertuples(index=False):
        lines.append(
            f"| {r.season}/{(r.season + 1) % 100:02d} | {r.matches} | {r.rps_model:.4f} | {r.rps_base:.4f} | {r.rps_naive:.4f} "
            f"| {r.brier_o25_model:.4f} | {r.brier_o25_base:.4f} |"
        )

    for group, title in GROUP_TITLES.items():
        g = binary[binary["group"] == group].copy()
        g = g[~g["selection"].isin(["under", "no"])]
        lines += ["", f"## {title}", "", "| Markt | Auswahl | Linie | n | Quote eingetreten | Brier Modell | Brier Liga | Brier Form | Skill ggü. Liga | Skill ggü. Form | ECE |",
                  "|---|---|---|---|---|---|---|---|---|---|---|"]  # fmt: skip
        for r in g.sort_values(["market", "line", "selection"]).itertuples(index=False):
            line = "" if pd.isna(r.line) else f"{r.line:g}"
            lines.append(
                f"| {MARKET_LABELS.get(r.market, r.market)} | {r.selection} | {line} | {r.n} | {_pct(r.rate)} | "
                f"{r.brier_model:.4f} | {r.brier_base:.4f} | {r.brier_naive:.4f} | {_signed_pct(r.skill_vs_base)} | "
                f"{_signed_pct(r.skill_vs_naive)} | {_pct(r.ece_model)} |"
            )

    lines += ["", "## 5. Torschützen (Anytime, mit bekannter Aufstellung)", "",
              f"{s['n']} Spieler-Einsätze (Feldspieler in Startelf oder auf der Bank), {s['unknown_players']} ohne Vorgeschichte "
              "ausgelassen. Vergleichswert: Trefferquote nach Position und Startelf/Bank.", "",
              "| | Log-Loss | Brier |", "|---|---|---|",
              f"| Modell | {s['model']['logloss']:.4f} | {s['model']['brier']:.5f} |",
              f"| Positions-Schnitt | {s['base']['logloss']:.4f} | {s['base']['brier']:.5f} |", "",
              "Kalibrierung:", "", "| vorhergesagt (Klasse) | n | Ø vorhergesagt | eingetreten |", "|---|---|---|---|"]  # fmt: skip
    for r in scorer_summary["calibration"].itertuples(index=False):
        lines.append(f"| {r.bin} | {r.n} | {_pct(r.predicted)} | {_pct(r.observed)} |")

    lines += ["", "## Kalibrierung ausgewählter Märkte", ""]
    for market, selection, line, label in (("1x2", "H", None, "Heimsieg"), ("ou_ft", "over", 2.5, "Über 2.5"),
                                           ("btts", "yes", None, "Beide treffen"), ("ou_1h", "over", 0.5, "1. HZ Über 0.5")):  # fmt: skip
        cal = ev.calibration_table(results, market, selection, line)
        lines += [f"**{label}**", "", "| Klasse | n | Ø vorhergesagt | eingetreten |", "|---|---|---|---|"]
        for idx, r in cal.iterrows():
            lines.append(f"| {idx} | {int(r['n'])} | {_pct(r['predicted'])} | {_pct(r['observed'])} |")
        lines.append("")

    lines += ["## Pattern-Signale außerhalb der Trainingsdaten", "",
              "Ein Signal *hoch* bzw. *niedrig* entsteht, wenn die Serie (Wilson-Intervall) deutlich über bzw. unter dem "
              "Ligaschnitt liegt. *Eingetreten* = tatsächliche Quote des Zielereignisses in diesen Spielen. "
              "*Rest ggü. Modell* = eingetreten minus Modellwahrscheinlichkeit: nahe 0 heißt, das Modell kennt die "
              "Information bereits; deutlich ≠ 0 heißt, das Pattern liefert Zusatzinformation.", "",
              "| Gruppe | Pattern | Signal | n | eingetreten | Liga | Modell | Abstand ggü. Liga | Rest ggü. Modell |",
              "|---|---|---|---|---|---|---|---|---|"]  # fmt: skip
    for r in signals.sort_values(["group", "pattern", "signal"]).itertuples(index=False):
        lines.append(
            f"| {r.group} | `{r.pattern}` | {'hoch' if r.signal == 'high' else 'niedrig'} | {r.n} | {_pct(r.observed)} | "
            f"{_pct(r.base)} | {_pct(r.model)} | {_signed_pct(r.lift_vs_base)} | {_signed_pct(r.residual_vs_model)} |"
        )
    lines.append("")
    return "\n".join(lines)


SHOW_MARKETS = [
    ("1x2", None, "1X2"), ("ou_ft", 2.5, "Tore gesamt 2.5"), ("btts", None, "Beide treffen"),
    ("ou_home", 1.5, "Tore Heim 1.5"), ("ou_away", 1.5, "Tore Gast 1.5"), ("ou_1h", 0.5, "1. HZ 0.5"),
    ("ou_1h", 1.5, "1. HZ 1.5"), ("ou_2h", 1.5, "2. HZ 1.5"),
]  # fmt: skip


def show_fixture(engine: Engine, fixture_id: int) -> str:
    from sqlalchemy import text

    with engine.connect() as conn:
        head = conn.execute(
            text(
                """select f.kickoff_utc, h.name, a.name, r.id, r.as_of from core.fixtures f
                   join core.teams h on h.id = f.home_team_id join core.teams a on a.id = f.away_team_id
                   join analytics.predictions p on p.fixture_id = f.id
                   join analytics.model_runs r on r.id = p.model_run_id
                   where f.id = :f order by r.id desc limit 1"""
            ),
            {"f": fixture_id},
        ).first()
        if head is None:
            return "Keine Prognose gefunden – zuerst `qf model forecast` ausführen."
        preds = pd.read_sql(
            text("select * from analytics.predictions where model_run_id = :r and fixture_id = :f"),
            conn, params={"r": head[3], "f": fixture_id},
        )  # fmt: skip
        pats = pd.read_sql(
            text("select * from analytics.pattern_results where model_run_id = :r and fixture_id = :f"),
            conn, params={"r": head[3], "f": fixture_id},
        )  # fmt: skip
        names = dict(conn.execute(text("select id::text, name from core.players")).all())
    out = [
        f"{head[1]} – {head[2]}  ({head[0]:%d.%m.%Y %H:%M} UTC, Prognose vom {head[4]:%d.%m.%Y %H:%M})",
        "",
    ]
    for market, line, label in SHOW_MARKETS:
        sel = preds[
            (preds["market"] == market) & (preds["line"].isna() if line is None else preds["line"] == line)
        ]
        parts = [
            f"{r.selection} {r.probability * 100:.1f} % ({float(r.fair_odd):.2f})"
            for r in sel.itertuples()
            if r.fair_odd
        ]
        out.append(f"{label:16} " + "  ".join(parts))
    scorers = preds[preds["market"] == "scorer_anytime"].sort_values("probability", ascending=False).head(8)
    out += ["", "Torschützen (Anytime, ohne bekannte Aufstellung):"]
    out += [f"  {names.get(r.selection, r.selection):28} {r.probability * 100:5.1f} %  ({float(r.fair_odd):.2f})"
            for r in scorers.itertuples()]  # fmt: skip
    signals = pats[pats["signal"].notna()]
    out += ["", "Pattern-Signale:"]
    out += [f"  [{r.signal:4}] {r.label}: {r.value * 100:.0f} % (n={r.n}, Liga {r.baseline * 100:.0f} %)"
            for r in signals.itertuples()]  # fmt: skip
    return "\n".join(out)


# --------------------------------------------------------------------------- backtest + settlement


def scorer_outcomes(fixture_id: int, player_goals: pd.DataFrame, goal_events: pd.DataFrame) -> dict:
    """{(market, player_id_str, None): bool} for anytime and first goalscorer of one finished fixture."""
    res = {}
    pg = player_goals[player_goals["fixture_id"] == fixture_id]
    for r in pg.itertuples(index=False):
        res[("scorer_anytime", str(r.player_id), None)] = bool(r.goals > 0)
    ev_ = goal_events[goal_events["fixture_id"] == fixture_id].sort_values(
        ["minute", "extra_minute"], na_position="first"
    )
    first = ev_.iloc[0] if len(ev_) else None
    if first is not None and first["detail"] != "Own Goal" and pd.isna(first["player_id"]):
        return res  # scorer of the first goal unknown (missing in the API data): first goalscorer stays unsettled
    first_scorer = None if first is None or first["detail"] == "Own Goal" else str(int(first["player_id"]))
    for r in pg.itertuples(index=False):
        res[("scorer_first", str(r.player_id), None)] = str(r.player_id) == first_scorer
    return res


def _key(market: str, selection: str, line) -> tuple:
    if line is None or (isinstance(line, float) and math.isnan(line)):
        return (market, selection, None)
    return (market, selection, float(line))


def match_outcomes(match) -> dict:
    out = {}
    for module in GROUPS.values():
        for (market, selection, line), hit in module.outcomes(match).items():
            out[_key(market, selection, line)] = None if hit is None else bool(hit)
    return out


def run_backtest(
    engine: Engine,
    league_id: int,
    seasons: Iterable[int],
    params: PoissonParams | None = None,
    scorer_params: ScorerParams | None = None,
) -> dict:
    """Walk-forward predictions for all finished matches of ``seasons`` incl. outcomes (replaces older backtests).

    Every matchday is predicted with models fitted only on matches before its first kickoff. Goalscorer
    predictions use the actual lineups (starters/bench are published before kickoff).
    """
    from sqlalchemy import delete

    if is_cup(league_id):
        return run_cup_backtest(engine, league_id, seasons, params)
    params = params or model_params()
    scorer_params = scorer_params or ScorerParams()
    seasons = list(seasons)
    matches = load_matches(engine, league_id)
    players = load_player_matches(engine, league_id)
    goals = load_goal_events(engine, league_id)
    pool = model_pool(engine, league_id)
    pool_seasons = season_leagues(pool)

    with Session(engine) as session:
        session.execute(delete(ModelRun).where(ModelRun.kind == "backtest", ModelRun.league_id == league_id))
        run = ModelRun(
            kind="backtest", model_version=MODEL_VERSION, league_id=league_id,
            params={"poisson": dataclasses.asdict(params), "scorers": dataclasses.asdict(scorer_params),
                    "seasons": seasons, "leagues": _pool_leagues(pool, league_id)},
        )  # fmt: skip
        session.add(run)
        session.flush()
        total = 0
        for as_of, md in ev._matchdays(matches, seasons):
            season = md["season"].iloc[0]
            teams = set(matches.loc[matches["season"] == season, "home_id"])
            model = fit_match_model(pool, as_of, params, teams, pool_seasons.get(int(season)))
            scorer_model = ScorerModel(scorer_params).fit(players, matches, as_of)
            rows = []
            for f in md.itertuples(index=False):
                pred = model.predict(f.fixture_id, f.home_id, f.away_id)
                outcomes = match_outcomes(f)
                for group, module in GROUPS.items():
                    for p in module.probabilities(pred):
                        row = _prediction_row(run.id, f.fixture_id, group, p)
                        row["predicted_at"] = as_of.to_pydatetime()
                        row["outcome"] = outcomes.get(_key(p.market, p.selection, p.line))
                        rows.append(row)
                squad = players[
                    (players["fixture_id"] == f.fixture_id) & players["position"].isin(["D", "M", "F"])
                ]
                squad = squad[squad["player_id"].isin(scorer_model.players.keys())]
                s_out = scorer_outcomes(f.fixture_id, players, goals)
                for p in scorer_model.probabilities(
                    squad[["player_id", "team_id", "is_starter"]], pred.lh, pred.la, f.home_id
                ):
                    row = _prediction_row(run.id, f.fixture_id, "scorers", p)
                    row["predicted_at"] = as_of.to_pydatetime()
                    row["outcome"] = s_out.get((p.market, p.selection, None))
                    rows.append(row)
            upsert(session, Prediction, rows, update=False)
            total += len(rows)
        run.summary = {"predictions": total, "matches": int(matches["season"].isin(seasons).sum())}
        session.commit()
        return {"model_run_id": run.id, **run.summary}


# --------------------------------------------------------------------------- European cups
#
# Cup competitions are forecast with the European pool (all leagues + cups, one strength scale, validated in
# docs/15_europapokal.md). Goalscorers use the player data of every competition with match details (full
# leagues and the recent cup seasons), so a Bundesliga team's scorers come from its league matches too; teams
# without player data get none. Patterns are computed over all competitions of the pool (baseline: all of
# Europe). Fixtures are grouped by ISO week (cups have no matchdays); finals are on neutral ground.


def _cup_teams(pool: pd.DataFrame, season: int) -> dict[int, int]:
    """Domestic league per team for a cup season (calendar-year leagues: the previous season as fallback)."""
    by_season = season_leagues(pool)
    return {**by_season.get(season - 1, {}), **by_season.get(season, {})}


def _cup_data(engine: Engine) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """European pool plus matches, player matches and goal events of all competitions with player data."""
    from quotenfabrik.app_config import cup_leagues, league_ids

    pool = europe_pool(engine)
    matches, players, goals = load_competitions(engine, league_ids(), [lg.id for lg in cup_leagues()])
    return pool, matches, players, goals


def _cup_rows(
    run_id: int, model, fixtures: pd.DataFrame, with_outcomes: bool, scorer_model: ScorerModel,
    players: pd.DataFrame, goals: pd.DataFrame, as_of: pd.Timestamp,
) -> list[dict]:  # fmt: skip
    rows = []
    for f in fixtures.itertuples(index=False):
        pred = model.predict(f.fixture_id, f.home_id, f.away_id, cup=True, neutral=f.round == "Final")
        outcomes = match_outcomes(f) if with_outcomes else {}
        for group, module in GROUPS.items():
            for p in module.probabilities(pred):
                row = _prediction_row(run_id, f.fixture_id, group, p)
                if with_outcomes:
                    row["outcome"] = outcomes.get(_key(p.market, p.selection, p.line))
                rows.append(row)
        # backtest: the actual line-up where the cup fixture has details, otherwise the likely squad
        lineup = players[(players["fixture_id"] == f.fixture_id) & players["position"].isin(["D", "M", "F"])]
        lineup = lineup[lineup["player_id"].isin(scorer_model.players.keys())]
        squads = [lineup[["player_id", "team_id", "is_starter"]]] if with_outcomes else []
        for team in (f.home_id, f.away_id):
            if not with_outcomes or lineup[lineup["team_id"] == team].empty:
                squads.append(_squad(players, scorer_model, team, as_of))
        s_out = scorer_outcomes(f.fixture_id, players, goals) if with_outcomes else {}
        for p in scorer_model.probabilities(pd.concat(squads), pred.lh, pred.la, f.home_id):
            if p.probability >= MIN_SCORER_PROBABILITY or p.market == "scorer_first":
                row = _prediction_row(run_id, f.fixture_id, "scorers", p)
                if with_outcomes:
                    row["outcome"] = s_out.get((p.market, p.selection, None))
                rows.append(row)
    return rows


def run_cup_forecast(
    engine: Engine,
    league_id: int,
    days_ahead: int = 10,
    params: PoissonParams | None = None,
    as_of: pd.Timestamp | None = None,
) -> dict:
    """Forecast of the cup fixtures in the next ``days_ahead`` days (European pool, scorers and patterns from
    all competitions)."""
    params = params or model_params()
    as_of = as_of or pd.Timestamp(datetime.now(UTC))
    matches = load_matches(engine, league_id)
    upcoming = matches[
        ~matches["finished"]
        & (matches["kickoff"] >= as_of)
        & (matches["kickoff"] <= as_of + pd.Timedelta(days=days_ahead))
    ]
    if upcoming.empty:
        return {"fixtures": 0}
    season = int(upcoming["season"].iloc[0])
    pool, all_matches, players, goals = _cup_data(engine)
    teams = set(upcoming["home_id"]) | set(upcoming["away_id"])
    model = fit_match_model(pool, as_of, params, teams, _cup_teams(pool, season))
    scorer_model = ScorerModel().fit(players, all_matches, as_of)
    ctx = PatternContext.build(pool, as_of, goals, players)
    with Session(engine) as session:
        run = ModelRun(
            kind="forecast", model_version=MODEL_VERSION, league_id=league_id, as_of=as_of.to_pydatetime(),
            params={"poisson": dataclasses.asdict(params), "scorers": dataclasses.asdict(scorer_model.params),
                    "leagues": _pool_leagues(pool, league_id), "cup": True},
        )  # fmt: skip
        session.add(run)
        session.flush()
        rows = _cup_rows(run.id, model, upcoming, False, scorer_model, players, goals, as_of)
        for row in rows:
            row["predicted_at"] = as_of.to_pydatetime()
        patterns = [
            {"model_run_id": run.id, "fixture_id": f.fixture_id, "market_group": p.group, "key": p.key,
             "label": p.label, "scope": p.scope, "value": p.value, "n": p.n, "baseline": p.baseline,
             "signal": p.signal, "details": p.details or None}
            for f in upcoming.itertuples(index=False)
            for p in compute_patterns(ctx, f.home_id, f.away_id)
        ]  # fmt: skip
        upsert(session, Prediction, rows, update=False)
        upsert(session, PatternResultRow, patterns, update=False)
        run.summary = {"fixtures": len(upcoming), "predictions": len(rows), "patterns": len(patterns)}
        session.commit()
        return {"model_run_id": run.id, **run.summary}


def run_cup_backtest(
    engine: Engine, league_id: int, seasons: Iterable[int], params: PoissonParams | None = None
) -> dict:
    """Walk-forward predictions of finished cup matches, one fit per ISO week (replaces older backtests)."""
    from sqlalchemy import delete

    params = params or model_params()
    seasons = list(seasons)
    matches = load_matches(engine, league_id)
    pool, all_matches, players, goals = _cup_data(engine)
    test = matches[matches["season"].isin(seasons) & matches["finished"]].copy()
    iso = test["kickoff"].dt.isocalendar()
    test["week"] = iso["year"].astype(int) * 100 + iso["week"].astype(int)
    with Session(engine) as session:
        session.execute(delete(ModelRun).where(ModelRun.kind == "backtest", ModelRun.league_id == league_id))
        run = ModelRun(
            kind="backtest", model_version=MODEL_VERSION, league_id=league_id,
            params={"poisson": dataclasses.asdict(params), "seasons": seasons,
                    "leagues": _pool_leagues(pool, league_id), "cup": True},
        )  # fmt: skip
        session.add(run)
        session.flush()
        total = 0
        for _, week in test.groupby("week"):
            as_of = week["kickoff"].min()
            teams = set(week["home_id"]) | set(week["away_id"])
            model = fit_match_model(pool, as_of, params, teams, _cup_teams(pool, int(week["season"].iloc[0])))
            scorer_model = ScorerModel().fit(players, all_matches, as_of)
            rows = _cup_rows(run.id, model, week, True, scorer_model, players, goals, as_of)
            for row in rows:
                row["predicted_at"] = as_of.to_pydatetime()
            upsert(session, Prediction, rows, update=False)
            total += len(rows)
        run.summary = {"predictions": total, "matches": len(test)}
        session.commit()
        return {"model_run_id": run.id, **run.summary}


def settle_predictions(engine: Engine, league_id: int) -> int:
    """Fills ``outcome`` of forecast predictions whose fixtures are finished."""
    from sqlalchemy import text

    matches = load_matches(engine, league_id).set_index("fixture_id")
    players = load_player_matches(engine, league_id)
    goals = load_goal_events(engine, league_id)
    with Session(engine) as session:
        open_ = pd.read_sql(
            text(
                """select p.id, p.fixture_id, p.market, p.selection, p.line from analytics.predictions p
                   join analytics.model_runs r on r.id = p.model_run_id
                   where r.league_id = :l and p.outcome is null"""
            ),
            session.connection(), params={"l": league_id},
        )  # fmt: skip
        updates = []
        for fixture_id, preds in open_.groupby("fixture_id"):
            if fixture_id not in matches.index or not matches.loc[fixture_id, "finished"]:
                continue
            m = matches.loc[fixture_id]
            outcomes = match_outcomes(m) | scorer_outcomes(fixture_id, players, goals)
            for r in preds.itertuples(index=False):
                hit = outcomes.get(_key(r.market, r.selection, None if r.line is None else float(r.line)))
                if hit is not None:
                    updates.append({"pid": int(r.id), "hit": bool(hit)})
        if updates:
            session.execute(text("update analytics.predictions set outcome = :hit where id = :pid"), updates)
        session.commit()
        return len(updates)
