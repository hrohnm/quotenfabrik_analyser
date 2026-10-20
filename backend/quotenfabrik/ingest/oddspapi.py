"""OddsPapi ingest: Betano (and Pinnacle) odds histories for API-Football fixtures.

Quota: only ``/markets``, ``/fixtures`` and ``/odds-by-tournaments`` are billable (free plan: 250 per month).
Odds histories come from the free ``/historical-odds`` endpoint (5 s cooldown). Histories are available
from January 2026 on.
"""

import gzip
import hashlib
import json
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from quotenfabrik.ingest import oddspapi_parsers as parsers
from quotenfabrik.ingest.db_utils import upsert
from quotenfabrik.models import (
    Fixture,
    OddsHistory,
    OddsPapiFixture,
    OddsPapiMarket,
    OddsPapiPlayer,
    OddsPapiResponse,
    Team,
    TeamAlias,
)
from quotenfabrik.sources.oddspapi import OddsPapiClient, OddsPapiNotFound, OddsPapiResult

log = logging.getLogger(__name__)

SOURCE = "oddspapi"
HISTORY_SINCE = datetime(2026, 1, 1, tzinfo=UTC)  # OddsPapi keeps odds histories from January 2026
PRE_MATCH_WINDOW = timedelta(days=14)
FINAL_AFTER_KICKOFF = timedelta(hours=3)  # history is complete once the match is over
CANCELLED = 3
KICKOFF_TOLERANCE = timedelta(hours=1)  # for name-based voting
LINK_TOLERANCE = timedelta(days=4)  # for linking via mapped teams (rescheduled matches)
MIN_VOTES = 2
MIN_SHARE = 0.7


def _now() -> datetime:
    return datetime.now(UTC)


def store_raw(session: Session, result: OddsPapiResult) -> None:
    session.add(
        OddsPapiResponse(
            endpoint=result.endpoint,
            params={k: str(v) for k, v in result.params.items()},
            sha256=hashlib.sha256(result.content).hexdigest(),
            content_gzip=gzip.compress(result.content, 6),
        )
    )


def load_raw(response: OddsPapiResponse) -> Any:
    return json.loads(gzip.decompress(response.content_gzip))


# --------------------------------------------------------------------------- processing


def process_markets_payload(session: Session, payload: list[dict]) -> int:
    rows = parsers.parse_markets(payload)
    upsert(session, OddsPapiMarket, rows)
    return len(rows)


def process_fixtures_payload(session: Session, payload: list[dict], fetched_at: datetime) -> int:
    rows = parsers.parse_fixtures(payload, fetched_at)
    upsert(
        session,
        OddsPapiFixture,
        rows,
        exclude_from_update=("fixture_id", "history_synced_at", "history_final"),
    )
    return len(rows)


def tracked_market_ids(session: Session) -> set[int]:
    return set(session.scalars(select(OddsPapiMarket.id).where(OddsPapiMarket.market_group.is_not(None))))


def process_history_payload(
    session: Session, payload: dict, start_time: datetime, fetched_at: datetime, final: bool
) -> int:
    """Stores pre-match price changes. Returns the number of parsed rows (duplicates are skipped)."""
    rows = parsers.parse_history(payload, tracked_market_ids(session), before=start_time)
    upsert(session, OddsHistory, rows, update=False)
    session.execute(
        update(OddsPapiFixture)
        .where(OddsPapiFixture.id == payload["fixtureId"])
        .values(history_synced_at=fetched_at, history_final=final)
    )
    return len(rows)


def process_player_names_payload(session: Session, payload: list[dict], fetched_at: datetime) -> int:
    names = parsers.parse_player_names(payload)
    upsert(
        session,
        OddsPapiPlayer,
        [{"id": pid, "name": name, "updated_at": fetched_at} for pid, name in names.items()],
        exclude_from_update=("player_id",),
    )
    return len(names)


# --------------------------------------------------------------------------- jobs (API calls)


def sync_markets(session: Session, client: OddsPapiClient, sport_id: int = 10) -> int:
    """Market catalog (1 billable request)."""
    result = client.get("markets", {"sportId": sport_id})
    store_raw(session, result)
    count = process_markets_payload(session, result.payload)
    session.commit()
    return count


def sync_fixtures(
    session: Session, client: OddsPapiClient, tournament_id: int, start: datetime, end: datetime
) -> int:
    """Fixture list of a tournament between two dates (1 billable request)."""
    result = client.get(
        "fixtures",
        {
            "tournamentId": tournament_id,
            "from": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "to": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )
    store_raw(session, result)
    count = process_fixtures_payload(session, result.payload, _now())
    session.commit()
    return count


def fixtures_needing_history(
    session: Session, tournament_id: int, now: datetime | None = None, limit: int | None = None
) -> list[OddsPapiFixture]:
    """Fixtures since January 2026 up to 14 days ahead whose history is not final yet."""
    now = now or _now()
    stmt = (
        select(OddsPapiFixture)
        .where(
            OddsPapiFixture.tournament_id == tournament_id,
            OddsPapiFixture.history_final.is_(False),
            OddsPapiFixture.start_time >= HISTORY_SINCE,
            OddsPapiFixture.start_time <= now + PRE_MATCH_WINDOW,
            func.coalesce(OddsPapiFixture.status_id, 0) != CANCELLED,
        )
        .order_by(OddsPapiFixture.start_time)
    )
    if limit:
        stmt = stmt.limit(limit)
    return list(session.scalars(stmt))


def unlink_tournament(session: Session, league_id: int, tournament_id: int) -> int:
    """Removes the links of a tournament's fixtures to the league (after the tournament ID was changed)."""
    league_fixtures = select(Fixture.id).where(Fixture.league_id == league_id)
    result = session.execute(
        update(OddsPapiFixture)
        .where(
            OddsPapiFixture.tournament_id == tournament_id, OddsPapiFixture.fixture_id.in_(league_fixtures)
        )
        .values(fixture_id=None)
    )
    return result.rowcount or 0


def reset_empty_histories(session: Session, tournament_id: int) -> int:
    """Marks finished fixtures without any stored price as not final, so their history is fetched again."""
    has_prices = select(OddsHistory.oddspapi_fixture_id).where(
        OddsHistory.oddspapi_fixture_id == OddsPapiFixture.id
    )
    result = session.execute(
        update(OddsPapiFixture)
        .where(
            OddsPapiFixture.tournament_id == tournament_id,
            OddsPapiFixture.history_final.is_(True),
            ~has_prices.exists(),
        )
        .values(history_final=False)
    )
    return result.rowcount or 0


def sync_history(
    session: Session, client: OddsPapiClient, fixtures: list[OddsPapiFixture], bookmakers: list[str]
) -> dict[str, int]:
    """Odds histories via the free /historical-odds endpoint (5 s per fixture)."""
    stats = {"fixtures": 0, "final": 0, "rows": 0, "not_found": 0}
    for fixture in fixtures:
        now = _now()
        final = fixture.start_time + FINAL_AFTER_KICKOFF < now
        try:
            result = client.get(
                "historical-odds", {"fixtureId": fixture.id, "bookmakers": ",".join(bookmakers[:3])}
            )
            payload = result.payload
            if final:
                store_raw(session, result)  # complete history: keep the raw response
        except OddsPapiNotFound:
            # OddsPapi has no history for this fixture (seen for some early-2026 fixtures).
            payload = {"fixtureId": fixture.id, "bookmakers": {}}
            stats["not_found"] += 1
        stats["rows"] += process_history_payload(session, payload, fixture.start_time, now, final)
        stats["fixtures"] += 1
        stats["final"] += int(final)
        session.commit()
        log.info(
            "%s %s - %s: history %s", fixture.start_time.date(), fixture.participant1_name,
            fixture.participant2_name, "final" if final else "snapshot",
        )  # fmt: skip
    return stats


def sync_player_names(
    session: Session, client: OddsPapiClient, tournament_id: int, bookmaker: str = "betano.de"
) -> int:
    """Player names for scorer markets of upcoming fixtures (1 billable request)."""
    result = client.get("odds-by-tournaments", {"tournamentIds": tournament_id, "bookmakers": bookmaker})
    store_raw(session, result)
    count = process_player_names_payload(session, result.payload, _now())
    session.commit()
    return count


# --------------------------------------------------------------------------- mapping to API-Football


@dataclass
class OddsPapiMappingReport:
    aliases_total: int = 0
    aliases_new: int = 0
    linked: int = 0
    unlinked: list[str] = field(default_factory=list)


def map_fixtures(session: Session, league_id: int, tournament_id: int) -> OddsPapiMappingReport:
    """Maps OddsPapi participants to API-Football teams and links fixtures.

    1) Fixtures kicking off at the same time are matched by team-name similarity; unambiguous matches vote
       for participant -> team. 2) With the participant map, fixtures are linked via (home, away, date).
    """
    report = OddsPapiMappingReport()
    team_names = {row.id: row.name for row in session.execute(select(Team.id, Team.name))}
    api_fixtures = session.execute(
        select(Fixture.id, Fixture.kickoff_utc, Fixture.home_team_id, Fixture.away_team_id).where(
            Fixture.league_id == league_id, Fixture.kickoff_utc >= HISTORY_SINCE - LINK_TOLERANCE
        )
    ).all()
    op_fixtures = list(
        session.scalars(select(OddsPapiFixture).where(OddsPapiFixture.tournament_id == tournament_id))
    )

    votes: dict[int, Counter] = defaultdict(Counter)
    for op in op_fixtures:
        scored = sorted(
            (
                (
                    parsers.name_similarity(op.participant1_name, team_names.get(f.home_team_id))
                    + parsers.name_similarity(op.participant2_name, team_names.get(f.away_team_id)),
                    f,
                )
                for f in api_fixtures
                if abs(f.kickoff_utc - op.start_time) <= KICKOFF_TOLERANCE
            ),
            key=lambda x: x[0],
            reverse=True,
        )
        if not scored or scored[0][0] < 1.0:
            continue
        if len(scored) > 1 and scored[0][0] - scored[1][0] < 0.5:
            continue
        best = scored[0][1]
        votes[op.participant1_id][best.home_team_id] += 1
        votes[op.participant2_id][best.away_team_id] += 1

    existing = {
        int(a.alias): a.team_id for a in session.scalars(select(TeamAlias).where(TeamAlias.source == SOURCE))
    }
    new_aliases = []
    for participant, counter in votes.items():
        team_id, count = counter.most_common(1)[0]
        if participant in existing:
            if existing[participant] != team_id:
                log.warning("OddsPapi participant %s mapped to %s, votes suggest %s", participant,
                            existing[participant], team_id)  # fmt: skip
            continue
        if count >= MIN_VOTES and count / sum(counter.values()) >= MIN_SHARE:
            new_aliases.append(
                {"source": SOURCE, "alias": str(participant), "team_id": team_id, "matched_games": count}
            )
            existing[participant] = team_id
    upsert(session, TeamAlias, new_aliases)
    report.aliases_new = len(new_aliases)
    report.aliases_total = len(existing)

    by_teams: dict[tuple[int, int], list] = defaultdict(list)
    for f in api_fixtures:
        by_teams[(f.home_team_id, f.away_team_id)].append(f)
    for op in op_fixtures:
        home, away = existing.get(op.participant1_id), existing.get(op.participant2_id)
        candidates = [
            f for f in by_teams.get((home, away), []) if abs(f.kickoff_utc - op.start_time) <= LINK_TOLERANCE
        ]
        if len(candidates) == 1:
            if op.fixture_id != candidates[0].id:
                op.fixture_id = candidates[0].id
            report.linked += 1
        elif op.start_time >= HISTORY_SINCE and op.status_id != CANCELLED:
            report.unlinked.append(
                f"{op.start_time:%Y-%m-%d} {op.participant1_name} - {op.participant2_name}"
            )
    session.commit()
    return report
