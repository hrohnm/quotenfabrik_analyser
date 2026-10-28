"""Status of the Betano/Pinnacle odds archive (OddsPapi price histories) per league for the settings page.

Per league from January 2026 (OddsPapi keeps histories from then on): finished fixtures, linked to
OddsPapi, with a Betano / Pinnacle history, still to be loaded (backfill), without data at OddsPapi; upcoming
fixtures (14 days) with prices, and fixtures in the next 48 hours without any Betano price (missed odds cannot
be loaded later). Plus an estimate for the backfill (5 s and about 2.3 MB of database per fixture) and
the number of fixtures with prices added since the Tippschein model was last trained.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine, text

from quotenfabrik import app_config
from quotenfabrik.ingest.oddspapi import COOLDOWN_S, HISTORY_SINCE, PRE_MATCH_WINDOW

MB_PER_FIXTURE = 2.3  # raw response (~0.6 MB gzip) + core.odds_history rows (~1.7 MB), measured 10/2026
STALE_AFTER = timedelta(hours=6)  # cron loads histories every 3 hours
SOON = timedelta(hours=48)
FINISHED = ("FT", "AET", "PEN", "AWD", "WO")

COUNTS = ("finished", "linked", "with_betano", "with_pinnacle", "to_load", "no_data", "upcoming",
          "upcoming_linked", "upcoming_betano", "soon_missing", "new_since_fit")  # fmt: skip

_SQL = """
    with fx as (
        select f.id, f.league_id, f.kickoff_utc, f.status = any(:fin) as finished, o.id as oid,
               o.history_final, o.history_synced_at, o.status_id,
               exists (select 1 from core.odds_history h where h.oddspapi_fixture_id = o.id
                       and h.bookmaker = 'betano.de') as betano,
               exists (select 1 from core.odds_history h where h.oddspapi_fixture_id = o.id
                       and h.bookmaker = 'pinnacle') as pinnacle
        from core.fixtures f
        left join core.oddspapi_fixtures o on o.fixture_id = f.id
        where f.league_id = any(:leagues) and f.kickoff_utc >= :since and f.kickoff_utc <= :horizon
    )
    select league_id,
           count(*) filter (where finished) as finished,
           count(*) filter (where finished and oid is not null) as linked,
           count(*) filter (where finished and betano) as with_betano,
           count(*) filter (where finished and pinnacle) as with_pinnacle,
           count(*) filter (where finished and oid is not null and not history_final) as to_load,
           count(*) filter (where finished and history_final and not betano) as no_data,
           count(*) filter (where kickoff_utc > :now) as upcoming,
           count(*) filter (where kickoff_utc > :now and oid is not null) as upcoming_linked,
           count(*) filter (where kickoff_utc > :now and betano) as upcoming_betano,
           count(*) filter (where kickoff_utc > :now and kickoff_utc <= :soon and not betano) as soon_missing,
           max(history_synced_at) as last_sync,
           count(*) filter (where betano and history_synced_at > :fitted) as new_since_fit
    from fx group by league_id
"""


def status(engine: Engine, now: datetime | None = None) -> dict:
    now = now or datetime.now(UTC)
    leagues = [lg for lg in app_config.leagues() if lg.kind == "full"]
    with engine.connect() as conn:
        fitted = conn.execute(text("select min(fitted_at) from analytics.decision_models")).scalar()
        rows = conn.execute(text(_SQL), {
            "fin": list(FINISHED), "leagues": [lg.id for lg in leagues], "since": HISTORY_SINCE,
            "horizon": now + PRE_MATCH_WINDOW, "now": now, "soon": now + SOON,
            "fitted": fitted or datetime(2100, 1, 1, tzinfo=UTC),
        }).mappings().all()  # fmt: skip
    by_league = {r["league_id"]: dict(r) for r in rows}
    out, todo = [], 0
    for lg in leagues:
        r = by_league.get(lg.id, {})
        tournament = app_config.oddspapi_tournament_for(lg.id)
        warnings = []
        if not tournament:
            warnings.append("kein OddsPapi-Turnier hinterlegt – keine Betano-Quoten")
        else:
            if r.get("soon_missing"):
                warnings.append(f"{r['soon_missing']} Spiele in den nächsten 48 h ohne Betano-Quote")
            last = r.get("last_sync")
            if r.get("upcoming_linked") and (last is None or now - last > STALE_AFTER):
                warnings.append("Quotenverläufe seit über 6 Stunden nicht aktualisiert")
            if r.get("upcoming") and not r.get("upcoming_linked"):
                warnings.append("kommende Spiele nicht mit OddsPapi verknüpft (Spielplan neu laden)")
        todo += r.get("to_load") or 0
        out.append({
            "id": lg.id, "name": lg.name, "country": lg.country, "tournament": tournament,
            **{k: int(r.get(k) or 0) for k in COUNTS},
            "last_sync": r["last_sync"].isoformat() if r.get("last_sync") else None,
            "warnings": warnings,
        })  # fmt: skip
    seconds = todo * COOLDOWN_S["historical-odds"]
    return {
        "since": HISTORY_SINCE.date().isoformat(),
        "history_days": app_config.get("oddspapi.history_days"),
        "leagues": out,
        "backfill": {
            "fixtures": todo,
            "minutes": int(seconds // 60) + (1 if todo else 0),
            "megabytes": round(todo * MB_PER_FIXTURE),
        },  # fmt: skip
        "model_fitted_at": fitted.isoformat() if fitted else None,
        "new_since_fit": sum(lg["new_since_fit"] for lg in out),
    }
