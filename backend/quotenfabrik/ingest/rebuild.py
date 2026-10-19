"""Rebuilds ``core`` tables from ``raw`` without new API requests (e.g. after a parser fix)."""

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from quotenfabrik.config import get_settings
from quotenfabrik.ingest import api_football, football_data, odds, oddspapi
from quotenfabrik.models import ApiResponse, FootballDataFile, OddsPapiFixture, OddsPapiResponse

log = logging.getLogger(__name__)

BATCH = 200


def rebuild_from_raw(session: Session) -> dict[str, int]:
    counts: dict[str, int] = {}
    bookmakers = set(get_settings().odds_bookmakers)
    last_id = 0
    while True:
        responses = session.scalars(
            select(ApiResponse).where(ApiResponse.id > last_id).order_by(ApiResponse.id).limit(BATCH)
        ).all()
        if not responses:
            break
        for r in responses:
            if r.endpoint == "fixtures":
                api_football.process_fixtures_payload(session, r.payload, r.fetched_at)
            elif r.endpoint == "fixtures/statistics" and r.params.get("half") == "true":
                api_football.process_half_stats_payload(
                    session, int(r.params["fixture"]), r.payload, r.fetched_at
                )
            elif r.endpoint == "injuries":
                api_football.process_injuries_payload(session, r.payload)
            elif r.endpoint == "odds":
                odds.process_odds_payload(session, r.payload, r.fetched_at, bookmakers)
            else:
                continue
            counts[r.endpoint] = counts.get(r.endpoint, 0) + 1
        last_id = responses[-1].id
        session.commit()

    # football-data: newest file per league/season
    latest = (
        select(
            FootballDataFile.league_code,
            FootballDataFile.season_code,
            func.max(FootballDataFile.id).label("id"),
        )
        .group_by(FootballDataFile.league_code, FootballDataFile.season_code)
        .subquery()
    )
    for file in session.scalars(select(FootballDataFile).join(latest, FootballDataFile.id == latest.c.id)):
        football_data.process_file(session, file.league_code, file.season_code, file.content)
        counts["football_data"] = counts.get("football_data", 0) + 1
    session.commit()

    _rebuild_oddspapi(session, counts)
    return counts


def _rebuild_oddspapi(session: Session, counts: dict[str, int]) -> None:
    """Replays OddsPapi responses in order: markets and fixtures first, then histories and player names."""
    order = ["markets", "fixtures", "odds-by-tournaments", "historical-odds"]
    for endpoint in order:
        ids = session.scalars(
            select(OddsPapiResponse.id)
            .where(OddsPapiResponse.endpoint == endpoint)
            .order_by(OddsPapiResponse.id)
        ).all()
        for response_id in ids:
            response = session.get(OddsPapiResponse, response_id)
            payload = oddspapi.load_raw(response)
            if endpoint == "markets":
                oddspapi.process_markets_payload(session, payload)
            elif endpoint == "fixtures":
                oddspapi.process_fixtures_payload(session, payload, response.fetched_at)
            elif endpoint == "odds-by-tournaments":
                oddspapi.process_player_names_payload(session, payload, response.fetched_at)
            else:
                fixture = session.get(OddsPapiFixture, payload["fixtureId"])
                if fixture is None:
                    continue
                oddspapi.process_history_payload(
                    session, payload, fixture.start_time, response.fetched_at, final=True
                )
            counts[f"oddspapi/{endpoint}"] = counts.get(f"oddspapi/{endpoint}", 0) + 1
            session.commit()
            session.expunge(response)
