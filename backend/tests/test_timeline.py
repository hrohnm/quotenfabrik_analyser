"""Match timeline from the API events (no database)."""

from quotenfabrik.api.routers.fixtures import timeline


def ev(minute, team, player, type_, detail, extra=None, assist=None, pid=None):
    return {"minute": minute, "extra_minute": extra, "team_id": team, "player_id": pid or hash(player) % 10000,
            "player_name": player, "assist_name": assist, "type": type_, "detail": detail, "comments": None}  # fmt: skip


def test_timeline_kinds_score_and_order():
    rows = [
        ev(12, 2, "Poulsen", "Goal", "Normal Goal", assist="X"),
        ev(45, 1, "VAR", "Var", "Goal cancelled", extra=3),  # API order: before the own goal in minute 45
        ev(45, 1, "Bornauw", "Goal", "Own Goal"),
        ev(55, 1, "Bernardo", "Card", "Yellow Card", pid=7),
        ev(65, 1, "Bernardo", "Card", "Yellow Card", pid=7),
        ev(65, 1, "Bernardo", "Card", "Red Card", pid=7),
        ev(70, 2, "Out", "subst", "Substitution 1", assist="In"),
        ev(80, 2, "Keeper", "Card", "Red Card", pid=9),
        ev(88, 1, "Missed", "Goal", "Missed Penalty"),
    ]
    t = timeline(rows, home_id=1)
    assert [(e["minute"], e["kind"]) for e in t] == [
        (12, "goal"), (45, "own_goal"), (45, "var"), (55, "yellow"), (65, "second_yellow"), (70, "sub"), (80, "red"),
        (88, "missed_penalty"),
    ]  # fmt: skip
    assert t[0]["side"] == "away" and t[0]["score"] == [0, 1] and t[0]["related"] == "X"
    assert t[1]["side"] == "home" and t[1]["score"] == [1, 1]  # own goal counts for the team it carries
    assert "score" not in t[-1]  # missed penalty
    sub = next(e for e in t if e["kind"] == "sub")
    assert sub["player"] == "Out" and sub["related"] == "In"
