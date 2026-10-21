"""API-Football ingest: fixtures, match details, half-time statistics and injuries.

Every ``process_*`` function works on a payload alone, so ``core`` can be rebuilt from ``raw.api_responses``
without new API requests (see ``quotenfabrik.ingest.rebuild``).
"""

import logging
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from quotenfabrik.ingest import parsers
from quotenfabrik.ingest.db_utils import upsert
from quotenfabrik.models import (
    Fixture,
    FixtureEvent,
    FixtureLineup,
    FixturePlayerStats,
    FixtureTeamStats,
    Injury,
    League,
    Player,
    Team,
    Venue,
)
from quotenfabrik.sources.api_football import ApiFootballClient

log = logging.getLogger(__name__)

IDS_PER_REQUEST = 20  # API maximum for /fixtures?ids=
HALF_STATS_FROM_SEASON = 2024  # /fixtures/statistics?half=true has data from this season on


def _now() -> datetime:
    return datetime.now(UTC)


def _chunks(items: Sequence[int], size: int) -> Iterable[Sequence[int]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


# --------------------------------------------------------------------------- processing


def process_fixtures_payload(session: Session, payload: dict[str, Any], fetched_at: datetime) -> list[int]:
    """Upserts fixtures (and, if present, their details). Returns the processed fixture ids."""
    items = payload.get("response") or []
    parsed = [parsers.parse_fixture(item, fetched_at) for item in items]
    if not parsed:
        return []

    leagues = {p["league"]["id"]: p["league"] for p in parsed}
    teams = {t["id"]: t for p in parsed for t in p["teams"]}
    venues = {p["venue"]["id"]: p["venue"] for p in parsed if p["venue"]}
    upsert(session, League, list(leagues.values()))
    upsert(session, Team, list(teams.values()))
    upsert(session, Venue, list(venues.values()))
    upsert(session, Fixture, [p["fixture"] for p in parsed], exclude_from_update=("details_synced_at",))

    for item, p in zip(items, parsed, strict=True):
        if "events" in item or "players" in item:
            _process_details(session, item, p["fixture"], fetched_at)
    return [p["fixture"]["id"] for p in parsed]


def _process_details(session: Session, item: dict, fixture: dict, fetched_at: datetime) -> None:
    fixture_id = fixture["id"]
    upsert(session, Team, parsers.detail_teams(item), update=False)  # known teams keep their data
    session.execute(delete(FixtureEvent).where(FixtureEvent.fixture_id == fixture_id))
    events = parsers.parse_events(fixture_id, item.get("events"))
    if events:
        session.execute(FixtureEvent.__table__.insert(), events)

    lineups, grids = parsers.parse_lineups(fixture_id, item.get("lineups"))
    upsert(session, FixtureLineup, lineups)

    upsert(session, FixtureTeamStats, parsers.parse_statistics_block(fixture_id, item.get("statistics")))

    players, player_stats = parsers.parse_player_stats(fixture_id, item.get("players"), grids)
    upsert(session, Player, players)
    upsert(session, FixturePlayerStats, player_stats)

    if fixture["status"] in parsers.FINISHED_STATUSES and item.get("players"):
        session.execute(update(Fixture).where(Fixture.id == fixture_id).values(details_synced_at=fetched_at))


def process_half_stats_payload(
    session: Session, fixture_id: int, payload: dict[str, Any], fetched_at: datetime
) -> None:
    rows = parsers.parse_statistics_block(fixture_id, payload.get("response"))
    upsert(session, FixtureTeamStats, rows)
    if any(r["period"] == "1H" for r in rows):
        session.execute(
            update(Fixture).where(Fixture.id == fixture_id).values(half_stats_synced_at=fetched_at)
        )


def process_injuries_payload(session: Session, payload: dict[str, Any]) -> int:
    rows = parsers.parse_injuries(payload.get("response"))
    known = set(session.scalars(select(Fixture.id).where(Fixture.id.in_({r["fixture_id"] for r in rows}))))
    rows = [r for r in rows if r["fixture_id"] in known]
    upsert(session, Injury, rows)
    return len(rows)


# --------------------------------------------------------------------------- jobs


def sync_season(session: Session, client: ApiFootballClient, league_id: int, season: int) -> int:
    """Loads the full fixture list (schedule + results) of one season. 1 request."""
    result = client.get("fixtures", {"league": league_id, "season": season})
    ids = process_fixtures_payload(session, result.payload, _now())
    session.commit()
    log.info("League %s season %s: %d fixtures", league_id, season, len(ids))
    return len(ids)


def fixtures_missing_details(session: Session, league_id: int, season: int) -> list[int]:
    return list(
        session.scalars(
            select(Fixture.id)
            .where(
                Fixture.league_id == league_id,
                Fixture.season == season,
                Fixture.status.in_(parsers.FINISHED_STATUSES),
                Fixture.details_synced_at.is_(None),
            )
            .order_by(Fixture.kickoff_utc)
        )
    )


def sync_details(session: Session, client: ApiFootballClient, fixture_ids: Sequence[int]) -> int:
    """Events, lineups, statistics and player stats via /fixtures?ids= (20 fixtures per request)."""
    done = 0
    for chunk in _chunks(list(fixture_ids), IDS_PER_REQUEST):
        result = client.get("fixtures", {"ids": "-".join(map(str, chunk))})
        done += len(process_fixtures_payload(session, result.payload, _now()))
        session.commit()
    return done


DUE_AFTER = timedelta(minutes=110)  # 90 minutes + half-time + stoppage time
POLL_FOR = timedelta(days=2)  # stop polling fixtures that never got a result (the daily import catches them)
NOT_PLAYED = {"PST", "CANC", "ABD"}  # postponed, cancelled, abandoned: no result to wait for


def fixtures_due(session: Session, league_ids: Sequence[int], now: datetime | None = None) -> list[int]:
    """Fixtures whose regular end has passed but that have no final result yet."""
    now = now or _now()
    return list(
        session.scalars(
            select(Fixture.id)
            .where(
                Fixture.league_id.in_(list(league_ids)),
                Fixture.kickoff_utc <= now - DUE_AFTER,
                Fixture.kickoff_utc >= now - POLL_FOR,
                Fixture.status.not_in(parsers.FINISHED_STATUSES | NOT_PLAYED),
            )
            .order_by(Fixture.kickoff_utc)
        )
    )


def fixtures_missing_half_stats(session: Session, league_id: int, season: int) -> list[int]:
    if season < HALF_STATS_FROM_SEASON:
        return []
    return list(
        session.scalars(
            select(Fixture.id)
            .where(
                Fixture.league_id == league_id,
                Fixture.season == season,
                Fixture.status.in_(parsers.FINISHED_STATUSES),
                Fixture.half_stats_synced_at.is_(None),
            )
            .order_by(Fixture.kickoff_utc)
        )
    )


def sync_half_stats(session: Session, client: ApiFootballClient, fixture_ids: Sequence[int]) -> int:
    """Team statistics per half (1 request per fixture, data from season 2024)."""
    for fixture_id in fixture_ids:
        result = client.get("fixtures/statistics", {"fixture": fixture_id, "half": "true"})
        process_half_stats_payload(session, fixture_id, result.payload, _now())
        session.commit()
    return len(fixture_ids)


def sync_injuries(session: Session, client: ApiFootballClient, league_id: int, season: int) -> int:
    result = client.get("injuries", {"league": league_id, "season": season})
    count = process_injuries_payload(session, result.payload)
    session.commit()
    return count
