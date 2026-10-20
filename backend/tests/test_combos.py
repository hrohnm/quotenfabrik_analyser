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
    s = ComboSettings(max_legs=6)
    # six times Über 1,5 (≈ 1.13 each) would only reach ≈ 2.1
    (combo,) = build_day(preds, s)
    assert s.target_min <= combo.odds <= s.target_max
    assert any(leg["line"] == 2.5 for leg in combo.legs)
    assert combo.legs[0]["line"] == 1.5  # still starts with the best leg while the target is reachable


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
