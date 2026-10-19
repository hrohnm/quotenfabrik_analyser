"""Phase 3, way 1: Betano side markets against fair prices of the market-implied model (``mkt-v1``).

For every match with OddsPapi histories and a point in time T before kickoff:
1. Pinnacle prices at T (last change ≤ T) → margin-free targets → ``market_model.fit`` → fair price of every
   market.
2. Betano prices at T → edge = p_fair × odd − 1.
3. Validation: outcome-based ROI (noisy with ~130 matches) and closing line value against the fair closing
   probability (fit on Pinnacle's last prices before kickoff), plus Betano's own closing odd.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sqlalchemy import Engine, text

from quotenfabrik.analytics import market_model as mm
from quotenfabrik.analytics.value import remove_margin

_RESULT = {"1": "H", "X": "D", "2": "A"}
_PERIOD = {"fulltime": "", "p1": "_1h", "p2": "_2h"}


def oddspapi_key(
    market_type: str, period: str, handicap: float, name: str
) -> tuple[str, float | None, str] | None:
    """OddsPapi market + outcome name → (market, line, selection) of ``market_model``; None if not priced."""
    hc = float(handicap)
    if market_type == "1x2":
        return {"fulltime": "1x2", "p1": "ht_1x2", "p2": "2h_1x2"}[period], None, _RESULT[name]
    if period != "fulltime" and market_type not in {
        "totals",
        "teamtotals-team1",
        "teamtotals-team2",
        "bothteamsscore",
    }:
        return None
    if market_type == "doublechance":
        return "dc", None, {"1X": "1X", "12": "12", "2X": "X2"}[name]
    if market_type == "drawnobet":
        return "dnb", None, _RESULT[name]
    if market_type == "spreads-european":
        return "eh", hc, _RESULT[name]
    if market_type == "totals":
        return f"ou_{'ft' if period == 'fulltime' else period.replace('p', '') + 'h'}", hc, name.lower()
    if market_type in {"teamtotals-team1", "teamtotals-team2"}:
        side = "home" if market_type.endswith("1") else "away"
        return f"ou_{side}{_PERIOD[period]}", hc, name.lower()
    if market_type == "bothteamsscore":
        return f"btts{_PERIOD[period]}", None, name.lower()
    if market_type == "highestscoringh":
        return "highest_half", None, {"1st": "1H", "X": "equal", "2nd": "2H"}[name]
    if market_type == "exactscore":
        return "tg", None, name
    # exactscore-team1/2 (exact team goals): Betano prices contradict its own team totals over the whole
    # history (e.g. "4+" at 16.5 while over 3.5 is 1.44) – most likely mislabelled outcomes, not used.
    return None  # toscore-team* duplicates ou_home/ou_away 0.5; player markets need the player mapping


# Exhaustive selection sets (margin = Σ 1/odd − 1). Over/under and BTTS are complete with two selections.
EXHAUSTIVE = {
    "1x2": mm.HDA,
    "ht_1x2": mm.HDA,
    "2h_1x2": mm.HDA,
    "eh": mm.HDA,
    "dnb": ("H", "A"),
    "highest_half": ("1H", "2H", "equal"),
    "btts": ("yes", "no"),
    "btts_1h": ("yes", "no"),
    "btts_2h": ("yes", "no"),
    **{m: ("over", "under") for m in mm.LINE_MARKETS},
}

FAMILIES = {
    "1X2 & Handicap": {"1x2", "dc", "dnb", "eh"},
    "Tore gesamt": {"ou_ft", "btts", "tg"},
    "Team-Tore": {"ou_home", "ou_away"},
    "Halbzeiten": {"ht_1x2", "2h_1x2", "ou_1h", "ou_2h", "ou_home_1h", "ou_away_1h", "ou_home_2h",
                   "ou_away_2h", "btts_1h", "btts_2h", "highest_half"},
}  # fmt: skip
FAMILY_OF = {m: f for f, ms in FAMILIES.items() for m in ms}

_FIXTURES_SQL = text(
    """
    select o.id as oddspapi_id, f.id as fixture_id, f.season, f.kickoff_utc as kickoff,
           f.ft_home as hg, f.ft_away as ag, f.ht_home as h1, f.ht_away as a1,
           th.name as home, ta.name as away
    from core.oddspapi_fixtures o
    join core.fixtures f on f.id = o.fixture_id
    join core.teams th on th.id = f.home_team_id
    join core.teams ta on ta.id = f.away_team_id
    where f.league_id = :league and f.status in ('FT', 'AET', 'PEN') and f.ht_home is not null
      and o.history_final
    """
)
_ODDS_SQL = text(
    """
    select h.oddspapi_fixture_id as oddspapi_id, h.bookmaker, h.market_id, h.outcome_id, h.changed_at,
           h.price, h.active, m.market_type, m.period, m.handicap, m.outcomes ->> h.outcome_id::text as name
    from core.odds_history h
    join core.oddspapi_markets m on m.id = h.market_id
    where h.player_id = 0 and h.oddspapi_fixture_id = any(:ids)
    """
)


def load(engine: Engine, league_id: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Finished fixtures with OddsPapi histories and their price changes mapped to market-model keys."""
    fixtures = pd.read_sql(_FIXTURES_SQL, engine, params={"league": league_id})
    fixtures["kickoff"] = pd.to_datetime(fixtures["kickoff"], utc=True)
    odds = pd.read_sql(_ODDS_SQL, engine, params={"ids": list(fixtures["oddspapi_id"])})
    odds["changed_at"] = pd.to_datetime(odds["changed_at"], utc=True)
    odds["price"] = odds["price"].astype(float)
    keys = {
        k: oddspapi_key(*k)
        for k in odds[["market_type", "period", "handicap", "name"]].drop_duplicates().itertuples(index=False)
    }
    mapped = [keys[k] for k in odds[["market_type", "period", "handicap", "name"]].itertuples(index=False)]
    odds["market"] = [k[0] if k else None for k in mapped]
    odds["line"] = [k[1] if k else None for k in mapped]
    odds["selection"] = [k[2] if k else None for k in mapped]
    odds = odds[odds["market"].notna()].merge(fixtures[["oddspapi_id", "kickoff"]], on="oddspapi_id")
    return fixtures, odds


def snapshot(odds: pd.DataFrame, hours_before: float) -> pd.DataFrame:
    """Price per bookmaker and selection at kickoff − hours (last change before; suspended → dropped)."""
    cutoff = odds["kickoff"] - pd.to_timedelta(hours_before, unit="h")
    before = (
        odds[odds["changed_at"] < cutoff] if hours_before > 0 else odds[odds["changed_at"] < odds["kickoff"]]
    )
    last = (
        before.sort_values("changed_at")
        .groupby(["oddspapi_id", "bookmaker", "market", "line", "selection"], dropna=False)
        .tail(1)
    )
    return last[last["active"]][
        ["oddspapi_id", "bookmaker", "market", "line", "selection", "price", "changed_at"]
    ]


def targets(prices: pd.DataFrame) -> list[mm.Target]:
    """Margin-free (Shin) Pinnacle probabilities of the fit markets (complete selection sets only)."""
    out = []
    for (market, line), g in prices.groupby(["market", "line"], dropna=False):
        sels = EXHAUSTIVE.get(market)
        if market not in mm.FIT_MARKETS or sels is None or set(g["selection"]) != set(sels):
            continue
        g = g.set_index("selection").loc[list(sels)]
        probs = remove_margin(g["price"].to_numpy()[None, :])[0]
        if not np.isnan(probs).any():
            out.append(mm.Target(market, None if pd.isna(line) else float(line), tuple(sels), probs))
    return out


@dataclass
class Evaluation:
    hours_before: float
    fits: pd.DataFrame  # per fixture: fit quality
    rows: pd.DataFrame  # per Betano selection: odd, fair p (bet time and close), outcome, closing odd


def evaluate(fixtures: pd.DataFrame, odds: pd.DataFrame, hours_before: float) -> Evaluation:
    """Betano prices at kickoff − hours against fair probabilities, with closing values and outcomes."""
    bet, close = snapshot(odds, hours_before), snapshot(odds, 0)
    fair_bet, fits = _fair(bet, fixtures)
    fair_close, _ = _fair(close, fixtures)
    keys = ["oddspapi_id", "market", "line", "selection"]
    betano = bet[bet["bookmaker"] == "betano.de"].drop(columns=["bookmaker"])
    betano_close = close[close["bookmaker"] == "betano.de"][[*keys, "price"]].rename(
        columns={"price": "close_odd"}
    )
    pin = bet[bet["bookmaker"] == "pinnacle"]
    pinnacle = {
        (o, m, _line_key(ln)) for o, m, ln in pin[["oddspapi_id", "market", "line"]].itertuples(index=False)
    }
    rows = (
        betano.rename(columns={"price": "odd"})
        .merge(fair_bet, on=keys)
        .merge(fair_close.rename(columns={"p_fair": "p_close"}), on=keys, how="left")
        .merge(betano_close, on=keys, how="left")
        .merge(fixtures, on="oddspapi_id")
    )
    rows["family"] = rows["market"].map(FAMILY_OF)
    rows["direct"] = [
        (o, m, _line_key(ln)) in pinnacle
        for o, m, ln in rows[["oddspapi_id", "market", "line"]].itertuples(index=False)
    ]
    rows["outcome"] = [
        mm.outcome(
            {"hg": r.hg, "ag": r.ag, "h1": r.h1, "a1": r.a1},
            r.market,
            None if pd.isna(r.line) else r.line,
            r.selection,
        )  # noqa: E501
        for r in rows.itertuples(index=False)
    ]
    rows["edge"] = rows["p_fair"] * rows["odd"] - 1
    rows["clv"] = rows["odd"] * rows["p_close"] - 1
    rows["clv_betano"] = rows["odd"] / rows["close_odd"] - 1
    won = rows["outcome"].map(lambda o: o is True)
    rows["profit"] = np.where(rows["outcome"].isna(), 0.0, np.where(won, rows["odd"] - 1, -1.0))
    return Evaluation(hours_before, fits, rows)


def _line_key(line) -> float | None:
    return None if line is None or pd.isna(line) else float(line)


def _fair(prices: pd.DataFrame, fixtures: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fits mkt-v1 per fixture on Pinnacle and prices every quoted Betano selection."""
    pin = prices[prices["bookmaker"] == "pinnacle"]
    quoted = prices[prices["bookmaker"] == "betano.de"][
        ["oddspapi_id", "market", "line", "selection"]
    ].drop_duplicates()
    out, fits = [], []
    for oid, g in pin.groupby("oddspapi_id"):
        ts = targets(g)
        if not any(t.market == "1x2" for t in ts) or not any(t.market == "ou_ft" for t in ts):
            continue  # main markets are required
        pred, info = mm.fit(ts)
        fits.append({"oddspapi_id": oid, **info})
        q = quoted[quoted["oddspapi_id"] == oid].copy()
        q["p_fair"] = [
            mm.price(pred, m, None if pd.isna(ln) else ln, s)
            for m, ln, s in q[["market", "line", "selection"]].itertuples(index=False)
        ]  # noqa: E501
        out.append(q)
    fair = pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=[*quoted.columns, "p_fair"])
    return fair.dropna(subset=["p_fair"]), pd.DataFrame(fits).merge(
        fixtures[["oddspapi_id", "fixture_id"]], on="oddspapi_id"
    )


def value_bets(rows: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """At most one bet per match and market line: the selection with the largest edge above the threshold."""
    cand = rows[(rows["edge"] > threshold) & rows["p_fair"].between(0.02, 0.98)]
    return cand.sort_values("edge").groupby(["oddspapi_id", "market", "line"], dropna=False).tail(1)
