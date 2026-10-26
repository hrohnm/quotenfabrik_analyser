"""Bookmaker prices per fixture in model-market keys: Betano odds and Pinnacle's margin-free probability.

Source is the OddsPapi price history (``core.odds_history``): the last price before kickoff per selection,
i.e. the current price for upcoming fixtures and the closing price for finished ones.
Suspended prices are dropped.
"""

from datetime import datetime

import numpy as np
import pandas as pd
from sqlalchemy import Engine, text

from quotenfabrik.analytics.betano_value import EXHAUSTIVE, oddspapi_key
from quotenfabrik.analytics.value import remove_margin

BETANO, PINNACLE = "betano.de", "pinnacle"
KEY = ["fixture_id", "market", "line", "selection"]

_SQL = text(
    """
    select distinct on (o.fixture_id, h.bookmaker, h.market_id, h.outcome_id)
           o.fixture_id, h.bookmaker, h.price::float as price, h.active, h.changed_at,
           m.market_type, m.period, m.handicap::float as handicap, m.outcomes ->> h.outcome_id::text as name
    from core.oddspapi_fixtures o
    join core.fixtures f on f.id = o.fixture_id
    join core.odds_history h on h.oddspapi_fixture_id = o.id
    join core.oddspapi_markets m on m.id = h.market_id
    left join unnest(cast(:at_ids as bigint[]), cast(:at_times as timestamptz[])) c(fixture_id, at)
           on c.fixture_id = o.fixture_id
    where o.fixture_id = any(:ids) and h.player_id = 0 and h.bookmaker = any(:books)
      and h.changed_at < least(f.kickoff_utc, c.at)
      and (cast(:types as text[]) is null or m.market_type = any(:types))
    order by o.fixture_id, h.bookmaker, h.market_id, h.outcome_id, h.changed_at desc
    """
)


def _line(x) -> float | None:
    return None if x is None or pd.isna(x) else round(float(x), 2)


def latest_prices(
    engine: Engine,
    fixture_ids: list[int],
    market_types: list[str] | None = None,
    at: dict[int, datetime] | None = None,
) -> pd.DataFrame:
    """Last active price before kickoff per fixture, bookmaker and model selection (optionally only some
    OddsPapi market types, e.g. ``["totals", "doublechance"]``; ``at``: price at that time per fixture
    instead, e.g. when a pick was published)."""
    cols = ["fixture_id", "bookmaker", "market", "line", "selection", "price", "changed_at"]
    if not fixture_ids:
        return pd.DataFrame(columns=cols)
    raw = pd.read_sql(
        _SQL,
        engine,
        params={
            "ids": [int(i) for i in fixture_ids],
            "books": [BETANO, PINNACLE],
            "types": market_types,
            "at_ids": list(at or {}),
            "at_times": list((at or {}).values()),
        },
    )
    raw = raw[raw["active"].astype(bool) & raw["name"].notna()]
    if raw.empty:
        return pd.DataFrame(columns=cols)
    keys = {}
    for k in raw[["market_type", "period", "handicap", "name"]].drop_duplicates().itertuples(index=False):
        try:
            keys[tuple(k)] = oddspapi_key(
                k.market_type, k.period, 0.0 if pd.isna(k.handicap) else k.handicap, k.name
            )
        except KeyError:  # outcome name we do not price
            keys[tuple(k)] = None
    mapped = [
        keys[tuple(k)] for k in raw[["market_type", "period", "handicap", "name"]].itertuples(index=False)
    ]
    raw["market"] = [m[0] if m else None for m in mapped]
    raw["line"] = [_line(m[1]) if m else None for m in mapped]
    raw["selection"] = [m[2] if m else None for m in mapped]
    out = raw[raw["market"].notna()].sort_values("changed_at")
    # several OddsPapi markets can map to one model selection: keep the latest price
    out = out.drop_duplicates(["fixture_id", "bookmaker", "market", "line", "selection"], keep="last")
    out["changed_at"] = pd.to_datetime(out["changed_at"], utc=True)
    return out[cols].reset_index(drop=True)


def pinnacle_fair(prices: pd.DataFrame) -> pd.DataFrame:
    """Margin-free Pinnacle probability per selection (complete outcome sets only; double chance from 1X2)."""
    pin = prices[prices["bookmaker"] == PINNACLE]
    sets: dict[str, tuple[list, list]] = {}  # market -> (fixture_id, line) per outcome set, odds rows
    for (fixture_id, market, line), g in pin.groupby(["fixture_id", "market", "line"], dropna=False):
        names = EXHAUSTIVE.get(market)
        if names is None or set(g["selection"]) != set(names):
            continue
        by_sel = dict(zip(g["selection"], g["price"], strict=True))
        keys, odds = sets.setdefault(market, ([], []))
        keys.append((fixture_id, line))
        odds.append([by_sel[n] for n in names])
    rows = []
    for market, (keys, odds) in sets.items():  # one vectorised margin removal per market
        names = EXHAUSTIVE[market]
        for (fixture_id, line), fair in zip(keys, remove_margin(np.array(odds)), strict=True):
            if np.isnan(fair).any():
                continue
            rows += [(fixture_id, market, _line(line), n, float(p)) for n, p in zip(names, fair, strict=True)]
    fair = pd.DataFrame(rows, columns=[*KEY, "fair"])
    hda = fair[fair["market"] == "1x2"].pivot_table(index="fixture_id", columns="selection", values="fair")
    if not hda.empty and {"H", "D", "A"} <= set(hda.columns):
        dc = pd.DataFrame({"1X": hda["H"] + hda["D"], "X2": hda["D"] + hda["A"], "12": hda["H"] + hda["A"]})
        dc = dc.stack().rename("fair").reset_index().rename(columns={"level_1": "selection"})
        fair = pd.concat([fair, dc.assign(market="dc", line=None)[[*KEY, "fair"]]], ignore_index=True)
    return fair


def odds_table(
    engine: Engine,
    fixture_ids: list[int],
    market_types: list[str] | None = None,
    at: dict[int, datetime] | None = None,
) -> pd.DataFrame:
    """Per fixture and selection: ``betano``, ``betano_at`` and Pinnacle without margin (``fair``)."""
    prices = latest_prices(engine, fixture_ids, market_types, at)
    betano = prices[prices["bookmaker"] == BETANO].rename(
        columns={"price": "betano", "changed_at": "betano_at"}
    )
    betano = betano[[*KEY, "betano", "betano_at"]]
    fair = pinnacle_fair(prices)
    if betano.empty and fair.empty:
        return pd.DataFrame(columns=[*KEY, "betano", "betano_at", "fair"])
    betano, fair = betano.astype({"line": float}), fair.astype({"line": float})  # NaN = no line
    return betano.merge(fair, on=KEY, how="outer")


def lookup(table: pd.DataFrame) -> dict[tuple, dict]:
    """{(fixture_id, market, line, selection): {"betano", "betano_at", "fair"}} for the API."""
    out = {}
    for r in table.itertuples(index=False):
        out[(int(r.fixture_id), r.market, _line(r.line), r.selection)] = {
            "betano": None if pd.isna(r.betano) else round(float(r.betano), 2),
            "betano_at": None if pd.isna(r.betano_at) else r.betano_at.isoformat(),
            "fair": None if pd.isna(r.fair) else float(r.fair),
        }
    return out
