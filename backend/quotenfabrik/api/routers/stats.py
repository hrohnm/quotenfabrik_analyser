"""Evaluation page: hit rates of the model per league, season and market."""

import threading
import time

import numpy as np
import pandas as pd
from fastapi import APIRouter, Query

from quotenfabrik import app_config
from quotenfabrik.analytics.picks import default_profile, evaluate_picks, profiles
from quotenfabrik.api.data import chosen_runs_cte, df
from quotenfabrik.api.labels import GROUP_LABELS, MARKET_LABELS, PICK_SETS, SELECTION_LABELS, pick_label

router = APIRouter(prefix="/api/stats", tags=["stats"])

_cache: dict = {}
_lock = threading.Lock()
CACHE_TTL_S = 300
CONFIDENCE_BINS = [0, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]


def _settled(league_id: int) -> pd.DataFrame:
    """All settled predictions (chosen run per fixture) of a league, cached."""
    with _lock:
        hit = _cache.get(league_id)
        if hit and time.time() - hit[0] < CACHE_TTL_S:
            return hit[1]
        data = df(
            f"""with runs as ({chosen_runs_cte("and f.league_id = :league")})
                select p.fixture_id, f.season, p.market_group, p.market, p.selection, p.line, p.probability,
                       p.outcome, runs.kind
                from analytics.predictions p
                join runs on runs.model_run_id = p.model_run_id and runs.fixture_id = p.fixture_id
                join core.fixtures f on f.id = p.fixture_id
                where f.league_id = :league and p.outcome is not null""",
            league=league_id,
        )
        data["line"] = data["line"].astype(float)
        data["outcome"] = data["outcome"].astype(bool)
        _cache[league_id] = (time.time(), data)
        return data


def _filter(data: pd.DataFrame, season: int | None, group: str | None) -> pd.DataFrame:
    if season:
        data = data[data["season"] == season]
    if group:
        data = data[data["market_group"] == group]
    return data


def picks(data: pd.DataFrame) -> pd.DataFrame:
    """One row per (fixture, market, line): the model's most likely selection and whether it came true.

    Markets with exclusive selections: pick = most likely selection. Other markets (double chance, BTTS per
    half, clean sheet): every selection is a yes/no call (yes if probability >= 50 %).
    """
    data = data[~data["market"].str.startswith("scorer")]
    sets = data[data["market"].isin(PICK_SETS)]
    idx = sets.groupby(["fixture_id", "market", "line"], dropna=False)["probability"].idxmax()
    exclusive = sets.loc[idx].assign(pick_probability=lambda d: d["probability"], hit=lambda d: d["outcome"])
    single = data[~data["market"].isin(PICK_SETS)].copy()
    yes = single["probability"] >= 0.5
    single["pick_probability"] = np.where(yes, single["probability"], 1 - single["probability"])
    single["hit"] = yes == single["outcome"]
    return pd.concat([exclusive, single], ignore_index=True)


def _bin_label(b: pd.Interval) -> str:
    return f"{max(b.left, 0) * 100:.0f}–{b.right * 100:.0f} %"


def _league(league: int | None) -> int:
    return league or app_config.league_ids()[0]


@router.get("/overview")
def overview(league: int | None = None, season: int | None = None) -> dict:
    data = _filter(_settled(_league(league)), season, None)
    pk = picks(data)
    groups = []
    for group, g in pk.groupby("market_group"):
        groups.append({"group": group, "label": GROUP_LABELS.get(group, group), "picks": int(len(g)),
                       "hit_rate": float(g["hit"].mean()), "expected_hit_rate": float(g["pick_probability"].mean())})  # fmt: skip
    sc = _scorer_top_picks(data)
    return {
        "fixtures": int(data["fixture_id"].nunique()),
        "seasons": sorted(int(s) for s in data["season"].unique()),
        "groups": groups,
        "scorers": sc,
    }


@router.get("/markets")
def markets(league: int | None = None, season: int | None = None, group: str | None = None) -> list[dict]:
    data = _filter(_settled(_league(league)), season, group)
    pk = picks(data)
    brier = (
        data[~data["market"].str.startswith("scorer")]
        .assign(
            se=lambda d: (d["probability"] - d["outcome"].astype(float)) ** 2,
            line_key=lambda d: d["line"].fillna(-1),
        )
        .groupby(["market", "line_key"])["se"]
        .mean()
        .to_dict()
    )
    rows = []
    for (grp, market, line), g in pk.groupby(["market_group", "market", "line"], dropna=False):
        top = g["selection"].value_counts()
        rows.append({
            "group": grp, "group_label": GROUP_LABELS.get(grp, grp), "market": market,
            "label": MARKET_LABELS.get(market, market), "line": None if pd.isna(line) else float(line),
            "picks": int(len(g)), "hit_rate": float(g["hit"].mean()),
            "expected_hit_rate": float(g["pick_probability"].mean()),
            "brier": brier.get((market, -1 if pd.isna(line) else line)),
            "most_picked": SELECTION_LABELS.get(top.index[0], top.index[0]) if len(top) else None,
        })  # fmt: skip
    order = list(GROUP_LABELS)
    return sorted(rows, key=lambda r: (order.index(r["group"]), r["market"], r["line"] or 0))


def _market_filter(data: pd.DataFrame, market: str, line: float | None) -> pd.DataFrame:
    data = data[data["market"] == market]
    return data[data["line"].isna()] if line is None else data[data["line"] == line]


@router.get("/confidence")
def confidence(
    market: str = "1x2", line: float | None = None, league: int | None = None, season: int | None = None
) -> list[dict]:
    """Hit rate of the pick by the model's confidence (probability of the picked selection)."""
    pk = picks(_market_filter(_filter(_settled(_league(league)), season, None), market, line))
    pk = pk.assign(bin=pd.cut(pk["pick_probability"], CONFIDENCE_BINS, include_lowest=True))
    out = []
    for b, g in pk.groupby("bin", observed=True):
        out.append({"bin": _bin_label(b), "picks": int(len(g)),
                    "hit_rate": float(g["hit"].mean()), "expected_hit_rate": float(g["pick_probability"].mean())})  # fmt: skip
    return out


@router.get("/calibration")
def calibration(
    market: str = "ou_ft", selection: str = "over", line: float | None = None, league: int | None = None,
    season: int | None = None, bins: int = Query(10, ge=4, le=20),
) -> list[dict]:  # fmt: skip
    """Predicted vs. observed frequency of one selection."""
    data = _market_filter(_filter(_settled(_league(league)), season, None), market, line)
    data = data[data["selection"] == selection]
    cut = pd.cut(data["probability"], np.linspace(0, 1, bins + 1), include_lowest=True)
    out = []
    for b, g in data.groupby(cut, observed=True):
        out.append({"bin": _bin_label(b), "n": int(len(g)),
                    "predicted": float(g["probability"].mean()), "observed": float(g["outcome"].mean())})  # fmt: skip
    return out


@router.get("/seasons")
def seasons(market: str = "1x2", line: float | None = None, league: int | None = None) -> list[dict]:
    pk = picks(_market_filter(_settled(_league(league)), market, line))
    return [
        {"season": int(s), "picks": int(len(g)), "hit_rate": float(g["hit"].mean()),
         "expected_hit_rate": float(g["pick_probability"].mean())}
        for s, g in pk.groupby("season")
    ]  # fmt: skip


def _scorer_top_picks(data: pd.DataFrame) -> dict | None:
    """Top anytime-scorer pick per team and match: how often did he score?"""
    sc = data[data["market"] == "scorer_anytime"]
    if sc.empty:
        return None
    teams = df("select fixture_id, player_id::text as selection, team_id from core.fixture_player_stats "
               "where fixture_id = any(:ids)", ids=sc["fixture_id"].unique().tolist())  # fmt: skip
    sc = sc.merge(teams, on=["fixture_id", "selection"], how="left")
    top = sc.loc[sc.groupby(["fixture_id", "team_id"])["probability"].idxmax()]
    return {"picks": int(len(top)), "hit_rate": float(top["outcome"].mean()),
            "expected_hit_rate": float(top["probability"].mean())}  # fmt: skip


@router.get("/scorers")
def scorers(league: int | None = None, season: int | None = None) -> dict:
    data = _filter(_settled(_league(league)), season, None)
    sc = data[data["market"] == "scorer_anytime"]
    cut = pd.cut(sc["probability"], [0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.6, 1.0], include_lowest=True)
    calib = [{"bin": _bin_label(b), "n": int(len(g)),
              "predicted": float(g["probability"].mean()), "observed": float(g["outcome"].mean())}
             for b, g in sc.groupby(cut, observed=True)]  # fmt: skip
    return {"top_picks": _scorer_top_picks(data), "calibration": calib}


_picks_cache: dict = {}


def _settled_picks(league_id: int) -> pd.DataFrame:
    """Settled picks of all profiles (chosen run per fixture), cached."""
    with _lock:
        hit = _picks_cache.get(league_id)
        if hit and time.time() - hit[0] < CACHE_TTL_S:
            return hit[1]
        data = df(
            f"""with runs as ({chosen_runs_cte("and f.league_id = :league")})
                select k.fixture_id, f.season, k.profile, k.rank, k.market, k.selection, k.line, k.probability,
                       p.outcome, jsonb_typeof(k.reasons) = 'array' as has_reason
                from analytics.picks k
                join runs on runs.model_run_id = k.model_run_id and runs.fixture_id = k.fixture_id
                join analytics.predictions p on p.id = k.prediction_id
                join core.fixtures f on f.id = k.fixture_id
                where f.league_id = :league and p.outcome is not null""",
            league=league_id,
        )
        data["line"] = data["line"].astype(float)
        data["has_reason"] = data["has_reason"].fillna(False).astype(bool)
        _picks_cache[league_id] = (time.time(), data)
        return data


@router.get("/picks")
def pick_stats(league: int | None = None, season: int | None = None, profile: str | None = None) -> dict:
    """Hit rates of the suggested picks: per profile (singles and 3-pick combo) and details for one profile.

    Without ``league`` all configured leagues are combined.
    """
    leagues = [league] if league else app_config.league_ids()
    data = pd.concat([_settled_picks(lg) for lg in leagues], ignore_index=True)
    if season:
        data = data[data["season"] == season]
    overview = []
    profile = profile or default_profile()
    for key, p in profiles().items():
        result = evaluate_picks(data[data["profile"] == key])
        overview.append(
            {"profile": key, "label": p.label, "singles": result["singles"], "combo": result["combo"]}
        )
    detail = evaluate_picks(data[data["profile"] == profile])
    for m in detail["per_market"]:
        m["label"] = pick_label(m["market"], m["selection"], m["line"], "Heimteam", "Gastteam")
    return {"profiles": overview, "profile": profile, "detail": detail}
