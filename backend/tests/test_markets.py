from quotenfabrik.markets import BET_ID_TO_GROUP, is_tracked_selection


def test_asian_markets_are_not_tracked():
    for asian_bet in (4, 19, 50, 72, 104, 336):
        assert asian_bet not in BET_ID_TO_GROUP


def test_only_half_goal_lines():
    assert is_tracked_selection(5, "Over 2.5")
    assert is_tracked_selection(16, "Under 0.5")
    assert not is_tracked_selection(5, "Over 2.25")
    assert not is_tracked_selection(5, "Over 2.75")
    assert not is_tracked_selection(5, "Over 3")
    assert not is_tracked_selection(5, "Over 3.0")


def test_non_line_markets():
    assert is_tracked_selection(1, "Home")
    assert is_tracked_selection(92, "Tim Kleindienst")
    assert not is_tracked_selection(999, "Home")
