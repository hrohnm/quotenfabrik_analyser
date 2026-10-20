"""Daily combos and bet tracking."""

import time
from datetime import date
from decimal import Decimal

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from quotenfabrik import app_config, bets
from quotenfabrik.analytics import combos
from quotenfabrik.api.data import chosen_runs_cte, df, records
from quotenfabrik.api.labels import league_logo, pick_label
from quotenfabrik.db import get_engine
from quotenfabrik.models import Bet, BetLeg

router = APIRouter(prefix="/api", tags=["bets"])

_CACHE: dict[tuple, tuple[float, list]] = {}
CACHE_TTL_S = 600


def _day_predictions(day: date) -> pd.DataFrame:
    where = "and (f.kickoff_utc at time zone 'Europe/Berlin')::date = :day and f.league_id = any(:leagues)"
    return df(
        f"""with runs as ({chosen_runs_cte(where)})
            select p.fixture_id, p.model_run_id, p.market, p.selection, p.line::float as line, p.probability,
                   p.outcome, f.league_id, f.season, f.kickoff_utc as kickoff,
                   f.home_team_id, h.name as home_name, h.logo_url as home_logo,
                   f.away_team_id, a.name as away_name, a.logo_url as away_logo, f.status
            from analytics.predictions p
            join runs on runs.model_run_id = p.model_run_id and runs.fixture_id = p.fixture_id
            join core.fixtures f on f.id = p.fixture_id
            join core.teams h on h.id = f.home_team_id join core.teams a on a.id = f.away_team_id
            where p.market in ('ou_ft', 'ou_home', 'ou_away', 'dc') and p.selection in ('over', '1X', 'X2', '12')""",
        day=day, leagues=app_config.shown_league_ids(),
    )  # fmt: skip


@router.get("/combos")
def day_combos(day: date = Query(..., alias="date")) -> list[dict]:
    """Daily combos (Tore Über, Team-Tore Über, Doppelte Chance) of one day; empty without enough fixtures."""
    preds = _day_predictions(day)
    if preds.empty:
        return []
    key = (day, tuple(sorted(preds["model_run_id"].unique())), tuple(sorted(app_config.all_values().items())))
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL_S:
        return hit[1]
    preds["kickoff"] = pd.to_datetime(preds["kickoff"], utc=True)
    with_rates = combos.with_base_rates(get_engine(), preds)
    out = []
    for c in combos.build_day(
        with_rates, app_config.combo_settings(), rotation=pd.Timestamp(day).toordinal()
    ):
        legs = []
        for leg in sorted(c.legs, key=lambda x: x["kickoff"]):
            line = leg["line"]
            legs.append({
                "fixture_id": int(leg["fixture_id"]), "kickoff": leg["kickoff"].isoformat(),
                "league": {"id": int(leg["league_id"]), "logo": league_logo(int(leg["league_id"]))},
                "home": {"id": int(leg["home_team_id"]), "name": leg["home_name"], "logo": leg["home_logo"]},
                "away": {"id": int(leg["away_team_id"]), "name": leg["away_name"], "logo": leg["away_logo"]},
                "market": leg["market"], "selection": leg["selection"], "line": line,
                "label": pick_label(leg["market"], leg["selection"], line, leg["home_name"], leg["away_name"]),
                "probability": float(leg["probability"]), "odds": round(float(leg["odds"]), 2),
                "outcome": None if leg["outcome"] is None else bool(leg["outcome"]),
            })  # fmt: skip
        out.append({"kind": c.kind, "label": combos.KINDS[c.kind], "odds": round(c.odds, 2),
                    "probability": c.probability, "outcome": c.outcome, "legs": legs})  # fmt: skip
    _CACHE[key] = (time.time(), out)
    return out


# --------------------------------------------------------------------------- bets


class NewLeg(BaseModel):
    fixture_id: int | None = None
    market: str | None = None
    selection: str | None = None
    line: float | None = None
    label: str
    probability: float | None = Field(None, ge=0, le=1)
    odds: float | None = Field(None, gt=1)


class NewBet(BaseModel):
    label: str = Field(min_length=1)
    source: str = "manuell"
    bookmaker: str = "Betano"
    stake: float = Field(gt=0)
    odds: float = Field(gt=1)
    probability: float | None = Field(None, ge=0, le=1)
    notes: str | None = None
    legs: list[NewLeg] = []


class BetPatch(BaseModel):
    stake: float | None = Field(None, gt=0)
    odds: float | None = Field(None, gt=1)
    status: str | None = None
    notes: str | None = None


def _bets_frame() -> pd.DataFrame:
    return df(
        """select b.id, b.placed_at, b.source, b.label, b.bookmaker, b.stake::float as stake, b.odds::float as odds,
                  b.probability, b.status, b.payout::float as payout, b.settled_at, b.notes
           from app.bets b order by b.placed_at desc, b.id desc"""
    )


@router.get("/bets")
def list_bets(limit: int = Query(200, le=2000)) -> dict:
    """Settles open bets from the results, returns bets (with legs) and the evaluation."""
    bets.settle(get_engine())
    frame = _bets_frame()
    legs = df(
        """select l.bet_id, l.fixture_id, l.market, l.selection, l.line::float as line, l.label, l.probability,
                  l.odds::float as odds, l.outcome, f.kickoff_utc as kickoff, f.status as fixture_status,
                  f.ft_home, f.ft_away
           from app.bet_legs l left join core.fixtures f on f.id = l.fixture_id order by l.bet_id, l.id"""
    )
    by_bet: dict[int, list] = {}
    for leg in records(legs):
        by_bet.setdefault(int(leg.pop("bet_id")), []).append(leg)
    items = records(frame.head(limit))
    for item in items:
        item["legs"] = by_bet.get(item["id"], [])
    if not frame.empty:
        frame["settled_at"] = pd.to_datetime(frame["settled_at"], utc=True)
    return {"bets": items, "stats": bets.stats(frame)}


@router.post("/bets")
def create_bet(body: NewBet) -> dict:
    with Session(get_engine()) as session, session.begin():
        bet = Bet(label=body.label, source=body.source, bookmaker=body.bookmaker, stake=Decimal(str(body.stake)),
                  odds=Decimal(str(body.odds)), probability=body.probability, notes=body.notes)  # fmt: skip
        session.add(bet)
        session.flush()
        for leg in body.legs:
            session.add(BetLeg(bet_id=bet.id, fixture_id=leg.fixture_id, market=leg.market, selection=leg.selection,
                               line=None if leg.line is None else Decimal(str(leg.line)), label=leg.label,
                               probability=leg.probability,
                               odds=None if leg.odds is None else Decimal(str(leg.odds))))  # fmt: skip
        bet_id = bet.id
    bets.settle(get_engine())
    return {"id": bet_id}


@router.patch("/bets/{bet_id}")
def patch_bet(bet_id: int, body: BetPatch) -> dict:
    with Session(get_engine()) as session, session.begin():
        bet = session.get(Bet, bet_id)
        if bet is None:
            raise HTTPException(404, "Wette nicht gefunden")
        if body.stake is not None:
            bet.stake = Decimal(str(body.stake))
        if body.odds is not None:
            bet.odds = Decimal(str(body.odds))
        if body.notes is not None:
            bet.notes = body.notes
        if body.status is not None:
            if body.status not in ("open", "won", "lost", "void"):
                raise HTTPException(422, "Status: open, won, lost oder void")
            bets.set_status(bet, body.status)
        elif bet.status in ("won", "lost") and (body.stake is not None or body.odds is not None):
            bets.set_status(bet, bet.status)  # recompute the payout
    return {"ok": True}


@router.delete("/bets/{bet_id}")
def delete_bet(bet_id: int) -> dict:
    with Session(get_engine()) as session, session.begin():
        bet = session.get(Bet, bet_id)
        if bet is None:
            raise HTTPException(404, "Wette nicht gefunden")
        session.delete(bet)
    return {"ok": True}
