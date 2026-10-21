import pandas as pd

from quotenfabrik.analytics.lineups import Absences, evaluate, predict

POS = ["G"] + ["D"] * 4 + ["M"] * 4 + ["F"] * 2


def _match(fixture_id: int, day: int, starters: list[int], bench: list[int]) -> list[dict]:
    rows = []
    for i, pid in enumerate(starters):
        rows.append({"fixture_id": fixture_id, "kickoff": pd.Timestamp(f"2026-10-{day:02d}", tz="UTC"),
                     "league_id": 78, "team_id": 1, "player_id": pid, "player_name": f"P{pid}", "number": pid,
                     "pos": POS[i], "grid": f"{i}:1", "is_starter": True, "sort": i + 1, "formation": "4-4-2"})  # fmt: skip
    for i, (pid, pos) in enumerate(bench):
        rows.append({"fixture_id": fixture_id, "kickoff": pd.Timestamp(f"2026-10-{day:02d}", tz="UTC"),
                     "league_id": 78, "team_id": 1, "player_id": pid, "player_name": f"P{pid}", "number": pid,
                     "pos": pos, "grid": None, "is_starter": False, "sort": 101 + i, "formation": "4-4-2"})  # fmt: skip
    return rows


XI = list(range(1, 12))
HISTORY = pd.DataFrame(
    _match(1, 1, XI[:5] + [20] + XI[6:], [(6, "M"), (30, "D")])  # 6 benched once
    + _match(2, 8, XI, [(20, "M"), (21, "M"), (30, "D")])  # last match: regular XI
)


def test_predict_takes_the_last_starting_xi():
    pred = predict(HISTORY, Absences(set(), set()))
    assert pred["basis"]["fixture_id"] == 2 and pred["formation"] == "4-4-2"
    assert [p["player_id"] for p in pred["start"]] == XI
    assert all(p["replaces"] is None for p in pred["start"])


def test_absent_player_is_replaced_by_same_position_with_most_starts():
    pred = predict(HISTORY, Absences(missing={7}, questionable={9}))
    ids = [p["player_id"] for p in pred["start"]]
    assert 7 not in ids and ids[6] == 20  # midfielder 20 started match 1, 21 never did
    assert pred["start"][6]["replaces"] == "P7" and pred["start"][6]["grid"] == "6:1"  # takes the slot
    assert next(p for p in pred["start"] if p["player_id"] == 9)["questionable"]
    # without adjusting the absent player stays in and is flagged
    raw = predict(HISTORY, Absences(missing={7}, questionable=set()), adjust=False)
    assert next(p for p in raw["start"] if p["player_id"] == 7)["absent"]


def test_goalkeeper_is_only_replaced_by_a_goalkeeper():
    pred = predict(HISTORY, Absences(missing={1}, questionable=set()))
    assert pred["start"][0]["player_id"] == 1 and pred["start"][0]["replaces"] is None  # no keeper available


def test_evaluate_uses_only_earlier_line_ups():
    nxt = pd.DataFrame(_match(3, 15, XI[:10] + [30], []))  # striker 11 replaced by 30 in the real XI
    history = pd.concat([HISTORY, nxt], ignore_index=True)
    fixtures = pd.DataFrame([{"fixture_id": 3, "team_id": 1, "kickoff": pd.Timestamp("2026-10-15", tz="UTC"),
                              "league_id": 78, "season": 2026}])  # fmt: skip
    absences = pd.DataFrame(columns=["fixture_id", "team_id", "player_id", "player_name", "type", "reason"])
    result = evaluate(history, absences, fixtures)
    assert result["letzte Startelf"].tolist() == [10] and result["letzte Startelf|keeper"].tolist() == [True]
