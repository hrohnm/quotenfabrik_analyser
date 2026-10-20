"""European cups: walk-forward evaluation of the joint model on cup matches (results only, no odds).

All domestic leagues and the cups form one pool. Every week with cup matches is predicted from matches
strictly before its first kickoff. Variants:

* ``Basisrate``             – frequencies of 1X2 / over 2.5 / BTTS in cup matches of the last 3 years
* ``ohne Pokalspiele``      – joint model on the domestic leagues only: without cup matches the leagues are
                              not linked, so every league is treated as equally strong (naive approach)
* ``gemeinsam``             – joint model incl. cup matches (leagues on one scale, shared home advantage)
* ``gemeinsam + Heimvorteil`` – as above with an own home advantage for cup matches

Settlement after 90 minutes (``ft_home/ft_away`` = API-Football ``score.fulltime``, extra time excluded).
"""

from collections.abc import Iterable
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from quotenfabrik.analytics.data import season_leagues
from quotenfabrik.analytics.joint_eval import _probabilities, scores
from quotenfabrik.analytics.poisson import PoissonParams, fit_poisson

BASE_WINDOW_DAYS = 3 * 365
VARIANTS = ("Basisrate", "ohne Pokalspiele", "gemeinsam", "gemeinsam + Heimvorteil")


def stage(round_name: str | None) -> str:
    r = (round_name or "").lower()
    if "qualifying" in r or "preliminary" in r:
        return "Qualifikation"
    if ("play-off" in r or "playoff" in r) and "knockout" not in r:
        return "Play-offs"
    if "group" in r or "league stage" in r:
        return "Gruppen-/Ligaphase"
    return "K.-o.-Runde"


def _second_legs(cups: pd.DataFrame) -> set[int]:
    """Fixture ids of second legs: same pairing earlier in the same competition, season and round."""
    seen, second = set(), set()
    for f in cups.sort_values("kickoff").itertuples(index=False):
        key = (f.league_id, f.season, f.round, frozenset((f.home_id, f.away_id)))
        if key in seen:
            second.add(f.fixture_id)
        seen.add(key)
    return second


def _base_rates(cups: pd.DataFrame, as_of: pd.Timestamp) -> dict[str, float]:
    hist = cups[cups["finished"] & (cups["kickoff"] < as_of)
                & (cups["kickoff"] >= as_of - pd.Timedelta(days=BASE_WINDOW_DAYS))]  # fmt: skip
    if hist.empty:
        return {"H": 0.45, "D": 0.25, "A": 0.30, "over25": 0.5, "btts": 0.5}
    hg, ag = hist["hg"].to_numpy(), hist["ag"].to_numpy()
    return {"H": float(np.mean(hg > ag)), "D": float(np.mean(hg == ag)), "A": float(np.mean(hg < ag)),
            "over25": float(np.mean(hg + ag > 2.5)), "btts": float(np.mean((hg > 0) & (ag > 0)))}  # fmt: skip


def predictions(
    pool: pd.DataFrame, seasons: Iterable[int], params: PoissonParams, variant: str
) -> pd.DataFrame:
    """One row per finished cup match in ``seasons`` (cup season = start year) for one variant."""
    cups = pool[pool["cup"]]
    domestic = pool[~pool["cup"]]
    leagues_by_season = season_leagues(pool)
    second = _second_legs(cups)
    test = cups[cups["season"].isin(list(seasons)) & cups["finished"]].copy()
    iso = test["kickoff"].dt.isocalendar()
    test["week"] = iso["year"].astype(int) * 100 + iso["week"].astype(int)
    train = domestic if variant == "ohne Pokalspiele" else pool
    p = PoissonParams(**{**params.__dict__, "cup_home_adv": variant == "gemeinsam + Heimvorteil"})
    rows = []
    for _, md in test.groupby("week"):
        as_of = md["kickoff"].min()
        season = int(md["season"].iloc[0])
        # domestic league of every team: current season, else the previous one (calendar-year leagues)
        current = {**leagues_by_season.get(season - 1, {}), **leagues_by_season.get(season, {})}
        teams = set(md["home_id"]) | set(md["away_id"])
        if variant == "Basisrate":
            base = _base_rates(cups, as_of)
            probs = {f.fixture_id: base for f in md.itertuples(index=False)}
        else:
            model = fit_poisson(train, as_of, p, "hg", "ag", teams, "hxg", "axg", team_league=current)
            probs = {
                f.fixture_id: _probabilities(*model.lambdas(f.home_id, f.away_id, cup=True, neutral=f.neutral),
                                             model.rho)
                for f in md.itertuples(index=False)
            }  # fmt: skip
        for f in md.itertuples(index=False):
            rows.append({
                "fixture_id": f.fixture_id, "competition": int(f.league_id), "season": season,
                "stage": stage(f.round), "second_leg": f.fixture_id in second,
                "known": f.home_id in current and f.away_id in current, **probs[f.fixture_id],
                "result": "H" if f.hg > f.ag else "D" if f.hg == f.ag else "A",
                "y_over25": float(f.hg + f.ag > 2.5), "y_btts": float(f.hg > 0 and f.ag > 0),
            })  # fmt: skip
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- report

COMPETITIONS = {2: "Champions League", 3: "Europa League", 848: "Conference League"}


def _fmt(x: float) -> str:
    return f"{x:.4f}".replace(".", ",")


def _delta_ci(a: pd.DataFrame, b: pd.DataFrame, seed: int = 0) -> tuple[float, float, float]:
    """Mean 1X2 log-loss difference (b - a) with 95 % paired bootstrap interval."""
    b = b.set_index("fixture_id").loc[a["fixture_id"]]
    a = a.set_index("fixture_id")

    def ll(x: pd.DataFrame) -> np.ndarray:
        return -np.log(np.where(x["result"] == "H", x["H"], np.where(x["result"] == "D", x["D"], x["A"])))

    diff = ll(b) - ll(a)
    rng = np.random.default_rng(seed)
    boots = [diff[rng.integers(0, len(diff), len(diff))].mean() for _ in range(2000)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return float(diff.mean()), float(lo), float(hi)


def _table(preds: dict[str, pd.DataFrame], subsets: list[tuple[str, callable]]) -> list[str]:
    out = ["| Spiele | n | Modell | Log-Loss 1X2 | RPS 1X2 | Log-Loss Ü/U 2,5 | Log-Loss BTTS |",
           "|---|---:|---|---:|---:|---:|---:|"]  # fmt: skip
    for label, select in subsets:
        for name, d in preds.items():
            s = scores(select(d))
            if s["n"]:
                out.append(f"| {label} | {s['n']} | {name} | {_fmt(s['logloss_1x2'])} | {_fmt(s['rps_1x2'])} | "
                           f"{_fmt(s['logloss_ou25'])} | {_fmt(s['logloss_btts'])} |")  # fmt: skip
    return out


def report(
    validation: dict[str, pd.DataFrame],
    test: dict[str, pd.DataFrame],
    validation_seasons: list[int],
    test_seasons: list[int],
    league_levels: list[tuple[str, float]],
    bundesliga: list[str],
) -> str:
    """Markdown report from the variant predictions (``{variant: predictions}``) of both periods."""

    def label(s: list[int]) -> str:
        return f"{s[0]}/{(s[0] + 1) % 100:02d}–{s[-1]}/{(s[-1] + 1) % 100:02d}"

    out = [
        "# 15 – Europapokal: gemeinsame Stärkeskala über Ländergrenzen",
        "",
        f"Automatisch erzeugt von `qf model cup-eval` am {datetime.now(UTC):%d.%m.%Y %H:%M} UTC.",
        "",
        "**Frage:** Lassen sich Spiele zwischen Teams aus verschiedenen Ländern (Champions League, Europa League, "
        "Conference League) vorhersagen, wenn alle Ligen und die Pokalspiele in einem gemeinsamen Modell gerechnet "
        "werden?",
        "",
        "**Methode:** Walk-Forward pro Woche: Jede Woche mit Pokalspielen wird nur aus Spielen vor ihrem ersten "
        "Anpfiff vorhergesagt (kein Data Leakage). Grundlage sind die Ergebnisse von 1./2. Bundesliga, den "
        "Stärke-Ligen (erste Ligen Europas, inkl. Meister-/Abstiegsrunden) und der drei Europapokale. Pokalspiele "
        "gehen in die Teamstärken ein, bilden aber keine eigene Ligaebene; Endspiele zählen als neutraler Platz; "
        "abgerechnet wird nach 90 Minuten. Kennzahlen jeweils **kleiner ist besser**. Varianten wurden nur auf der "
        f"Validierung ({label(validation_seasons)}) verglichen, der Test ({label(test_seasons)}) bestätigt.",
        "",
        "| Variante | Beschreibung |",
        "|---|---|",
        "| Basisrate | Häufigkeit von Heimsieg/Remis/Auswärtssieg, Über 2,5 und BTTS in Pokalspielen der letzten 3 Jahre |",
        "| ohne Pokalspiele | gemeinsames Modell nur aus den Ligen – ohne Verbindung zwischen den Ländern gilt jede "
        "Liga als gleich stark (naiver Ansatz) |",
        "| gemeinsam | Ligen und Pokalspiele in einem Modell: alle Teams auf einer Skala |",
        "| gemeinsam + Heimvorteil | wie „gemeinsam“, mit eigenem Heimvorteil für Europapokalspiele |",
        "",
    ]
    subsets = [("alle", lambda d: d)]
    subsets += [(name, lambda d, c=c: d[d["competition"] == c]) for c, name in COMPETITIONS.items()]
    subsets += [(st, lambda d, st=st: d[d["stage"] == st])
                for st in ("Qualifikation", "Play-offs", "Gruppen-/Ligaphase", "K.-o.-Runde")]  # fmt: skip
    subsets += [("Rückspiele", lambda d: d[d["second_leg"]]),
                ("beide Teams aus geladenen Ligen", lambda d: d[d["known"]])]  # fmt: skip
    for period, preds, seasons in (
        ("Validierung", validation, validation_seasons),
        ("Test", test, test_seasons),
    ):
        out += [f"## {period}: {label(seasons)}", "", *_table(preds, subsets), ""]
        base = preds["ohne Pokalspiele"]
        for name in ("gemeinsam", "gemeinsam + Heimvorteil"):
            delta, lo, hi = _delta_ci(base, preds[name])
            verdict = "besser" if hi < 0 else "schlechter" if lo > 0 else "kein signifikanter Unterschied"
            out.append(f"- {name} gegen „ohne Pokalspiele“ (Log-Loss 1X2, alle): **{_fmt(delta)}** "
                       f"[{_fmt(lo)}; {_fmt(hi)}] → **{verdict}**")  # fmt: skip
        out.append("")
    out += ["## Stärke der Ligen (Ebene Angriff + Abwehr, letzter Stand)", "",
            "Höher = stärker. Die Ebene ist der Ausgangswert der Teams einer Liga; einzelne Teams weichen davon ab.",
            "", "| Liga | Ebene |", "|---|---:|"]  # fmt: skip
    out += [f"| {name} | {value:+.2f} |".replace(".", ",") for name, value in league_levels]
    out += ["", "## Auswirkung auf die Bundesliga-Prognosen", "", *bundesliga, ""]
    out += [
        "## Bewertung",
        "",
        "- Ohne Verbindung zwischen den Ländern ist ein Modell aus Ligadaten bei Europapokalspielen nicht besser als "
        "die Basisrate – die Teamstärken der Ligen sind nicht vergleichbar. Erst die Pokalspiele legen alle Teams auf "
        "eine Skala; das senkt den Log-Loss 1X2 deutlich und in jedem Wettbewerb und jeder Runde.",
        "- K.-o.-Runden bleiben am schwersten vorherzusagen (ausgeglichenere Paarungen); Rückspiele hängen zusätzlich "
        "vom Hinspiel ab, das im Modell noch nicht berücksichtigt ist.",
        "- Ein eigener Heimvorteil für Europapokalspiele ist minimal besser und ist Standard (`cup_home_adv`).",
        "- Für die eigenen Ligen bringt der Europa-Pool keinen messbaren Vorteil, kostet aber ein Vielfaches an "
        "Rechenzeit – sie werden weiterhin nur mit verbundenen Ligen (1./2. Bundesliga) gerechnet. Der Europa-Pool "
        "wird für Prognosen von Europapokalspielen verwendet.",
        "",
    ]
    return "\n".join(out)


# --------------------------------------------------------------------------- run


def load_pool(engine, full: list[int], ratings: list[int], cups: list[int]) -> pd.DataFrame:
    from quotenfabrik.analytics.data import load_leagues

    return load_leagues(engine, [*full, *ratings, *cups], all_rounds=set(ratings), cups=set(cups))


def _task(args: tuple) -> tuple:
    """Worker (own process): cup predictions of one variant, or Bundesliga predictions with/without Europe."""
    from quotenfabrik.analytics import joint_eval
    from quotenfabrik.db import get_engine

    kind, key, seasons, full, ratings, cups, params = args
    if kind == "cup":
        pool = load_pool(get_engine(), full, ratings, cups)
        return kind, key, predictions(pool, seasons, params, key[1])
    league_id, europe = key
    pool = load_pool(get_engine(), full, ratings if europe else [], cups if europe else [])
    return kind, key, joint_eval.predictions(pool, league_id, seasons, params, True)


def run(
    full: list[int],
    ratings: list[int],
    cups: list[int],
    validation: list[int],
    test: list[int],
    league_test: list[int],
    params: PoissonParams,
    workers: int = 4,
) -> dict:
    """All predictions for the report (parallel). Returns {"cup": {(period, variant): df}, "league": {...}}."""
    from concurrent.futures import ProcessPoolExecutor

    tasks = [("cup", (period, v), seasons, full, ratings, cups, params)
             for period, seasons in (("validation", validation), ("test", test)) for v in VARIANTS]  # fmt: skip
    tasks += [("league", (lg, europe), league_test, full, ratings, cups, params)
              for lg in full for europe in (False, True)]  # fmt: skip
    out: dict = {"cup": {}, "league": {}}
    with ProcessPoolExecutor(workers) as ex:
        for kind, key, df in ex.map(_task, tasks):
            out[kind][key] = df
    return out


def league_section(results: dict, names: dict[int, str]) -> list[str]:
    """Bundesliga part of the report: own leagues with and without the European pool."""
    lines = ["Test der eigenen Ligen (gleiche Saisons wie in `docs/14_gemeinsames_modell.md`): Modell aus den eigenen "
             "Ligen allein gegen Modell mit allen europäischen Ligen und Pokalspielen.", "",
             "| Liga | n | Log-Loss 1X2 nur eigene Ligen | mit Europa | Differenz | 95-%-Intervall |",
             "|---|---:|---:|---:|---:|---:|"]  # fmt: skip
    for (lg, europe), df in sorted(results["league"].items()):
        if europe:
            continue
        with_europe = results["league"][(lg, True)]
        delta, lo, hi = _delta_ci(df, with_europe)
        lines.append(f"| {names.get(lg, lg)} | {len(df)} | {_fmt(scores(df)['logloss_1x2'])} | "
                     f"{_fmt(scores(with_europe)['logloss_1x2'])} | {_fmt(delta)} | [{_fmt(lo)}; {_fmt(hi)}] |")  # fmt: skip
    return lines
