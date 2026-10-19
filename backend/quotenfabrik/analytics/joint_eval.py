"""Joint model across leagues vs. separate models per league (walk-forward, full-time model).

Both variants predict every matchday of a league from matches strictly before its first kickoff. The
separate model is fitted on the league alone (current production approach: teams without recent matches
get the promoted-team prior). The joint model is fitted on all leagues at once with league levels
(see ``poisson.py``), so a promoted team keeps the strength it showed in the lower league.

Scored on 1X2 (log loss, RPS), over/under 2.5 and both teams to score; separately for matches with a team
that changed league since the previous season (promoted/relegated).
"""

from collections.abc import Iterable

import numpy as np
import pandas as pd

from quotenfabrik.analytics.data import load_leagues, season_leagues  # noqa: F401 (re-exported)
from quotenfabrik.analytics.poisson import PoissonParams, fit_poisson, score_matrix

EPS = 1e-12
EARLY_MATCHDAYS = 10  # "start of season": matchdays 1-10, where the treatment of promoted teams matters most


def _probabilities(lh: float, la: float, rho: float) -> dict[str, float]:
    m = score_matrix(lh, la, rho)
    i, j = np.indices(m.shape)
    return {
        "H": float(m[i > j].sum()),
        "D": float(m[i == j].sum()),
        "A": float(m[i < j].sum()),
        "over25": float(m[(i + j) > 2.5].sum()),
        "btts": float(m[(i > 0) & (j > 0)].sum()),
    }


def predictions(
    matches: pd.DataFrame, league_id: int, seasons: Iterable[int], params: PoissonParams, joint: bool
) -> pd.DataFrame:
    """One row per finished match of ``league_id`` in ``seasons`` with model probabilities and outcomes."""
    leagues_by_season = season_leagues(matches)
    own = matches[matches["league_id"] == league_id]
    train_sep = own.drop(columns="league_id")
    test = own[own["season"].isin(list(seasons)) & own["finished"]]
    rows = []
    for (season, matchday), md in test.groupby(["season", "matchday"]):
        as_of = md["kickoff"].min()
        current = leagues_by_season.get(int(season), {})
        previous = leagues_by_season.get(int(season) - 1, {})
        teams = {t for t, lg in current.items() if lg == league_id}
        if joint:
            model = fit_poisson(matches, as_of, params, "hg", "ag", teams, "hxg", "axg", team_league=current)
        else:
            model = fit_poisson(train_sep, as_of, params, "hg", "ag", teams, "hxg", "axg")
        for f in md.itertuples(index=False):
            p = _probabilities(*model.lambdas(f.home_id, f.away_id), model.rho)
            changed = previous.get(f.home_id) != league_id or previous.get(f.away_id) != league_id
            rows.append({
                "fixture_id": f.fixture_id, "league_id": league_id, "season": int(season),
                "matchday": int(matchday), "changed": changed, **p,
                "result": "H" if f.hg > f.ag else "D" if f.hg == f.ag else "A",
                "y_over25": float(f.hg + f.ag > 2.5), "y_btts": float(f.hg > 0 and f.ag > 0),
            })  # fmt: skip
    return pd.DataFrame(rows)


def scores(df: pd.DataFrame) -> dict[str, float]:
    """Mean scores (lower is better) of a prediction table."""
    if df.empty:
        return {"n": 0}
    p = df[["H", "D", "A"]].to_numpy()
    y = np.stack([(df["result"] == r).to_numpy(float) for r in ("H", "D", "A")], axis=1)
    cp, cy = np.cumsum(p, axis=1)[:, :2], np.cumsum(y, axis=1)[:, :2]

    def binary(col: str, target: str) -> float:
        q = np.clip(df[col].to_numpy(), EPS, 1 - EPS)
        t = df[target].to_numpy()
        return float(-np.mean(t * np.log(q) + (1 - t) * np.log(1 - q)))

    return {
        "n": len(df),
        "logloss_1x2": float(-np.mean(np.log(np.clip((p * y).sum(axis=1), EPS, None)))),
        "rps_1x2": float(np.mean(np.sum((cp - cy) ** 2, axis=1) / 2)),
        "logloss_ou25": binary("over25", "y_over25"),
        "logloss_btts": binary("btts", "y_btts"),
    }


def compare(
    matches: pd.DataFrame, league_ids: Iterable[int], seasons: Iterable[int], params: PoissonParams
) -> pd.DataFrame:
    """Scores of separate and joint model per league and subset (all / promoted-relegated / early season)."""
    rows = []
    for lg in league_ids:
        preds = {
            name: predictions(matches, lg, seasons, params, joint)
            for name, joint in (("getrennt", False), ("gemeinsam", True))
        }
        for subset, select in (
            ("alle Spiele", lambda d: d),
            ("mit Auf-/Absteiger", lambda d: d[d["changed"]]),
            (f"Spieltag 1–{EARLY_MATCHDAYS}", lambda d: d[d["matchday"] <= EARLY_MATCHDAYS]),
            (f"Auf-/Absteiger, Spieltag 1–{EARLY_MATCHDAYS}",
             lambda d: d[d["changed"] & (d["matchday"] <= EARLY_MATCHDAYS)]),
        ):  # fmt: skip
            for name, d in preds.items():
                rows.append({"league_id": lg, "subset": subset, "model": name, **scores(select(d))})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- report


def _mover_bias(
    matches: pd.DataFrame, league_id: int, seasons: Iterable[int], params: PoissonParams
) -> pd.DataFrame:
    """Matchdays 1-10: actual vs. expected goal difference of teams new in the league, per model."""
    sl = season_leagues(matches)
    own = matches[matches["league_id"] == league_id]
    rows = []
    for season in seasons:
        cur, prev = sl.get(season, {}), sl.get(season - 1, {})
        md = own[(own["season"] == season) & own["finished"] & (own["matchday"] <= EARLY_MATCHDAYS)]
        if md.empty:
            continue
        as_of = md["kickoff"].min()
        teams = {t for t, lg in cur.items() if lg == league_id}
        models = {
            "gemeinsam": fit_poisson(
                matches, as_of, params, "hg", "ag", teams, "hxg", "axg", team_league=cur
            ),
            "getrennt": fit_poisson(
                own.drop(columns="league_id"), as_of, params, "hg", "ag", teams, "hxg", "axg"
            ),
        }
        for f in md.itertuples(index=False):
            for home_side, team in ((True, f.home_id), (False, f.away_id)):
                before = prev.get(team)
                if before == league_id:
                    continue
                kind = "ohne Daten (z. B. aus 3. Liga)" if before is None else f"aus Liga {before}"
                diff = (f.hg - f.ag) if home_side else (f.ag - f.hg)
                for name, model in models.items():
                    lh, la = model.lambdas(f.home_id, f.away_id)
                    rows.append((kind, name, diff, (lh - la) if home_side else (la - lh)))
    d = pd.DataFrame(rows, columns=["kind", "model", "actual", "expected"])
    return d.groupby(["kind", "model"]).agg(
        n=("actual", "size"), actual=("actual", "mean"), expected=("expected", "mean")
    )


def _delta_ci(a: pd.DataFrame, b: pd.DataFrame, seed: int = 0) -> tuple[float, float, float]:
    """Mean 1X2 log-loss difference (b - a) with 95 % paired bootstrap interval over matches."""
    b = b.set_index("fixture_id").loc[a["fixture_id"]]
    a = a.set_index("fixture_id")

    def ll(x: pd.DataFrame) -> np.ndarray:
        return -np.log(np.where(x["result"] == "H", x["H"], np.where(x["result"] == "D", x["D"], x["A"])))

    diff = ll(b) - ll(a)
    rng = np.random.default_rng(seed)
    boots = [diff[rng.integers(0, len(diff), len(diff))].mean() for _ in range(2000)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return float(diff.mean()), float(lo), float(hi)


def report(
    matches: pd.DataFrame,
    league_ids: list[int],
    names: dict[int, str],
    validation: list[int],
    test: list[int],
    params: PoissonParams,
) -> str:
    """Markdown report: separate vs. joint model on validation and test seasons, plus bias for new teams."""
    from datetime import UTC, datetime

    def fmt(x: float) -> str:
        return f"{x:.4f}".replace(".", ",")

    def seasons_label(s: list[int]) -> str:
        return f"{s[0]}/{(s[0] + 1) % 100:02d}–{s[-1]}/{(s[-1] + 1) % 100:02d}"

    out = [
        "# 14 – Gemeinsames Modell über Ligen",
        "",
        f"Automatisch erzeugt von `qf model joint-eval` am {datetime.now(UTC):%d.%m.%Y %H:%M} UTC. "
        f"Ligen: {', '.join(names[lg] for lg in league_ids)}.",
        "",
        "**Frage:** Werden Prognosen besser, wenn verbundene Ligen gemeinsam gerechnet werden – mit einer Stärkeskala "
        "über alle Ligen und einer Ebene (Angriff/Abwehr) pro Liga – statt jede Liga getrennt?",
        "",
        "**Methode:** Walk-Forward pro Spieltag (nur Spiele vor dem ersten Anpfiff, kein Data Leakage), Vollzeitmodell "
        "Dixon-Coles mit den Standardparametern. *Getrennt* = bisheriges Vorgehen (Liga allein, Teams ohne Spiel im "
        "letzten Jahr starten mit dem Aufsteiger-Prior). *Gemeinsam* = alle Ligen in einem Fit, die Stärke eines Teams "
        "wird zur zeitgewichteten Mischung der Ligaebenen gezogen, in denen es gespielt hat; verbunden sind die Ligen "
        "über Auf- und Absteiger. Kennzahlen: Log-Loss und RPS (1X2), Log-Loss Über/Unter 2,5 und Beide treffen – "
        "jeweils **kleiner ist besser**. Varianten wurden nur auf den Validierungssaisons verglichen "
        f"({seasons_label(validation)}); die Testsaisons ({seasons_label(test)}) dienen allein der Bestätigung.",
        "",
    ]
    for period, seasons in (("Validierung", validation), ("Test", test)):
        out += [f"## {period}: {seasons_label(seasons)}", ""]
        for lg in league_ids:
            preds = {
                name: predictions(matches, lg, seasons, params, joint)
                for name, joint in (("getrennt", False), ("gemeinsam", True))
            }
            delta, lo, hi = _delta_ci(preds["getrennt"], preds["gemeinsam"])
            out += [
                f"### {names[lg]}",
                "",
                "| Spiele | n | Modell | Log-Loss 1X2 | RPS 1X2 | Log-Loss Ü/U 2,5 | Log-Loss BTTS |",
                "|---|---:|---|---:|---:|---:|---:|",
            ]
            for subset, select in (
                ("alle", lambda d: d),
                ("mit Auf-/Absteiger", lambda d: d[d["changed"]]),
                (f"Spieltag 1–{EARLY_MATCHDAYS}", lambda d: d[d["matchday"] <= EARLY_MATCHDAYS]),
                (f"Auf-/Absteiger, Spieltag 1–{EARLY_MATCHDAYS}",
                 lambda d: d[d["changed"] & (d["matchday"] <= EARLY_MATCHDAYS)]),
            ):  # fmt: skip
                for name, d in preds.items():
                    s = scores(select(d))
                    if not s["n"]:
                        continue
                    out.append(
                        f"| {subset} | {s['n']} | {name} | {fmt(s['logloss_1x2'])} | {fmt(s['rps_1x2'])} | "
                        f"{fmt(s['logloss_ou25'])} | {fmt(s['logloss_btts'])} |"
                    )
            verdict = "besser" if hi < 0 else "schlechter" if lo > 0 else "kein signifikanter Unterschied"
            out += [
                "",
                f"Differenz Log-Loss 1X2 (gemeinsam − getrennt, alle Spiele): **{fmt(delta)}**, "
                f"95-%-Intervall [{fmt(lo)}; {fmt(hi)}] (Bootstrap über Spiele) → gemeinsames Modell: **{verdict}**.",
                "",
            ]
    out += [
        "## Teams neu in der Liga (Testsaisons, Spieltag 1–10)",
        "",
        "Tatsächliche gegen erwartete Tordifferenz pro Spiel. Positive Abweichung = Team stärker als vom Modell "
        "erwartet.",
        "",
        "| Liga | Herkunft | Modell | n | Tordifferenz | erwartet | Abweichung |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for lg in league_ids:
        bias = _mover_bias(matches, lg, test, params)
        for (kind, model), r in bias.iterrows():
            kind_label = kind
            for other in league_ids:
                kind_label = kind_label.replace(f"Liga {other}", names[other])
            out.append(
                f"| {names[lg]} | {kind_label} | {model} | {int(r['n'])} | {fmt(r['actual'])} | "
                f"{fmt(r['expected'])} | {fmt(r['actual'] - r['expected'])} |"
            )
    out += [
        "",
        "## Bewertung",
        "",
        "- Das gemeinsame Modell nutzt für Aufsteiger deren Leistung in der unteren Liga statt eines pauschalen "
        "Startwerts; davon profitiert vor allem der Saisonbeginn der höheren Liga.",
        "- Bekannte Schwäche: Absteiger werden in der unteren Liga zu Saisonbeginn überschätzt (Kaderumbruch nach dem "
        "Abstieg ist im Modell nicht abgebildet). Eine Korrektur dafür wurde auf den Validierungssaisons geprüft "
        "(Startwert nach aktueller Liga, milderer Aufsteiger-Prior) und brachte keine Verbesserung.",
        "- Einstellung: `model.joint` auf der Einstellungsseite (Standard 1). Verbunden werden nur Ligen, die sich "
        "Teams teilen; andere Ligen werden weiterhin allein gerechnet.",
        "- Grundlage für den nächsten Schritt: weitere Ligen und Europapokal auf derselben Skala.",
        "",
    ]
    return "\n".join(out)
