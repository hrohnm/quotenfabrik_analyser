"""Daily combos and bet tracking (no database)."""

from datetime import UTC, datetime
from decimal import Decimal

import pandas as pd
import pytest

from quotenfabrik import app_config, bets
from quotenfabrik.analytics.combos import Combo, ComboSettings, build_day, candidates, kind_of
from quotenfabrik.models import Bet


def day_preds(n_fixtures: int = 8, p: float = 0.72) -> pd.DataFrame:
    rows = []
    for f in range(1, n_fixtures + 1):
        q = p + f * 0.005  # later fixtures slightly stronger
        rows += [
            (f, "ou_ft", "over", 1.5, q, 0.75, True),
            (f, "ou_ft", "over", 4.5, q, 0.10, True),  # line too high for the combo
            (f, "ou_home", "over", 0.5, q - 0.01, 0.70, f != 3),
            (f, "ou_away", "under", 1.5, q, 0.60, True),  # under: not part of any combo
            (f, "dc", "1X", None, q - 0.02, 0.70, None),
        ]
    return pd.DataFrame(
        rows, columns=["fixture_id", "market", "selection", "line", "probability", "base_rate", "outcome"]
    )


def test_kind_of():
    assert kind_of("ou_ft", "over", 2.5) == "tore"
    assert kind_of("ou_ft", "over", 4.5) is None
    assert kind_of("ou_ft", "under", 2.5) is None
    assert kind_of("ou_away", "over", 1.5) == "team_tore"
    assert kind_of("ou_home", "over", 3.5) is None
    assert kind_of("dc", "X2", None) == "doppelte_chance"
    assert kind_of("1x2", "H", None) is None


def test_candidates_best_leg_per_fixture_and_window():
    s = ComboSettings()
    c = candidates(day_preds(), s)
    assert set(c) == {"tore", "team_tore", "doppelte_chance"}
    assert (c["tore"]["line"] == 1.5).all()  # 4.5 is not a combo line
    assert c["tore"]["fixture_id"].iloc[0] == 8  # highest score first
    assert c["tore"]["probability"].between(s.min_p, s.max_p).all()
    assert c["tore"]["odds"].iloc[0] == pytest.approx((1 / c["tore"]["probability"].iloc[0]) * 0.95)


def test_build_day_targets_and_rules():
    s = ComboSettings()
    combos = build_day(day_preds(), s)
    assert {c.kind for c in combos} == {"tore", "team_tore", "doppelte_chance"}
    for c in combos:
        assert s.target_min <= c.odds <= s.target_max
        ids = [leg["fixture_id"] for leg in c.legs]
        assert len(ids) == len(set(ids))  # never the same fixture twice in one combo
    # rotation spreads the fixtures: the best fixture goes to only one combo first
    firsts = [c.legs[0]["fixture_id"] for c in combos]
    assert len(set(firsts)) == 3


def test_build_day_rotation_changes_who_picks_first():
    a = {c.kind: c.legs[0]["fixture_id"] for c in build_day(day_preds(), ComboSettings(), rotation=0)}
    b = {c.kind: c.legs[0]["fixture_id"] for c in build_day(day_preds(), ComboSettings(), rotation=1)}
    assert a["tore"] == 8 and b["team_tore"] == 8


def test_build_day_takes_higher_line_when_target_unreachable():
    rows = [(f, "ou_ft", "over", 1.5, 0.84, 0.80, None) for f in range(1, 7)]
    rows += [(f, "ou_ft", "over", 2.5, 0.60, 0.55, None) for f in range(1, 7)]
    preds = pd.DataFrame(
        rows, columns=["fixture_id", "market", "selection", "line", "probability", "base_rate", "outcome"]
    )
    s = ComboSettings(max_legs=6, min_leg_odds=1.0)
    # six times Über 1,5 (≈ 1.13 each) would only reach ≈ 2.1
    (combo,) = build_day(preds, s)
    assert s.target_min <= combo.odds <= s.target_max
    assert any(leg["line"] == 2.5 for leg in combo.legs)
    assert combo.legs[0]["line"] == 1.5  # still starts with the best leg while the target is reachable


def test_min_leg_odds():
    preds = day_preds()
    preds.loc[preds["fixture_id"] == 8, "probability"] = 0.84  # estimated odds 1.13
    s = ComboSettings()
    assert 8 not in set(candidates(preds, s)["tore"]["fixture_id"])
    assert 8 in set(candidates(preds, ComboSettings(min_leg_odds=1.0))["tore"]["fixture_id"])
    for c in build_day(preds, s):
        assert all(leg["odds"] >= s.min_leg_odds for leg in c.legs)


def test_build_day_without_enough_fixtures():
    assert build_day(day_preds(n_fixtures=2), ComboSettings()) == []
    assert build_day(day_preds().iloc[0:0], ComboSettings()) == []


def test_combo_outcome():
    c = Combo(
        "tore",
        [
            {"odds": 2.0, "probability": 0.5, "outcome": True},
            {"odds": 3.0, "probability": 0.3, "outcome": None},
        ],
    )
    assert c.odds == pytest.approx(6.0) and c.probability == pytest.approx(0.15)
    assert c.outcome is None
    c.legs.append({"odds": 1.5, "probability": 0.6, "outcome": False})
    assert c.outcome is False
    assert Combo("tore", [{"odds": 2.0, "probability": 0.5, "outcome": True}]).outcome is True


def test_set_status_payout():
    bet = Bet(label="x", stake=Decimal("10"), odds=Decimal("6.5"))
    bets.set_status(bet, "won")
    assert bet.payout == Decimal("65.00") and bet.settled_at is not None
    bets.set_status(bet, "lost")
    assert bet.payout == 0
    bets.set_status(bet, "void")
    assert bet.payout == Decimal("10")
    bets.set_status(bet, "open")
    assert bet.payout is None and bet.settled_at is None


def test_bet_stats():
    t = datetime(2026, 10, 1, tzinfo=UTC)
    frame = pd.DataFrame(
        [
            (1, "tageskombi", 10.0, 6.0, 0.15, "won", 60.0, t),
            (2, "tageskombi", 10.0, 6.0, 0.15, "lost", 0.0, t.replace(day=2)),
            (3, "manuell", 5.0, 2.0, None, "lost", 0.0, t.replace(day=3)),
            (4, "manuell", 5.0, 2.0, None, "open", None, None),
        ],
        columns=["id", "source", "stake", "odds", "probability", "status", "payout", "settled_at"],
    )
    st = bets.stats(frame)
    assert st["total"]["n"] == 3 and st["open"] == 1
    assert st["total"]["profit"] == pytest.approx(35.0)
    assert st["total"]["roi"] == pytest.approx(35 / 25)
    assert st["total"]["expected_hit_rate"] == pytest.approx(0.15)
    assert st["total"]["expected_profit"] == pytest.approx(2 * 10 * (0.15 * 6 - 1))
    assert st["by_source"]["manuell"]["hit_rate"] == 0
    assert [c["profit"] for c in st["curve"]] == [50.0, 40.0, 35.0]
    assert bets.stats(frame.iloc[0:0])["total"] == {"n": 0}


def test_validate_combo_settings():
    assert app_config.validate({"combos.target_min": 4})["combos.target_min"] == 4
    with pytest.raises(ValueError):
        app_config.validate({"combos.target_min": 12})
    with pytest.raises(ValueError):
        app_config.validate({"combos.min_p": 0.9})


def test_candidates_prefer_real_betano_odds_and_edge_filter():
    preds = day_preds()
    preds["betano"] = float("nan")
    preds.loc[
        (preds["fixture_id"] == 1) & (preds["market"] == "ou_ft") & (preds["line"] == 1.5), "betano"
    ] = 1.60
    c = candidates(preds, ComboSettings())["tore"]
    real = c[c["fixture_id"] == 1].iloc[0]
    assert real["odds"] == 1.60 and real["odds_source"] == "betano"
    assert real["edge"] == pytest.approx(real["probability"] * 1.60 - 1)
    assert (c[c["fixture_id"] != 1]["odds_source"] == "geschätzt").all()
    only_value = candidates(preds, ComboSettings(min_edge=0.0))["tore"]
    assert list(only_value["fixture_id"]) == [1]  # estimated legs never count as value


def test_pinnacle_fair_removes_margin_and_derives_double_chance():
    from quotenfabrik.analytics.bookmaker_odds import PINNACLE, pinnacle_fair

    rows = [(1, PINNACLE, "1x2", None, s, o) for s, o in (("H", 2.0), ("D", 3.6), ("A", 4.0))]
    rows += [(1, PINNACLE, "ou_ft", 2.5, "over", 1.9), (1, PINNACLE, "ou_ft", 2.5, "under", 1.95)]
    rows += [(1, PINNACLE, "ou_ft", 3.5, "over", 2.9)]  # incomplete pair: no fair price
    prices = pd.DataFrame(rows, columns=["fixture_id", "bookmaker", "market", "line", "selection", "price"])
    fair = pinnacle_fair(prices).set_index(["market", "selection"])["fair"]
    assert fair.loc[("1x2", "H")] + fair.loc[("1x2", "D")] + fair.loc[("1x2", "A")] == pytest.approx(1)
    assert fair.loc[("1x2", "H")] < 1 / 2.0 * 1.06 and fair.loc[("1x2", "H")] > 0.45
    assert fair.loc[("dc", "1X")] == pytest.approx(fair.loc[("1x2", "H")] + fair.loc[("1x2", "D")])
    assert fair.loc[("ou_ft", "over")] + fair.loc[("ou_ft", "under")] == pytest.approx(1)
    assert len(fair.loc["ou_ft"]) == 2


def test_set_payout_and_recompute():
    bet = Bet(label="x", stake=Decimal("10"), odds=Decimal("5"), status="open")
    with pytest.raises(ValueError):
        bets.set_payout(bet, Decimal("30"))  # open bets cannot get a payout
    bets.set_status(bet, "won")
    bets.set_payout(bet, Decimal("32.5"))  # cash-out / boost
    assert bet.payout == Decimal("32.50") and bet.payout_manual
    bet.odds = Decimal("6")
    bets.recompute_payout(bet)
    assert bet.payout == Decimal("32.50")  # manual payout is kept
    bet.payout_manual = False
    bets.recompute_payout(bet)
    assert bet.payout == Decimal("60.00")


def test_bankroll_and_period():
    t = datetime(2026, 10, 1, tzinfo=UTC)
    tx = pd.DataFrame(
        [(1, t, "start", 100.0), (2, t.replace(day=5), "reset", 0.0), (3, t.replace(day=5), "start", 200.0),
         (4, t.replace(day=6), "deposit", 50.0), (5, t.replace(day=7), "withdrawal", 30.0)],
        columns=["id", "at", "kind", "amount"],
    )  # fmt: skip
    start = bets.period_start(tx)
    assert start == pd.Timestamp(t.replace(day=5))
    period_tx = tx[tx["at"] >= start]
    frame = pd.DataFrame(
        [("won", 10.0, 60.0), ("lost", 10.0, 0.0), ("void", 5.0, 5.0), ("open", 20.0, None)],
        columns=["status", "stake", "payout"],
    )
    b = bets.bankroll(period_tx, frame)
    assert b["start"] == 200 and b["deposits"] == 50 and b["withdrawals"] == 30
    assert b["profit"] == pytest.approx(40.0)
    assert b["balance"] == pytest.approx(200 + 50 - 30 + 40)
    assert b["available"] == pytest.approx(b["balance"] - 20)
    assert b["roi"] == pytest.approx(40 / 250)
    assert bets.period_start(tx.iloc[0:0]) is None
    assert bets.bankroll(tx.iloc[0:0], frame.iloc[0:0])["configured"] is False
