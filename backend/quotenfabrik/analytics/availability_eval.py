"""Do schedule (rest days, European cup match next to a league match), absences and rotation improve the
goal model? (``qf model availability-eval`` → ``docs/22_ausfaelle_und_belastung.md``)

1. Walk-forward base model per matchday (production setup: joint model, goals + shots) → λ per team.
2. Correction layer: goals ~ Poisson(λ · exp(β·x_own + γ·x_opponent)), fitted on the validation seasons
   (only information before kickoff), evaluated on the test seasons against the base model
   (1X2 log loss with paired bootstrap interval, over/under 2.5, both teams score).
3. Descriptive: goals and points against the model's expectation in the situations themselves.
"""

from collections.abc import Iterable

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from quotenfabrik.analytics import joint_eval
from quotenfabrik.analytics.availability import FEATURES
from quotenfabrik.analytics.data import season_leagues
from quotenfabrik.analytics.poisson import PoissonParams, fit_poisson

RIDGE = 1.0  # L2 penalty on the correction coefficients (keeps them small without data)


def base_lambdas(
    matches: pd.DataFrame, league_ids: Iterable[int], seasons: Iterable[int], params: PoissonParams
) -> pd.DataFrame:
    """Walk-forward λ of the joint model for every finished league match in ``seasons``."""
    leagues_by_season = season_leagues(matches)
    rows = []
    for league_id in league_ids:
        own = matches[matches["league_id"] == league_id]
        test = own[own["season"].isin(list(seasons)) & own["finished"]]
        for (season, _), md in test.groupby(["season", "matchday"]):
            current = leagues_by_season.get(int(season), {})
            teams = {t for t, lg in current.items() if lg == league_id}
            model = fit_poisson(matches, md["kickoff"].min(), params, "hg", "ag", teams, "hxg", "axg",
                                team_league=current)  # fmt: skip
            for f in md.itertuples(index=False):
                lh, la = model.lambdas(f.home_id, f.away_id)
                rows.append({"fixture_id": f.fixture_id, "league_id": league_id, "season": int(season),
                             "kickoff": f.kickoff, "home_id": f.home_id, "away_id": f.away_id,
                             "hg": int(f.hg), "ag": int(f.ag), "lh": lh, "la": la,
                             "rho": model.rho})  # fmt: skip
    return pd.DataFrame(rows)


def team_rows(base: pd.DataFrame, features: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Two rows per match (home and away view): goals, λ, own and opponent features."""
    f = features.set_index(["fixture_id", "team_id"])[cols]
    out = []
    for side, team, opp, goals, lam in (
        ("home", "home_id", "away_id", "hg", "lh"),
        ("away", "away_id", "home_id", "ag", "la"),
    ):  # noqa: E501
        own = f.reindex(pd.MultiIndex.from_arrays([base["fixture_id"], base[team]])).to_numpy()
        other = f.reindex(pd.MultiIndex.from_arrays([base["fixture_id"], base[opp]])).to_numpy()
        part = pd.DataFrame({"fixture_id": base["fixture_id"].to_numpy(), "side": side,
                             "season": base["season"].to_numpy(),
                             "goals": base[goals].to_numpy(), "lam": base[lam].to_numpy()})  # fmt: skip
        part[[f"own_{c}" for c in cols]] = np.nan_to_num(own.astype(float))
        part[[f"opp_{c}" for c in cols]] = np.nan_to_num(other.astype(float))
        out.append(part)
    return pd.concat(out, ignore_index=True)


def fit_correction(rows: pd.DataFrame, cols: list[str]) -> np.ndarray:
    """β for [own features, opponent features] by penalised Poisson likelihood with offset log λ."""
    x = rows[[f"own_{c}" for c in cols] + [f"opp_{c}" for c in cols]].to_numpy(float)
    y, off = rows["goals"].to_numpy(float), np.log(rows["lam"].to_numpy(float))

    def nll(beta):
        eta = off + x @ beta
        return float(np.sum(np.exp(eta) - y * eta) + RIDGE * beta @ beta), x.T @ (
            np.exp(eta) - y
        ) + 2 * RIDGE * beta

    return minimize(nll, np.zeros(x.shape[1]), jac=True, method="L-BFGS-B").x


def adjusted(
    base: pd.DataFrame, rows: pd.DataFrame, cols: list[str], beta: np.ndarray | None
) -> pd.DataFrame:
    """Probabilities per match from (corrected) λ, in the format of ``joint_eval.scores``."""
    lh, la = base["lh"].to_numpy(), base["la"].to_numpy()
    if beta is not None:
        x_cols = [f"own_{c}" for c in cols] + [f"opp_{c}" for c in cols]
        for side, arr in (("home", "lh"), ("away", "la")):
            part = rows[rows["side"] == side].set_index("fixture_id").reindex(base["fixture_id"])
            factor = np.exp(part[x_cols].to_numpy(float) @ beta)
            if arr == "lh":
                lh = lh * factor
            else:
                la = la * factor
    out = []
    for f, h, a in zip(base.itertuples(index=False), lh, la, strict=True):
        p = joint_eval._probabilities(h, a, f.rho)
        out.append({"fixture_id": f.fixture_id, "league_id": f.league_id, "season": f.season, **p,
                    "result": "H" if f.hg > f.ag else "D" if f.hg == f.ag else "A",
                    "y_over25": float(f.hg + f.ag > 2.5),
                    "y_btts": float(f.hg > 0 and f.ag > 0)})  # fmt: skip
    return pd.DataFrame(out)


VARIANTS = {
    "Termine (Ruhetage, Europapokal davor/danach)": ["schedule"],
    "Ausfälle (gemeldete Ausfälle, gewichtet)": ["absences"],
    "Termine + Ausfälle": ["schedule", "absences"],
    "Termine + Ausfälle + Rotation (bestätigte Elf)": ["schedule", "absences", "rotation"],
}


def evaluate(
    base: pd.DataFrame, features: pd.DataFrame, splits: dict[str, tuple[list[int], list[int]]]
) -> dict:
    """Per variant: coefficients, test scores of base and corrected model, 1X2 log-loss difference."""
    out = {}
    for name, groups in VARIANTS.items():
        cols = [c for g in groups for c in FEATURES[g]]
        split = "schedule" if groups == ["schedule"] else "availability"
        train_seasons, test_seasons = splits[split]
        data = base[base["season"].isin(train_seasons + test_seasons)]
        if split == "availability":
            data = data[
                data["fixture_id"].isin(features.loc[features["has_roles"].fillna(False), "fixture_id"])
            ]
        rows = team_rows(data, features, cols)
        beta = fit_correction(rows[rows["season"].isin(train_seasons)], cols)
        test = data[data["season"].isin(test_seasons)]
        test_rows = rows[rows["season"].isin(test_seasons)]
        before, after = adjusted(test, test_rows, cols, None), adjusted(test, test_rows, cols, beta)
        out[name] = {
            "seasons": (train_seasons, test_seasons),
            "coef": dict(
                zip([f"own_{c}" for c in cols] + [f"opp_{c}" for c in cols], beta.round(4), strict=True)
            ),
            "base": joint_eval.scores(before),
            "adjusted": joint_eval.scores(after),
            "delta": joint_eval._delta_ci(before, after),
        }
    return out


def situations(base: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    """Goals and points of a team against the base model's expectation, per situation."""
    rows = []
    for f in base.itertuples(index=False):
        p = joint_eval._probabilities(f.lh, f.la, f.rho)
        for team, gf, ga, xf, xa, pts, xpts in (
            (f.home_id, f.hg, f.ag, f.lh, f.la, 3 * (f.hg > f.ag) + (f.hg == f.ag), 3 * p["H"] + p["D"]),
            (f.away_id, f.ag, f.hg, f.la, f.lh, 3 * (f.ag > f.hg) + (f.hg == f.ag), 3 * p["A"] + p["D"]),
        ):
            rows.append({"fixture_id": f.fixture_id, "team_id": team, "season": f.season, "gf": gf, "ga": ga,
                         "xf": xf, "xa": xa, "pts": pts, "xpts": xpts})  # fmt: skip
    data = pd.DataFrame(rows).merge(features, on=["fixture_id", "team_id"], how="left")
    groups = {
        "alle Ligaspiele": data,
        "Europapokal ≤ 4 Tage danach": data[data["next_cup"] == 1],
        "Europapokal ≤ 4 Tage davor": data[data["prev_cup"] == 1],
        "höchstens 3,5 Tage Pause": data[data["short_rest"] == 1],
        "mind. 2 Stammspieler fehlen": data[data["miss_starters"] >= 2],
        "Topscorer fehlt (≥ 25 % der Tore + Vorlagen)": data[data["miss_attack"] >= 0.25],
        "mind. 2 Stammspieler rotiert (Elf)": data[data["rotated"] >= 2],
    }
    out = []
    for label, g in groups.items():
        g = g.dropna(subset=["xf"])
        if g.empty:
            continue
        out.append({"situation": label, "n": len(g), "goals_ratio": g["gf"].sum() / g["xf"].sum(),
                    "conceded_ratio": g["ga"].sum() / g["xa"].sum(),
                    "pts_diff": float((g["pts"] - g["xpts"]).mean()),
                    "rotated": g["rotated"].mean() if g["rotated"].notna().any() else None})  # fmt: skip
    return pd.DataFrame(out)


def _f(x: float, d: int = 4) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def _s(x: float, d: int = 4) -> str:
    return f"{x:+.{d}f}".replace(".", ",").replace("-", "−")


def report(result: dict, table: pd.DataFrame, league_names: list[str]) -> str:
    from datetime import UTC, datetime

    span = lambda s: f"{s[0]}/{(s[0] + 1) % 100:02d}–{s[-1]}/{(s[-1] + 1) % 100:02d}"  # noqa: E731
    out = [
        "# 22 – Ausfälle, Aufstellung und Belastung",
        "",
        f"Automatisch erzeugt von `qf model availability-eval` am {datetime.now(UTC):%d.%m.%Y %H:%M} UTC. "
        f"Ligen: {', '.join(league_names)}. Basis: Produktionsmodell (gemeinsames Modell, Tore + Schüsse), "
        "Walk-Forward "
        "je Spieltag.",
        "",
        "**Frage:** Kennt das Modell zu wenig über den Spieltag? Rotation vor/nach Europapokalspielen, "
        "wenige "
        "Ruhetage, fehlende Stammspieler und eine rotierte Startelf sind ihm bisher unbekannt.",
        "",
        "## Situationen gegen die Modell-Erwartung",
        "",
        "Verhältnis > 1 = mehr als erwartet. Punkte: Ø Differenz zu den erwarteten Punkten je Spiel.",
        "",
        "| Situation | Spiele | Tore / erwartet | Gegentore / erwartet | Punkte vs. erwartet "
        "| Ø rotierte Stammspieler |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in table.itertuples(index=False):
        rot = "–" if r.rotated is None or pd.isna(r.rotated) else _f(r.rotated, 2)
        out.append(f"| {r.situation} | {r.n} | {_f(r.goals_ratio, 3)} | {_f(r.conceded_ratio, 3)} | "
                   f"{_s(r.pts_diff, 3)} | {rot} |")  # fmt: skip
    out += ["", "## Korrektur des Modells (Validierung → Test)", "",
            "Korrekturfaktor je Team: exp(β · eigene Merkmale + γ · Merkmale des Gegners), "
            "auf den Validierungssaisons geschätzt.", "",
            "| Variante | Saisons (Validierung → Test) | Spiele | Log-Loss 1X2 vorher → nachher | Δ (95 %) | "
            "Log-Loss Ü/U 2,5 | Log-Loss Beide treffen |",
            "|---|---|---:|---|---|---|---|"]  # fmt: skip
    for name, r in result.items():
        b, a = r["base"], r["adjusted"]
        d, lo, hi = r["delta"]
        tr, te = r["seasons"]
        out.append(f"| {name} | {span(tr)} → {span(te)} | {a['n']} | "
                   f"{_f(b['logloss_1x2'])} → {_f(a['logloss_1x2'])} | "
                   f"{_s(d)} ({_s(lo)} … {_s(hi)}) | {_f(b['logloss_ou25'])} → {_f(a['logloss_ou25'])} | "
                   f"{_f(b['logloss_btts'])} → {_f(a['logloss_btts'])} |")  # fmt: skip
    out += ["", "### Koeffizienten (log-Faktor auf die erwarteten Tore)", ""]
    for name, r in result.items():
        coefs = ", ".join(f"{k} {_s(v, 3)}" for k, v in r["coef"].items())
        out.append(f"- {name}: {coefs}")
    out += ["", "## Bewertung", ""]
    for name, r in result.items():
        d, lo, hi = r["delta"]
        best = "**signifikant besser** (Intervall unter 0) – Kandidat für das Produktionsmodell"
        verdict = (best if hi < 0 else
                   "tendenziell besser, aber nicht belastbar" if d < 0 else "kein Gewinn")  # fmt: skip
        out.append(f"- {name}: {verdict}.")
    out += [
        "- Rotation ist erst mit der bestätigten Aufstellung bekannt (20–40 Minuten vor Anpfiff); nutzbar "
        "nur mit "
        "einer Prognose kurz vor Anpfiff.",
        "- Nicht abgedeckt: nationale Pokale (DFB-Pokal ist nicht in der Datenbank), Ausfall-Meldungen "
        "vor 2021.",
        "",
    ]
    return "\n".join(out)
