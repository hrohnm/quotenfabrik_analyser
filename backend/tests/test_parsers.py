from datetime import UTC, datetime
from decimal import Decimal

from quotenfabrik.ingest import parsers
from tests.conftest import load_json

NOW = datetime(2026, 10, 19, tzinfo=UTC)


def test_matchday_from_round():
    assert parsers.matchday_from_round("Regular Season - 6") == 6
    assert parsers.matchday_from_round("Relegation Round") is None
    assert parsers.matchday_from_round(None) is None


def test_parse_fixture_detail():
    item = load_json("fixture_detail.json")["response"][0]
    p = parsers.parse_fixture(item, NOW)
    fx = p["fixture"]
    assert fx["id"] == 1575189
    assert fx["league_id"] == 78 and fx["season"] == 2026 and fx["matchday"] == 6
    assert (fx["home_team_id"], fx["away_team_id"]) == (163, 167)
    assert (fx["ft_home"], fx["ft_away"], fx["ht_home"], fx["ht_away"]) == (1, 2, 0, 1)
    assert fx["kickoff_utc"] == datetime(2026, 10, 18, 15, 30, tzinfo=UTC)
    assert {t["id"] for t in p["teams"]} == {163, 167}


def test_events_contain_all_goals():
    item = load_json("fixture_detail.json")["response"][0]
    events = parsers.parse_events(item["fixture"]["id"], item["events"])
    goals = [e for e in events if e["type"] == "Goal" and e["detail"] != "Missed Penalty"]
    assert len(goals) == item["goals"]["home"] + item["goals"]["away"]
    assert [e["seq"] for e in events] == list(range(len(events)))


def test_team_stats_and_players():
    item = load_json("fixture_detail.json")["response"][0]
    stats = parsers.parse_statistics_block(item["fixture"]["id"], item["statistics"])
    assert {s["period"] for s in stats} == {"FT"}
    assert len(stats) == 2
    home = next(s for s in stats if s["team_id"] == 163)
    assert isinstance(home["possession"], Decimal) and 0 < home["possession"] < 100
    assert home["shots_total"] >= home["shots_on"]
    assert "xg" in home

    lineups, grids = parsers.parse_lineups(item["fixture"]["id"], item["lineups"])
    assert len(lineups) == 2 and len(grids) == 22
    players, player_stats = parsers.parse_player_stats(item["fixture"]["id"], item["players"], grids)
    assert len(players) == len(player_stats) >= 22
    scorers = sum(p["goals"] or 0 for p in player_stats)
    assert scorers == 3
    assert sum(1 for p in player_stats if p["is_starter"]) == 22


def test_half_statistics():
    payload = load_json("statistics_half.json")
    rows = parsers.parse_statistics_block(1575189, payload["response"])
    assert {r["period"] for r in rows} == {"FT", "1H", "2H"}
    # every row has the same keys (needed for multi-row inserts)
    assert len({tuple(sorted(r)) for r in rows}) == 1


def test_parse_odds_filters_bookmakers_markets_and_asian_lines():
    payload = load_json("odds_fixture.json")
    rows = parsers.parse_odds(payload["response"], NOW, bookmakers={4, 8})
    assert rows
    assert {r["bookmaker_id"] for r in rows} == {4, 8}
    selections = {r["selection"] for r in rows if r["bet_id"] == 5}
    assert "Over 2.5" in selections
    assert not any(s.endswith((".25", ".75", ".0")) for s in selections)
    assert any(r["bet_id"] == 92 for r in rows)  # scorer market (Bet365)
    assert not any(r["bet_id"] == 4 for r in rows)  # Asian handicap is never stored
    keys = [(r["fixture_id"], r["bookmaker_id"], r["bet_id"], r["selection"], r["handicap"]) for r in rows]
    assert len(keys) == len(set(keys))


def test_parse_odds_without_betano_returns_nothing_for_betano():
    payload = load_json("odds_fixture.json")
    assert parsers.parse_odds(payload["response"], NOW, bookmakers={32}) == []


def test_to_decimal_is_lenient():
    assert parsers.to_decimal("7.3") == Decimal("7.3")
    assert parsers.to_decimal("55%") == Decimal("55")
    for bad in ("–", "-", "", None, "NaN"):
        assert parsers.to_decimal(bad) is None


def test_venue_id_zero_means_unknown():
    item = load_json("fixture_detail.json")["response"][0]
    item["fixture"]["venue"] = {"id": 0, "name": None, "city": None}
    p = parsers.parse_fixture(item, NOW)
    assert p["fixture"]["venue_id"] is None and p["venue"] is None


def test_detail_teams_include_teams_outside_the_fixture():
    item = {
        "events": [{"team": {"id": 853, "name": "Team A"}}, {"team": None}],
        "lineups": [
            {"team": {"id": 853, "name": "Team A", "logo": "a.png"}},
            {"team": {"id": 2263, "name": "Team X"}},
        ],
        "players": [{"team": {"id": 2263, "name": "Team X", "logo": "x.png"}}],
    }
    teams = {t["id"]: t for t in parsers.detail_teams(item)}
    assert set(teams) == {853, 2263}
    assert teams[2263]["logo_url"] == "x.png" and teams[853]["name"] == "Team A"
    assert parsers.detail_teams({}) == []
