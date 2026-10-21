"""Calibration of the model probabilities per market (post-hoc, learned from earlier matches only).

For every market / line a logistic recalibration p' = σ(a + b · logit p) is fitted on settled walk-forward
predictions (penalised towards the identity a = 0, b = 1, so small samples change little). Consistency:

* two-way markets (over/under, yes/no): the 'over' / 'yes' side is calibrated, the other side is 1 − p'
* outcome sets (1X2, half-time 1X2, European handicap, highest half, exact goals): every outcome is calibrated,
  then the set is normalised to 1
* double chance and draw no bet are derived from the calibrated 1X2
* single binary selections (both teams score per half, clean sheet): calibrated on their own
* goalscorers: not calibrated (validated separately)

``qf model calibration-eval`` (``docs/20_kalibrierung.md``) compares raw and calibrated predictions season by
season, every season calibrated only with the seasons before it.
"""

from collections.abc import Iterable

import numpy as np
import pandas as pd
from scipy.optimize import minimize

MIN_N = 300  # settled predictions needed for a calibrator
PENALTY = 20.0  # L2 pull towards the identity (in units of observations)
EPS = 1e-6

TWO_WAY = {"over": "under", "yes": "no"}  # calibrated side -> complement
SETS = {"1x2", "ht_1x2", "2h_1x2", "eh", "highest_half", "exact_goals"}
DERIVED = {"dc", "dnb"}


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, EPS, 1 - EPS)
    return np.log(p / (1 - p))


def fit_one(p: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """(a, b) of σ(a + b · logit p) by penalised maximum likelihood."""
    x = _logit(np.asarray(p, float))
    y = np.asarray(y, float)

    def nll(theta):
        a, b = theta
        z = a + b * x
        q = 1 / (1 + np.exp(-z))
        loss = -np.sum(y * np.log(np.clip(q, EPS, 1)) + (1 - y) * np.log(np.clip(1 - q, EPS, 1)))
        loss += 0.5 * PENALTY * (a**2 + (b - 1) ** 2)
        r = q - y
        grad = np.array([r.sum() + PENALTY * a, (r * x).sum() + PENALTY * (b - 1)])
        return loss, grad

    res = minimize(nll, np.array([0.0, 1.0]), jac=True, method="L-BFGS-B")
    return float(res.x[0]), float(res.x[1])


def _key(market: str, selection: str, line) -> tuple:
    return (market, selection, None if line is None or pd.isna(line) else round(float(line), 2))


def _calibrated_selections(df: pd.DataFrame) -> pd.Series:
    """Which rows get their own calibrator (two-way: only the 'over'/'yes' side; derived and scorers: none)."""
    m, s = df["market"], df["selection"]
    two_way_other = s.isin(list(TWO_WAY.values())) & ~m.isin(SETS)
    return ~m.str.startswith("scorer") & ~m.isin(DERIVED) & ~two_way_other


def fit(train: pd.DataFrame) -> dict[tuple, tuple[float, float]]:
    """Calibrators per (market, selection, line) from settled predictions (columns market, selection, line,
    probability, outcome)."""
    d = train[train["outcome"].notna() & _calibrated_selections(train)]
    out = {}
    for (market, selection, line), g in d.groupby(["market", "selection", d["line"].fillna(-1)]):
        if len(g) >= MIN_N:
            out[_key(market, selection, None if line == -1 else line)] = fit_one(
                g["probability"].to_numpy(), g["outcome"].astype(float).to_numpy()
            )
    return out


def apply(preds: pd.DataFrame, calibrators: dict[tuple, tuple[float, float]]) -> pd.Series:
    """Calibrated probabilities for ``preds`` (columns fixture_id, market, selection, line, probability)."""
    if not calibrators or preds.empty:
        return preds["probability"].astype(float)
    df = preds[["fixture_id", "market", "selection", "line", "probability"]].reset_index(drop=True).copy()
    df["lk"] = df["line"].astype(float).round(2).fillna(-1.0)
    cal = pd.DataFrame(
        [(m, s, -1.0 if ln is None else ln, a, b) for (m, s, ln), (a, b) in calibrators.items()],
        columns=["market", "selection", "lk", "a", "b"],
    )
    df = df.merge(cal, on=["market", "selection", "lk"], how="left")
    has = df["a"].notna().to_numpy()
    p = df["probability"].astype(float).to_numpy()
    z = df["a"].to_numpy(float) + df["b"].to_numpy(float) * _logit(p)
    df["p"] = np.where(has, 1 / (1 + np.exp(-np.where(has, z, 0.0))), p)
    df["calibrated"] = has

    # two-way markets: the other side is the complement of the calibrated side
    other = df["selection"].isin(list(TWO_WAY.values())) & ~df["market"].isin(SETS)
    sides = df[df["selection"].isin(list(TWO_WAY)) & df["calibrated"]][
        ["fixture_id", "market", "lk", "selection", "p"]
    ]
    sides = sides.assign(selection=sides["selection"].map(TWO_WAY)).rename(columns={"p": "p_side"})
    df = df.merge(sides, on=["fixture_id", "market", "lk", "selection"], how="left")
    df.loc[other & df["p_side"].notna(), "p"] = 1 - df.loc[other & df["p_side"].notna(), "p_side"]

    # outcome sets: normalise
    sets = df["market"].isin(SETS)
    if sets.any():
        total = df[sets].groupby(["fixture_id", "market", "lk"])["p"].transform("sum")
        df.loc[sets, "p"] = df.loc[sets, "p"] / total

    # double chance / draw no bet from the calibrated 1X2
    hda = df[df["market"] == "1x2"].pivot_table(index="fixture_id", columns="selection", values="p")
    if {"H", "D", "A"} <= set(hda.columns):
        derived = {
            ("dc", "1X"): hda["H"] + hda["D"], ("dc", "X2"): hda["D"] + hda["A"], ("dc", "12"): hda["H"] + hda["A"],
            ("dnb", "H"): hda["H"] / (hda["H"] + hda["A"]), ("dnb", "A"): hda["A"] / (hda["H"] + hda["A"]),
        }  # fmt: skip
        for (m, s), values in derived.items():
            rows = (df["market"] == m) & (df["selection"] == s)
            df.loc[rows, "p"] = df.loc[rows, "fixture_id"].map(values).fillna(df.loc[rows, "p"])
    return pd.Series(df["p"].clip(EPS, 1 - EPS).to_numpy(), index=preds.index)


# --------------------------------------------------------------------------- evaluation


def _scores(p: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    p = np.clip(p, EPS, 1 - EPS)
    logloss = float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
    brier = float(np.mean((p - y) ** 2))
    bins = np.minimum((p * 10).astype(int), 9)
    ece = float(sum(abs(p[bins == b].mean() - y[bins == b].mean()) * (bins == b).mean() for b in range(10)
                    if (bins == b).any()))  # fmt: skip
    return logloss, brier, ece


def walk_forward(preds: pd.DataFrame, seasons: Iterable[int]) -> pd.DataFrame:
    """Raw and calibrated probability for every settled prediction of ``seasons``; each season is calibrated
    with all earlier seasons."""
    preds = preds[~preds["market"].str.startswith("scorer") & preds["outcome"].notna()]
    out = []
    for season in seasons:
        train, test = preds[preds["season"] < season], preds[preds["season"] == season]
        if test.empty:
            continue
        cal = fit(train)
        if not cal:  # nothing to learn from yet (first season)
            continue
        out.append(test.assign(calibrated=apply(test, cal).to_numpy()))
    return pd.concat(out, ignore_index=True) if out else preds.iloc[0:0]


def summary(results: pd.DataFrame, group_of) -> pd.DataFrame:
    """Log loss, Brier and ECE raw vs. calibrated per market group (all selections of the group)."""
    rows = []
    results = results.assign(group=results["market"].map(group_of))
    for group, g in results.groupby("group"):
        y = g["outcome"].astype(float).to_numpy()
        raw, cal = _scores(g["probability"].to_numpy(), y), _scores(g["calibrated"].to_numpy(), y)
        diff = -(
            y * np.log(np.clip(g["calibrated"], EPS, 1))
            + (1 - y) * np.log(np.clip(1 - g["calibrated"], EPS, 1))
        ) + (
            y * np.log(np.clip(g["probability"], EPS, 1))
            + (1 - y) * np.log(np.clip(1 - g["probability"], EPS, 1))
        )
        rng = np.random.default_rng(0)
        fixtures = g["fixture_id"].to_numpy()
        per_fixture = pd.Series(diff.to_numpy()).groupby(fixtures).mean().to_numpy()  # matches are the units
        boots = [per_fixture[rng.integers(0, len(per_fixture), len(per_fixture))].mean() for _ in range(1000)]
        rows.append({"group": group, "n": len(g), "logloss_raw": raw[0], "logloss_cal": cal[0], "brier_raw": raw[1],
                     "brier_cal": cal[1], "ece_raw": raw[2], "ece_cal": cal[2],
                     "delta": float(per_fixture.mean()), "ci": (float(np.percentile(boots, 2.5)),
                                                               float(np.percentile(boots, 97.5)))})  # fmt: skip
    return pd.DataFrame(rows)


def calibration_rows(results: pd.DataFrame, market: str, selection: str, line=None) -> pd.DataFrame:
    """Reliability table (10 classes) raw vs. calibrated for one selection."""
    g = results[(results["market"] == market) & (results["selection"] == selection)]
    if line is not None:
        g = g[g["line"].round(2) == line]
    bins = pd.cut(g["probability"], np.linspace(0, 1, 11))
    return g.groupby(bins, observed=True).agg(
        n=("outcome", "size"), raw=("probability", "mean"), calibrated=("calibrated", "mean"),
        actual=("outcome", lambda s: s.astype(float).mean()),
    )  # fmt: skip


# --------------------------------------------------------------------------- data and report

_BACKTEST_SQL = """
    select p.fixture_id, f.season, p.market, p.selection, p.line::float as line, p.probability, p.outcome
    from analytics.predictions p
    join analytics.model_runs r on r.id = p.model_run_id
    join core.fixtures f on f.id = p.fixture_id
    where r.kind = 'backtest' and r.league_id = :league and p.market not like 'scorer%'
      and r.id = (select max(id) from analytics.model_runs where kind = 'backtest' and league_id = :league)
"""


def load_backtest(engine, league_id: int) -> pd.DataFrame:
    """Settled walk-forward predictions of the latest backtest run of a league (without goalscorers)."""
    from sqlalchemy import text

    with engine.connect() as conn:
        d = pd.read_sql(text(_BACKTEST_SQL), conn, params={"league": league_id})
    return d[d["outcome"].notna()].assign(outcome=lambda x: x["outcome"].astype(float))


GROUP_LABELS = {"1x2": "Spielausgang (1X2, DC, DNB, Handicap)", "totals": "Tore gesamt", "team_totals": "Tore pro Team",
                "halves": "Halbzeiten"}  # fmt: skip


def _f(x: float, d: int = 4) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def _s(x: float, d: int = 4) -> str:
    return f"{x:+.{d}f}".replace(".", ",").replace("-", "−")


def report(results: dict[str, pd.DataFrame], group_of) -> str:
    """``results``: league name -> walk_forward() output."""
    from datetime import UTC, datetime

    out = [
        "# 20 – Kalibrierung der Prognosen",
        "",
        f"Automatisch erzeugt von `qf model calibration-eval` am {datetime.now(UTC):%d.%m.%Y %H:%M} UTC.",
        "",
        "**Verfahren:** Je Markt und Linie eine logistische Nachkorrektur p' = σ(a + b · logit p), gelernt aus den "
        "abgerechneten rückwirkenden Prognosen **früherer Saisons** (jede Saison wird nur mit den Saisons davor "
        f"kalibriert, mindestens {MIN_N} Prognosen je Markt, zur Identität gezogen). Über/Unter ergeben weiter 100 %, "
        "1X2 ebenso; Doppelte Chance und Draw No Bet folgen aus dem korrigierten 1X2. Torschützen bleiben unverändert.",
        "",
        "**Kennzahlen** (kleiner = besser): Log-Loss, Brier-Score und ECE (mittlerer Kalibrierungsfehler: Abstand "
        "zwischen vorhergesagter und eingetretener Quote über 10 Klassen). Δ = Log-Loss kalibriert − roh je Spiel, "
        "mit 95-%-Bootstrap-Intervall über Spiele.",
    ]
    for league, res in results.items():
        if res.empty:
            continue
        seasons = sorted(res["season"].unique())
        out += ["", f"## {league} (Testsaisons {seasons[0]}/{(seasons[0] + 1) % 100:02d}–{seasons[-1]}/{(seasons[-1] + 1) % 100:02d})", "",
                "| Marktgruppe | Prognosen | Log-Loss roh | kalibriert | Δ (95 %) | Brier roh | kalibriert | ECE roh | kalibriert |",
                "|---|---:|---:|---:|---|---:|---:|---:|---:|"]  # fmt: skip
        for r in summary(res, group_of).itertuples():
            lo, hi = r.ci
            sig = " ✓" if hi < 0 else " ✗" if lo > 0 else ""
            out.append(f"| {GROUP_LABELS.get(r.group, r.group)} | {r.n} | {_f(r.logloss_raw)} | {_f(r.logloss_cal)} | "
                       f"{_s(r.delta)} ({_s(lo)} … {_s(hi)}){sig} | {_f(r.brier_raw)} | {_f(r.brier_cal)} | "
                       f"{_f(r.ece_raw * 100, 2)} % | {_f(r.ece_cal * 100, 2)} % |")  # fmt: skip
        for title, (m, s, ln) in (("Heimsieg", ("1x2", "H", None)), ("Über 2,5", ("ou_ft", "over", 2.5)),
                                  ("Beide treffen", ("btts", "yes", None))):  # fmt: skip
            t = calibration_rows(res, m, s, ln)
            if t.empty:
                continue
            out += ["", f"**{title}** – vorhergesagt roh / kalibriert gegen eingetreten", "",
                    "| Klasse (roh) | n | roh | kalibriert | eingetreten |", "|---|---:|---:|---:|---:|"]  # fmt: skip
            for b, r in t.iterrows():
                out.append(f"| {b} | {int(r['n'])} | {_f(r['raw'] * 100, 1)} % | {_f(r['calibrated'] * 100, 1)} % | "
                           f"{_f(r['actual'] * 100, 1)} % |")  # fmt: skip
    out += ["", "✓ = signifikant besser, ✗ = signifikant schlechter.", ""]
    return "\n".join(out)
