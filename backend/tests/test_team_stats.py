import pandas as pd

from quotenfabrik.analytics import team_stats

T = lambda s: pd.Timestamp(s, tz="UTC")  # noqa: E731


def _m(fid, day, home, away, hg, ag, hthg, htag):
    return {"fixture_id": fid, "kickoff": T(f"2026-09-{day:02d}"), "league_id": 78, "home_id": home, "away_id": away,
            "hg": hg, "ag": ag, "hthg": hthg, "htag": htag}  # fmt: skip


MATCHES = pd.DataFrame([
    _m(1, 1, 7, 2, 3, 1, 1, 0),  # home win
    _m(2, 8, 3, 7, 1, 1, 1, 0),  # away draw
    _m(3, 15, 7, 4, 2, 0, 0, 0),  # home win, clean sheet
    _m(4, 22, 5, 7, 0, 2, 0, 1),  # away win, clean sheet
])  # fmt: skip


def test_team_view_and_splits():
    v = team_stats.team_view(MATCHES, 7)
    assert v["result"].tolist() == ["S", "U", "S", "S"] and v["home"].tolist() == [True, False, True, False]
    s = team_stats.splits(v)
    assert s["total"]["played"] == 4 and s["total"]["points_per_game"] == 2.5
    assert s["home"]["gf_per_game"] == 2.5 and s["away"]["ga_per_game"] == 0.5
    assert (
        s["total"]["clean_sheet"] == 0.5 and s["total"]["over_2_5"] == 0.25 and s["total"]["ht_lead"] == 0.5
    )
    assert s["total"]["second_half_goals"] == 1.75  # (3 + 1 + 2 + 1) / 4
    assert team_stats.split(v.iloc[0:0]) == {"played": 0}


def test_streaks_from_latest_match_backwards():
    v = team_stats.team_view(MATCHES, 7)
    by_key = {s["key"]: s["length"] for s in team_stats.streaks(v)}
    assert by_key["unbeaten"] == 4 and by_key["wins"] == 2 and by_key["clean_sheets"] == 2
    assert "winless" not in by_key and "btts" not in by_key


def test_goal_segments_and_expected_points():
    goals = pd.DataFrame({"minute": [3, 44, 90, 95, 60], "scoring_team": [7, 7, 2, 7, 2]})
    seg = {s["label"]: s for s in team_stats.goal_segments(goals, 7, 4)}
    assert seg["1–15"]["scored"] == 1 and seg["76–90"]["scored"] == 1 and seg["76–90"]["conceded"] == 1
    assert seg["46–60"]["conceded"] == 1 and sum(s["scored"] for s in seg.values()) == 3
    v = team_stats.team_view(MATCHES, 7)
    probs = pd.DataFrame({"fixture_id": [1, 2], "p_win": [0.6, 0.3], "p_draw": [0.2, 0.3]})
    xp = team_stats.expected_points(v, probs)
    assert xp["points"] == 4 and abs(xp["expected"] - (2.0 + 1.2)) < 1e-9 and xp["matches"] == 2


def test_stat_averages_against_league():
    stats = pd.DataFrame([
        {"fixture_id": 1, "team_id": 7, "shots_total": 20, "shots_on": 8, "xg": 2.0, "possession": 60, "corners": 6,
         "fouls": 10, "yellow": 1, "passes_total": 500, "passes_accurate": 450},
        {"fixture_id": 1, "team_id": 2, "shots_total": 8, "shots_on": 2, "xg": 0.6, "possession": 40, "corners": 2,
         "fouls": 14, "yellow": 3, "passes_total": 300, "passes_accurate": 210},
    ])  # fmt: skip
    rows = {r["key"]: r for r in team_stats.stat_averages(stats, 7)}
    assert (
        rows["shots_total"]["team"] == 20
        and rows["shots_total"]["against"] == 8
        and rows["shots_total"]["league"] == 14
    )
    assert rows["passes_accurate_pct"]["team"] == 90
