"""Phase 3, step 1: walk-forward predictions against historical football-data.co.uk odds (1X2, O/U 2.5).

Questions answered:
1. Quality: is the model (or a model/market blend) better than the margin-free bookmaker probabilities?
2. Information: do odds move towards the model between opening and closing (CLV)?
3. Betting: flat-stake value bets on soft (Bet365, proxy for Betano) and sharp (Pinnacle) odds – ROI with
   bootstrap interval, CLV, drawdown.

Everything that is chosen (blend weights, edge threshold) is fitted on the validation seasons only and then
evaluated once on the test seasons.
"""

import dataclasses
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sqlalchemy import Engine, text

from quotenfabrik.analytics.value import (
    closing_line_value,
    expected_value,
    log_pool,
    overround,
    remove_margin,
)


@dataclass(frozen=True)
class MarketSpec:
    key: str
    label: str
    market: str
    line: float | None
    selections: tuple[str, ...]
    suffixes: tuple[str, ...]  # football-data column suffixes, same order as selections


MARKETS = (
    MarketSpec("1x2", "1X2", "1x2", None, ("H", "D", "A"), ("h", "d", "a")),
    MarketSpec("ou25", "Über/Unter 2,5", "ou_ft", 2.5, ("over", "under"), ("o25", "u25")),
)
# football-data column prefixes: (opening = when the CSV is compiled, ~Fri/Tue before the match; closing)
BOOKS = {"pinnacle": ("ps", "psc"), "b365": ("b365", "b365c"), "avg": ("avg", "avgc")}
BOOK_LABELS = {"pinnacle": "Pinnacle", "b365": "Bet365 (Proxy für Betano)", "avg": "Marktschnitt"}
BET_BOOKS = ("b365", "pinnacle")
THRESHOLDS = (0.0, 0.02, 0.04, 0.06, 0.08, 0.10)
MIN_VALIDATION_BETS = 50


@dataclass
class MarketData:
    spec: MarketSpec
    fixture_id: np.ndarray
    season: np.ndarray
    date: np.ndarray
    p_model: np.ndarray  # (n, k)
    y: np.ndarray  # (n, k) one-hot outcome
    odds: dict[str, dict[str, np.ndarray]] = field(default_factory=dict)  # book -> open/close -> (n, k)

    def __len__(self) -> int:
        return len(self.fixture_id)

    def reference(self, when: str, method: str = "shin") -> np.ndarray:
        """Margin-free market probabilities: Pinnacle, else market average, else Bet365."""
        out = np.full(self.p_model.shape, np.nan)
        for book in ("pinnacle", "avg", "b365"):
            p = remove_margin(self.odds[book][when], method)
            missing = np.isnan(out).any(axis=1)
            out[missing] = p[missing]
        return out


_SQL = text(
    """
    select p.fixture_id, f.season, p.selection, p.probability, p.outcome
    from analytics.predictions p
    join analytics.model_runs r on r.id = p.model_run_id and r.kind = 'backtest' and r.league_id = :league
    join core.fixtures f on f.id = p.fixture_id
    where p.market = :market and (p.line = :line or (:line is null and p.line is null))
    """
)


def load_market(engine: Engine, league_id: int, spec: MarketSpec) -> MarketData:
    preds = pd.read_sql(_SQL, engine, params={"league": league_id, "market": spec.market, "line": spec.line})
    hist = pd.read_sql(
        text("select * from core.historical_matches where fixture_id is not null"), engine
    ).drop(columns="raw_row")
    return build_market(spec, preds, hist)


def build_market(spec: MarketSpec, preds: pd.DataFrame, hist: pd.DataFrame) -> MarketData:
    """Joins long-format predictions (fixture_id, season, selection, probability, outcome) with odds rows."""
    sel = list(spec.selections)
    p = preds.pivot_table(index="fixture_id", columns="selection", values="probability")
    y = preds.pivot_table(index="fixture_id", columns="selection", values="outcome", aggfunc="first")
    season = preds.groupby("fixture_id")["season"].first()
    ids = p.dropna(subset=sel).index.intersection(y.dropna(subset=sel).index)
    df = (
        pd.DataFrame({"fixture_id": ids, "season": season.loc[ids].to_numpy()})
        .merge(hist, on="fixture_id")
        .sort_values(["match_date", "fixture_id"])
        .reset_index(drop=True)
    )
    data = MarketData(
        spec=spec,
        fixture_id=df["fixture_id"].to_numpy(),
        season=df["season"].to_numpy(),
        date=pd.to_datetime(df["match_date"]).to_numpy(),
        p_model=p.loc[df["fixture_id"], sel].to_numpy(dtype=float),
        y=y.loc[df["fixture_id"], sel].to_numpy(dtype=float),
    )
    for book, prefixes in BOOKS.items():
        data.odds[book] = {}
        for when, prefix in zip(("open", "close"), prefixes, strict=True):
            cols = [f"{prefix}_{s}" for s in spec.suffixes]
            values = (
                df[cols].to_numpy(dtype=float, copy=True)
                if all(c in df for c in cols)
                else np.full(data.y.shape, np.nan)
            )
            values[~(values > 1).all(axis=1)] = np.nan  # incomplete or invalid odds (e.g. 0 in the CSV)
            data.odds[book][when] = values
    return data


# --------------------------------------------------------------------------- quality


def log_loss(p: np.ndarray, y: np.ndarray) -> float:
    return float(-np.mean(np.log(np.clip((p * y).sum(axis=1), 1e-12, 1))))


def brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean(((p - y) ** 2).sum(axis=1)))


def rps(p: np.ndarray, y: np.ndarray) -> float:
    """Ranked probability score for ordered outcomes (home, draw, away)."""
    cp, cy = np.cumsum(p, axis=1)[:, :-1], np.cumsum(y, axis=1)[:, :-1]
    return float(np.mean(((cp - cy) ** 2).sum(axis=1) / (p.shape[1] - 1)))


def quality(data: MarketData, sources: dict[str, np.ndarray], mask: np.ndarray) -> dict[str, dict]:
    """Metrics per probability source on the rows where every source is available."""
    ok = mask & np.all([~np.isnan(p).any(axis=1) for p in sources.values()], axis=0)
    out = {}
    for name, p in sources.items():
        out[name] = {
            "n": int(ok.sum()),
            "log_loss": log_loss(p[ok], data.y[ok]),
            "brier": brier(p[ok], data.y[ok]),
        }
        if data.y.shape[1] == 3:
            out[name]["rps"] = rps(p[ok], data.y[ok])
    return out


def fit_blend(p_market: np.ndarray, p_model: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Weights (market, model) of the logarithmic pool with minimal log-loss."""
    ok = ~np.isnan(p_market).any(axis=1)

    def loss(w):
        return log_loss(log_pool(p_market[ok], p_model[ok], w[0], w[1]), y[ok])

    w = minimize(loss, x0=[1.0, 0.0], method="Nelder-Mead", options={"xatol": 1e-4, "fatol": 1e-7}).x
    return float(w[0]), float(w[1])


def movement(data: MarketData, p_open: np.ndarray, p_close: np.ndarray, mask: np.ndarray) -> dict:
    """Do odds move towards the model? Correlation of (model − open) with (close − open), all selections."""
    ok = mask & ~np.isnan(p_open).any(axis=1) & ~np.isnan(p_close).any(axis=1)
    diff = (data.p_model - p_open)[ok].ravel()
    move = (p_close - p_open)[ok].ravel()
    big = np.abs(diff) >= 0.05
    return {
        "n": int(ok.sum()),
        "corr": float(np.corrcoef(diff, move)[0, 1]) if diff.std() > 0 and move.std() > 0 else None,
        # among clear disagreements (≥ 5 points): share where the market moved towards the model
        "towards_model": float(np.mean(np.sign(move[big]) == np.sign(diff[big]))) if big.any() else None,
        "n_disagreements": int(big.sum()),
    }


# --------------------------------------------------------------------------- betting


def value_bets(
    data: MarketData, p: np.ndarray, book: str, threshold: float, mask: np.ndarray, p_close: np.ndarray
) -> pd.DataFrame:
    """At most one flat-stake bet per match: the selection with the largest edge above the threshold."""
    odds = data.odds[book]["open"]
    edge = expected_value(p, odds)
    edge = np.where(np.isnan(edge), -np.inf, edge)
    best = edge.argmax(axis=1)
    rows = np.arange(len(data))
    take = mask & (edge[rows, best] > threshold) & np.isfinite(edge[rows, best])
    i, j = rows[take], best[take]
    won = data.y[i, j] == 1
    odd = odds[i, j]
    return pd.DataFrame(
        {
            "fixture_id": data.fixture_id[i],
            "season": data.season[i],
            "date": data.date[i],
            "selection": np.asarray(data.spec.selections)[j],
            "probability": p[i, j],
            "odd": odd,
            "edge": edge[i, j],
            "closing_odd": data.odds[book]["close"][i, j],
            "clv": closing_line_value(odd, p_close[i, j]),
            "won": won,
            "profit": np.where(won, odd - 1, -1.0),
        }
    )


def summarize(bets: pd.DataFrame, seed: int = 7, draws: int = 2000) -> dict:
    n = len(bets)
    if n == 0:
        return {"n": 0}
    profit = bets["profit"].to_numpy()
    rng = np.random.default_rng(seed)
    boot = profit[rng.integers(0, n, size=(draws, n))].mean(axis=1)
    curve = np.cumsum(profit)
    clv = bets["clv"].dropna()
    return {
        "n": n,
        "hit_rate": float(bets["won"].mean()),
        "avg_odd": float(bets["odd"].mean()),
        "profit": float(profit.sum()),
        "roi": float(profit.mean()),
        "roi_low": float(np.quantile(boot, 0.025)),
        "roi_high": float(np.quantile(boot, 0.975)),
        "clv": float(clv.mean()) if len(clv) else None,
        "clv_positive": float((clv > 0).mean()) if len(clv) else None,
        "max_drawdown": float((np.maximum.accumulate(np.r_[0, curve]) - np.r_[0, curve]).max()),
    }


def choose_threshold(validation: dict[float, dict]) -> float:
    """Validation threshold with the best ROI among those with enough bets (fallback: no threshold)."""
    candidates = [(s["roi"], t) for t, s in validation.items() if s.get("n", 0) >= MIN_VALIDATION_BETS]
    return max(candidates)[1] if candidates else THRESHOLDS[0]


@dataclass
class MarketResult:
    spec: MarketSpec
    n: int
    validation_seasons: list[int]
    test_seasons: list[int]
    margins: dict[str, float]
    quality: dict[str, dict[str, dict]]  # period -> source -> metrics
    blend: tuple[float, float]
    movement: dict[str, dict]
    strategies: list[dict]
    bets: pd.DataFrame


def analyse_market(data: MarketData, validation_until: int, method: str = "shin") -> MarketResult:
    val = data.season <= validation_until
    test = ~val
    p_open, p_close = data.reference("open", method), data.reference("close", method)
    blend_w = fit_blend(p_open[val], data.p_model[val], data.y[val])
    p_blend = log_pool(p_open, data.p_model, *blend_w)
    sources = {"model": data.p_model, "open": p_open, "blend": p_blend, "close": p_close}
    margins = {}
    for book in BOOKS:
        o = data.odds[book]["open"][test]
        o = o[~np.isnan(o).any(axis=1)]
        if len(o):
            margins[book] = float(overround(o).mean())

    strategies, all_bets = [], []
    for source in ("model", "blend"):
        p = sources[source]
        for book in BET_BOOKS:
            val_stats = {t: summarize(value_bets(data, p, book, t, val, p_close)) for t in THRESHOLDS}
            test_stats = {t: summarize(value_bets(data, p, book, t, test, p_close)) for t in THRESHOLDS}
            chosen = choose_threshold(val_stats)
            bets = value_bets(data, p, book, chosen, val | test, p_close)
            bets["period"] = np.where(bets["season"] <= validation_until, "validation", "test")
            bets["source"], bets["book"], bets["threshold"] = source, book, chosen
            all_bets.append(bets)
            per_season = {int(s): summarize(b) for s, b in bets[bets["period"] == "test"].groupby("season")}
            strategies.append(
                {"source": source, "book": book, "threshold": chosen, "validation": val_stats[chosen],
                 "test": test_stats[chosen], "grid_test": test_stats, "per_season": per_season}
            )  # fmt: skip
    return MarketResult(
        spec=data.spec,
        n=len(data),
        validation_seasons=sorted({int(s) for s in data.season[val]}),
        test_seasons=sorted({int(s) for s in data.season[test]}),
        margins=margins,
        quality={"validation": quality(data, sources, val), "test": quality(data, sources, test)},
        blend=blend_w,
        movement={
            "validation": movement(data, p_open, p_close, val),
            "test": movement(data, p_open, p_close, test),
        },
        strategies=strategies,
        bets=pd.concat(all_bets, ignore_index=True),
    )


def result_summary(result: MarketResult) -> dict:
    """JSON-serialisable summary (for ``analytics.model_runs.summary``)."""
    d = {
        f.name: getattr(result, f.name) for f in dataclasses.fields(result) if f.name not in {"spec", "bets"}
    }
    d["market"] = result.spec.key
    d["strategies"] = [
        {**s, "grid_test": {f"{t:.2f}": g for t, g in s["grid_test"].items()}} for s in result.strategies
    ]
    return d
