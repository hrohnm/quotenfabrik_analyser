"""Three picks per fixture from the model probabilities, spread over the market groups.

Candidates are the model predictions of common markets (no scorers, no exotic lines). A candidate qualifies for a
profile when its probability lies in the profile's window; it is scored by probability plus weighted *lift*
(probability − league frequency of the last 3 seasons), so picks where the model sees something specific in this
match are preferred. Per fixture the best candidate of each market group is taken and the three best groups win
(spread / rotation: never two picks from the same group). Supporting pattern signals are attached as reasons.

Everything uses only information from before the matchday (walk-forward predictions, base rates, patterns).
"""

from dataclasses import dataclass
from decimal import Decimal

import numpy as np
import pandas as pd
from sqlalchemy import Engine, delete, text
from sqlalchemy.orm import Session

from quotenfabrik.analytics import evaluation as ev
from quotenfabrik.analytics.data import load_matches
from quotenfabrik.analytics.patterns import PatternContext, compute_patterns
from quotenfabrik.app_config import PROFILE_KEYS, get
from quotenfabrik.ingest.db_utils import upsert
from quotenfabrik.models import Pick


@dataclass(frozen=True)
class Profile:
    label: str
    min_p: float
    max_p: float
    lift_weight: float


def profiles() -> dict[str, Profile]:
    """Profiles with the thresholds from the configuration page (``app_config.SETTINGS``, ``picks.*``)."""
    return {
        key: Profile(
            label, get(f"picks.{key}.min_p"), get(f"picks.{key}.max_p"), get(f"picks.{key}.lift_weight")
        )
        for key, label in PROFILE_KEYS.items()
    }


def default_profile() -> str:
    return get("picks.default_profile")


PICKS_PER_FIXTURE = 3

# Common markets with usual lines (None = market without line). Handicaps, exotic lines and exact goals are left
# out: hard to read and, at Betano, with high margins (docs/11_betano_nebenmaerkte.md).
ALLOWED: dict[str, set[float] | None] = {
    "1x2": None, "dc": None, "btts": None, "ht_1x2": None, "clean_sheet": None, "btts_1h": None,
    "ou_ft": {1.5, 2.5, 3.5}, "ou_home": {0.5, 1.5, 2.5}, "ou_away": {0.5, 1.5, 2.5},
    "ou_1h": {0.5, 1.5}, "ou_2h": {0.5, 1.5},
    "ou_home_1h": {0.5}, "ou_away_1h": {0.5}, "ou_home_2h": {0.5}, "ou_away_2h": {0.5},
}  # fmt: skip

# Pattern (signal "high") -> supported selection; signal "low" supports the opposite of over/yes selections.
SUPPORT: dict[str, tuple[str, str, float | None]] = {
    "home_win_rate_home": ("1x2", "H", None), "h2h_home_wins": ("1x2", "H", None),
    "away_win_rate_away": ("1x2", "A", None),
    "home_draw_rate": ("1x2", "D", None), "away_draw_rate": ("1x2", "D", None),
    "home_o15": ("ou_ft", "over", 1.5), "away_o15": ("ou_ft", "over", 1.5), "combined_o15": ("ou_ft", "over", 1.5),
    "home_o25": ("ou_ft", "over", 2.5), "away_o25": ("ou_ft", "over", 2.5), "combined_o25": ("ou_ft", "over", 2.5),
    "home_o35": ("ou_ft", "over", 3.5), "away_o35": ("ou_ft", "over", 3.5), "combined_o35": ("ou_ft", "over", 3.5),
    "combined_btts": ("btts", "yes", None),
    "home_scored": ("ou_home", "over", 0.5), "away_conceded_away": ("ou_home", "over", 0.5),
    "home_2plus": ("ou_home", "over", 1.5), "away_conceded_2plus_away": ("ou_home", "over", 1.5),
    "away_scored": ("ou_away", "over", 0.5), "home_conceded_home": ("ou_away", "over", 0.5),
    "away_2plus": ("ou_away", "over", 1.5),
    "home_clean_sheet": ("clean_sheet", "home", None), "away_clean_sheet": ("clean_sheet", "away", None),
    "combined_o05_1h": ("ou_1h", "over", 0.5), "combined_o15_1h": ("ou_1h", "over", 1.5),
    "combined_o15_2h": ("ou_2h", "over", 1.5),
    "home_scored_1h": ("ou_home_1h", "over", 0.5), "away_scored_1h": ("ou_away_1h", "over", 0.5),
}  # fmt: skip
OPPOSITE = {"over": "under", "yes": "no"}


def supported_key(pattern_key: str, signal: str | None) -> tuple[str, str, float | None] | None:
    key = SUPPORT.get(pattern_key)
    if key is None or signal is None:
        return None
    if signal == "high":
        return key
    opposite = OPPOSITE.get(key[1])
    return (key[0], opposite, key[2]) if opposite else None


def is_candidate(market: str, line: float | None) -> bool:
    if market not in ALLOWED:
        return False
    lines = ALLOWED[market]
    return lines is None or (line is not None and not pd.isna(line) and float(line) in lines)


def select_picks(cands: pd.DataFrame, profile: Profile, n: int = PICKS_PER_FIXTURE) -> pd.DataFrame:
    """cands: fixture_id, market_group, market, selection, line, probability, base_rate (+ any extra columns).

    Returns at most n picks per fixture (one per market group) with ``score`` and ``rank``.
    """
    c = cands[cands["probability"].between(profile.min_p, profile.max_p)].copy()
    lift = (c["probability"] - c["base_rate"]).fillna(0.0)
    c["score"] = c["probability"] + profile.lift_weight * lift
    c = c.sort_values(["score", "market", "selection"], ascending=[False, True, True])
    best = c.groupby(["fixture_id", "market_group"], sort=False).head(1)
    picks = best.groupby("fixture_id", sort=False).head(n).copy()
    picks["rank"] = picks.groupby("fixture_id").cumcount() + 1
    return picks.sort_values(["fixture_id", "rank"]).reset_index(drop=True)


# --------------------------------------------------------------------------- base rates and pattern reasons


def base_rates(matches: pd.DataFrame, fixtures: pd.DataFrame) -> pd.DataFrame:
    """League frequency per selection over the 3 seasons before each matchday (as ``base_rate``)."""
    outcomes = ev.outcome_table(matches)
    keys = ["market", "selection", "line"]
    parts = []
    for _, md in fixtures.groupby(["season", "matchday"], dropna=False):
        as_of = md["kickoff"].min()
        hist = outcomes[
            (outcomes["kickoff"] < as_of) & (outcomes["kickoff"] >= as_of - pd.Timedelta(days=3 * 365))
        ]
        rates = hist.groupby(keys, dropna=False)["outcome"].mean().rename("base_rate").reset_index()
        hda = rates[rates["market"] == "1x2"].set_index("selection")["base_rate"]
        if {"H", "D", "A"} <= set(hda.index):  # double chance is not in the outcome table
            dc = pd.DataFrame({"market": "dc", "selection": ["1X", "X2", "12"], "line": np.nan,
                               "base_rate": [hda["H"] + hda["D"], hda["D"] + hda["A"], hda["H"] + hda["A"]]})  # fmt: skip
            rates = pd.concat([rates, dc], ignore_index=True)
        parts.append(rates.merge(md[["fixture_id"]], how="cross"))
    out = (
        pd.concat(parts, ignore_index=True)
        if parts
        else pd.DataFrame(columns=[*keys, "base_rate", "fixture_id"])
    )
    out["line"] = out["line"].astype(float)
    return out


def pattern_reasons(matches: pd.DataFrame, fixtures: pd.DataFrame) -> dict[tuple, list[dict]]:
    """Signals of the descriptive patterns (computed before each matchday) keyed by (fixture, market, sel, line)."""
    reasons: dict[tuple, list[dict]] = {}
    for _, md in fixtures.groupby(["season", "matchday"], dropna=False):
        ctx = PatternContext.build(matches, md["kickoff"].min())
        for f in md.itertuples(index=False):
            for p in compute_patterns(ctx, int(f.home_id), int(f.away_id)):
                key = supported_key(p.key, p.signal)
                if key:
                    reasons.setdefault((int(f.fixture_id), *key), []).append(
                        {
                            "label": p.label,
                            "value": p.value,
                            "baseline": p.baseline,
                            "n": p.n,
                            "signal": p.signal,
                        }
                    )
    return reasons


# --------------------------------------------------------------------------- build


_PREDICTIONS_SQL = text(
    """
    select p.id as prediction_id, p.model_run_id, p.fixture_id, p.market_group, p.market, p.selection,
           p.line::float as line, p.probability
    from analytics.predictions p
    join analytics.model_runs r on r.id = p.model_run_id
    where r.league_id = :league and r.kind in ('backtest', 'forecast') and p.market_group <> 'scorers'
      and (cast(:run as bigint) is null or r.id = cast(:run as bigint))
    """
)


def build_picks(engine: Engine, league_id: int, run_id: int | None = None) -> dict:
    """Computes and stores the picks of all profiles for the backtest and forecast runs of a league."""
    preds = pd.read_sql(_PREDICTIONS_SQL, engine, params={"league": league_id, "run": run_id})
    preds = preds[[is_candidate(m, ln) for m, ln in zip(preds["market"], preds["line"], strict=True)]]
    if preds.empty:
        return {"runs": 0, "picks": 0}
    matches = load_matches(engine, league_id)
    fixtures = matches[matches["fixture_id"].isin(preds["fixture_id"].unique())][
        ["fixture_id", "season", "matchday", "kickoff", "home_id", "away_id"]
    ].copy()
    cup = fixtures["matchday"].isna().all()  # European cups: no matchdays, results only
    if cup:  # group by ISO week instead of matchday
        iso = fixtures["kickoff"].dt.isocalendar()
        fixtures["matchday"] = iso["year"].astype(int) * 100 + iso["week"].astype(int)
    rates = base_rates(matches, fixtures)
    preds = preds.merge(rates, on=["fixture_id", "market", "selection", "line"], how="left")
    reasons = {} if cup else pattern_reasons(matches, fixtures)  # patterns are validated for leagues only

    rows = []
    for name, profile in profiles().items():
        for run, part in preds.groupby("model_run_id"):
            for r in select_picks(part, profile).itertuples(index=False):
                line = None if pd.isna(r.line) else r.line
                rows.append(
                    {"model_run_id": int(run), "prediction_id": int(r.prediction_id), "fixture_id": int(r.fixture_id),
                     "profile": name, "rank": int(r.rank), "market_group": r.market_group, "market": r.market,
                     "selection": r.selection, "line": None if line is None else Decimal(str(line)),
                     "probability": float(r.probability),
                     "base_rate": None if pd.isna(r.base_rate) else float(r.base_rate), "score": float(r.score),
                     "reasons": reasons.get((int(r.fixture_id), r.market, r.selection, line)) or None}
                )  # fmt: skip
    runs = [int(r) for r in preds["model_run_id"].unique()]
    with Session(engine) as session:
        session.execute(delete(Pick).where(Pick.model_run_id.in_(runs)))
        upsert(session, Pick, rows, update=False)
        session.commit()
    return {"runs": len(runs), "fixtures": int(preds["fixture_id"].nunique()), "picks": len(rows)}


def picks_missing(engine: Engine) -> bool:
    with engine.connect() as conn:
        return not conn.execute(text("select 1 from analytics.picks limit 1")).first()


# --------------------------------------------------------------------------- evaluation

CALIBRATION_BINS = [0.0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]


def _rate(frame: pd.DataFrame) -> dict:
    return {"n": len(frame), "hit_rate": float(frame["outcome"].mean()) if len(frame) else None,
            "expected": float(frame["probability"].mean()) if len(frame) else None}  # fmt: skip


def combos(frame: pd.DataFrame) -> pd.DataFrame:
    """One row per fixture with all picks settled: hits, combo hit, naive combo probability (product)."""
    g = frame.groupby("fixture_id")
    out = pd.DataFrame(
        {"season": g["season"].first(), "n": g.size(), "hits": g["outcome"].sum(),
         "p_naive": g["probability"].prod(), "p_mean": g["probability"].mean()}
    )  # fmt: skip
    out = out[out["n"] == PICKS_PER_FIXTURE]
    out["hit"] = out["hits"] == PICKS_PER_FIXTURE
    return out


def _combo_rate(c: pd.DataFrame) -> dict:
    if c.empty:
        return {"n": 0}
    return {"n": len(c), "hit_rate": float(c["hit"].mean()), "expected_naive": float(c["p_naive"].mean()),
            "fair_odd_median": float(np.median(1 / c["p_naive"]))}  # fmt: skip


def evaluate_picks(frame: pd.DataFrame) -> dict:
    """Hit rates of settled picks of one profile.

    frame: fixture_id, season, rank, market, selection, line, probability, outcome (bool), has_reason (bool).
    """
    frame = frame[frame["outcome"].notna()].copy()
    frame["outcome"] = frame["outcome"].astype(bool)
    c = combos(frame)
    keys = ["market", "selection", "line"]
    per_market = [
        {"market": m, "selection": s, "line": None if pd.isna(ln) else float(ln), **_rate(g)}
        for (m, s, ln), g in frame.groupby(keys, dropna=False)
    ]
    bins = pd.cut(frame["probability"], CALIBRATION_BINS)
    return {
        "singles": _rate(frame),
        "combo": _combo_rate(c),
        "hits_distribution": {str(k): float((c["hits"] == k).mean()) if len(c) else None for k in range(4)},
        "per_rank": [{"rank": int(r), **_rate(g)} for r, g in frame.groupby("rank")],
        "per_market": sorted(per_market, key=lambda m: -m["n"]),
        "per_season": [
            {"season": int(s), **_rate(g), "combo": _combo_rate(c[c["season"] == s])}
            for s, g in frame.groupby("season")
        ],
        "calibration": [
            {"bin": f"{b.left * 100:.0f}–{b.right * 100:.0f} %", **_rate(g)}
            for b, g in frame.groupby(bins, observed=True)
        ],
        "reasons": {"with": _rate(frame[frame["has_reason"]]), "without": _rate(frame[~frame["has_reason"]])},
    }
