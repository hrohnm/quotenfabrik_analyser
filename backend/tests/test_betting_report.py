from decimal import Decimal

import pandas as pd

from quotenfabrik.api import betting_report


def _p(fid, market, sel, line, p, outcome, group="1x2"):
    return {"fixture_id": fid, "market_group": group, "market": market, "selection": sel, "line": line,
            "probability": p, "outcome": outcome}  # fmt: skip


def test_model_section_hit_rates_and_markets():
    rows = []
    for fid, result in ((1, "H"), (2, "A"), (3, "H")):
        for sel, p in (("H", 0.6), ("D", 0.25), ("A", 0.15)):
            rows.append(_p(fid, "1x2", sel, None, p, sel == result))
        rows.append(_p(fid, "ou_ft", "over", 2.5, 0.7, fid != 2, "totals"))
        rows.append(_p(fid, "ou_ft", "under", 2.5, 0.3, fid == 2, "totals"))
    out = betting_report.model_section(pd.DataFrame(rows))
    assert out["fixtures"] == 3
    markets = {(m["market"], m["line"]): m for m in out["markets"]}
    assert markets[("1x2", None)]["n"] == 3 and abs(markets[("1x2", None)]["hit_rate"] - 2 / 3) < 1e-9
    assert (
        markets[("1x2", None)]["most_picked"] == "Heim"
        and abs(markets[("ou_ft", 2.5)]["expected"] - 0.7) < 1e-9
    )
    assert [g["group"] for g in out["groups"]] == ["1x2", "totals"]
    assert betting_report.model_section(pd.DataFrame()) == {"fixtures": 0, "groups": [], "markets": [],
                                                             "calibration": []}  # fmt: skip


def test_bets_section_counts_matching_legs(session, engine, monkeypatch):
    from quotenfabrik.api import data
    from quotenfabrik.models import Bet, BetLeg

    monkeypatch.setattr(data, "get_engine", lambda: engine)
    won = Bet(label="A", source="manuell", bookmaker="Betano", stake=Decimal("10"), odds=Decimal("2.0"),
              status="won", payout=Decimal("20"))  # fmt: skip
    lost = Bet(label="B", source="manuell", bookmaker="Betano", stake=Decimal("5"), odds=Decimal("3.0"),
               status="lost", payout=Decimal("0"))  # fmt: skip
    other = Bet(label="C", source="manuell", bookmaker="Betano", stake=Decimal("7"), odds=Decimal("1.5"),
                status="open")  # fmt: skip
    session.add_all([won, lost, other])
    session.flush()
    session.add_all([
        BetLeg(bet_id=won.id, market="scorer_anytime", selection="184", label="Kane trifft", outcome=True),
        BetLeg(bet_id=lost.id, market="scorer_anytime", selection="184", label="Kane trifft", outcome=False),
        BetLeg(bet_id=other.id, market="scorer_anytime", selection="999", label="X trifft"),
    ])  # fmt: skip
    session.commit()
    out = betting_report.bets_section("l.market like 'scorer%' and l.selection = :sel", sel="184")
    assert (out["bets"], out["won"], out["lost"], out["open"]) == (2, 1, 1, 0)
    assert out["stake"] == 15 and out["profit"] == 5 and abs(out["roi"] - 1 / 3) < 1e-9
    assert out["legs"] == 2 and out["legs_won"] == 1 and out["legs_settled"] == 2
    assert {b["label"] for b in out["recent"]} == {"A", "B"}
