"""Shots in the goal model: does a blend of goals and a shot-based expectation predict better? (``qf model shots-eval``)

Walk-forward per matchday with the production setup (joint model over the connected leagues). Variants:
shot type (shots on target / all shots) × weight. The variant is chosen on the validation seasons and then
compared with the current model (goals only) on the test seasons, with a paired bootstrap interval of the
1X2 log-loss difference.
"""

from collections.abc import Iterable
from dataclasses import replace

import pandas as pd

from quotenfabrik.analytics import joint_eval
from quotenfabrik.analytics.poisson import PoissonParams

WEIGHTS = (0.25, 0.5, 0.75)
MODES = {"on_target": "Schüsse aufs Tor", "all": "alle Schüsse"}


def variants(base: PoissonParams) -> dict[str, PoissonParams]:
    out = {"nur Tore (aktuell)": replace(base, shots_weight=0.0)}
    for mode, label in MODES.items():
        for weight in WEIGHTS:
            out[f"{label}, Gewicht {weight:.2f}".replace(".", ",")] = replace(
                base, shots_weight=weight, shots_mode=mode
            )
    return out


def _predict(matches: pd.DataFrame, league_ids: Iterable[int], seasons: list[int], params) -> pd.DataFrame:
    return pd.concat(
        [joint_eval.predictions(matches, lg, seasons, params, joint=True) for lg in league_ids],
        ignore_index=True,
    )


def evaluate(
    matches: pd.DataFrame, league_ids: list[int], validation: list[int], test: list[int], base: PoissonParams
) -> dict:
    vs = variants(base)
    val = {name: joint_eval.scores(_predict(matches, league_ids, validation, p)) for name, p in vs.items()}
    baseline = "nur Tore (aktuell)"
    best = min((n for n in val if n != baseline), key=lambda n: val[n]["logloss_1x2"])
    preds = {name: _predict(matches, league_ids, test, vs[name]) for name in (baseline, best)}
    test_scores = {name: joint_eval.scores(d) for name, d in preds.items()}
    per_league = {
        lg: {name: joint_eval.scores(d[d["league_id"] == lg]) for name, d in preds.items()}
        for lg in league_ids
    }
    return {
        "validation": val, "best": best, "best_params": vs[best], "test": test_scores, "per_league": per_league,
        "delta": joint_eval._delta_ci(preds[baseline], preds[best]), "seasons": (validation, test),
    }  # fmt: skip


def _f(x: float, digits: int = 4) -> str:
    return f"{x:.{digits}f}".replace(".", ",")


def _s(x: float, digits: int = 4) -> str:
    return f"{x:+.{digits}f}".replace(".", ",").replace("-", "−")


def report(result: dict, league_names: dict[int, str]) -> str:
    from datetime import UTC, datetime

    validation, test = result["seasons"]
    span = lambda s: f"{s[0]}/{(s[0] + 1) % 100:02d}–{s[-1]}/{(s[-1] + 1) % 100:02d}"  # noqa: E731
    out = [
        "# 19 – Schüsse im Modell",
        "",
        f"Automatisch erzeugt von `qf model shots-eval` am {datetime.now(UTC):%d.%m.%Y %H:%M} UTC. Ligen: "
        f"{', '.join(league_names.values())} (gemeinsames Modell wie in der Produktion), Walk-Forward je Spieltag.",
        "",
        "**Idee:** Das Modell schätzt die Teamstärke bisher nur aus Toren. Tore sind stark vom Zufall geprägt; "
        "Schüsse zeigen stabiler, wie gut ein Team ist (Nachweis: `18_spielstil.md`). Deshalb rechnet das Modell "
        "mit einer Mischung aus Toren und einer Schuss-Erwartung (Schüsse × Torquote pro Schuss der Trainingsspiele).",
        "",
        f"## Auswahl auf den Validierungssaisons {span(validation)}",
        "",
        "| Variante | Spiele | Log-Loss 1X2 | RPS 1X2 | Log-Loss Ü/U 2,5 | Log-Loss Beide treffen |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, s in result["validation"].items():
        mark = " **← gewählt**" if name == result["best"] else ""
        out.append(f"| {name}{mark} | {s['n']} | {_f(s['logloss_1x2'])} | {_f(s['rps_1x2'])} | "
                   f"{_f(s['logloss_ou25'])} | {_f(s['logloss_btts'])} |")  # fmt: skip
    d, lo, hi = result["delta"]
    out += [
        "",
        f"## Test auf {span(test)} (kleiner = besser)",
        "",
        "| Modell | Spiele | Log-Loss 1X2 | RPS 1X2 | Log-Loss Ü/U 2,5 | Log-Loss Beide treffen |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, s in result["test"].items():
        out.append(f"| {name} | {s['n']} | {_f(s['logloss_1x2'])} | {_f(s['rps_1x2'])} | "
                   f"{_f(s['logloss_ou25'])} | {_f(s['logloss_btts'])} |")  # fmt: skip
    out += ["", f"Differenz Log-Loss 1X2 (gewählt − aktuell): {_s(d)} (95 %: {_s(lo)} … {_s(hi)}).", "",
            "| Liga | Modell | Log-Loss 1X2 | Log-Loss Ü/U 2,5 | Log-Loss Beide treffen |", "|---|---|---:|---:|---:|"]  # fmt: skip
    for lg, by_model in result["per_league"].items():
        for name, s in by_model.items():
            out.append(f"| {league_names.get(lg, lg)} | {name} | {_f(s['logloss_1x2'])} | {_f(s['logloss_ou25'])} | "
                       f"{_f(s['logloss_btts'])} |")  # fmt: skip
    better = hi < 0
    t = result["test"]
    base, best = t["nur Tore (aktuell)"], t[result["best"]]
    goals_better = (
        best["logloss_ou25"] < base["logloss_ou25"] and best["logloss_btts"] <= base["logloss_btts"] + 1e-4
    )
    out += ["", "## Bewertung", ""]
    if better:
        out.append(f"- **Übernehmen:** „{result['best']}“ ist im Test signifikant besser als das reine Tor-Modell "
                   f"(1X2-Log-Loss {_s(d)}, Intervall ohne 0).")  # fmt: skip
    elif d < 0:
        out.append(f"- Tendenziell besser (1X2-Log-Loss {_s(d)}), aber das Intervall schließt 0 ein.")
    else:
        out.append("- Kein Vorteil im Test: das reine Tor-Modell bleibt.")
    out.append(
        f"- Tor-Märkte (Ü/U 2,5, Beide treffen) im Test: {'ebenfalls besser' if goals_better else 'nicht besser'}."
    )
    out.append("")
    return "\n".join(out)
