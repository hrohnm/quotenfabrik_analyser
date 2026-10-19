"""Odds snapshots from API-Football (pre-match odds exist only 1-14 days before kickoff, 7 days history).

Only tracked markets (see ``quotenfabrik.markets``) of the configured bookmakers are stored, and only when
an odd changed since its last capture.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from quotenfabrik.ingest import parsers
from quotenfabrik.ingest.db_utils import upsert
from quotenfabrik.markets import BET_ID_TO_GROUP, MARKET_GROUPS
from quotenfabrik.models import BetType, Bookmaker, Fixture, OddsSnapshot
from quotenfabrik.sources.api_football import ApiFootballClient

log = logging.getLogger(__name__)

_LATEST_SQL = text(
    """
    select distinct on (fixture_id, bookmaker_id, bet_id, selection, handicap)
           fixture_id, bookmaker_id, bet_id, selection, handicap, odd
    from core.odds_snapshots
    where fixture_id = any(:ids)
    order by fixture_id, bookmaker_id, bet_id, selection, handicap, captured_at desc
    """
)


def process_odds_payload(
    session: Session, payload: dict[str, Any], captured_at: datetime, bookmakers: set[int] | None
) -> int:
    """Stores changed odds of one /odds response page. Returns the number of rows written."""
    rows = parsers.parse_odds(payload.get("response"), captured_at, bookmakers)
    if not rows:
        return 0
    fixture_ids = {r["fixture_id"] for r in rows}
    known = set(session.scalars(select(Fixture.id).where(Fixture.id.in_(fixture_ids))))
    missing = fixture_ids - known
    if missing:
        log.warning("Odds for %d unknown fixtures skipped (sync fixtures first): %s", len(missing), missing)
    latest = {
        (r.fixture_id, r.bookmaker_id, r.bet_id, r.selection, r.handicap): r.odd
        for r in session.execute(_LATEST_SQL, {"ids": list(known)})
    }
    changed = [
        r
        for r in rows
        if r["fixture_id"] in known
        and latest.get((r["fixture_id"], r["bookmaker_id"], r["bet_id"], r["selection"], r["handicap"]))
        != r["odd"]
    ]
    upsert(session, OddsSnapshot, changed, update=False)
    return len(changed)


def snapshot(session: Session, client: ApiFootballClient, league_id: int, season: int) -> dict[str, int]:
    """Captures the current pre-match odds of all upcoming fixtures of a league season."""
    bookmakers = set(client.settings.odds_bookmakers)
    captured_at = datetime.now(UTC)
    pages = written = 0
    for result in client.get_all_pages("odds", {"league": league_id, "season": season}, use_reserve=True):
        pages += 1
        written += process_odds_payload(session, result.payload, captured_at, bookmakers)
        session.commit()
    log.info("Odds snapshot league %s: %d pages, %d changed odds stored", league_id, pages, written)
    return {"pages": pages, "rows": written}


def sync_reference_data(session: Session, client: ApiFootballClient) -> None:
    """Bookmakers and bet types (2 requests, call rarely)."""
    bookmakers = client.get("odds/bookmakers").payload["response"]
    upsert(session, Bookmaker, [{"id": b["id"], "name": b["name"] or ""} for b in bookmakers])
    bets = client.get("odds/bets").payload["response"]
    upsert(
        session,
        BetType,
        [
            {"id": b["id"], "name": b["name"] or "", "market_group": BET_ID_TO_GROUP.get(b["id"])}
            for b in bets
        ],
    )
    session.commit()


def seed_bet_types(session: Session) -> None:
    """Writes the tracked markets without an API call (keeps market_group in sync with markets.py)."""
    rows = [
        {"id": bet_id, "name": name, "market_group": group}
        for group, bets in MARKET_GROUPS.items()
        for bet_id, name in bets.items()
    ]
    upsert(session, BetType, rows)
