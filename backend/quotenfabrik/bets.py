"""Bet tracking: placed bets (singles and combos), automatic settlement from results, evaluation.

Legs with a fixture and a model market are settled automatically once the fixture is finished (90 minutes,
the same outcome logic as the predictions). A bet is lost as soon as one leg is lost and won when all legs
won; bets without settleable legs (free text) are settled manually.
"""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pandas as pd
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from quotenfabrik.models import Bet, BetLeg

FINISHED = ("FT", "AET", "PEN", "AWD", "WO")


def _fixture_outcomes(session: Session, fixture_ids: list[int]) -> dict[int, dict]:
    """Outcomes of all model markets for finished fixtures (90-minute scores)."""
    from quotenfabrik.analytics.service import match_outcomes

    if not fixture_ids:
        return {}
    rows = session.execute(
        text("""select id, ft_home, ft_away, ht_home, ht_away from core.fixtures
                where id = any(:ids) and status = any(:fin)
                  and ft_home is not null and ht_home is not null"""),
        {"ids": fixture_ids, "fin": list(FINISHED)},
    ).all()
    out = {}
    for r in rows:
        m = SimpleNamespace(hg=r.ft_home, ag=r.ft_away, hthg=r.ht_home, htag=r.ht_away,
                            h2g=r.ft_home - r.ht_home, a2g=r.ft_away - r.ht_away)  # fmt: skip
        out[int(r.id)] = match_outcomes(m)
    return out


def settle(engine: Engine) -> int:
    """Settles open legs and bets; returns the number of bets settled now."""
    from quotenfabrik.analytics.service import _key

    with Session(engine) as session, session.begin():
        open_legs = select(BetLeg).join(Bet, Bet.id == BetLeg.bet_id)
        legs = session.scalars(open_legs.where(Bet.status == "open", BetLeg.outcome.is_(None))).all()
        outcomes = _fixture_outcomes(session, sorted({leg.fixture_id for leg in legs if leg.fixture_id}))
        for leg in legs:
            if leg.fixture_id in outcomes and leg.market:
                line = None if leg.line is None else float(leg.line)
                leg.outcome = outcomes[leg.fixture_id].get(_key(leg.market, leg.selection, line))
        session.flush()
        settled = 0
        for bet in session.scalars(select(Bet).where(Bet.status == "open")).all():
            bet_legs = session.scalars(select(BetLeg).where(BetLeg.bet_id == bet.id)).all()
            if not bet_legs or any(leg.market is None for leg in bet_legs):
                continue  # free-text bet: settled manually
            if any(leg.outcome is False for leg in bet_legs):
                bet.status, bet.payout = "lost", Decimal("0")
            elif all(leg.outcome is True for leg in bet_legs):
                bet.status, bet.payout = "won", (bet.stake * bet.odds).quantize(Decimal("0.01"))
            else:
                continue
            bet.settled_at = datetime.now(UTC)
            settled += 1
        return settled


def set_status(bet: Bet, status: str) -> None:
    """Manual settlement (free-text bets, void); the payout follows from stake × odds again."""
    bet.status = status
    bet.payout_manual = False
    if status == "won":
        bet.payout = (bet.stake * bet.odds).quantize(Decimal("0.01"))
    elif status == "lost":
        bet.payout = Decimal("0")
    elif status == "void":
        bet.payout = bet.stake
    else:
        bet.payout = None
    bet.settled_at = None if status == "open" else datetime.now(UTC)


def set_payout(bet: Bet, payout: Decimal) -> None:
    """Corrected payout (cash-out, boost, different settlement) of a settled bet; kept on later edits."""
    if bet.status == "open":
        raise ValueError(
            "Erst den Status setzen (gewonnen, verloren oder storniert), dann die Auszahlung korrigieren"
        )
    bet.payout = payout.quantize(Decimal("0.01"))
    bet.payout_manual = True


def recompute_payout(bet: Bet) -> None:
    """After stake or odds changed: payout of a settled bet from stake × odds (not for manual payouts)."""
    if bet.status in ("won", "lost", "void") and not bet.payout_manual:
        status, settled = bet.status, bet.settled_at
        set_status(bet, status)
        bet.settled_at = settled


# --------------------------------------------------------------------------- bankroll and period


def period_start(transactions: pd.DataFrame) -> pd.Timestamp | None:
    """Start of the current evaluation period: the latest reset (None = everything counts)."""
    resets = transactions[transactions["kind"] == "reset"] if not transactions.empty else transactions
    return None if resets.empty else pd.Timestamp(resets["at"].max())


def bankroll(transactions: pd.DataFrame, bets: pd.DataFrame) -> dict:
    """Balance of the current period: starting capital + deposits − withdrawals + profit of settled bets.

    ``transactions`` and ``bets`` must already be restricted to the period. Open stakes are reserved
    (``available``)."""

    def total(kind: str) -> float:
        return (
            float(transactions.loc[transactions["kind"] == kind, "amount"].sum())
            if not transactions.empty
            else 0.0
        )

    start, deposits, withdrawals = total("start"), total("deposit"), total("withdrawal")
    settled = bets[bets["status"] != "open"] if not bets.empty else bets
    profit = float((settled["payout"] - settled["stake"]).sum()) if not settled.empty else 0.0
    open_stakes = float(bets.loc[bets["status"] == "open", "stake"].sum()) if not bets.empty else 0.0
    invested = start + deposits
    balance = invested - withdrawals + profit
    return {"start": start, "deposits": deposits, "withdrawals": withdrawals, "profit": profit,
            "open_stakes": open_stakes, "balance": balance, "available": balance - open_stakes,
            "roi": profit / invested if invested > 0 else None, "configured": invested > 0}  # fmt: skip


def stats(bets: pd.DataFrame) -> dict:
    """Totals of settled bets: stake, return, profit, ROI, hit rate, model expectation; per source; curve."""
    done = bets[bets["status"].isin(["won", "lost"])].copy() if not bets.empty else bets

    def block(d: pd.DataFrame) -> dict:
        if d.empty:
            return {"n": 0}
        stake, ret = float(d["stake"].sum()), float(d["payout"].sum())
        known = d[d["probability"].notna()]
        ev = known["stake"] * (known["probability"] * known["odds"] - 1)
        expected = float(ev.sum()) if len(known) else None
        return {"n": len(d), "won": int((d["status"] == "won").sum()), "stake": stake, "return": ret,
                "profit": ret - stake, "roi": (ret - stake) / stake if stake else None,
                "hit_rate": float((d["status"] == "won").mean()),
                "expected_hit_rate": float(known["probability"].mean()) if len(known) else None,
                "expected_profit": expected, "avg_odds": float(d["odds"].mean())}  # fmt: skip

    by_source = {s: block(g) for s, g in done.groupby("source")} if not done.empty else {}
    n_open = int((bets["status"] == "open").sum()) if not bets.empty else 0
    out = {"total": block(done), "open": n_open, "by_source": by_source}
    if not done.empty:
        curve = done.sort_values("settled_at")
        curve = curve.assign(profit=(curve["payout"] - curve["stake"]).cumsum())
        out["curve"] = [
            {"at": r.settled_at.isoformat(), "profit": float(r.profit)} for r in curve.itertuples()
        ]
    else:
        out["curve"] = []
    return out
