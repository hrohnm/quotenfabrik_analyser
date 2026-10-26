"""Ingest against a real PostgreSQL database (set QF_TEST_DATABASE_URL)."""

import copy
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select

from quotenfabrik.ingest import api_football, football_data, odds, team_mapping
from quotenfabrik.models import (
    Fixture,
    FixtureEvent,
    FixturePlayerStats,
    FixtureTeamStats,
    HistoricalMatch,
    OddsSnapshot,
    TeamAlias,
)
from tests.conftest import load_json

NOW = datetime(2026, 10, 19, tzinfo=UTC)


def test_fixture_details_are_idempotent(session):
    payload = load_json("fixture_detail.json")
    for _ in range(2):
        api_football.process_fixtures_payload(session, payload, NOW)
        session.commit()
    fixture = session.get(Fixture, 1575189)
    assert fixture.details_synced_at is not None
    assert session.scalar(select(func.count()).select_from(FixtureEvent)) == len(
        payload["response"][0]["events"]
    )
    assert session.scalar(select(func.count()).select_from(FixtureTeamStats)) == 2
    assert session.scalar(select(func.sum(FixturePlayerStats.goals))) == 3

    api_football.process_half_stats_payload(session, 1575189, load_json("statistics_half.json"), NOW)
    session.commit()
    periods = set(session.scalars(select(FixtureTeamStats.period)))
    assert periods == {"FT", "1H", "2H"}
    assert session.get(Fixture, 1575189).half_stats_synced_at is not None


def test_odds_only_store_changes(session):
    payload = load_json("odds_fixture.json")
    fixture_id = payload["response"][0]["fixture"]["id"]
    # minimal fixture row so the odds can reference it
    detail = copy.deepcopy(load_json("fixture_detail.json"))
    item = detail["response"][0]
    item["fixture"]["id"] = fixture_id
    item["fixture"]["status"]["short"] = "NS"
    for key in ("events", "lineups", "statistics", "players"):
        item.pop(key)
    api_football.process_fixtures_payload(session, detail, NOW)

    first = odds.process_odds_payload(session, payload, NOW, {4, 8})
    session.commit()
    assert first > 0
    assert odds.process_odds_payload(session, payload, NOW + timedelta(hours=3), {4, 8}) == 0
    session.commit()

    changed = copy.deepcopy(payload)
    pinnacle = next(b for b in changed["response"][0]["bookmakers"] if b["id"] == 4)
    match_winner = next(b for b in pinnacle["bets"] if b["id"] == 1)
    match_winner["values"][0]["odd"] = "9.99"
    assert odds.process_odds_payload(session, changed, NOW + timedelta(hours=6), {4, 8}) == 1
    session.commit()
    assert session.scalar(select(func.count()).select_from(OddsSnapshot)) == first + 1


def test_team_mapping_links_football_data_rows(session):
    detail = load_json("fixture_detail.json")
    api_football.process_fixtures_payload(session, detail, NOW)
    # second, different match of the same teams so each alias gets two votes
    second = copy.deepcopy(detail)
    item = second["response"][0]
    item["fixture"]["id"] = 999999
    item["fixture"]["date"] = "2026-03-07T14:30:00+00:00"
    item["teams"]["home"], item["teams"]["away"] = item["teams"]["away"], item["teams"]["home"]
    item["score"]["halftime"] = {"home": 2, "away": 2}
    item["score"]["fulltime"] = {"home": 4, "away": 3}
    for key in ("events", "lineups", "statistics", "players"):
        item.pop(key)
    api_football.process_fixtures_payload(session, second, NOW)
    session.commit()

    header = "Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,FTR,HTHG,HTAG,HTR\n"
    csv = (
        header
        + "D1,18/10/2026,16:30,M'gladbach,Hoffenheim,1,2,A,0,1,A\n"
        + "D1,07/03/2026,15:30,Hoffenheim,M'gladbach,4,3,H,2,2,D\n"
    )
    football_data.process_file(session, "D1", "2627", csv.encode())
    session.commit()

    report = team_mapping.map_and_link(session, 78, "D1")
    assert report.rows_linked == 2 and report.rows_unlinked == 0
    aliases = {a.alias: a.team_id for a in session.scalars(select(TeamAlias))}
    assert aliases == {"M'gladbach": 163, "Hoffenheim": 167}
    linked = session.scalar(
        select(HistoricalMatch.fixture_id).where(HistoricalMatch.match_date == date(2026, 10, 18))
    )
    assert linked == 1575189


def test_oddspapi_mapping_history_and_rebuild(session):
    from quotenfabrik.ingest import oddspapi, rebuild
    from quotenfabrik.models import OddsHistory, OddsPapiFixture, OddsPapiResponse
    from quotenfabrik.sources.oddspapi import OddsPapiResult

    # API-Football: Gladbach - Hoffenheim (18.10.) plus the reverse fixture for a second vote
    detail = load_json("fixture_detail.json")
    api_football.process_fixtures_payload(session, detail, NOW)
    second = copy.deepcopy(detail)
    item = second["response"][0]
    item["fixture"]["id"] = 999998
    item["fixture"]["date"] = "2026-03-07T14:30:00+00:00"
    item["teams"]["home"], item["teams"]["away"] = item["teams"]["away"], item["teams"]["home"]
    for key in ("events", "lineups", "statistics", "players"):
        item.pop(key)
    api_football.process_fixtures_payload(session, second, NOW)

    oddspapi.process_markets_payload(session, load_json("oddspapi_markets.json"))
    fixtures = [f for f in load_json("oddspapi_fixtures.json") if f["fixtureId"] == "id1000003572513246"]
    reverse = copy.deepcopy(fixtures[0])
    reverse.update(
        fixtureId="id_reverse",
        startTime="2026-03-07T14:30:00.000Z",
        participant1Id=fixtures[0]["participant2Id"],
        participant2Id=fixtures[0]["participant1Id"],
        participant1Name=fixtures[0]["participant2Name"],
        participant2Name=fixtures[0]["participant1Name"],
    )
    oddspapi.process_fixtures_payload(session, [*fixtures, reverse], NOW)
    session.commit()

    report = oddspapi.map_fixtures(session, 78, 35)
    assert report.aliases_total == 2 and report.linked == 2
    assert session.get(OddsPapiFixture, "id1000003572513246").fixture_id == 1575189
    assert session.get(OddsPapiFixture, "id_reverse").fixture_id == 999998

    payload = load_json("oddspapi_history.json")
    start = session.get(OddsPapiFixture, "id1000003572513246").start_time
    n = oddspapi.process_history_payload(session, payload, start, NOW, final=True)
    session.commit()
    stored = session.scalar(select(func.count()).select_from(OddsHistory))
    assert n == stored > 0
    assert session.scalar(select(func.max(OddsHistory.changed_at))) < start
    # idempotent
    oddspapi.process_history_payload(session, payload, start, NOW, final=True)
    session.commit()
    assert session.scalar(select(func.count()).select_from(OddsHistory)) == stored

    # rebuild from the compressed raw response
    import json

    body = json.dumps(payload).encode()
    oddspapi.store_raw(
        session, OddsPapiResult("historical-odds", {"fixtureId": payload["fixtureId"]}, 200, payload, body)
    )
    session.execute(OddsHistory.__table__.delete())
    session.commit()
    rebuild.rebuild_from_raw(session)
    assert session.scalar(select(func.count()).select_from(OddsHistory)) == stored
    assert session.scalar(select(func.count()).select_from(OddsPapiResponse)) == 1

    # latest prices before kickoff in model-market keys
    from quotenfabrik.analytics.bookmaker_odds import latest_prices, odds_table

    prices = latest_prices(session.get_bind(), [1575189])
    assert not prices.empty and (prices["changed_at"] < start).all()
    assert set(prices["bookmaker"]) <= {"betano.de", "pinnacle"}
    assert not prices.duplicated(["fixture_id", "bookmaker", "market", "line", "selection"]).any()
    assert "1x2" in set(prices["market"])
    table = odds_table(session.get_bind(), [1575189])
    assert table["betano"].notna().any()

    # odds reload: finished fixtures without prices are fetched again, fixtures with prices stay final
    session.get(OddsPapiFixture, "id1000003572513246").history_final = True
    session.get(OddsPapiFixture, "id_reverse").history_final = True
    session.commit()
    assert oddspapi.reset_empty_histories(session, 35) == 1
    assert session.get(OddsPapiFixture, "id_reverse").history_final is False
    assert session.get(OddsPapiFixture, "id1000003572513246").history_final is True

    # tournament ID changed: the old tournament's links to the league are removed
    assert oddspapi.unlink_tournament(session, 78, 35) == 2
    session.commit()
    assert session.get(OddsPapiFixture, "id1000003572513246").fixture_id is None


def test_fixtures_due_for_live_results(session):
    from datetime import timedelta

    from quotenfabrik.ingest.api_football import fixtures_due
    from quotenfabrik.models import Fixture

    api_football.process_fixtures_payload(session, load_json("fixture_detail.json"), NOW)
    session.commit()
    f = session.get(Fixture, 1575189)
    league = f.league_id
    cases = {  # (minutes since kickoff, status) -> due?
        (130, "2H"): True,  # regular end passed, still running in the data
        (130, "NS"): True,  # kickoff passed but never updated
        (60, "1H"): False,  # still being played
        (130, "FT"): False,  # result known
        (130, "PST"): False,  # postponed
        (60 * 24 * 3, "2H"): False,  # older than the polling window
    }
    for (minutes, status), expected in cases.items():
        f.kickoff_utc, f.status = NOW - timedelta(minutes=minutes), status
        session.commit()
        assert (fixtures_due(session, [league], NOW) == [1575189]) is expected, (minutes, status)
    assert fixtures_due(session, [league + 1000], NOW) == []


def test_fixtures_lineup_due(session):
    from datetime import timedelta

    from sqlalchemy import delete, func, select

    from quotenfabrik.ingest.api_football import fixtures_lineup_due
    from quotenfabrik.models import Fixture, FixtureLineupPlayer

    api_football.process_fixtures_payload(session, load_json("fixture_detail.json"), NOW)
    session.commit()
    count = (
        select(func.count()).select_from(FixtureLineupPlayer).where(FixtureLineupPlayer.fixture_id == 1575189)
    )
    assert session.scalar(count) > 22  # starting XI and bench of both teams
    f = session.get(Fixture, 1575189)
    f.kickoff_utc, f.status = NOW + timedelta(minutes=30), "NS"
    session.commit()
    assert fixtures_lineup_due(session, [f.league_id], NOW) == []  # line-up already known
    session.execute(delete(FixtureLineupPlayer).where(FixtureLineupPlayer.fixture_id == 1575189))
    session.commit()
    cases = {  # (minutes until kickoff, status) -> due?
        (30, "NS"): True,
        (90, "NS"): False,  # too early, the line-ups are not out yet
        (-20, "1H"): True,  # running without a line-up
        (30, "PST"): False,
    }
    for (minutes, status), expected in cases.items():
        f.kickoff_utc, f.status = NOW + timedelta(minutes=minutes), status
        session.commit()
        assert (fixtures_lineup_due(session, [f.league_id], NOW) == [1575189]) is expected, (minutes, status)
    # a payload without line-ups (before they are announced) keeps the stored ones
    payload = load_json("fixture_detail.json")
    api_football.process_fixtures_payload(session, payload, NOW)
    payload["response"][0]["lineups"] = []
    api_football.process_fixtures_payload(session, payload, NOW)
    session.commit()
    assert session.scalar(count) > 22


def test_frozen_run_stays_chosen_after_a_new_forecast(session, engine, monkeypatch):
    from datetime import timedelta
    from zoneinfo import ZoneInfo

    from sqlalchemy import text

    from quotenfabrik import app_config, day_freeze
    from quotenfabrik.api import data
    from quotenfabrik.models import Fixture, FrozenRun, ModelRun, Prediction

    monkeypatch.setattr(data, "get_engine", lambda: engine)
    monkeypatch.setattr(app_config, "shown_league_ids", lambda: [78])
    api_football.process_fixtures_payload(session, load_json("fixture_detail.json"), NOW)
    f = session.get(Fixture, 1575189)
    kickoff = NOW + timedelta(days=1, hours=14)
    f.kickoff_utc, f.status = kickoff, "NS"

    def forecast(as_of: datetime, p: float) -> int:
        run = ModelRun(kind="forecast", model_version="dc-v1", league_id=78, as_of=as_of, params={})
        session.add(run)
        session.flush()
        session.add(Prediction(model_run_id=run.id, fixture_id=1575189, market_group="1x2", market="1x2",
                               selection="H", probability=p, predicted_at=as_of))  # fmt: skip
        session.flush()
        return run.id

    def chosen() -> int:
        sql = f"with runs as ({data.chosen_runs_cte('and p.fixture_id = 1575189')}) select model_run_id from runs"
        return session.execute(text(sql)).scalar_one()

    morning = forecast(kickoff - timedelta(hours=8), 0.5)
    session.commit()
    day = kickoff.astimezone(ZoneInfo("Europe/Berlin")).date()
    assert day_freeze.freeze_day(engine, day, now=kickoff - timedelta(hours=7)) == {
        "fixtures": 1,
        "combos": 0,
    }
    noon = forecast(kickoff - timedelta(hours=2), 0.6)
    session.commit()
    assert noon != morning and chosen() == morning  # the frozen run, not the newer forecast
    assert day_freeze.freeze_day(engine, day, now=kickoff - timedelta(hours=1))["fixtures"] == 0
    session.execute(text("delete from analytics.frozen_runs"))
    session.commit()
    assert chosen() == noon  # without freezing: the latest forecast before kickoff
    assert session.query(FrozenRun).count() == 0
