import pandas as pd

from quotenfabrik.analytics import player_stats as ps

T = lambda s: pd.Timestamp(s, tz="UTC")  # noqa: E731


def _r(fid, day, minutes, starter, goals=0, assists=0, shots=0, league=78, p=None, rating=7.0):
    return {"fixture_id": fid, "kickoff": T(f"2026-09-{day:02d}"), "league_id": league, "minutes": minutes,
            "is_starter": starter, "goals": goals, "assists": assists, "shots_total": shots, "shots_on": 0,
            "key_passes": 0, "yellow": 0, "red": 0, "penalties_scored": 0, "penalties_missed": 0, "rating": rating,
            "p_anytime": p}  # fmt: skip


ROWS = pd.DataFrame([
    _r(1, 1, 90, True, goals=2, shots=5, p=0.5),
    _r(2, 8, 30, False, assists=1, shots=1, p=0.3),
    _r(3, 15, 0, False, rating=None),  # unused substitute: no appearance
    _r(4, 22, 60, True, goals=1, shots=2, league=2, p=0.4),
])  # fmt: skip


def test_summary_and_per_90():
    s = ps.summary(ROWS)
    assert (s["apps"], s["starts"], s["minutes"], s["goals"], s["assists"]) == (3, 2, 180, 3, 1)
    assert s["per90"]["goals"] == 1.5 and s["conversion"] == 3 / 8 and s["minutes_per_goal"] == 60
    assert ps.summary(ROWS.iloc[2:3]) == {"apps": 0}
    comps = {c["league_id"]: c for c in ps.by_competition(ROWS)}
    assert comps[78]["apps"] == 2 and comps[2]["goals"] == 1


def test_team_share_and_scoring_track():
    share = ps.team_share({"goals": 3, "assists": 1, "shots_total": 8, "minutes": 180}, {"goals": 6, "assists": 4,
                          "shots": 40, "matches": 3})  # fmt: skip
    assert share == {"goals": 0.5, "assists": 0.25, "shots": 0.2, "minutes": 180 / 270}
    track = ps.scoring_track(ROWS)
    assert track["matches"] == 3 and abs(track["expected"] - 1.2) < 1e-9 and track["actual"] == 2
    assert [p["actual"] for p in track["series"]] == [1, 1, 2]


def test_absence_summary():
    a = pd.DataFrame({"type": ["Missing Fixture", "Missing Fixture", "Questionable"],
                      "reason_label": ["Knieverletzung", "Knieverletzung", "Prellung"]})  # fmt: skip
    s = ps.absence_summary(a)
    assert s == {"missed": 2, "doubtful": 1, "reasons": [{"reason": "Knieverletzung", "matches": 2}]}
