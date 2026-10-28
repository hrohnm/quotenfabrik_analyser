"""Value tips: selections where our probability times the Betano odds clearly exceeds 1.

Independent of the 3 picks per fixture. Candidates are the common markets of the picks (``picks.ALLOWED``:
1X2, double chance, goals, team goals, halves, both teams score, clean sheet; x.5 lines only). Our
probability is the Tippschein decision model where it covers the market (winner, over 1.5 / 2.5, both teams
score, goal per half; everything we know), otherwise the goal model. Pinnacle without margin is sharper than
our model alone (backtest), so the probability used for the edge is a blend: ``value.model_weight`` × ours +
rest × Pinnacle (selections without a complete Pinnacle market are skipped).

A tip is a value tip if ``edge`` = probability × Betano odds − 1 ≥ ``value.min_edge``, probability ≥
``value.min_p`` and odds ≤ ``value.max_odds``; at most ``value.per_fixture`` per fixture (largest edge first).
The backtest takes the Betano and Pinnacle prices at the time the tip would have been shown (like the CLV:
frozen day, else the forecast; backtest: first kickoff of the matchday), settles at that price and measures
the CLV against the closing price. Shown tips are frozen per day (``analytics.value_tips``) for an honest live
record.
"""

from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from decimal import Decimal

import numpy as np
import pandas as pd
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from quotenfabrik.analytics import clv
from quotenfabrik.analytics.bookmaker_odds import KEY, odds_table
from quotenfabrik.analytics.picks import is_candidate

MIN_LEAD_H = 1.0
# decision model key per (market, line): its probabilities replace the goal model's
DECISION_MARKETS = {
    ("1x2", None): "winner", ("ou_ft", 1.5): "o15", ("ou_ft", 2.5): "o25", ("btts", None): "btts",
    ("ou_1h", 0.5): "goal_1h", ("ou_2h", 0.5): "goal_2h",
}  # fmt: skip


@dataclass(frozen=True)
class ValueSettings:
    model_weight: float = 0.25
    min_edge: float = 0.02
    min_p: float = 0.3
    max_odds: float = 4.0
    per_fixture: int = 2


_SQL = """
    with runs as ({runs})
    select p.fixture_id, runs.model_run_id, runs.kind, f.league_id, f.season, f.kickoff_utc as kickoff,
           p.market_group, p.market, p.selection, p.line::float as line, p.probability, p.outcome,
           greatest(runs.predicted_at, coalesce(z.frozen_at, runs.predicted_at)) as taken_at
    from analytics.predictions p
    join runs on runs.model_run_id = p.model_run_id and runs.fixture_id = p.fixture_id
    join core.fixtures f on f.id = p.fixture_id
    left join analytics.frozen_runs z on z.fixture_id = p.fixture_id and z.model_run_id = p.model_run_id
    where p.market not like 'scorer%'
      and exists (select 1 from core.oddspapi_fixtures o where o.fixture_id = p.fixture_id) {extra}
"""


def load_candidates(engine: Engine, where: str, extra: str = "", **params) -> pd.DataFrame:
    """Predictions of the chosen run (common markets) of fixtures with Betano prices, decision model
    applied."""
    from quotenfabrik.analytics import decision_runs
    from quotenfabrik.api.data import chosen_runs_cte

    with engine.connect() as conn:
        rows = pd.read_sql(text(_SQL.format(runs=chosen_runs_cte(where), extra=extra)), conn, params=params)
    rows = rows[[is_candidate(m, ln) for m, ln in zip(rows["market"], rows["line"], strict=True)]].copy()
    if rows.empty:
        return rows
    for col in ("kickoff", "taken_at"):
        rows[col] = pd.to_datetime(rows[col], utc=True)
    rows["model_probability"] = rows["probability"]
    stacked = decision_runs.stacked(engine, where, **params)
    if not stacked.empty:
        cols = [stacked[c] for c in ("fixture_id", "decision", "probabilities")]
        probs = {(int(f), k): d for f, k, d in zip(*cols, strict=True)}
        new = []
        keys = [rows[c] for c in ("fixture_id", "market", "line", "selection", "probability")]
        for f, m, ln, s, p in zip(*keys, strict=True):
            key = DECISION_MARKETS.get((m, None if pd.isna(ln) else float(ln)))
            d = probs.get((int(f), key)) if key else None
            new.append(float(d[s]) if d and s in d else p)
        rows["probability"] = new
    return rows.reset_index(drop=True)


def with_prices(engine: Engine, rows: pd.DataFrame, at_taken: bool = True) -> pd.DataFrame:
    """Betano (``taken``) and Pinnacle without margin (``fair_taken``) at the time the tip is shown, closing
    prices (``close``, ``fair_close``) and the CLV; ``at_taken=False``: current prices (upcoming fixtures)."""
    if rows.empty:
        return rows
    if at_taken:
        taken_at = rows.groupby("fixture_id")["taken_at"].min()
        early, late = clv.price_tables(engine, {int(f): t.to_pydatetime() for f, t in taken_at.items()})
        return clv.attach_prices(rows, early, late)
    now = odds_table(engine, sorted(int(f) for f in rows["fixture_id"].unique()))
    now = now[[*KEY, "betano", "fair"]].rename(columns={"betano": "taken", "fair": "fair_taken"})
    m = rows.astype({"line": float}).merge(now, on=KEY, how="inner").dropna(subset=["taken"])
    m["close"], m["fair_close"], m["clv"] = m["taken"], m["fair_taken"], np.nan
    return m.reset_index(drop=True)


def blend(rows: pd.DataFrame, s: ValueSettings) -> pd.DataFrame:
    """``p_model`` (ours), ``p_market`` (Pinnacle), blended ``probability`` and ``edge``; rows without a
    Pinnacle reference are dropped."""
    if rows.empty:
        return rows.assign(p_model=[], p_market=[], edge=[])
    m = rows.dropna(subset=["fair_taken"]).copy()
    m["p_model"] = m["probability"] if "p_model" not in m else m["p_model"]
    m["p_market"] = m["fair_taken"]
    m["probability"] = s.model_weight * m["p_model"] + (1 - s.model_weight) * m["p_market"]
    m["edge"] = m["probability"] * m["taken"] - 1
    return m


def select(rows: pd.DataFrame, s: ValueSettings) -> pd.DataFrame:
    """Value tips among blended, priced candidates."""
    if rows.empty:
        return rows
    ok = (rows["edge"] >= s.min_edge) & (rows["probability"] >= s.min_p) & (rows["taken"] <= s.max_odds)
    v = rows[ok].sort_values(["fixture_id", "edge"], ascending=[True, False])
    return v.groupby("fixture_id", sort=False).head(s.per_fixture).reset_index(drop=True)


def summarize(tips: pd.DataFrame) -> dict:
    """Result at the odds taken (settled tips), CLV and a fixture-clustered bootstrap interval of the ROI."""
    settled = tips.dropna(subset=["outcome"]) if len(tips) else tips
    if settled.empty:
        return {"n": 0, "fixtures": 0}
    hit = settled["outcome"].astype(bool)
    profit = np.where(hit, settled["taken"] - 1, -1.0)
    per_fixture = pd.Series(profit, index=settled.index).groupby(settled["fixture_id"]).agg(["sum", "size"])
    sums, counts = per_fixture["sum"].to_numpy(), per_fixture["size"].to_numpy()
    rng = np.random.default_rng(0)
    boot = []
    for _ in range(1000):
        idx = rng.integers(0, len(sums), len(sums))
        boot.append(sums[idx].sum() / counts[idx].sum())
    c = settled.dropna(subset=["clv"]) if "clv" in settled else settled.iloc[0:0]
    return {
        "n": int(len(settled)),
        "fixtures": int(settled["fixture_id"].nunique()),
        "odds": float(settled["taken"].mean()),
        "hit_rate": float(hit.mean()),
        "expected": float(settled["probability"].mean()),
        "edge": float(settled["edge"].mean()),
        "roi": float(profit.mean()),
        "roi_ci": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
        "profit": float(profit.sum()),
        "clv": float(c["clv"].mean()) if len(c) else None,
        "beat_close": float((settled["taken"] > settled["close"]).mean()) if "close" in settled else None,
    }


def backtest_rows(engine: Engine, leagues: list[int]) -> pd.DataFrame:
    """Priced candidates of finished fixtures with a Betano history (tip shown at least an hour before
    kickoff)."""
    rows = load_candidates(
        engine, "and f.league_id = any(:leagues)", "and f.kickoff_utc < now()", leagues=leagues
    )
    if rows.empty:
        return rows
    rows = rows[(rows["kickoff"] - rows["taken_at"]).dt.total_seconds() >= MIN_LEAD_H * 3600]
    return with_prices(engine, rows.assign(p_model=rows["probability"]))


def backtest(engine: Engine, leagues: list[int], s: ValueSettings) -> dict:
    """Result of the settings, a grid over model weight and minimum edge, and the result per market group."""
    from quotenfabrik.api.labels import GROUP_LABELS

    rows = backtest_rows(engine, leagues)
    if rows.empty:
        return {"candidates": 0}
    tips = select(blend(rows, s), s)
    grid = []
    for w in (0.0, 0.25, 0.5, 0.75, 1.0):
        b = blend(rows, replace(s, model_weight=w))
        for e in (0.0, 0.02, 0.04, 0.06, 0.1):
            grid.append(
                {
                    "model_weight": w,
                    "min_edge": e,
                    **summarize(select(b, replace(s, model_weight=w, min_edge=e))),
                }
            )
    b = blend(rows, s)
    y = b["outcome"].dropna().astype(float)

    def log_loss(p):  # noqa: E306
        p = np.clip(p.loc[y.index], 1e-6, 1 - 1e-6)
        return float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())

    groups = [
        {"group": g, "label": GROUP_LABELS.get(g, g), **summarize(x)} for g, x in tips.groupby("market_group")
    ]
    return {
        "candidates": int(len(rows)),
        "fixtures": int(rows["fixture_id"].nunique()),
        "from": rows["kickoff"].min().isoformat(),
        "to": rows["kickoff"].max().isoformat(),
        "log_loss": {
            "model": log_loss(b["p_model"]),
            "market": log_loss(b["p_market"]),
            "blend": log_loss(b["probability"]),
        },  # fmt: skip
        "settings": s.__dict__,
        "result": summarize(tips),
        "groups": groups,
        "grid": grid,
    }


# --------------------------------------------------------------------------- live: day, freeze, record


def current_tips(engine: Engine, fixture_ids: list[int], s: ValueSettings) -> pd.DataFrame:
    """Value tips of upcoming fixtures at the current prices."""
    if not fixture_ids:
        return pd.DataFrame()
    rows = load_candidates(
        engine, "and p.fixture_id = any(:ids)", "and f.kickoff_utc > now()", ids=fixture_ids
    )
    if rows.empty:
        return rows
    priced = with_prices(engine, rows.assign(p_model=rows["probability"]), at_taken=False)
    return select(blend(priced, s), s)


def frozen(engine: Engine, where: str = "true", **params) -> pd.DataFrame:
    """Frozen value tips with their result (outcome of the prediction of the chosen run)."""
    from quotenfabrik.api.data import chosen_runs_cte

    runs = chosen_runs_cte("and p.fixture_id in (select fixture_id from analytics.value_tips)")
    sql = f"""with runs as ({runs})
              select v.day, v.fixture_id, v.market, v.selection, v.line::float as line, v.probability,
                     v.p_model, v.p_market, v.odds::float as taken, v.edge, v.frozen_at, p.outcome,
                     p.market_group
              from analytics.value_tips v
              left join runs on runs.fixture_id = v.fixture_id
              left join analytics.predictions p on p.model_run_id = runs.model_run_id
                    and p.fixture_id = v.fixture_id and p.market = v.market and p.selection = v.selection
                    and p.line is not distinct from v.line
              where {where}"""
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


def _key(r: dict) -> tuple:
    return r["fixture_id"], r["market"], r["selection"], None if r["line"] is None else float(r["line"])


def freeze(engine: Engine, day: date, now: datetime | None = None) -> int:
    """Stores the value tips of the day's fixtures that have not started (once per selection)."""
    from quotenfabrik import app_config
    from quotenfabrik.models import ValueTip

    now = now or datetime.now(UTC)
    with engine.connect() as conn:
        ids = [int(r[0]) for r in conn.execute(text(
            """select id from core.fixtures where (kickoff_utc at time zone 'Europe/Berlin')::date = :day
               and kickoff_utc > :now and league_id = any(:leagues)"""),
            {"day": day, "now": now, "leagues": app_config.shown_league_ids()})]  # fmt: skip
    tips = current_tips(engine, ids, app_config.value_settings())
    if tips.empty:
        return 0
    rows = [
        {
            "day": day, "fixture_id": int(t.fixture_id), "market": t.market, "selection": t.selection,
            "line": None if pd.isna(t.line) else Decimal(str(t.line)), "probability": float(t.probability),
            "p_model": float(t.p_model), "p_market": None if pd.isna(t.p_market) else float(t.p_market),
            "odds": Decimal(str(round(float(t.taken), 2))), "edge": float(t.edge),
        }
        for t in tips.itertuples()
    ]  # fmt: skip
    with Session(engine) as session:
        stored = session.execute(
            text("""select fixture_id, market, selection, line from analytics.value_tips
                    where fixture_id = any(:ids)"""),
            {"ids": ids},
        )
        existing = {(int(f), m, sel, None if ln is None else float(ln)) for f, m, sel, ln in stored}
        new = [r for r in rows if _key(r) not in existing]
        session.add_all(ValueTip(**r) for r in new)
        session.commit()
    return len(new)


def live_record(engine: Engine) -> dict:
    """Result of the frozen value tips (settled at the frozen Betano odds)."""
    tips = frozen(engine)
    return summarize(tips.assign(close=np.nan)) if len(tips) else {"n": 0, "fixtures": 0}


# --------------------------------------------------------------------------- report


def _pct(x, digits: int = 1, sign: bool = False) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    return f"{x * 100:{'+' if sign else ''}.{digits}f} %".replace(".", ",")


def _num(x: float, digits: int = 4) -> str:
    return f"{x:.{digits}f}".replace(".", ",")


def _row(label: str, r: dict) -> str:
    if not r.get("n"):
        return f"| {label} | 0 | – | – | – | – | – | – |"
    lo, hi = r["roi_ci"]
    roi = f"{_pct(r['roi'], sign=True)} [{_pct(lo, 0, True)}; {_pct(hi, 0, True)}]"
    return (
        f"| {label} | {r['n']} | {_num(r['odds'], 2)} | {_pct(r['hit_rate'])} | {_pct(r['expected'])} "
        f"| {roi} "
        f"| {_pct(r.get('clv'), sign=True)} | {_pct(r.get('beat_close'), 0)} |"
    )


METHOD = (
    "Kandidaten sind die üblichen Märkte (1X2, Doppelte Chance, Tore, Team-Tore, Halbzeiten, Beide treffen, "
    "Zu null; nur x,5-Linien). Unsere Wahrscheinlichkeit: Tippschein-Entscheidungsmodell, wo es den Markt "
    "abdeckt, sonst das Tor-Modell. Weil Pinnacle ohne Marge auf diesen Spielen genauer ist als unser Modell "
    "(Log-Loss {market} gegen {model}), wird gemischt: {weight} Modell, Rest Pinnacle (Mischung {blend}). "
    "Value-Tipp = Wahrscheinlichkeit × Betano-Quote − 1 ≥ {edge}, Wahrscheinlichkeit ≥ {min_p}, Quote ≤ "
    "{max_odds}, höchstens {per_fixture} je Spiel."
)
BACKTEST = (
    "Backtest: Betano- und Pinnacle-Preis zu dem Zeitpunkt, an dem der Tipp gezeigt worden wäre (fixierter "
    "Tag, sonst Prognose; Backtest: erster Anpfiff des Spieltags), abgerechnet zu diesem Preis; CLV gegen "
    "den Schlusspreis. ROI-Intervall per Bootstrap über Spiele."
)
VERDICT = (
    "**Einordnung:** Ein Intervall, das 0 einschließt, ist kein Nachweis. Aussagekräftiger ist der CLV: "
    "liegt er über 0, waren die Quoten besser als der faire Schlusspreis."
)


def report(result: dict, live: dict) -> str:
    head = "| | Tipps | Ø Quote | Treffer | erwartet | ROI [95 %] | CLV | Quote fiel danach |"
    sep = "|---|--:|--:|--:|--:|--:|--:|--:|"
    lines = ["# Value-Tipps", "", "_Automatisch erzeugt mit `qf value tips`. Nicht von Hand bearbeiten._", ""]
    if not result.get("candidates"):
        return "\n".join([*lines, "Noch keine Spiele mit Betano-Verlauf.", ""])
    s, ll = result["settings"], result["log_loss"]
    method = METHOD.format(
        market=_num(ll["market"]), model=_num(ll["model"]), blend=_num(ll["blend"]),
        weight=_pct(s["model_weight"], 0), edge=_pct(s["min_edge"], 0), min_p=_pct(s["min_p"], 0),
        max_odds=f"{s['max_odds']:g}".replace(".", ","), per_fixture=s["per_fixture"],
    )  # fmt: skip
    basis = (f"Datenbasis: {result['candidates']} Auswahlen aus {result['fixtures']} Spielen mit "
             f"Betano-Verlauf ({result['from'][:10]} bis {result['to'][:10]}).")  # fmt: skip
    grid = [_row(f"{_pct(g['model_weight'], 0)} / {_pct(g['min_edge'], 0)}", g) for g in result["grid"]]
    lines += [
        "## Methode", "", method, "", BACKTEST, "", basis, "",
        "## Ergebnis", "", head, sep,
        _row("Backtest (aktuelle Einstellungen)", result["result"]),
        _row("Live (fixierte Value-Tipps)", live), "", VERDICT, "",
        "## Je Marktgruppe (Backtest)", "", head, sep, *[_row(g["label"], g) for g in result["groups"]], "",
        "## Gewicht des Modells × Mindest-Vorteil (Backtest)", "",
        head.replace("| |", "| Gewicht / Vorteil |"), sep, *grid, "",
    ]  # fmt: skip
    return "\n".join(lines)
