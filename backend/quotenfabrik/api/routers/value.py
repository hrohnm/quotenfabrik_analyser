"""Value tips of a day (frozen, current or retrospective) and their evaluation (backtest and live record)."""

import logging
from datetime import date

import pandas as pd
from fastapi import APIRouter, Query

from quotenfabrik import app_config
from quotenfabrik.analytics import value_tips as vt
from quotenfabrik.api.data import df, engine, json_safe
from quotenfabrik.api.labels import GROUP_LABELS, pick_label
from quotenfabrik.api.routers.fixtures import FIXTURE_SQL, _clean, _fixture_dict
from quotenfabrik.api.routers.stats import _Background

router = APIRouter(prefix="/api", tags=["value"])
log = logging.getLogger(__name__)


def _tip(t, home: str, away: str) -> dict:
    line = None if pd.isna(t.line) else float(t.line)
    outcome = getattr(t, "outcome", None)
    return {
        "market": t.market, "selection": t.selection, "line": line, "group": _clean(getattr(t, "market_group", None)),
        "group_label": GROUP_LABELS.get(getattr(t, "market_group", None) or "", None),
        "label": pick_label(t.market, t.selection, line, home, away),
        "probability": float(t.probability), "p_model": float(t.p_model),
        "p_market": None if pd.isna(t.p_market) else float(t.p_market),
        "odds": round(float(t.taken), 2), "fair_odd": 1 / float(t.probability), "edge": float(t.edge),
        "outcome": None if outcome is None or pd.isna(outcome) else bool(outcome),
    }  # fmt: skip


@router.get("/value")
def value_day(day: date = Query(..., alias="date"), league: int | None = None) -> dict:
    """Value tips of the fixtures of a day: frozen ones (shown on the day), otherwise at the current prices
    (upcoming) or retrospectively at the price when the tip would have been shown (``source``)."""
    settings = app_config.value_settings()
    rows = df(
        f"""{FIXTURE_SQL} where (f.kickoff_utc at time zone 'Europe/Berlin')::date = :day
            and f.league_id = any(:leagues) order by f.kickoff_utc, f.id""",
        day=day, leagues=[league] if league else app_config.shown_league_ids(),
    )  # fmt: skip
    fixtures = {int(r.id): _fixture_dict(r) for r in rows.itertuples()}
    ids = list(fixtures)
    tips: dict[int, tuple[str, pd.DataFrame]] = {}
    if ids:
        frozen = vt.frozen(engine(), "v.fixture_id = any(:ids)", ids=ids)
        for f, g in frozen.groupby("fixture_id"):
            tips[int(f)] = ("fixiert", g)
        open_ids = [f for f in ids if f not in tips and not fixtures[f]["finished"]]
        current = vt.current_tips(engine(), open_ids, settings)
        for f, g in current.groupby("fixture_id") if len(current) else []:
            tips[int(f)] = ("aktuell", g)
        past = [f for f in ids if f not in tips and fixtures[f]["finished"]]
        if past:
            cand = vt.load_candidates(engine(), "and p.fixture_id = any(:ids)", ids=past)
            if len(cand):
                retro = vt.select(vt.blend(vt.with_prices(engine(), cand.assign(p_model=cand["probability"])),
                                           settings), settings)  # fmt: skip
                for f, g in retro.groupby("fixture_id") if len(retro) else []:
                    tips[int(f)] = ("rückwirkend", g)
    out = []
    for f, fx in fixtures.items():
        if f in tips:
            source, g = tips[f]
            home, away = fx["home"]["name"], fx["away"]["name"]
            out.append({"fixture": fx, "source": source,
                        "tips": [_tip(t, home, away) for t in g.sort_values("edge", ascending=False).itertuples()]})  # fmt: skip
    return json_safe({"fixtures_checked": len(fixtures), "settings": settings.__dict__, "fixtures": out})


_backtest = _Background(
    "value backtest",
    lambda: vt.backtest(engine(), app_config.shown_league_ids(), app_config.value_settings()),
    ttl=3600,
)


@router.get("/stats/value")
def value_stats() -> dict:
    """Backtest of the value tips (current settings) and the live record of the frozen tips; a failing part
    is reported in ``error`` instead of failing the whole response."""
    backtest = _backtest.get()
    if backtest is None:
        backtest = {"candidates": 0, "error": _backtest.error}
    try:
        live = vt.live_record(engine())
    except Exception as exc:  # noqa: BLE001 - shown on the page
        log.exception("value live record failed")
        live = {"n": 0, "fixtures": 0, "error": f"{type(exc).__name__}: {exc}"}
    return json_safe({"backtest": backtest, "live": live})
