"""football-data.co.uk ingest: historical results, match stats and 1X2 / O/U 2.5 odds."""

import hashlib
import logging

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from quotenfabrik.ingest.db_utils import upsert
from quotenfabrik.models import FootballDataFile, HistoricalMatch
from quotenfabrik.sources import football_data

log = logging.getLogger(__name__)


def store_file(session: Session, league_code: str, season: str, content: bytes) -> None:
    sha = hashlib.sha256(content).hexdigest()
    exists = session.scalar(
        select(FootballDataFile.id).where(
            FootballDataFile.league_code == league_code,
            FootballDataFile.season_code == season,
            FootballDataFile.sha256 == sha,
        )
    )
    if not exists:
        session.add(
            FootballDataFile(league_code=league_code, season_code=season, sha256=sha, content=content)
        )


def process_file(session: Session, league_code: str, season: str, content: bytes) -> int:
    rows = football_data.parse(content, league_code, season)
    upsert(
        session,
        HistoricalMatch,
        [{**r.values, "raw_row": r.raw} for r in rows],
        exclude_from_update=("fixture_id",),
        conflict_columns=("league_code", "season_code", "match_date", "home_alias", "away_alias"),
    )
    return len(rows)


def sync_season(session: Session, league_code: str, season_start_year: int, client: httpx.Client) -> int:
    season = football_data.season_code(season_start_year)
    try:
        content = football_data.download(season_start_year, league_code, client)
    except httpx.HTTPStatusError as exc:
        log.warning("football-data %s %s not available: %s", league_code, season, exc.response.status_code)
        return 0
    store_file(session, league_code, season, content)
    count = process_file(session, league_code, season, content)
    session.commit()
    log.info("football-data %s %s: %d matches", league_code, season, count)
    return count
