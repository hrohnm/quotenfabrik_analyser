"""Closing line value (CLV) of the picks: Betano odds when a pick was published against the closing market.

A pick counts as taken at the moment it was shown: for forecasts when the day was frozen (``qf picks freeze``,
otherwise when the forecast was made), for backtest picks when the model was fitted (first kickoff of the
matchday, only data known by then). Prices come from the OddsPapi history (``core.odds_history``).

Per pick:

- ``clv`` = Betano odds taken × Pinnacle probability without margin at kickoff − 1 (value against the sharp
  closing market; the main measure),
- ``move`` = Betano odds taken / Betano closing odds − 1 (> 0: the odds dropped after the pick),
- ``shift`` = Pinnacle probability at kickoff − at pick time (> 0: the market moved towards the pick).

The baseline are all selections of the same markets with prices (what a random bet at Betano yields).
Picks only add information if their CLV is clearly above the baseline. Standard errors are clustered by
fixture (the picks of one fixture are correlated).
"""

from datetime import datetime

import numpy as np
import pandas as pd
from sqlalchemy import Engine, text

from quotenfabrik.analytics.bookmaker_odds import KEY, odds_table

MIN_LEAD_H = 1.0  # picks published less than an hour before kickoff are not counted
LEAD_BUCKETS = [0, 6, 24, 72, np.inf]
LEAD_LABELS = ["unter 6 h", "6–24 h", "1–3 Tage", "über 3 Tage"]

_PICKS_SQL = """
    with runs as ({runs})
    select k.fixture_id, f.league_id, f.season, f.kickoff_utc, runs.kind, k.profile, k.rank, k.market_group,
           k.market, k.selection, k.line::float as line, k.probability, p.outcome,
           greatest(runs.predicted_at, coalesce(z.frozen_at, runs.predicted_at)) as taken_at
    from analytics.picks k
    join runs on runs.model_run_id = k.model_run_id and runs.fixture_id = k.fixture_id
    join analytics.predictions p on p.id = k.prediction_id
    join core.fixtures f on f.id = k.fixture_id
    left join analytics.frozen_runs z on z.fixture_id = k.fixture_id and z.model_run_id = k.model_run_id
    where f.kickoff_utc < now()  -- closing odds known
      and exists (select 1 from core.oddspapi_fixtures o where o.fixture_id = k.fixture_id)
"""

_BASELINE_SQL = """
    with runs as ({runs})
    select p.fixture_id, runs.kind, p.market_group, p.market, p.selection, p.line::float as line,
           p.probability, p.outcome
    from analytics.predictions p
    join runs on runs.model_run_id = p.model_run_id and runs.fixture_id = p.fixture_id
    where p.fixture_id = any(:ids) and p.market = any(:markets)
"""


def load_picks(engine: Engine, leagues: list[int]) -> pd.DataFrame:
    """Picks (chosen run per fixture) of started fixtures with an OddsPapi history and the time they were
    taken."""
    from quotenfabrik.api.data import chosen_runs_cte

    sql = _PICKS_SQL.format(runs=chosen_runs_cte("and f.league_id = any(:leagues)"))
    with engine.connect() as conn:
        picks = pd.read_sql(text(sql), conn, params={"leagues": list(leagues)})
    for col in ("kickoff_utc", "taken_at"):
        picks[col] = pd.to_datetime(picks[col], utc=True)
    picks["lead_h"] = (picks["kickoff_utc"] - picks["taken_at"]).dt.total_seconds() / 3600
    return picks[picks["lead_h"] >= MIN_LEAD_H].reset_index(drop=True)


def price_tables(engine: Engine, taken_at: dict[int, datetime]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Betano odds and Pinnacle fair probability per selection at pick time (``taken``, ``fair_taken``) and at
    kickoff (``close``, ``fair_close``)."""
    ids = sorted(int(f) for f in taken_at)
    early = odds_table(engine, ids, at=taken_at).rename(columns={"betano": "taken", "fair": "fair_taken"})
    late = odds_table(engine, ids).rename(columns={"betano": "close", "fair": "fair_close"})
    return early[[*KEY, "taken", "fair_taken"]], late[[*KEY, "close", "fair_close"]]


def attach_prices(rows: pd.DataFrame, early: pd.DataFrame, late: pd.DataFrame) -> pd.DataFrame:
    """Adds the prices of :func:`price_tables` plus ``clv``, ``move`` and ``shift``; rows without Betano odds
    at both times are dropped."""
    m = rows.astype({"line": float}).merge(early, on=KEY, how="inner")
    m = m.merge(late, on=KEY, how="inner").dropna(subset=["taken", "close"])
    m["clv"] = m["taken"] * m["fair_close"] - 1
    m["move"] = m["taken"] / m["close"] - 1
    m["shift"] = m["fair_close"] - m["fair_taken"]
    return m.reset_index(drop=True)


def load(engine: Engine, leagues: list[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(picks, baseline) with prices; baseline = all selections of the picked markets of the same fixtures,
    priced at the same time as the picks of the fixture."""
    from quotenfabrik.api.data import chosen_runs_cte

    picks = load_picks(engine, leagues)
    if picks.empty:
        empty = picks.assign(taken=[], close=[], fair_taken=[], fair_close=[], clv=[], move=[], shift=[])
        return empty, empty
    taken_at = picks.groupby("fixture_id")["taken_at"].min().to_dict()
    early, late = price_tables(engine, {int(f): t.to_pydatetime() for f, t in taken_at.items()})
    sql = _BASELINE_SQL.format(runs=chosen_runs_cte("and p.fixture_id = any(:ids)"))
    with engine.connect() as conn:
        base = pd.read_sql(
            text(sql), conn, params={"ids": list(taken_at), "markets": sorted(picks["market"].unique())}
        )
    meta = picks.drop_duplicates("fixture_id")[["fixture_id", "league_id", "season", "lead_h"]]
    base = base.merge(meta, on="fixture_id")
    return attach_prices(picks, early, late), attach_prices(base, early, late)


ODDS_BANDS = [1.0, 1.2, 1.35, 1.5, 1.7, 2.0, 2.5, 3.5, np.inf]


def matched_baseline(picks: pd.DataFrame, base: pd.DataFrame) -> float | None:
    """Mean CLV of all selections reweighted to the odds distribution of ``picks`` (Betano's margin is lower
    on favourites, so picks with short odds must be compared with selections at similar odds)."""
    p, b = picks.dropna(subset=["clv"]), base.dropna(subset=["clv"])
    if p.empty or b.empty:
        return None
    pb = pd.cut(p["taken"], ODDS_BANDS).value_counts(normalize=True)
    bb = b.groupby(pd.cut(b["taken"], ODDS_BANDS), observed=True)["clv"].mean()
    common = pb[pb > 0].index.intersection(bb.index)
    if common.empty:
        return None
    w = pb[common] / pb[common].sum()
    return float((bb[common] * w).sum())


def lead_bucket(lead_h: pd.Series) -> pd.Series:
    return pd.cut(lead_h, LEAD_BUCKETS, labels=LEAD_LABELS, right=False).astype(str)


def summarize(rows: pd.DataFrame) -> dict:
    """Mean CLV with a fixture-clustered standard error, odds moves and the result at the odds taken."""
    if rows.empty:
        return {"n": 0, "fixtures": 0}
    c = rows.dropna(subset=["clv"])  # needs a complete Pinnacle outcome set at kickoff
    mean = float(c["clv"].mean()) if len(c) else None
    # cluster-robust SE of the mean: residuals summed per fixture
    cluster = (c["clv"] - (mean or 0)).groupby(c["fixture_id"]).sum()
    se = float(np.sqrt((cluster**2).sum()) / len(c)) if len(cluster) > 1 else None
    settled = rows.dropna(subset=["outcome"])
    hit = settled["outcome"].astype(bool)
    profit = np.where(hit, settled["taken"] - 1, -1.0)
    return {
        "n": int(len(rows)),
        "fixtures": int(rows["fixture_id"].nunique()),
        "odds": float(rows["taken"].mean()),
        "clv": mean,
        "clv_se": se,
        "clv_n": int(len(c)),
        "clv_positive": float((c["clv"] > 0).mean()) if len(c) else None,
        "beat_close": float((rows["taken"] > rows["close"]).mean()),
        "worse_close": float((rows["taken"] < rows["close"]).mean()),
        "move": float(rows["move"].mean()),
        "shift": float(rows["shift"].mean()) if rows["shift"].notna().any() else None,
        "settled": int(len(settled)),
        "hit_rate": float(hit.mean()) if len(settled) else None,
        "expected": float(settled["probability"].mean()) if len(settled) else None,
        "roi": float(profit.mean()) if len(settled) else None,
    }


def by(rows: pd.DataFrame, column: str, min_n: int = 1) -> list[dict]:
    out = []
    for key, g in rows.groupby(column, sort=True):
        if len(g) >= min_n:
            out.append({"key": key if isinstance(key, str) else key.item(), **summarize(g)})
    return out


SOURCE_LABELS = {"forecast": "Live (fixierte Tipps)", "backtest": "Backtest (Modell zum Spieltagsbeginn)"}


def _row(key, label: str, rows: pd.DataFrame, base: pd.DataFrame) -> dict:
    s = summarize(rows)
    s["baseline"] = matched_baseline(rows, base)
    s["delta"] = None if s.get("clv") is None or s["baseline"] is None else s["clv"] - s["baseline"]
    return {"key": key, "label": label, **s}


def evaluate(picks: pd.DataFrame, base: pd.DataFrame, labels: dict | None = None) -> dict:
    """CLV per source (live / backtest) and, over all picks, per profile, market group, lead time and league,
    each with the odds-matched baseline of the same subset; plus picks with model EV > 0 at the odds taken."""
    labels = labels or {}
    if picks.empty:
        return {"picks": 0}
    picks, base = picks.copy(), base.copy()
    picks["lead"], base["lead"] = lead_bucket(picks["lead_h"]), lead_bucket(base["lead_h"])
    out = {"picks": int(len(picks)), "fixtures": int(picks["fixture_id"].nunique()),
           "from": picks["kickoff_utc"].min().isoformat(),
           "to": picks["kickoff_utc"].max().isoformat()}  # fmt: skip
    out["total"] = _row("all", "Alle Tipps", picks, base)
    out["sources"] = [_row(k, SOURCE_LABELS.get(k, k), g, base[base["kind"] == k])
                      for k, g in picks.groupby("kind")]  # fmt: skip
    sections = (("profiles", "profile", None), ("groups", "market_group", "market_group"),
                ("leads", "lead", "lead"), ("leagues", "league_id", "league_id"))  # fmt: skip
    for name, col, base_col in sections:
        rows = []
        for k, g in picks.groupby(col):
            b = base if base_col is None else base[base[base_col] == k]
            key = k if isinstance(k, str) else int(k)
            rows.append(_row(key, str(labels.get(name, {}).get(key, key)), g, b))
        if name == "leads":
            rows.sort(key=lambda r: LEAD_LABELS.index(r["key"]) if r["key"] in LEAD_LABELS else 99)
        out[name] = rows
    ev = picks[picks["probability"] * picks["taken"] > 1]
    out["value"] = _row("ev", "Tipps mit Modell-EV > 0 zur genommenen Quote", ev, base) if len(ev) else None
    return out


def _pct(x, digits: int = 1, sign: bool = True) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    return f"{x * 100:{'+' if sign else ''}.{digits}f} %".replace(".", ",")


def _table(rows: list[dict], first: str) -> list[str]:
    lines = [f"| {first} | Tipps | Spiele | Ø Quote | CLV | ± SE | Vergleich* | Abstand | Quote fiel danach "
             "| Treffer | ROI zur Quote |",
             "|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|"]  # fmt: skip
    for r in rows:
        if not r.get("n"):
            continue
        odds = f"{r['odds']:.2f}".replace(".", ",")
        lines.append(
            f"| {r['label']} | {r['n']} | {r['fixtures']} | {odds} | {_pct(r.get('clv'))} "
            f"| {_pct(r.get('clv_se'), sign=False)} | {_pct(r.get('baseline'))} | {_pct(r.get('delta'))} "
            f"| {_pct(r['beat_close'], 0, False)} | {_pct(r.get('hit_rate'), 0, False)} "
            f"| {_pct(r.get('roi'))} |"
        )
    return lines


def verdict(r: dict) -> str:
    if not r.get("n") or r.get("delta") is None or not r.get("clv_se"):
        return "Noch zu wenig Daten für eine Aussage."
    z = r["delta"] / r["clv_se"]
    if r["clv"] > 0 and z >= 2:
        return ("Positiver CLV und deutlich über der Vergleichsgruppe: Hinweis auf echten Vorteil gegenüber "
                "dem Markt.")  # fmt: skip
    if z >= 2:
        return ("Die Tipps schlagen die Vergleichsgruppe gleicher Quotenhöhe deutlich (Modell erkennt "
                "Richtung), liegen aber nach Betano-Marge noch unter dem fairen Schlusspreis: Einzeln ohne "
                "Value-Filter kein Gewinn zu erwarten.")  # fmt: skip
    if z <= -2:
        return "Die Tipps liegen deutlich unter der Vergleichsgruppe: Der Markt bewegt sich gegen die Tipps."
    return "Kein belastbarer Unterschied zur Vergleichsgruppe gleicher Quotenhöhe."


def report(result: dict) -> str:
    lines = ["# Closing Line Value der Tipps", "",
             "_Automatisch erzeugt mit `qf value clv`. Nicht von Hand bearbeiten._", ""]  # fmt: skip
    if not result.get("picks"):
        return "\n".join([*lines, "Noch keine Tipps mit Betano-Quotenverlauf.", ""])
    total = result["total"]
    lines += [
        "## Methode", "",
        "- **Zeitpunkt des Tipps:** Live-Tipps beim Fixieren des Tages (`qf picks freeze`, sonst bei der "
        "Prognose), Backtest-Tipps zum ersten Anpfiff des Spieltags (das Modell kennt nur Spiele davor). "
        f"Tipps weniger als {MIN_LEAD_H:g} h vor Anpfiff zählen nicht.",
        "- **Genommene Quote:** letzter Betano-Preis vor diesem Zeitpunkt (OddsPapi-Verlauf).",
        "- **CLV** = genommene Betano-Quote × Pinnacle-Wahrscheinlichkeit ohne Marge beim Anpfiff − 1. "
        "Über 0 heißt: Die Quote war besser als der faire Schlusspreis des schärfsten Marktes.",
        "- **Vergleich\\*** = CLV aller Auswahlen derselben Märkte und Spiele zur selben Zeit, gewichtet auf "
        "die Quotenverteilung der Tipps (Betano nimmt auf Favoriten weniger Marge als auf Außenseiter). "
        "**Abstand** = CLV − Vergleich: Zeigt, ob die Auswahl des Modells Information enthält, die der Markt "
        "erst später einpreist.",
        "- **± SE**: Standardfehler, nach Spiel geclustert (die 3 Tipps eines Spiels hängen zusammen). "
        "Ein Abstand ab etwa 2 SE gilt als belastbar.",
        "- **Quote fiel danach** = Anteil der Tipps, deren Betano-Quote bis zum Anpfiff gesunken ist.",
        "",
        f"Datenbasis: {result['picks']} Tipps aus {result['fixtures']} Spielen mit Betano-Verlauf "
        f"({result['from'][:10]} bis {result['to'][:10]}). Für neue Ligen werden Verläufe nur für kommende "
        "Spiele geladen (`oddspapi.history_days`) – die Live-Zahl wächst mit jedem fixierten Spieltag.",
        "",
        "## Ergebnis", "",
        f"**{verdict(total)}**", "",
        *_table([total, *result["sources"]], "Quelle"), "",
    ]  # fmt: skip
    if result.get("value"):
        v = result["value"]
        lines += ["## Tipps mit Modell-Value", "",
                  "Tipps, bei denen Modellwahrscheinlichkeit × genommene Quote > 1 war (Vorschau auf ein "
                  "Value-Profil; nur sinnvoll, wenn der CLV hier höher ist als bei allen Tipps).", "",
                  *_table([v], "Auswahl"), ""]  # fmt: skip
    sections = (("profiles", "Je Profil", "Profil"), ("groups", "Je Marktgruppe", "Marktgruppe"),
                ("leads", "Je Vorlauf bis Anpfiff", "Vorlauf"), ("leagues", "Je Liga", "Liga"))  # fmt: skip
    for name, title, first in sections:
        lines += [f"## {title}", "", *_table(result[name], first), ""]
    return "\n".join(lines)


def run(engine: Engine, leagues: list[int]) -> dict:
    """Loads, prices and evaluates the picks of ``leagues`` (with display labels)."""
    from quotenfabrik.analytics.picks import profiles
    from quotenfabrik.api.labels import GROUP_LABELS

    picks, base = load(engine, leagues)
    with engine.connect() as conn:
        names = dict(conn.execute(text("select id, name from core.leagues where id = any(:ids)"),
                                  {"ids": list(leagues)}).all())  # fmt: skip
    labels = {"profiles": {k: p.label for k, p in profiles().items()}, "groups": GROUP_LABELS,
              "leagues": names}  # fmt: skip
    return evaluate(picks, base, labels)
