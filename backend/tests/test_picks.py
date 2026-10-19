"""Pick selection, labels and evaluation (no database)."""

import pandas as pd

from quotenfabrik.analytics.picks import (
    Profile,
    combos,
    evaluate_picks,
    is_candidate,
    profiles,
    select_picks,
    supported_key,
)
from quotenfabrik.api.labels import pick_label


def candidates() -> pd.DataFrame:
    rows = [  # fixture, group, market, selection, line, probability, base_rate
        (1, "1x2", "dc", "1X", None, 0.80, 0.70),
        (1, "1x2", "1x2", "H", None, 0.62, 0.45),
        (1, "totals", "ou_ft", "over", 1.5, 0.84, 0.80),
        (1, "totals", "ou_ft", "over", 2.5, 0.66, 0.55),
        (1, "team_totals", "ou_home", "over", 0.5, 0.95, 0.80),  # above the window
        (1, "team_totals", "ou_away", "under", 1.5, 0.70, 0.60),
        (1, "halves", "ou_2h", "over", 0.5, 0.78, 0.80),  # below league average
        (2, "1x2", "1x2", "A", None, 0.40, 0.30),  # below the window -> fixture 2 gets no pick
    ]
    return pd.DataFrame(rows, columns=["fixture_id", "market_group", "market", "selection", "line", "probability",
                                       "base_rate"])  # fmt: skip


def test_select_picks_spreads_over_groups():
    picks = select_picks(candidates(), Profile("Test", 0.58, 0.85, 1.0))
    assert list(picks["fixture_id"].unique()) == [1]
    assert picks["market_group"].is_unique and len(picks) == 3
    assert picks["probability"].between(0.58, 0.85).all()
    # score = p + lift: dc 0.90 beats 1x2 H 0.79; ou_ft 1.5 (0.88) beats 2.5 (0.77)
    assert picks.set_index("market_group").loc["1x2", "market"] == "dc"
    assert picks.set_index("market_group").loc["totals", "line"] == 1.5
    assert list(picks["rank"]) == [1, 2, 3]
    assert (picks["score"].diff().dropna() <= 0).all()


def test_lift_weight_prefers_match_specific_picks():
    c = candidates()
    plain = select_picks(c, Profile("p", 0.58, 0.85, 0.0))
    lifted = select_picks(c, Profile("l", 0.58, 0.85, 3.0))
    # without lift the ordinary 2nd-half goal (0.78, below average) is a pick; with strong lift it is not
    assert "halves" in set(plain["market_group"])
    assert "halves" not in set(lifted["market_group"])


def test_candidates_and_support():
    assert is_candidate("ou_ft", 2.5) and not is_candidate("ou_ft", 5.5) and not is_candidate("eh", -1.0)
    assert is_candidate("1x2", None) and not is_candidate("scorer_anytime", None)
    assert supported_key("combined_o25", "high") == ("ou_ft", "over", 2.5)
    assert supported_key("combined_o25", "low") == ("ou_ft", "under", 2.5)
    assert supported_key("home_win_rate_home", "low") is None
    assert supported_key("unknown", "high") is None
    assert set(profiles()) == {"sicher", "ausgewogen", "mutig"}


def test_pick_labels():
    assert pick_label("1x2", "H", None, "Bayern", "Köln") == "Sieg Bayern"
    assert pick_label("dc", "X2", None, "Bayern", "Köln") == "Köln oder Remis"
    assert pick_label("ou_ft", "over", 2.5, "Bayern", "Köln") == "Über 2,5 Tore"
    assert pick_label("ou_home", "over", 0.5, "Bayern", "Köln") == "Bayern trifft"
    assert pick_label("ou_away", "under", 1.5, "Bayern", "Köln") == "Köln: Unter 1,5 Tore"
    assert pick_label("ou_away_2h", "under", 0.5, "Bayern", "Köln") == "Köln trifft nicht in der 2. HZ"
    assert pick_label("ou_1h", "over", 0.5, "Bayern", "Köln") == "1. HZ: Über 0,5 Tore"


def test_evaluate_picks_combo():
    rows = []
    for fid, outcomes in (
        (1, [True, True, True]),
        (2, [True, False, True]),
        (3, [True, True]),
    ):  # 3: incomplete
        for rank, hit in enumerate(outcomes, start=1):
            rows.append((fid, 2025, rank, "ou_ft", "over", 1.5, 0.8, hit, rank == 1))
    frame = pd.DataFrame(rows, columns=["fixture_id", "season", "rank", "market", "selection", "line", "probability",
                                        "outcome", "has_reason"])  # fmt: skip
    c = combos(frame)
    assert list(c.index) == [1, 2] and list(c["hit"]) == [True, False]
    result = evaluate_picks(frame)
    assert result["singles"]["n"] == 8 and abs(result["singles"]["hit_rate"] - 7 / 8) < 1e-9
    assert result["combo"]["n"] == 2 and result["combo"]["hit_rate"] == 0.5
    assert abs(result["combo"]["expected_naive"] - 0.8**3) < 1e-9
    assert result["hits_distribution"]["3"] == 0.5 and result["hits_distribution"]["2"] == 0.5
    assert result["reasons"]["with"]["n"] == 3
