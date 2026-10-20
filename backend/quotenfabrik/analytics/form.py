"""Current form of a team: its last matches in all competitions compared with the model's expectation.

Raw form (points of the last matches) mostly mirrors team strength, which the model already knows. The form
pattern therefore measures points **above or below expectation**: per match, points minus expected points
from the walk-forward prediction made before that match (3 × P(win) + P(draw)). Only matches before kickoff
are used (no leakage); matches without a prediction (results-only leagues) count for the table of recent
results but not for the expectation. ``qf model form-eval`` checks whether this form carries information the
model does not have yet (``docs/17_form.md``).
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sqlalchemy import Engine, text

FINISHED = ("FT", "AET", "PEN", "AWD", "WO")
FORM_N = 6  # matches of the form pattern
LIST_N = 10  # matches shown on the detail page
MIN_EXPECTED = 4  # matches with a prediction needed for a form value
SIGNAL = 0.5  # points per match above / below expectation for a signal


# --------------------------------------------------------------------------- data

_HISTORY_SQL = """
    with tf as (
        select f.id as fixture_id, f.kickoff_utc as kickoff, f.league_id, f.round, f.home_team_id as home_id,
               f.away_team_id as away_id, f.ft_home as hg, f.ft_away as ag
        from core.fixtures f
        where f.status = any(:fin) and f.ft_home is not null and f.kickoff_utc < :before
          and (cast(:teams as int[]) is null or f.home_team_id = any(:teams) or f.away_team_id = any(:teams))
    ), runs as (
        select distinct on (p.fixture_id) p.fixture_id, p.model_run_id
        from analytics.predictions p
        join analytics.model_runs r on r.id = p.model_run_id
        join tf on tf.fixture_id = p.fixture_id
        where p.market = '1x2' and p.selection = 'H' and r.kind = any(:kinds)
          and (r.kind = 'backtest' or coalesce(p.predicted_at, r.as_of) <= tf.kickoff)
        order by p.fixture_id, (r.kind = 'forecast') desc, r.id desc
    )
    select tf.*, l.name as league_name,
           max(p.probability) filter (where p.selection = 'H') as p_h,
           max(p.probability) filter (where p.selection = 'D') as p_d,
           max(p.probability) filter (where p.selection = 'A') as p_a
    from tf
    left join core.leagues l on l.id = tf.league_id
    left join runs on runs.fixture_id = tf.fixture_id
    left join analytics.predictions p on p.model_run_id = runs.model_run_id and p.fixture_id = tf.fixture_id
                                      and p.market = '1x2'
    group by tf.fixture_id, tf.kickoff, tf.league_id, tf.round, tf.home_id, tf.away_id, tf.hg, tf.ag, l.name
"""


def load_history(
    engine: Engine,
    before: pd.Timestamp,
    teams: list[int] | None = None,
    kinds: tuple[str, ...] = ("forecast", "backtest"),
) -> pd.DataFrame:
    """Finished matches before ``before`` (all competitions) with the 1X2 prediction made before kickoff.

    ``kinds=("backtest",)`` uses walk-forward backtests only (evaluation)."""
    params = {"fin": list(FINISHED), "before": before.to_pydatetime(), "kinds": list(kinds),
              "teams": [int(t) for t in teams] if teams else None}  # fmt: skip
    with engine.connect() as conn:
        frame = pd.read_sql(text(_HISTORY_SQL), conn, params=params)
    frame["kickoff"] = pd.to_datetime(frame["kickoff"], utc=True)
    return frame.sort_values(["kickoff", "fixture_id"], ignore_index=True)


def team_rows(history: pd.DataFrame) -> pd.DataFrame:
    """One row per team and match: goals, points and expected points (NaN without prediction)."""
    common = ["fixture_id", "kickoff", "league_id", "league_name", "round"]
    home = history[common].assign(
        team=history["home_id"], opp=history["away_id"], venue="home", gf=history["hg"], ga=history["ag"],
        xpts=3 * history["p_h"] + history["p_d"], p_win=history["p_h"],
    )  # fmt: skip
    away = history[common].assign(
        team=history["away_id"], opp=history["home_id"], venue="away", gf=history["ag"], ga=history["hg"],
        xpts=3 * history["p_a"] + history["p_d"], p_win=history["p_a"],
    )  # fmt: skip
    rows = pd.concat([home, away], ignore_index=True).sort_values(
        ["kickoff", "fixture_id"], ignore_index=True
    )
    rows["points"] = np.select([rows["gf"] > rows["ga"], rows["gf"] == rows["ga"]], [3, 1], 0)
    rows["result"] = np.select([rows["gf"] > rows["ga"], rows["gf"] == rows["ga"]], ["S", "U"], "N")
    rows["residual"] = rows["points"] - rows["xpts"]
    return rows


# --------------------------------------------------------------------------- form of one team


@dataclass
class Form:
    matches: int
    ppg: float | None  # points per match
    goal_diff: float | None  # goal difference per match
    expected_ppg: float | None  # model expectation for the same matches (only those with a prediction)
    residual: float | None  # points minus expected points per match (None below MIN_EXPECTED)
    n_expected: int
    sequence: str  # e.g. "SSUNS" (oldest first)
    signal: str | None  # 'high' (above expectation) / 'low' / None


def team_form(rows: pd.DataFrame, n: int = FORM_N) -> Form:
    """Form over the last ``n`` matches of one team (``rows`` from :func:`team_rows`, before kickoff)."""
    last = rows.sort_values("kickoff").tail(n)
    known = last[last["xpts"].notna()]
    residual = float(known["residual"].mean()) if len(known) >= MIN_EXPECTED else None
    signal = None
    if residual is not None and residual >= SIGNAL:
        signal = "high"
    elif residual is not None and residual <= -SIGNAL:
        signal = "low"
    return Form(
        matches=len(last),
        ppg=float(last["points"].mean()) if len(last) else None,
        goal_diff=float((last["gf"] - last["ga"]).mean()) if len(last) else None,
        expected_ppg=float(known["xpts"].mean()) if len(known) >= MIN_EXPECTED else None,
        residual=residual,
        n_expected=len(known),
        sequence="".join(last["result"]),
        signal=signal,
    )


def rolling_form(rows: pd.DataFrame, n: int = FORM_N) -> pd.DataFrame:
    """Form residual and points per match of each team *before* every match (for the evaluation)."""
    rows = rows.sort_values(["team", "kickoff", "fixture_id"]).copy()
    g = rows.groupby("team", sort=False)
    prev_res = g["residual"].shift(1)
    prev_pts = g["points"].shift(1)
    rows["form_n"] = (
        prev_res.notna().groupby(rows["team"]).transform(lambda s: s.rolling(n, min_periods=1).sum())
    )
    rows["form_residual"] = prev_res.groupby(rows["team"]).transform(
        lambda s: s.rolling(n, min_periods=1).mean()
    )
    rows.loc[rows["form_n"] < MIN_EXPECTED, "form_residual"] = np.nan
    rows["form_ppg"] = prev_pts.groupby(rows["team"]).transform(lambda s: s.rolling(n, min_periods=n).mean())
    return rows


# --------------------------------------------------------------------------- evaluation


def _corr_ci(x: pd.Series, y: pd.Series) -> tuple[float, float, float, int]:
    """Pearson correlation with a 95 % confidence interval (Fisher z)."""
    n = len(x)
    r = float(np.corrcoef(x, y)[0, 1])
    z, se = np.arctanh(r), 1 / np.sqrt(max(n - 3, 1))
    return r, float(np.tanh(z - 1.96 * se)), float(np.tanh(z + 1.96 * se)), n


def evaluate(rows: pd.DataFrame) -> dict:
    """Does form before a match explain the points *above expectation* in that match?"""
    data = rolling_form(rows)
    target = data[data["xpts"].notna() & data["form_residual"].notna()]
    res = {"n": len(target)}
    if len(target) < 50:
        return res
    res["corr_residual"] = _corr_ci(target["form_residual"], target["residual"])
    raw = target[target["form_ppg"].notna()]
    res["corr_ppg"] = _corr_ci(raw["form_ppg"], raw["residual"])
    bins = [-np.inf, -SIGNAL, -0.2, 0.2, SIGNAL, np.inf]
    labels = ["deutlich unter Erwartung", "leicht darunter", "wie erwartet", "leicht darüber",
              "deutlich über Erwartung"]  # fmt: skip
    target = target.assign(bucket=pd.cut(target["form_residual"], bins, labels=labels))
    res["buckets"] = [
        {"bucket": str(b), "n": len(g), "points": float(g["points"].mean()), "xpts": float(g["xpts"].mean()),
         "residual": float(g["residual"].mean()),
         "residual_se": float(g["residual"].std(ddof=1) / np.sqrt(len(g))) if len(g) > 1 else None,
         "win": float((g["points"] == 3).mean()), "p_win": float(g["p_win"].mean())}
        for b, g in target.groupby("bucket", observed=True)
    ]  # fmt: skip
    res["by_competition"] = [
        {"league": str(name), "n": len(g), "corr": _corr_ci(g["form_residual"], g["residual"])}
        for name, g in target.groupby("league_name")
        if len(g) >= 200
    ]
    return res


def _pct(x: float) -> str:
    return f"{x * 100:.1f} %".replace(".", ",")


def _num(x: float, digits: int = 2) -> str:
    return f"{x:+.{digits}f}".replace(".", ",").replace("+-", "−").replace("-", "−")


def report(result: dict) -> str:
    from datetime import UTC, datetime

    out = [
        "# 17 – Form-Pattern: Punkte über oder unter der Modell-Erwartung",
        "",
        f"Automatisch erzeugt von `qf model form-eval` am {datetime.now(UTC):%d.%m.%Y %H:%M} UTC.",
        "",
        f"**Form** = Mittel aus (Punkte − erwartete Punkte) der letzten {FORM_N} Pflichtspiele in allen "
        "Wettbewerben; erwartete Punkte = 3 × P(Sieg) + P(Remis) aus der rückwirkenden Prognose vor dem jeweiligen "
        f"Spiel (Walk-Forward). Mindestens {MIN_EXPECTED} Spiele mit Prognose. Signal ab "
        f"±{str(SIGNAL).replace('.', ',')} Punkten pro Spiel.",
        "",
        "**Frage:** Holt eine Mannschaft, die zuletzt mehr Punkte geholt hat als erwartet, auch im nächsten "
        "Spiel mehr als das Modell erwartet? Dann wüsste die Form etwas, das das Modell noch nicht weiß.",
        "",
    ]
    if "corr_residual" not in result:
        return "\n".join([*out, f"Zu wenige Spiele ({result['n']}) für eine Auswertung.", ""])
    r, lo, hi, n = result["corr_residual"]
    rp, lop, hip, np_ = result["corr_ppg"]
    out += [
        "## Zusammenhang mit dem nächsten Spiel",
        "",
        "| Merkmal vor dem Spiel | Spiele | Korrelation mit (Punkte − Erwartung) im Spiel | 95-%-Intervall |",
        "|---|---:|---:|---|",
        f"| Form über/unter Erwartung (letzte {FORM_N}) | {n} | {_num(r, 3)} | {_num(lo, 3)} … {_num(hi, 3)} |",
        f"| Punkte pro Spiel (letzte {FORM_N}, roh) | {np_} | {_num(rp, 3)} | {_num(lop, 3)} … {_num(hip, 3)} |",
        "",
        "## Nach Form-Gruppe",
        "",
        "| Form vor dem Spiel | Spiele | Punkte | Modell erwartet | Differenz | Siegquote | Modell |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for b in result["buckets"]:
        se = f" (± {b['residual_se']:.2f})".replace(".", ",") if b["residual_se"] else ""
        out.append(f"| {b['bucket']} | {b['n']} | {b['points']:.2f} | {b['xpts']:.2f} | {_num(b['residual'])}{se} | "
                   f"{_pct(b['win'])} | {_pct(b['p_win'])} |".replace(".", ","))  # fmt: skip
    if result["by_competition"]:
        out += ["", "## Je Wettbewerb", "", "| Wettbewerb | Spiele | Korrelation | 95-%-Intervall |",
                "|---|---:|---:|---|"]  # fmt: skip
        for c in result["by_competition"]:
            cr, clo, chi, _ = c["corr"]
            out.append(f"| {c['league']} | {c['n']} | {_num(cr, 3)} | {_num(clo, 3)} … {_num(chi, 3)} |")
    significant = lo > 0 or hi < 0
    out += ["", "## Bewertung", ""]
    if significant and r > 0:
        out.append("- Die Form trägt zusätzliche Information: Teams über Erwartung bleiben im Mittel leicht über "
                   "Erwartung. Der Effekt ist klein – als Hinweis nutzen, nicht als eigene Wette.")  # fmt: skip
    elif significant and r < 0:
        out.append("- Gegenläufig: Teams über Erwartung fallen danach eher unter die Erwartung (Rückkehr zum "
                   "Mittel). Gute Form ist also eher Glück, das das Modell zu Recht nicht übernimmt.")  # fmt: skip
    else:
        out.append("- Kein messbarer Zusatznutzen: Ob ein Team zuletzt über oder unter Erwartung lag, sagt "
                   "nichts über das nächste Spiel, das das Modell nicht schon weiß. Das Modell gewichtet jüngere "
                   "Spiele bereits stärker (Zeitgewichtung).")  # fmt: skip
    out += [
        "- Die Form wird auf der Detailseite als Pattern angezeigt (mit den letzten 10 Spielen). Sie fließt nicht "
        "in Prognosen oder Tipps ein, solange sie hier keinen klaren Zusatznutzen zeigt.",
        "",
    ]
    return "\n".join(out)
