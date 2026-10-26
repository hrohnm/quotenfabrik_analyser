""" "Wetten & Modell" for a set of fixtures (a competition season or a team's season): how well the model and
the picks did, own bets, and Betano against Pinnacle and the model. Retrospective only, no betting signal."""

import numpy as np
import pandas as pd

from quotenfabrik.analytics import bookmaker_odds
from quotenfabrik.analytics.picks import evaluate_picks, profiles
from quotenfabrik.api.data import chosen_runs_cte, df, engine
from quotenfabrik.api.labels import GROUP_LABELS, MARKET_LABELS, SELECTION_LABELS, pick_label

KEY_MARKETS = [("1x2", None), ("ou_ft", 1.5), ("ou_ft", 2.5), ("ou_ft", 3.5), ("btts", None), ("dc", None),
               ("ou_home", 1.5), ("ou_away", 1.5), ("ou_1h", 0.5), ("ou_2h", 1.5)]  # fmt: skip
CALIBRATION_BINS = np.linspace(0, 1, 11)


def _predictions(fixture_ids: list[int]) -> pd.DataFrame:
    """Settled predictions of the chosen run per fixture (no goalscorers)."""
    data = df(
        f"""with runs as ({chosen_runs_cte("and p.fixture_id = any(:ids)")})
            select p.fixture_id, p.market_group, p.market, p.selection, p.line::float as line, p.probability,
                   p.outcome
            from analytics.predictions p
            join runs on runs.model_run_id = p.model_run_id and runs.fixture_id = p.fixture_id
            where p.fixture_id = any(:ids) and p.outcome is not null and p.market not like 'scorer%'""",
        ids=fixture_ids,
    )  # fmt: skip
    data["outcome"] = data["outcome"].astype(bool)
    return data


def model_section(data: pd.DataFrame) -> dict:
    """Hit rate of the most likely selection per market group and key market, and calibration."""
    from quotenfabrik.api.routers.stats import picks as market_picks

    if data.empty:
        return {"fixtures": 0, "groups": [], "markets": [], "calibration": []}
    pk = market_picks(data)
    groups = [{"group": g, "label": GROUP_LABELS.get(g, g), "n": int(len(x)),
               "hit_rate": float(x["hit"].mean()),
               "expected": float(x["pick_probability"].mean())}
              for g, x in pk.groupby("market_group")]  # fmt: skip
    order = list(GROUP_LABELS)
    groups.sort(key=lambda g: order.index(g["group"]) if g["group"] in order else len(order))
    markets = []
    for market, line in KEY_MARKETS:
        x = pk[(pk["market"] == market) & ((pk["line"] == line) if line is not None else pk["line"].isna())]
        if x.empty:
            continue
        label = MARKET_LABELS.get(market, market) + ("" if line is None else f" {line:g}".replace(".", ","))
        top = x["selection"].value_counts()
        markets.append({"market": market, "line": line, "label": label, "n": int(len(x)),
                        "hit_rate": float(x["hit"].mean()), "expected": float(x["pick_probability"].mean()),
                        "most_picked": SELECTION_LABELS.get(top.index[0], top.index[0])})  # fmt: skip
    cut = pd.cut(data["probability"], CALIBRATION_BINS, include_lowest=True)
    calibration = [{"bin": f"{max(b.left, 0) * 100:.0f}–{b.right * 100:.0f} %", "n": int(len(g)),
                    "predicted": float(g["probability"].mean()), "observed": float(g["outcome"].mean())}
                   for b, g in data.groupby(cut, observed=True) if len(g) >= 20]  # fmt: skip
    return {"fixtures": int(data["fixture_id"].nunique()), "groups": groups, "markets": markets,
            "calibration": calibration}  # fmt: skip


def _surprise(m: dict) -> float:
    """Pick types that beat the model's expectation the most come first."""
    return (m["expected"] or 0) - (m["hit_rate"] or 0)


def picks_section(fixture_ids: list[int]) -> list[dict]:
    """The 3 picks per fixture: singles and 3-pick combo per profile, and the best and worst pick types."""
    rows = df(
        f"""with runs as ({chosen_runs_cte("and p.fixture_id = any(:ids)")})
            select k.fixture_id, f.season, k.profile, k.rank, k.market, k.selection, k.line::float as line,
                   k.probability, p.outcome, jsonb_typeof(k.reasons) = 'array' as has_reason
            from analytics.picks k
            join runs on runs.model_run_id = k.model_run_id and runs.fixture_id = k.fixture_id
            join analytics.predictions p on p.id = k.prediction_id
            join core.fixtures f on f.id = k.fixture_id
            where k.fixture_id = any(:ids) and p.outcome is not null""",
        ids=fixture_ids,
    )  # fmt: skip
    if rows.empty:
        return []
    rows["has_reason"] = rows["has_reason"].fillna(False).astype(bool)
    out = []
    for key, prof in profiles().items():
        r = evaluate_picks(rows[rows["profile"] == key])
        markets = [m for m in r["per_market"] if m["n"] >= 5]
        for m in markets:
            m["label"] = pick_label(m["market"], m["selection"], m["line"], "Heimteam", "Gastteam")
        out.append({"profile": key, "label": prof.label, "singles": r["singles"], "combo": r["combo"],
                    "markets": sorted(markets, key=_surprise)[:8]})  # fmt: skip
    return out


def bets_section(where: str, **params) -> dict:
    """Own bets with at least one leg matching ``where`` (SQL on ``l`` = app.bet_legs)."""
    bets = df(
        f"""select distinct b.id, b.placed_at, b.label, b.source, b.stake::float as stake,
                   b.odds::float as odds,
                   b.status, b.payout::float as payout
            from app.bets b join app.bet_legs l on l.bet_id = b.id
            where {where} order by b.placed_at desc""",
        **params,
    )  # fmt: skip
    legs = df(f"select l.outcome from app.bet_legs l where {where}", **params)
    settled = bets[bets["status"].isin(["won", "lost"])]
    stake = float(settled["stake"].sum())
    returned = float(settled["payout"].fillna(0).sum())
    return {
        "bets": len(bets),
        "open": int((bets["status"] == "open").sum()),
        "won": int((bets["status"] == "won").sum()),
        "lost": int((bets["status"] == "lost").sum()),
        "stake": stake,
        "profit": returned - stake,
        "roi": (returned - stake) / stake if stake else None,
        "legs": len(legs),
        "legs_won": int((legs["outcome"] == True).sum()),  # noqa: E712
        "legs_settled": int(legs["outcome"].notna().sum()),
        "recent": [{"id": int(r.id), "placed_at": pd.Timestamp(r.placed_at).isoformat(), "label": r.label,
                    "odds": r.odds, "stake": r.stake, "status": r.status,
                    "payout": None if pd.isna(r.payout) else r.payout}
                   for r in bets.head(10).itertuples()],
    }  # fmt: skip


def market_section(fixture_ids: list[int], data: pd.DataFrame) -> dict:
    """Betano (last price before kickoff) against Pinnacle without margin and against the model, settled
    fixtures: payout ratio Betano × fair probability, share above Pinnacle, model edge and its result."""
    table = bookmaker_odds.odds_table(engine(), fixture_ids)
    if table.empty or data.empty:
        return {"selections": 0, "groups": []}
    t = table.dropna(subset=["betano"]).copy()
    t["line"] = t["line"].astype(float)
    m = t.merge(data, on=["fixture_id", "market", "selection", "line"], how="inner")
    if m.empty:
        return {"selections": 0, "groups": []}
    m["payback"] = m["betano"] * m["fair"]
    m["edge"] = m["probability"] * m["betano"] - 1
    m["profit"] = np.where(m["outcome"], m["betano"] - 1, -1.0)
    groups = []
    for g, x in m.groupby("market_group"):
        with_fair = x.dropna(subset=["fair"])
        value = x[x["edge"] > 0]
        groups.append({
            "group": g, "label": GROUP_LABELS.get(g, g), "n": int(len(x)),
            "payback": float(with_fair["payback"].mean()) if len(with_fair) else None,
            "above_pinnacle": float((with_fair["payback"] > 1).mean()) if len(with_fair) else None,
            "edge_share": float((x["edge"] > 0).mean()),
            "value_bets": int(len(value)),
            "value_roi": float(value["profit"].mean()) if len(value) else None,
        })  # fmt: skip
    order = list(GROUP_LABELS)
    groups.sort(key=lambda g: order.index(g["group"]) if g["group"] in order else len(order))
    return {"selections": int(len(m)), "fixtures": int(m["fixture_id"].nunique()), "groups": groups}


def report(fixture_ids: list[int], bets_where: str, **bets_params) -> dict:
    data = _predictions(fixture_ids) if fixture_ids else pd.DataFrame()
    return {
        "model": model_section(data),
        "picks": picks_section(fixture_ids) if fixture_ids else [],
        "bets": bets_section(bets_where, **bets_params),
        "market": market_section(fixture_ids, data) if fixture_ids else {"selections": 0, "groups": []},
    }
