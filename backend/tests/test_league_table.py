import pandas as pd

from quotenfabrik.analytics.league_table import figures, standings, table_group, top_players


def _m(day, home, away, gh, ga):
    return {"kickoff": pd.Timestamp(f"2026-09-{day:02d}", tz="UTC"), "home_id": home, "away_id": away,
            "ft_home": gh, "ft_away": ga}  # fmt: skip


MATCHES = pd.DataFrame([_m(1, 1, 2, 2, 0), _m(1, 3, 4, 1, 1), _m(8, 2, 3, 3, 1), _m(8, 4, 1, 0, 1)])


def test_standings_order_points_goal_difference_goals():
    table = standings(MATCHES, teams=[1, 2, 3, 4, 5])
    assert [r["team_id"] for r in table] == [1, 2, 4, 3, 5]  # 4 and 3 level on points, 4 better difference
    top = table[0]
    assert (top["played"], top["won"], top["points"], top["gf"], top["ga"], top["gd"]) == (2, 2, 6, 3, 0, 3)
    assert top["form"] == "SS" and table[1]["form"] == "NS"  # oldest first
    assert table[-1] == {"team_id": 5, "played": 0, "won": 0, "drawn": 0, "lost": 0, "gf": 0, "ga": 0, "form": "",
                         "gd": 0, "points": 0, "rank": 5}  # fmt: skip


def test_home_and_away_tables():
    home = {r["team_id"]: r for r in standings(MATCHES, scope="home")}
    away = {r["team_id"]: r for r in standings(MATCHES, scope="away")}
    assert (
        home[1]["played"] == 1
        and away[1]["played"] == 1
        and home[4]["points"] == 0
        and away[4]["points"] == 1
    )


def test_table_groups():
    assert table_group("Regular Season - 7") == "" and table_group("League Stage - 3") == ""
    assert (
        table_group("Group A - 2") == "Group A"
        and table_group("Round of 16") is None
        and table_group(None) == ""
    )


def test_top_players_ranks_ties_and_counts_assists():
    goals = pd.DataFrame([
        {"scorer_id": 10, "scorer_name": "Kane", "assist_id": 11, "assist_name": "Olise", "team_id": 1, "penalty": True},
        {"scorer_id": 10, "scorer_name": "Kane", "assist_id": None, "assist_name": None, "team_id": 1, "penalty": False},
        {"scorer_id": 11, "scorer_name": "Olise", "assist_id": 10, "assist_name": "Kane", "team_id": 1, "penalty": False},
        {"scorer_id": 20, "scorer_name": "Undav", "assist_id": None, "assist_name": None, "team_id": 2, "penalty": False},
    ])  # fmt: skip
    scorers = top_players(goals, "scorer", 3)
    assert scorers[0] == {"rank": 1, "player_id": 10, "name": "Kane", "team_id": 1, "goals": 2, "penalties": 1,
                          "assists": 1}  # fmt: skip
    assert [(s["name"], s["rank"]) for s in scorers[1:]] == [
        ("Olise", 2),
        ("Undav", 2),
    ]  # Olise ahead by assists
    assists = top_players(goals, "assist", 5)
    assert [(a["name"], a["assists"], a["goals"]) for a in assists] == [("Kane", 1, 2), ("Olise", 1, 1)]
    assert top_players(goals.iloc[0:0], "scorer", 3) == []


def test_figures():
    f = figures(MATCHES)
    assert f["matches"] == 4 and f["goals_per_match"] == 2.25 and f["home_win"] == 0.5 and f["draw"] == 0.25
    assert figures(MATCHES.iloc[0:0]) is None
