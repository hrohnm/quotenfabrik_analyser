"""Import steps per league, shared by the CLI (``qf ingest …``, ``qf oddspapi …``) and background jobs.

Every function returns a short German summary; ``log`` receives progress lines (per season etc.).
"""

from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from quotenfabrik import app_config
from quotenfabrik.config import get_settings
from quotenfabrik.ingest import api_football, football_data, oddspapi, team_mapping
from quotenfabrik.sources.api_football import ApiFootballClient, QuotaExhausted
from quotenfabrik.sources.oddspapi import OddsPapiClient

Log = Callable[[str], None]
HALF_STATS_FROM = 2024  # 1 request per match -> only recent seasons
INJURIES_FROM = 2021


def _noop(_: str) -> None:
    pass


def football_data_seasons(session: Session, league_id: int, seasons: Iterable[int], log: Log = _noop) -> str:
    code = app_config.fd_code_for(league_id)
    if not code:
        return "kein football-data-Kürzel – übersprungen"
    total = 0
    with httpx.Client(timeout=60, follow_redirects=True) as http:
        for season in seasons:
            try:
                n = football_data.sync_season(session, code, season, http)
            except httpx.HTTPError as exc:  # missing season file or timeout: continue with the next season
                log(f"{code} {season}: nicht geladen ({type(exc).__name__})")
                continue
            total += n
            log(f"{code} {season}: {n} Spiele")
    return f"{code}: {total} Spiele"


def api_football_seasons(
    session: Session,
    client: ApiFootballClient,
    league_id: int,
    seasons: Iterable[int],
    *,
    details: bool = True,
    half_stats: bool = True,
    injuries: bool = True,
    log: Log = _noop,
) -> str:
    """Fixtures, details, half-time stats (from 2024) and injuries (from 2021). Stops at the quota reserve."""
    if client.quota_remaining is None:
        client.status()
    loaded = 0
    try:
        for season in seasons:
            n = api_football.sync_season(session, client, league_id, season)
            loaded += n
            msg = f"Saison {season}: {n} Spiele"
            if details:
                missing = api_football.fixtures_missing_details(session, league_id, season)
                msg += f", Details {api_football.sync_details(session, client, missing)}"
            if half_stats and season >= HALF_STATS_FROM:
                missing = api_football.fixtures_missing_half_stats(session, league_id, season)
                msg += f", Halbzeit-Stats {api_football.sync_half_stats(session, client, missing)}"
            if injuries and season >= INJURIES_FROM:
                msg += f", Ausfälle {api_football.sync_injuries(session, client, league_id, season)}"
            log(msg)
    except QuotaExhausted as exc:
        log(f"Abgebrochen: {exc}")
        raise
    return f"{loaded} Spiele, {client.requests_made} Requests, verbleibend heute {client.quota_remaining}"


def live_results(
    engine, session: Session, client: ApiFootballClient, league_ids: Iterable[int], log: Log = _noop
) -> str:
    """Results of fixtures whose regular end has passed and confirmed line-ups of fixtures kicking off within
    the next hour (``/fixtures?ids=``, 20 per request, both in the same requests), then settles the
    predictions / picks of the affected leagues and the open bets."""
    from quotenfabrik import bets
    from quotenfabrik.analytics.service import settle_predictions
    from quotenfabrik.ingest.parsers import FINISHED_STATUSES
    from quotenfabrik.models import Fixture, FixtureLineupPlayer

    league_ids = list(league_ids)
    due = api_football.fixtures_due(session, league_ids)
    lineup_due = [f for f in api_football.fixtures_lineup_due(session, league_ids) if f not in due]
    if not due and not lineup_due:
        return "keine fälligen Spiele"
    api_football.sync_details(session, client, due + lineup_due)
    lineups = 0
    if lineup_due:
        lineups = len(set(session.scalars(
            select(FixtureLineupPlayer.fixture_id).where(FixtureLineupPlayer.fixture_id.in_(lineup_due))
        )))  # fmt: skip
    if not due:
        return f"Aufstellungen: {lineups} von {len(lineup_due)} bestätigt, {client.requests_made} Requests"
    rows = session.query(Fixture.id, Fixture.league_id, Fixture.status).filter(Fixture.id.in_(due)).all()
    finished = [r for r in rows if r.status in FINISHED_STATUSES]
    settled = sum(settle_predictions(engine, lg) for lg in sorted({r.league_id for r in finished}))
    bets_settled = bets.settle(engine) if finished else 0
    still_open = [f"{r.id} ({r.status})" for r in rows if r.status not in FINISHED_STATUSES]
    if still_open:
        log(f"noch ohne Endergebnis: {', '.join(still_open)}")
    lineup_msg = f", Aufstellungen {lineups} von {len(lineup_due)}" if lineup_due else ""
    return (f"{len(due)} fällig, {len(finished)} beendet, {settled} Prognosen und {bets_settled} Wetten "
            f"abgerechnet{lineup_msg}, {client.requests_made} Requests")  # fmt: skip


CUP_DETAIL_SEASONS = (
    2  # cups: match details (line-ups, goals, player stats) for the current and previous season
)


def results_seasons(
    session: Session, client: ApiFootballClient, league_id: int, seasons: Iterable[int], log: Log = _noop
) -> str:
    """Strength leagues: results only (1 request per season). Cups: in the recent seasons also match details
    (20 fixtures per request) for the goalscorer model and settling scorer predictions."""
    seasons = list(seasons)
    if not app_config.is_cup(league_id):
        return api_football_seasons(session, client, league_id, seasons, details=False, half_stats=False,
                                    injuries=False, log=log)  # fmt: skip
    now = datetime.now(UTC)
    first_detailed = (now.year if now.month >= 7 else now.year - 1) - CUP_DETAIL_SEASONS + 1
    out = []
    for detailed, part in ((False, [s for s in seasons if s < first_detailed]),
                           (True, [s for s in seasons if s >= first_detailed])):  # fmt: skip
        if part:
            out.append(api_football_seasons(session, client, league_id, part, details=detailed,
                                            half_stats=False, injuries=False, log=log))  # fmt: skip
    return "; ".join(out)


def map_teams(session: Session, league_id: int, log: Log = _noop) -> str:
    code = app_config.fd_code_for(league_id)
    if not code:
        return "kein football-data-Kürzel – übersprungen"
    r = team_mapping.map_and_link(session, league_id, code)
    if r.unmapped_aliases:
        log(f"Nicht gemappt: {', '.join(r.unmapped_aliases)}")
    return (
        f"{r.aliases_total} Aliase ({r.aliases_new} neu), {r.rows_linked} Spiele verknüpft, "
        f"{r.rows_unlinked} offen"
    )


def oddspapi_fixtures(
    session: Session,
    client: OddsPapiClient,
    league_id: int,
    start: datetime | None = None,
    end: datetime | None = None,
    log: Log = _noop,
) -> str:
    """Schedule from OddsPapi (1 billable request) and mapping to API-Football fixtures."""
    tournament = app_config.oddspapi_tournament_for(league_id)
    if not tournament:
        return "kein OddsPapi-Turnier – übersprungen"
    start = start or datetime(2026, 1, 1, tzinfo=UTC)
    end = end or datetime.now(UTC) + timedelta(days=60)
    count = oddspapi.sync_fixtures(session, client, tournament, start, end)
    r = oddspapi.map_fixtures(session, league_id, tournament)
    for line in r.unlinked[:20]:
        log(f"nicht verknüpft: {line}")
    return f"Turnier {tournament}: {count} Spiele, {r.aliases_total} Teams gemappt, {r.linked} verknüpft"


def _minutes(fixtures: int) -> str:
    m = fixtures * 5 // 60 + 1  # 5 s per fixture
    return f"{m} Minute" if m == 1 else f"{m} Minuten"


def oddspapi_history(
    session: Session,
    client: OddsPapiClient,
    league_id: int,
    limit: int | None = None,
    log: Log = _noop,
    retry_empty: bool = False,
    since: datetime | None = None,
    batch: int = 20,
) -> str:
    """Betano/Pinnacle price histories of all open fixtures (free, 5 s per fixture).

    ``retry_empty`` also fetches finished fixtures again that have no stored price yet; ``since`` overrides
    the setting ``oddspapi.history_days`` (backfill: everything from January 2026). Progress is logged per
    batch.
    """
    tournament = app_config.oddspapi_tournament_for(league_id)
    if not tournament:
        return "kein OddsPapi-Turnier – übersprungen"
    if retry_empty:
        n = oddspapi.reset_empty_histories(session, tournament)
        session.commit()
        if n:
            log(f"{n} Spiele ohne gespeicherte Quoten werden erneut abgefragt")
    if not oddspapi.tracked_market_ids(session):
        log("Marktkatalog fehlt, wird geladen (1 Request)")
        oddspapi.sync_markets(session, client)
    since = since or datetime.now(UTC) - timedelta(days=app_config.get("oddspapi.history_days"))
    fixtures = oddspapi.fixtures_needing_history(session, tournament, limit=limit, since=since)
    log(f"{len(fixtures)} Spiele, ca. {_minutes(len(fixtures))}")
    total = {"fixtures": 0, "final": 0, "rows": 0, "not_found": 0}
    books = get_settings().oddspapi_bookmakers
    for i in range(0, len(fixtures), batch):
        stats = oddspapi.sync_history(session, client, fixtures[i : i + batch], books)
        total = {k: total[k] + stats[k] for k in total}
        left = len(fixtures) - total["fixtures"]
        if left:
            log(f"{total['fixtures']}/{len(fixtures)} Spiele, noch ca. {_minutes(left)}")
    return (
        f"{total['fixtures']} Verläufe ({total['final']} abgeschlossen, {total['not_found']} ohne Daten), "
        f"{total['rows']} Preisänderungen"
    )
