import numpy as np
import pandas as pd

from quotenfabrik.analytics.availability import availability_features, schedule_features
from quotenfabrik.analytics.availability_eval import fit_correction

T = lambda s: pd.Timestamp(s, tz="UTC")  # noqa: E731


def test_schedule_features_cup_next_to_league_match():
    schedule = pd.DataFrame([
        {"fixture_id": 1, "team_id": 7, "kickoff": T("2026-10-04 15:30"), "cup": False, "league_id": 78},
        {"fixture_id": 2, "team_id": 7, "kickoff": T("2026-10-07 19:00"), "cup": True, "league_id": 2},
        {"fixture_id": 3, "team_id": 7, "kickoff": T("2026-10-10 15:30"), "cup": False, "league_id": 78},
        {"fixture_id": 4, "team_id": 7, "kickoff": T("2026-10-24 15:30"), "cup": False, "league_id": 78},
    ])  # fmt: skip
    f = schedule_features(schedule).set_index("fixture_id")
    assert f.loc[1, "next_cup"] == 1 and f.loc[1, "rest_days"] == 14  # no earlier match: capped
    assert f.loc[3, "prev_cup"] == 1 and f.loc[3, "short_rest"] == 1 and f.loc[3, "games_14d"] == 2
    assert f.loc[4, "prev_cup"] == 0 and f.loc[4, "next_cup"] == 0 and f.loc[4, "rest_days"] == 14


def _players():
    rows = []
    for i, day in enumerate(("2026-09-01", "2026-09-08", "2026-09-15", "2026-09-22")):
        for pid, pos, starts, ga in (
            (1, "G", True, 0),
            (2, "D", True, 0),
            (9, "F", True, 2),
            (10, "F", i == 3, 0),
        ):
            rows.append({"fixture_id": 100 + i, "kickoff": T(day), "team_id": 7, "player_id": pid,
                         "is_starter": starts, "minutes": 90, "ga": ga, "position": pos})  # fmt: skip
    rows.append({"fixture_id": 200, "kickoff": T("2026-10-01"), "team_id": 7, "player_id": 9, "is_starter": True,
                 "minutes": 90, "ga": 5, "position": "F"})  # after kickoff of the match below: ignored  # fmt: skip
    return pd.DataFrame(rows)


def test_absences_are_weighted_by_role_before_kickoff():
    fixtures = pd.DataFrame([{"fixture_id": 300, "team_id": 7, "kickoff": T("2026-09-29")}])
    absences = pd.DataFrame([{"fixture_id": 300, "team_id": 7, "player_id": 9, "type": "Missing Fixture"},
                             {"fixture_id": 300, "team_id": 7, "player_id": 2, "type": "Questionable"}])  # fmt: skip
    xi = pd.DataFrame([{"fixture_id": 300, "team_id": 7, "player_id": p} for p in (2, 10)])
    row = availability_features(fixtures, _players(), absences, xi).iloc[0]
    assert row["miss_starters"] == 1.0 and row["miss_attack"] == 1.0 and row["miss_defense"] == 0.0
    assert row["doubtful"] == 1.0
    assert row["rotated"] == 1.0  # keeper 1 is a regular starter, not absent and not in the XI


def test_correction_recovers_a_known_effect():
    rng = np.random.default_rng(0)
    n = 20000
    x = rng.integers(0, 2, n).astype(float)
    lam = rng.uniform(0.8, 2.0, n)
    goals = rng.poisson(lam * np.exp(-0.2 * x))
    rows = pd.DataFrame({"goals": goals, "lam": lam, "own_a": x, "opp_a": 0.0})
    beta = fit_correction(rows, ["a"])
    assert abs(beta[0] + 0.2) < 0.03 and abs(beta[1]) < 0.01


def test_neighbour_matches_and_missing_players():
    from quotenfabrik.analytics.availability import missing_players, neighbour_matches, roles_before

    schedule = pd.DataFrame([
        {"fixture_id": 1, "kickoff": T("2026-10-07 19:00"), "league_id": 2, "league": "UEFA Champions League",
         "cup": True, "home_id": 8, "away_id": 7, "home": "Viking", "away": "Bayern", "hg": 3, "ag": 1},
        {"fixture_id": 3, "kickoff": T("2026-10-14 19:00"), "league_id": 2, "league": "UEFA Champions League",
         "cup": True, "home_id": 7, "away_id": 9, "home": "Bayern", "away": "Arsenal", "hg": None, "ag": None},
    ])  # fmt: skip
    ctx = neighbour_matches(schedule, 7, T("2026-10-10 15:30"))
    assert ctx["prev"]["score"] == [1, 3] and not ctx["prev"]["home"] and ctx["prev"]["opponent"] == "Viking"
    assert ctx["next"]["days"] == 4.1 and ctx["next"]["home"] and ctx["next"]["score"] is None

    roles = roles_before(_players(), 7, T("2026-09-29"))
    absences = pd.DataFrame([
        {"player_id": 10, "player_name": "P10", "type": "Missing Fixture", "reason": "Knock"},
        {"player_id": 9, "player_name": "P9", "type": "Missing Fixture", "reason": "Knee Injury"},
        {"player_id": 1, "player_name": "P1", "type": "Questionable", "reason": None},
    ])  # fmt: skip
    out = missing_players(roles, absences, {9: "Stürmer Neun"})
    assert [p["player_id"] for p in out] == [9, 10, 1]  # missing regulars first, doubtful last
    assert (
        out[0]["name"] == "Stürmer Neun" and out[0]["regular"] and out[0]["reason_label"] == "Knieverletzung"
    )
    assert (
        not out[1]["regular"] and out[2]["type"] == "doubtful" and out[2]["reason_label"] == "Grund unbekannt"
    )
