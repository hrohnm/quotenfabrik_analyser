"""Does the playing style carry information the goal model does not have yet? (``qf model style-eval``)

Target: goals of a team minus the goals the model expected before the match (λ from the walk-forward backtest,
λ = −ln P(team scores 0)). Features: the team's style profile before the match (own attack) and the opponent's
profile (its defence). Three checks:

1. Correlation of every feature with the residual (with a 95 % interval).
2. Out of sample: linear correction fitted on the early seasons, tested on the later ones. Does the error of
   the goal expectation shrink?
3. Style duels: total goals and Over 2.5 per pairing (possession team vs. little possession, …) against the
   model.
"""

import numpy as np
import pandas as pd
from sqlalchemy import Engine, text

from quotenfabrik.analytics import style

FEATURES = {  # feature -> (label, side): side 'own' = attacking team, 'opp' = opponent
    "shots": ("Schüsse pro Spiel", "own"),
    "shots_on": ("Schüsse aufs Tor pro Spiel", "own"),
    "inside_share": ("Anteil Schüsse aus dem Strafraum", "own"),
    "possession": ("Ballbesitz", "own"),
    "shot_share": ("Anteil an allen Schüssen", "own"),
    "possession_yield": ("Ertrag des Ballbesitzes", "own"),
    "goals": ("Tore pro Spiel", "own"),
    "conversion_on": ("Tore pro Schuss aufs Tor (Abschlussglück?)", "own"),
    "xg": ("xG pro Spiel", "own"),
    "goals_minus_xg": ("Tore minus xG", "own"),
    "opp_shots_against": ("Gegner: zugelassene Schüsse", "opp"),
    "opp_shots_on_against": ("Gegner: zugelassene Schüsse aufs Tor", "opp"),
    "opp_goals_against": ("Gegner: Gegentore pro Spiel", "opp"),
    "opp_save_rate": ("Gegner: Paradenquote", "opp"),
    "opp_xg_against": ("Gegner: zugelassene xG", "opp"),
}
MODEL_FEATURES = [
    "shots_on",
    "shots",
    "inside_share",
    "conversion_on",
    "possession_yield",
    "opp_shots_on_against",
    "opp_save_rate",
]  # fmt: skip  (available since 2015, no xG)
TRAIN_UNTIL = 2021

_LAMBDA_SQL = """
    with runs as (
        select distinct on (p.fixture_id) p.fixture_id, p.model_run_id
        from analytics.predictions p join analytics.model_runs r on r.id = p.model_run_id
        where r.kind = 'backtest' and r.league_id = any(:leagues) and p.market = '1x2' and p.selection = 'H'
        order by p.fixture_id, r.id desc
    )
    select p.fixture_id,
           max(p.probability) filter (where p.market = 'ou_home' and p.line = 0.5 and p.selection = 'over') as p_home,
           max(p.probability) filter (where p.market = 'ou_away' and p.line = 0.5 and p.selection = 'over') as p_away,
           max(p.probability) filter (where p.market = 'ou_ft' and p.line = 2.5 and p.selection = 'over') as p_o25
    from analytics.predictions p join runs on runs.model_run_id = p.model_run_id and runs.fixture_id = p.fixture_id
    where p.market in ('ou_home', 'ou_away', 'ou_ft')
    group by p.fixture_id
"""


def load(engine: Engine, league_ids: list[int]) -> pd.DataFrame:
    """Team-match rows with the style before the match (own + opponent) and the model's expected goals."""
    frames = []
    for league_id in league_ids:  # profiles within each league (league matches only)
        rows = style.load_stats(engine, [league_id])
        frames.append(style.rolling_profiles(rows))
    prof = pd.concat(frames, ignore_index=True)
    opp = prof[["fixture_id", "team", *style.METRIC_KEYS]].rename(
        columns={"team": "opp", **{k: f"opp_{k}" for k in style.METRIC_KEYS}}
    )
    data = prof.merge(opp, on=["fixture_id", "opp"])
    with engine.connect() as conn:
        lam = pd.read_sql(text(_LAMBDA_SQL), conn, params={"leagues": list(league_ids)})
    data = data.merge(lam, on="fixture_id")
    p_score = np.where(data["venue"] == "home", data["p_home"], data["p_away"]).astype(float)
    data["lambda"] = -np.log(np.clip(1 - p_score, 1e-6, 1))
    data["residual"] = data["gf"] - data["lambda"]
    return data[data["lambda"].notna()].reset_index(drop=True)


def _corr(x: pd.Series, y: pd.Series) -> tuple[float, float, float, int]:
    ok = x.notna() & y.notna()
    x, y = x[ok], y[ok]
    n = len(x)
    if n < 30:
        return np.nan, np.nan, np.nan, n
    r = float(np.corrcoef(x, y)[0, 1])
    z, se = np.arctanh(r), 1 / np.sqrt(n - 3)
    return r, float(np.tanh(z - 1.96 * se)), float(np.tanh(z + 1.96 * se)), n


def correlations(data: pd.DataFrame) -> list[dict]:
    return [
        {"feature": f, "label": label, "corr": _corr(data[f], data["residual"])}
        for f, (label, _) in FEATURES.items()
    ]


def out_of_sample(data: pd.DataFrame) -> dict:
    """Linear correction of the goal expectation: fit on seasons ≤ TRAIN_UNTIL, test on the later seasons."""
    d = data.dropna(subset=MODEL_FEATURES)
    train, test = d[d["season"] <= TRAIN_UNTIL], d[d["season"] > TRAIN_UNTIL]
    if len(train) < 500 or len(test) < 200:
        return {"n_train": len(train), "n_test": len(test)}
    x_train = np.column_stack([np.ones(len(train)), train[MODEL_FEATURES]])
    coef, *_ = np.linalg.lstsq(x_train, train["residual"], rcond=None)
    x_test = np.column_stack([np.ones(len(test)), test[MODEL_FEATURES]])
    correction = x_test @ coef
    # reference: only a level correction (the model's average bias in the training seasons)
    level = test["residual"] - float(train["residual"].mean())
    base = test["residual"]
    corrected = base - correction
    mse_base, mse_level, mse_new = (
        float((base**2).mean()),
        float((level**2).mean()),
        float((corrected**2).mean()),
    )
    # paired bootstrap of the MSE difference against the level correction (= what the style adds)
    rng = np.random.default_rng(1)
    diff = (level**2 - corrected**2).to_numpy()
    boot = [diff[rng.integers(0, len(diff), len(diff))].mean() for _ in range(1000)]
    return {"n_train": len(train), "n_test": len(test), "mse_base": mse_base, "mse_level": mse_level,
            "mse_new": mse_new, "gain": (mse_level - mse_new) / mse_level, "ci": (float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))),
            "coef": dict(zip(["const", *MODEL_FEATURES], map(float, coef), strict=True)),
            "corr_test": _corr(pd.Series(correction, index=test.index), base)}  # fmt: skip


def duels(data: pd.DataFrame) -> list[dict]:
    """Total goals and Over 2.5 by possession pairing (terciles of possession before the match)."""
    home = data[data["venue"] == "home"].copy()
    away = data[data["venue"] == "away"][["fixture_id", "gf", "lambda", "possession", "shots"]]
    m = home.merge(away, on="fixture_id", suffixes=("", "_a"))
    m = m.dropna(subset=["possession", "possession_a"])
    cuts = np.nanpercentile(pd.concat([m["possession"], m["possession_a"]]), [33.3, 66.7])
    cls = lambda v: np.select([v <= cuts[0], v >= cuts[1]], ["wenig", "viel"], "mittel")  # noqa: E731
    m["pair"] = [f"{a} gegen {b}" for a, b in zip(cls(m["possession"]), cls(m["possession_a"]), strict=True)]
    m["total"] = m["gf"] + m["gf_a"]
    m["total_res"] = m["total"] - (m["lambda"] + m["lambda_a"])
    m["o25"] = (m["total"] > 2.5).astype(float)
    out = []
    for pair, g in m.groupby("pair"):
        out.append({"pair": pair, "n": len(g), "goals": float(g["total"].mean()),
                    "expected": float((g["lambda"] + g["lambda_a"]).mean()),
                    "residual": float(g["total_res"].mean()), "se": float(g["total_res"].std(ddof=1) / np.sqrt(len(g))),
                    "o25": float(g["o25"].mean()), "p_o25": float(g["p_o25"].mean())})  # fmt: skip
    order = ["viel", "mittel", "wenig"]
    return sorted(
        out, key=lambda r: (order.index(r["pair"].split(" ")[0]), order.index(r["pair"].split(" ")[-1]))
    )


def evaluate(engine: Engine, league_ids: list[int]) -> dict:
    data = load(engine, league_ids)
    return {"n": len(data), "seasons": (int(data["season"].min()), int(data["season"].max())) if len(data) else None,
            "correlations": correlations(data), "oos": out_of_sample(data), "duels": duels(data)}  # fmt: skip


# --------------------------------------------------------------------------- report


def _n(x: float, digits: int = 3) -> str:
    return "–" if x is None or pd.isna(x) else f"{x:+.{digits}f}".replace(".", ",").replace("-", "−")


def report(result: dict, league_names: list[str]) -> str:
    from datetime import UTC, datetime

    out = [
        "# 18 – Spielstil: Weiß er mehr als das Modell?",
        "",
        f"Automatisch erzeugt von `qf model style-eval` am {datetime.now(UTC):%d.%m.%Y %H:%M} UTC. Ligen: "
        f"{', '.join(league_names)}; {result['n']} Team-Spiele mit rückwirkender Prognose.",
        "",
        f"**Spielstil** = Profil aus den Statistiken der letzten {style.WINDOW} Ligaspiele vor dem Spiel (mindestens "
        f"{style.MIN_MATCHES}). **Ziel:** Tore eines Teams minus die vom Modell erwarteten Tore (Walk-Forward). "
        "Korrelation nahe 0 heißt: das Modell kennt die Information schon.",
        "",
        "## 1. Zusammenhang mit den Toren über/unter Modell-Erwartung",
        "",
        "| Merkmal vor dem Spiel | Spiele | Korrelation | 95-%-Intervall | auffällig |",
        "|---|---:|---:|---|---|",
    ]
    for c in result["correlations"]:
        r, lo, hi, n = c["corr"]
        sig = "ja" if not pd.isna(lo) and (lo > 0 or hi < 0) else ""
        out.append(f"| {c['label']} | {n} | {_n(r)} | {_n(lo)} … {_n(hi)} | {sig} |")
    oos = result["oos"]
    out += [
        "",
        f"## 2. Test auf späteren Saisons (Training bis {TRAIN_UNTIL}/{(TRAIN_UNTIL + 1) % 100:02d})",
        "",
    ]
    if "gain" in oos:
        lo, hi = oos["ci"]
        r, rlo, rhi, _ = oos["corr_test"]
        out += [
            f"Lineare Korrektur der erwarteten Tore aus {len(MODEL_FEATURES)} Spielstil-Merkmalen (ohne xG, da erst "
            f"ab 2022 vorhanden). Training {oos['n_train']} Team-Spiele, Test {oos['n_test']}.",
            "",
            "| | mittlerer quadratischer Fehler der Tore |",
            "|---|---:|",
            f"| nur Modell | {oos['mse_base']:.4f} |".replace(".", ","),
            f"| Modell + Niveau-Korrektur (mittlere Abweichung im Training) | {oos['mse_level']:.4f} |".replace(
                ".", ","
            ),
            f"| Modell + Spielstil-Korrektur | {oos['mse_new']:.4f} |".replace(".", ","),
            f"| Verbesserung durch den Spielstil (ggü. Niveau-Korrektur) | {_n(oos['gain'] * 100, 2)} % "
            f"(95 %: {_n(lo, 4)} … {_n(hi, 4)} absolut) |",
            "",
            f"Korrelation Korrektur ↔ tatsächlicher Rest im Test: {_n(r)} ({_n(rlo)} … {_n(rhi)}).",
            "",
            "Gewichte (Training): " + ", ".join(f"{k} {_n(v)}" for k, v in oos["coef"].items()),
        ]
    else:
        out.append(f"Zu wenige Spiele (Training {oos['n_train']}, Test {oos['n_test']}).")
    out += ["", "## 3. Stil-Duelle: Ballbesitz Heim gegen Gast", "",
            "Drittel nach Ballbesitz vor dem Spiel. Tore und Über 2,5 tatsächlich gegen Modell.", "",
            "| Heim gegen Gast | Spiele | Tore | Modell | Differenz | Über 2,5 | Modell |", "|---|---:|---:|---:|---:|---:|---:|"]  # fmt: skip
    for d in result["duels"]:
        out.append(f"| {d['pair']} | {d['n']} | {d['goals']:.2f} | {d['expected']:.2f} | {_n(d['residual'], 2)} "
                   f"(± {d['se']:.2f}) | {d['o25'] * 100:.1f} % | {d['p_o25'] * 100:.1f} % |".replace(".", ","))  # fmt: skip
    sig = [c for c in result["correlations"]
           if not pd.isna(c["corr"][1]) and (c["corr"][1] > 0 or c["corr"][2] < 0)]  # fmt: skip
    useful = "gain" in oos and oos["ci"][0] > 0
    out += ["", "## Bewertung", ""]
    if useful:
        out.append(f"- Der Spielstil verbessert die Tor-Erwartung im Test messbar ({_n(oos['gain'] * 100, 2)} %). "
                   "Kandidat für das Modell (nächster Schritt: als Merkmal einbauen und erneut prüfen).")  # fmt: skip
    else:
        out.append("- Kein belastbarer Zusatznutzen im Test: Die Spielstil-Korrektur macht die Tor-Erwartung nicht "
                   "sicher besser. Das Modell kennt die Stärke der Teams über die Tore bereits.")  # fmt: skip
    if sig:
        out.append("- Auffällig (Intervall ohne 0, bei vielen getesteten Merkmalen mit Vorsicht): "
                   + ", ".join(f"{c['label']} ({_n(c['corr'][0])})" for c in sig) + ".")  # fmt: skip
    out += [
        "- Der Spielstil wird auf der Detailseite angezeigt (Tab „Spielstil“) – als Beschreibung der Teams.",
        "",
    ]
    return "\n".join(out)
