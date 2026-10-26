"""Freezes the picks and the daily combos of a day (``qf picks freeze``, morning job after the forecast).

Forecasts run several times a day; without freezing, picks and combos could change during the day. Freezing
records the chosen forecast run of every fixture of the day (``analytics.frozen_runs``: shown, settled and
evaluated from then on) and stores the daily combos as published (``analytics.day_combos``). Repeated calls
only add fixtures that were not frozen yet (e.g. forecast later); the combos of a day are stored once.
"""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import Engine, exists, select, text
from sqlalchemy.orm import Session

from quotenfabrik import app_config
from quotenfabrik.api.data import CHOSEN_RUNS_SQL
from quotenfabrik.models import DayCombo, FrozenRun

BERLIN = ZoneInfo("Europe/Berlin")


def today() -> date:
    return datetime.now(BERLIN).date()


def freeze_day(engine: Engine, day: date, now: datetime | None = None) -> dict:
    """Freezes the forecast runs of the day's fixtures and, once, the combos (fixtures not yet started)."""
    from quotenfabrik.api.routers.bets import compute_combos

    now = now or datetime.now(UTC)
    where = "and (f.kickoff_utc at time zone 'Europe/Berlin')::date = :day and f.league_id = any(:leagues)"
    with Session(engine) as session:
        runs = session.execute(
            text(f"""with runs as ({CHOSEN_RUNS_SQL.format(where=where)})
                     select runs.fixture_id, runs.model_run_id from runs
                     where runs.kind = 'forecast'
                       and not exists (select 1 from analytics.frozen_runs z
                                       where z.fixture_id = runs.fixture_id)"""),
            {"day": day, "leagues": app_config.shown_league_ids()},
        ).all()
        session.add_all(FrozenRun(fixture_id=r.fixture_id, model_run_id=r.model_run_id) for r in runs)
        session.flush()
        stored = 0
        if not session.scalar(select(exists().where(DayCombo.day == day))):
            session.commit()  # the combos read the frozen runs
            for c in compute_combos(day, not_before=now):
                session.add(DayCombo(day=day, kind=c["kind"], odds=c["odds"], probability=c["probability"],
                                     real_odds=c["real_odds"], legs=c["legs"]))  # fmt: skip
                stored += 1
        session.commit()
    return {"fixtures": len(runs), "combos": stored}
