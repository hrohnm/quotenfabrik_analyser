import pandas as pd

from quotenfabrik.analytics import competition_stats as cs

T = lambda s: pd.Timestamp(s, tz="UTC")  # noqa: E731


def _m(fid, md, home, away, ft, ht):
    return {"fixture_id": fid, "matchday": md, "kickoff": T(f"2026-09-{md:02d}"), "home_id": home, "away_id": away,
            "ft_home": ft[0], "ft_away": ft[1], "ht_home": ht[0], "ht_away": ht[1]}  # fmt: skip


MATCHES = pd.DataFrame([
    _m(1, 1, 1, 2, (2, 0), (0, 0)), _m(2, 1, 3, 4, (1, 1), (1, 0)),
    _m(3, 2, 2, 3, (0, 3), (0, 2)), _m(4, 2, 4, 1, (2, 2), (2, 0)),
])  # fmt: skip
TEAMS = [1, 2, 3, 4]


def test_half_tables_and_position_history():
    first = {r["team_id"]: r for r in cs_standings(cs.half_matches(MATCHES, 1))}
    assert first[3]["points"] == 6 and first[4]["points"] == 3 and first[1]["points"] == 1  # 0:0, then 0:2
    second = {r["team_id"]: r for r in cs_standings(cs.half_matches(MATCHES, 2))}
    assert second[1]["points"] == 6 and second[1]["gf"] == 4  # 2:0 and 2:0 in the second halves
    hist = cs.position_history(MATCHES, TEAMS)
    assert hist["matchdays"] == [1, 2] and hist["positions"][1] == [1, 2] and hist["positions"][3] == [2, 1]


def cs_standings(m):
    from quotenfabrik.analytics.league_table import standings

    return standings(m, TEAMS)


def test_form_and_expected_tables():
    form = {r["team_id"]: r for r in cs.form_table(MATCHES, TEAMS, n=1)}
    assert form[3]["played"] == 1 and form[3]["points"] == 3 and form[1]["points"] == 1  # only the last match
    probs = pd.DataFrame({"fixture_id": [1, 3], "H": [0.5, 0.2], "D": [0.3, 0.3], "A": [0.2, 0.5]})
    exp = {r["team_id"]: r for r in cs.expected_table(MATCHES, probs, TEAMS)}
    assert exp[1]["points"] == 3 and abs(exp[1]["expected"] - 1.8) < 1e-9 and exp[1]["matches"] == 1
    assert abs(exp[2]["expected"] - (0.9 + 0.9)) < 1e-9 and exp[2]["points"] == 0


def test_player_rankings_and_knockout_ties():
    players = pd.DataFrame([
        {"fixture_id": 1, "player_id": 9, "name": "Kane", "team_id": 1, "minutes": 900, "goals": 9, "assists": 1,
         "penalties_scored": 2, "yellow": 0, "red": 0, "rating": 8.0, "shots_total": 30},
        {"fixture_id": 1, "player_id": 7, "name": "Joker", "team_id": 1, "minutes": 90, "goals": 2, "assists": 0,
         "penalties_scored": 0, "yellow": 1, "red": 1, "rating": 9.0, "shots_total": 3},
    ])  # fmt: skip
    r = cs.player_rankings(players)
    assert [p["name"] for p in r["goals"]] == ["Kane", "Joker"]
    assert [p["name"] for p in r["goals_per_90"]] == ["Kane"]  # Joker below the minutes threshold
    assert r["cards"][0]["name"] == "Joker" and r["cards"][0]["value"] == 4

    ko = pd.DataFrame([
        {"fixture_id": 10, "round": "Round of 16", "round_label": "Achtelfinale", "kickoff": T("2027-02-17"),
         "home_id": 1, "away_id": 2, "ft_home": 2, "ft_away": 1, "finished": True},
        {"fixture_id": 11, "round": "Round of 16", "round_label": "Achtelfinale", "kickoff": T("2027-03-10"),
         "home_id": 2, "away_id": 1, "ft_home": 3, "ft_away": 0, "finished": True},
        {"fixture_id": 12, "round": "League Stage - 1", "round_label": "Ligaphase", "kickoff": T("2026-09-17"),
         "home_id": 1, "away_id": 3, "ft_home": 1, "ft_away": 0, "finished": True},
    ])  # fmt: skip
    rounds = cs.knockout_ties(ko)
    assert len(rounds) == 1 and rounds[0]["label"] == "Achtelfinale"
    tie = rounds[0]["ties"][0]
    assert tie["team_a"] == 1 and tie["aggregate"] == [2, 4] and len(tie["legs"]) == 2
