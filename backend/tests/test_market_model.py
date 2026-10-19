"""Market-implied model and Betano side-market evaluation (no database)."""

import numpy as np
import pandas as pd
import pytest

from quotenfabrik.analytics import betano_value as bv
from quotenfabrik.analytics import market_model as mm

TRUE = [1.8, 1.1, 0.44, 0.47, -0.06]


@pytest.fixture(scope="module")
def pred():
    return mm.prediction(TRUE)


def test_exhaustive_markets_sum_to_one(pred):
    for market, sels in bv.EXHAUSTIVE.items():
        line = 1.5 if market in mm.LINE_MARKETS else (-1.0 if market == "eh" else None)
        total = sum(mm.price(pred, market, line, s) for s in sels)  # dnb: conditional on no draw
        assert total == pytest.approx(1.0, abs=1e-9), market
    exact = sum(mm.price(pred, "tg", None, str(k)) for k in range(21))
    assert exact == pytest.approx(1.0, abs=1e-9)
    assert mm.price(pred, "tg", None, "3+") == pytest.approx(mm.price(pred, "ou_ft", 2.5, "over"))


def test_consistency_between_markets(pred):
    over05_home = mm.price(pred, "ou_home", 0.5, "over")
    assert mm.price(pred, "tg_home", None, "1+") == pytest.approx(over05_home)
    # handicap -1 home win = home wins by 2+
    assert mm.price(pred, "eh", -1.0, "H") < mm.price(pred, "1x2", None, "H")
    assert mm.price(pred, "dc", None, "1X") == pytest.approx(
        mm.price(pred, "1x2", None, "H") + mm.price(pred, "1x2", None, "D")
    )
    # half totals: 1st half share 44 % / 47 % -> fewer goals before the break
    assert mm.price(pred, "ou_1h", 0.5, "over") < mm.price(pred, "ou_2h", 0.5, "over")


def test_outcomes():
    goals = {"hg": 3, "ag": 1, "h1": 1, "a1": 1}  # 2nd half 2:0
    assert mm.outcome(goals, "1x2", None, "H")
    assert mm.outcome(goals, "ht_1x2", None, "D")
    assert mm.outcome(goals, "2h_1x2", None, "H")
    assert mm.outcome(goals, "eh", -2.0, "D")
    assert mm.outcome(goals, "ou_ft", 3.5, "over")
    assert mm.outcome(goals, "ou_away_2h", 0.5, "under")
    assert mm.outcome(goals, "btts_1h", None, "yes") and not mm.outcome(goals, "btts_2h", None, "yes")
    assert mm.outcome(goals, "highest_half", None, "equal")  # 2 goals in each half
    assert mm.outcome(goals, "tg", None, "4") and mm.outcome(goals, "tg", None, "2+")
    assert mm.outcome({"hg": 1, "ag": 1, "h1": 0, "a1": 0}, "dnb", None, "H") is None  # stake returned


def test_fit_recovers_parameters(pred):
    targets = []
    for market, line in [("1x2", None), ("ht_1x2", None), ("btts", None), ("btts_1h", None),
                         *[("ou_ft", ln) for ln in (1.5, 2.5, 3.5)], *[("ou_home", ln) for ln in (0.5, 1.5)],
                         *[("ou_away", ln) for ln in (0.5, 1.5)], ("ou_1h", 0.5), ("ou_1h", 1.5),
                         ("ou_home_1h", 0.5), ("ou_away_1h", 0.5)]:  # fmt: skip
        sels = bv.EXHAUSTIVE[market]
        targets.append(
            mm.Target(market, line, sels, np.array([mm.price(pred, market, line, s) for s in sels]))
        )
    fitted, info = mm.fit(targets)
    assert info["mae"] < 1e-3
    assert [fitted.lh, fitted.la, fitted.rho] == pytest.approx([TRUE[0], TRUE[1], TRUE[4]], abs=0.02)
    assert fitted.lh_1h / fitted.lh == pytest.approx(TRUE[2], abs=0.02)


def test_oddspapi_mapping():
    assert bv.oddspapi_key("1x2", "p1", 0, "X") == ("ht_1x2", None, "D")
    assert bv.oddspapi_key("doublechance", "fulltime", 0, "2X") == ("dc", None, "X2")
    assert bv.oddspapi_key("spreads-european", "fulltime", -1, "1") == ("eh", -1.0, "H")
    assert bv.oddspapi_key("totals", "p2", 1.5, "Over") == ("ou_2h", 1.5, "over")
    assert bv.oddspapi_key("teamtotals-team2", "p1", 0.5, "Under") == ("ou_away_1h", 0.5, "under")
    assert bv.oddspapi_key("bothteamsscore", "p2", 0, "Yes") == ("btts_2h", None, "yes")
    assert bv.oddspapi_key("highestscoringh", "fulltime", 0, "2nd") == ("highest_half", None, "2H")
    assert bv.oddspapi_key("exactscore", "fulltime", 0, "3+") == ("tg", None, "3+")
    assert bv.oddspapi_key("exactscore-team1", "fulltime", 0, "2") is None  # unreliable Betano data
    assert bv.oddspapi_key("toscore-team1", "fulltime", 0, "Yes") is None  # duplicate of ou_home 0.5


def test_snapshot_takes_last_active_price_before_cutoff():
    kick = pd.Timestamp("2026-05-16 13:30", tz="UTC")
    rows = [  # changed_at, price, active
        (kick - pd.Timedelta(hours=30), 2.0, True),
        (kick - pd.Timedelta(hours=20), 2.2, True),
        (kick - pd.Timedelta(hours=2), 2.4, False),
        (kick + pd.Timedelta(minutes=5), 9.9, True),  # in play, never used
    ]
    odds = pd.DataFrame(
        [{"oddspapi_id": "x", "bookmaker": "betano.de", "market": "1x2", "line": None, "selection": "H",
          "changed_at": c, "price": p, "active": a, "kickoff": kick} for c, p, a in rows]
    )  # fmt: skip
    assert bv.snapshot(odds, 24)["price"].tolist() == [2.0]
    assert bv.snapshot(odds, 6)["price"].tolist() == [2.2]
    assert bv.snapshot(odds, 0).empty  # suspended before kickoff


def test_value_bets_one_per_market_line():
    rows = pd.DataFrame(
        {"oddspapi_id": ["a"] * 3, "market": ["ou_ft"] * 3, "line": [2.5, 2.5, 3.5],
         "selection": ["over", "under", "over"], "edge": [0.03, 0.05, -0.01], "p_fair": [0.5, 0.5, 0.3]}
    )  # fmt: skip
    bets = bv.value_bets(rows, 0.0)
    assert bets[["line", "selection"]].values.tolist() == [[2.5, "under"]]
