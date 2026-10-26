"""Daily combos and bet tracking."""

import time
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete
from sqlalchemy.orm import Session

from quotenfabrik import app_config, bets
from quotenfabrik.analytics import combos
from quotenfabrik.api.data import chosen_runs_cte, df, records
from quotenfabrik.api.labels import league_logo, pick_label
from quotenfabrik.db import get_engine
from quotenfabrik.models import BankrollTransaction, Bet, BetLeg

router = APIRouter(prefix="/api", tags=["bets"])

_CACHE: dict[tuple, tuple[float, list]] = {}
CACHE_TTL_S = 600


def _day_predictions(day: date) -> pd.DataFrame:
    where = "and (f.kickoff_utc at time zone 'Europe/Berlin')::date = :day and f.league_id = any(:leagues)"
    return df(
        f"""with runs as ({chosen_runs_cte(where)})
            select p.id as prediction_id, p.fixture_id, p.model_run_id, p.market, p.selection,
                   p.line::float as line, p.probability, p.outcome, f.league_id, f.season, f.kickoff_utc as kickoff,
                   f.home_team_id, h.name as home_name, h.logo_url as home_logo,
                   f.away_team_id, a.name as away_name, a.logo_url as away_logo, f.status
            from analytics.predictions p
            join runs on runs.model_run_id = p.model_run_id and runs.fixture_id = p.fixture_id
            join core.fixtures f on f.id = p.fixture_id
            join core.teams h on h.id = f.home_team_id join core.teams a on a.id = f.away_team_id
            where p.market in ('ou_ft', 'ou_home', 'ou_away', 'dc') and p.selection in ('over', '1X', 'X2', '12')""",
        day=day, leagues=app_config.shown_league_ids(),
    )  # fmt: skip


def compute_combos(day: date, not_before: datetime | None = None) -> list[dict]:
    """Daily combos from the chosen prediction runs; with ``not_before`` only fixtures kicking off later."""
    preds = _day_predictions(day)
    if preds.empty:
        return []
    preds["kickoff"] = pd.to_datetime(preds["kickoff"], utc=True)
    if not_before is not None:
        preds = preds[preds["kickoff"] > pd.Timestamp(not_before)]
        if preds.empty:
            return []
    with_rates = combos.with_betano(get_engine(), combos.with_base_rates(get_engine(), preds))
    out = []
    for c in combos.build_day(
        with_rates, app_config.combo_settings(), rotation=pd.Timestamp(day).toordinal()
    ):
        legs = []
        for leg in sorted(c.legs, key=lambda x: x["kickoff"]):
            line = leg["line"]
            legs.append({
                "prediction_id": int(leg["prediction_id"]),
                "fixture_id": int(leg["fixture_id"]), "kickoff": leg["kickoff"].isoformat(),
                "league": {"id": int(leg["league_id"]), "logo": league_logo(int(leg["league_id"]))},
                "home": {"id": int(leg["home_team_id"]), "name": leg["home_name"], "logo": leg["home_logo"]},
                "away": {"id": int(leg["away_team_id"]), "name": leg["away_name"], "logo": leg["away_logo"]},
                "market": leg["market"], "selection": leg["selection"], "line": line,
                "label": pick_label(leg["market"], leg["selection"], line, leg["home_name"], leg["away_name"]),
                "probability": float(leg["probability"]), "odds": round(float(leg["odds"]), 2),
                "odds_source": leg["odds_source"], "edge": leg["edge"], "pinnacle": leg.get("fair"),
                "outcome": None if leg["outcome"] is None else bool(leg["outcome"]),
            })  # fmt: skip
        out.append({"kind": c.kind, "label": combos.KINDS[c.kind], "odds": round(c.odds, 2),
                    "real_odds": all(leg["odds_source"] == "betano" for leg in c.legs),
                    "probability": c.probability, "outcome": c.outcome, "legs": legs})  # fmt: skip
    return _by_kind(out)


def _by_kind(items: list[dict]) -> list[dict]:
    order = list(combos.KINDS)
    return sorted(items, key=lambda c: order.index(c["kind"]) if c["kind"] in order else len(order))


def _frozen_combos(day: date) -> list[dict]:
    """Combos as frozen on the day, with the current outcome of every leg."""
    rows = df(
        """select kind, frozen_at, odds::float as odds, probability, real_odds, legs
           from analytics.day_combos where day = :day""",
        day=day,
    )
    if rows.empty:
        return []
    ids = [leg["prediction_id"] for legs in rows["legs"] for leg in legs if leg.get("prediction_id")]
    outcome = df("select id, outcome from analytics.predictions where id = any(:ids)", ids=ids)
    outcome = {
        int(i): (None if o is None or pd.isna(o) else bool(o))
        for i, o in zip(outcome["id"], outcome["outcome"], strict=True)
    }
    out = []
    for r in rows.itertuples():
        legs = [
            {**leg, "outcome": outcome.get(leg.get("prediction_id"), leg.get("outcome"))} for leg in r.legs
        ]
        combo = combos.Combo(r.kind, legs)
        out.append({"kind": r.kind, "label": combos.KINDS.get(r.kind, r.kind), "odds": r.odds,
                    "real_odds": bool(r.real_odds), "probability": float(r.probability), "outcome": combo.outcome,
                    "legs": legs, "frozen_at": pd.Timestamp(r.frozen_at).isoformat()})  # fmt: skip
    return _by_kind(out)


@router.get("/combos")
def day_combos(day: date = Query(..., alias="date")) -> list[dict]:
    """Daily combos (Tore Über, Team-Tore Über, Doppelte Chance) of one day; empty without enough fixtures.

    Once the day is frozen (``qf day freeze``, morning job) the stored combos; before that and for days
    without a freeze (backtest) they are computed from the chosen prediction runs."""
    frozen = _frozen_combos(day)
    if frozen:
        return frozen
    runs = df(
        f"""with runs as ({chosen_runs_cte("and (f.kickoff_utc at time zone 'Europe/Berlin')::date = :day")})
            select model_run_id from runs""",
        day=day,
    )
    if runs.empty:
        return []
    key = (day, tuple(sorted(runs["model_run_id"].unique())), tuple(sorted(app_config.all_values().items())))
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL_S:
        return hit[1]
    out = [{**c, "frozen_at": None} for c in compute_combos(day)]
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
    payout: float | None = Field(None, ge=0)  # corrected payout (cash-out, boost, …) of a settled bet
    payout_auto: bool = False  # true: payout again from stake × odds


def _bets_frame() -> pd.DataFrame:
    frame = df(
        """select b.id, b.placed_at, b.source, b.label, b.bookmaker, b.stake::float as stake, b.odds::float as odds,
                  b.probability, b.status, b.payout::float as payout, b.payout_manual, b.settled_at, b.notes
           from app.bets b order by b.placed_at desc, b.id desc"""
    )
    frame["placed_at"] = pd.to_datetime(frame["placed_at"], utc=True)
    return frame


def _transactions() -> pd.DataFrame:
    frame = df(
        "select id, at, kind, amount::float as amount, note from app.bankroll_transactions order by at, id"
    )
    frame["at"] = pd.to_datetime(frame["at"], utc=True)
    return frame


@router.get("/bets")
def list_bets(limit: int = Query(200, le=2000), all_periods: bool = Query(False, alias="all")) -> dict:
    """Settles open bets from the results, returns the bets (with legs) of the current evaluation period
    (``all``: also earlier periods), the evaluation and the bankroll of the period."""
    bets.settle(get_engine())
    tx = _transactions()
    start = bets.period_start(tx)
    frame = _bets_frame()
    period = frame if start is None else frame[frame["placed_at"] >= start]
    period_tx = tx if start is None else tx[tx["at"] >= start]
    legs = df(
        """select l.bet_id, l.fixture_id, l.market, l.selection, l.line::float as line, l.label, l.probability,
                  l.odds::float as odds, l.outcome, f.kickoff_utc as kickoff, f.status as fixture_status,
                  f.ft_home, f.ft_away
           from app.bet_legs l left join core.fixtures f on f.id = l.fixture_id order by l.bet_id, l.id"""
    )
    by_bet: dict[int, list] = {}
    for leg in records(legs):
        by_bet.setdefault(int(leg.pop("bet_id")), []).append(leg)
    shown = frame if all_periods else period
    items = records(shown.head(limit))
    for item in items:
        item["legs"] = by_bet.get(item["id"], [])
        item["in_period"] = start is None or pd.Timestamp(item["placed_at"]) >= start
    period = period.assign(settled_at=pd.to_datetime(period["settled_at"], utc=True))
    return {
        "bets": items, "stats": bets.stats(period), "bankroll": bets.bankroll(period_tx, period),
        "transactions": records(period_tx[period_tx["kind"] != "reset"]),
        "period_start": None if start is None else start.isoformat(),
        "earlier_bets": int(len(frame) - len(period)),
    }  # fmt: skip


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
        if body.status is not None and body.status != bet.status:
            if body.status not in ("open", "won", "lost", "void"):
                raise HTTPException(422, "Status: open, won, lost oder void")
            bets.set_status(bet, body.status)
        elif body.payout_auto:
            bet.payout_manual = False
            bets.recompute_payout(bet)
        elif body.stake is not None or body.odds is not None:
            bets.recompute_payout(bet)
        if body.payout is not None:
            try:
                bets.set_payout(bet, Decimal(str(body.payout)))
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from None
    return {"ok": True}


# --------------------------------------------------------------------------- bankroll


class NewTransaction(BaseModel):
    kind: str
    amount: float = Field(gt=0)
    note: str | None = None
    at: datetime | None = None


class ResetRequest(BaseModel):
    delete_bets: bool = False  # delete the bets of earlier periods for good
    start_capital: float | None = Field(None, gt=0)  # starting capital of the new period


@router.post("/bankroll")
def add_transaction(body: NewTransaction) -> dict:
    if body.kind not in ("start", "deposit", "withdrawal"):
        raise HTTPException(422, "Art: start, deposit oder withdrawal")
    with Session(get_engine()) as session, session.begin():
        tx = BankrollTransaction(kind=body.kind, amount=Decimal(str(body.amount)), note=body.note)
        if body.at is not None:
            tx.at = body.at
        session.add(tx)
        session.flush()
        return {"id": tx.id}


@router.delete("/bankroll/{tx_id}")
def delete_transaction(tx_id: int) -> dict:
    with Session(get_engine()) as session, session.begin():
        tx = session.get(BankrollTransaction, tx_id)
        if tx is None or tx.kind == "reset":
            raise HTTPException(404, "Buchung nicht gefunden")
        session.delete(tx)
    return {"ok": True}


@router.post("/bets/reset")
def reset_period(body: ResetRequest) -> dict:
    """New evaluation period from now on: statistics and bankroll only count bets and bookings after it."""
    now = datetime.now(UTC)
    with Session(get_engine()) as session, session.begin():
        deleted = 0
        if body.delete_bets:
            deleted = session.execute(delete(Bet).where(Bet.placed_at < now)).rowcount or 0
        session.add(
            BankrollTransaction(kind="reset", amount=Decimal("0"), at=now, note="Auswertung zurückgesetzt")
        )
        if body.start_capital:
            session.add(BankrollTransaction(kind="start", amount=Decimal(str(body.start_capital)),
                                            at=now + timedelta(microseconds=1)))  # fmt: skip
    return {"ok": True, "deleted_bets": deleted}


@router.delete("/bets/{bet_id}")
def delete_bet(bet_id: int) -> dict:
    with Session(get_engine()) as session, session.begin():
        bet = session.get(Bet, bet_id)
        if bet is None:
            raise HTTPException(404, "Wette nicht gefunden")
        session.delete(bet)
    return {"ok": True}
