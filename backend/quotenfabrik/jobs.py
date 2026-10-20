"""Background jobs started from the configuration page.

A job is a list of named steps. ``spawn`` starts ``qf jobs run <id>`` as a detached process (survives the API
request); ``run`` executes the steps in order and records status and log lines per step in ``app.jobs`` so the
page can show the progress. Only one job runs at a time.

Kinds:
- ``add_league``: import (football-data, API-Football, team mapping, OddsPapi), backup of the fetched data,
  models + picks, reports, final backup
- ``models``: backtest + forecast (incl. picks) for all active leagues (after changing model parameters)
- ``picks``: rebuild picks for all active leagues (after changing pick thresholds)
- ``add_ratings``: results-only import of several leagues for the strength scale (1 request per season and
  league), then a backup
- ``backup``: database backup
"""

import os
import subprocess
import sys
import threading
import traceback
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from quotenfabrik import app_config
from quotenfabrik.db import get_engine
from quotenfabrik.models import Job

ACTIVE = ("queued", "running")
OPTIONAL_STEPS = {"reports"}  # a failure is shown but does not stop the job (the final backup still runs)
LOG_DIR = Path("/tmp")
MAX_LOG_LINES = 40


class JobConflict(RuntimeError):
    pass


class StepSkipped(Exception):  # noqa: N818 - control flow, not an error
    """Raised by a step that does not apply (e.g. no OddsPapi tournament); the job continues."""


def current_season(now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    return now.year if now.month >= 7 else now.year - 1


# --------------------------------------------------------------------------- definitions

STEP_LABELS = {
    "football_data": "football-data.co.uk (Historie, kostenlos)",
    "api_football": "API-Football (Spiele, Details, Halbzeit-Stats, Ausfälle)",
    "map_teams": "Teams zuordnen",
    "results": "API-Football: Ergebnisse (1 Request pro Saison und Liga)",
    "oddspapi_fixtures": "OddsPapi-Spielplan (1 Request)",
    "oddspapi_history": "Betano/Pinnacle-Quotenverläufe (kostenlos)",
    "backup_data": "Backup der abgerufenen Daten",
    "backtest": "Rückwirkende Prognosen + Tipps",
    "forecast": "Prognosen kommender Spiele + Tipps",
    "reports": "Berichte (Evaluation, Tipps)",
    "picks": "Tipps neu berechnen",
    "backup": "Backup",
}


def steps_for(kind: str, params: dict) -> list[str]:
    if kind == "add_league":
        return ["football_data", "api_football", "map_teams", "oddspapi_fixtures", "oddspapi_history",
                "backup_data", "backtest", "forecast", "reports", "backup"]  # fmt: skip
    if kind == "odds":
        return ["oddspapi_fixtures", "oddspapi_history", "backup_data"]
    if kind == "add_ratings":
        return ["results", "backup_data", "backtest", "forecast"]
    if kind == "models":
        return ["backtest", "forecast"]
    if kind == "picks":
        return ["picks"]
    if kind == "backup":
        return ["backup"]
    raise ValueError(f"unknown job kind {kind!r}")


# --------------------------------------------------------------------------- create / spawn


def ensure_idle(session: Session) -> None:
    refresh_stale(session)
    if session.scalar(select(Job.id).where(Job.status.in_(ACTIVE)).limit(1)):
        raise JobConflict("Es läuft bereits ein Job – bitte warten, bis er fertig ist.")


def create(kind: str, params: dict | None = None) -> int:
    params = params or {}
    with Session(get_engine()) as session, session.begin():
        ensure_idle(session)
        steps = [{"name": s, "label": STEP_LABELS[s], "status": "pending", "message": None, "log": []}
                 for s in steps_for(kind, params)]  # fmt: skip
        job = Job(kind=kind, params=params, status="queued", steps=steps)
        session.add(job)
        session.flush()
        return job.id


def spawn(job_id: int) -> None:
    """Runs the job in its own process group so it outlives the API request (and API restarts)."""
    backend = Path(__file__).resolve().parents[1]
    log = open(LOG_DIR / f"qf-job-{job_id}.log", "ab")  # noqa: SIM115 - handed to the child process
    proc = subprocess.Popen(
        [sys.executable, "-m", "quotenfabrik.cli", "jobs", "run", str(job_id)],
        cwd=backend, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True,
    )  # fmt: skip
    threading.Thread(target=proc.wait, daemon=True).start()  # reap the child when it ends (no zombie)
    with Session(get_engine()) as session, session.begin():
        job = session.get(Job, job_id)
        job.params = {**job.params, "pid": proc.pid}


def _alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:  # a finished child that was not reaped yet ("zombie") is not running anymore
        return Path(f"/proc/{pid}/stat").read_text().split(")")[-1].split()[0] != "Z"
    except OSError:
        return True


def refresh_stale(session: Session) -> None:
    """Marks jobs whose process is gone (container restart, crash) or that never started as failed."""
    now = datetime.now(UTC)
    for job in session.scalars(select(Job).where(Job.status.in_(ACTIVE))):
        pid = job.params.get("pid")
        never_started = job.status == "queued" and not pid and now - job.created_at > timedelta(minutes=5)
        if never_started or (pid and not _alive(pid)):
            job.status, job.error, job.finished_at = "failed", "Prozess beendet (Neustart?)", now


# --------------------------------------------------------------------------- run


class _Recorder:
    """Writes step status and log lines to the job row (own short transactions)."""

    def __init__(self, job_id: int) -> None:
        self.job_id = job_id
        self.engine = get_engine()

    def _update(self, **values) -> None:
        with Session(self.engine) as session, session.begin():
            session.execute(update(Job).where(Job.id == self.job_id).values(**values))

    def steps(self) -> list[dict]:
        with Session(self.engine) as session:
            return list(session.get(Job, self.job_id).steps)

    def step(self, name: str, **changes) -> None:
        steps = self.steps()
        for s in steps:
            if s["name"] == name:
                if "line" in changes:
                    s["log"] = ([*s["log"], changes.pop("line")])[-MAX_LOG_LINES:]
                s.update(changes)
        self._update(steps=steps)

    def job(self, **values) -> None:
        self._update(**values)


def run(job_id: int) -> str:
    """Executes all steps of a job; a failing step stops the job (status 'failed')."""
    rec = _Recorder(job_id)
    with Session(get_engine()) as session:
        job = session.get(Job, job_id)
        params = dict(job.params)
    rec.job(status="running", started_at=datetime.now(UTC), params={**params, "pid": os.getpid()})
    handlers = _handlers()
    for step in rec.steps():
        name = step["name"]
        rec.step(name, status="running")
        try:
            message = handlers[name](params, lambda line, n=name: rec.step(n, line=line))
            rec.step(name, status="done", message=message)
        except StepSkipped as exc:
            rec.step(name, status="skipped", message=str(exc))
        except Exception as exc:  # noqa: BLE001 - reported on the page
            rec.step(name, status="failed", message=f"{type(exc).__name__}: {exc}")
            if name in OPTIONAL_STEPS:
                continue
            rec.job(status="failed", error=traceback.format_exc()[-4000:], finished_at=datetime.now(UTC))
            return "failed"
    rec.job(status="done", finished_at=datetime.now(UTC))
    app_config.invalidate()
    return "done"


# --------------------------------------------------------------------------- step handlers

Handler = Callable[[dict, Callable[[str], None]], str]


def _target_leagues(params: dict) -> list[int]:
    """Leagues of a job: the given league, the cups of an add_ratings job, else all leagues and cups."""
    if params.get("league_id"):
        return [params["league_id"]]
    if params.get("league_ids"):  # add_ratings: only the cups get forecasts
        cups = [i for i in params["league_ids"] if app_config.is_cup(i)]
        if not cups:
            raise StepSkipped("keine Europapokale ausgewählt – Stärke-Ligen bekommen keine Prognosen")
        return cups
    return app_config.shown_league_ids()


CUP_BACKTEST_SEASONS = (
    2  # cups: retroactive forecasts for the current and previous season (big European pool)
)


def _seasons(params: dict) -> list[int]:
    return list(range(params["first_season"], params.get("last_season", current_season()) + 1))


def _handlers() -> dict[str, Handler]:
    from quotenfabrik import backup, pipeline
    from quotenfabrik.ingest.db_utils import raw_response_saver
    from quotenfabrik.sources.api_football import ApiFootballClient
    from quotenfabrik.sources.oddspapi import OddsPapiClient

    engine = get_engine()

    def _needs_fd(params):
        if not app_config.fd_code_for(params["league_id"]):
            raise StepSkipped("kein football-data-Kürzel hinterlegt")

    def football_data(params, log):
        _needs_fd(params)
        with Session(engine) as session:
            return pipeline.football_data_seasons(session, params["league_id"], _seasons(params), log)

    def api_football(params, log):
        with Session(engine) as session, ApiFootballClient(on_response=raw_response_saver(engine)) as client:
            return pipeline.api_football_seasons(
                session, client, params["league_id"], _seasons(params), log=log
            )

    def results(params, log):
        with Session(engine) as session, ApiFootballClient(on_response=raw_response_saver(engine)) as client:
            for league_id in params["league_ids"]:
                name = app_config.league(league_id).name
                pipeline.api_football_seasons(
                    session, client, league_id, _seasons(params), details=False, half_stats=False,
                    injuries=False, log=lambda m, name=name: log(f"{name}: {m}"),
                )  # fmt: skip
            n, used, left = len(params["league_ids"]), client.requests_made, client.quota_remaining
        return f"{n} Ligen, {used} Requests, verbleibend heute {left}"

    def map_teams(params, log):
        _needs_fd(params)
        with Session(engine) as session:
            return pipeline.map_teams(session, params["league_id"], log)

    def _oddspapi(fn, params, log):
        if not app_config.oddspapi_tournament_for(params["league_id"]):
            raise StepSkipped("kein OddsPapi-Turnier hinterlegt")
        try:
            client = OddsPapiClient()
        except Exception as exc:  # missing key
            raise StepSkipped(f"OddsPapi nicht verfügbar: {exc}") from None
        with Session(engine) as session, client:
            return fn(session, client, params["league_id"], log=log)

    def oddspapi_fixtures(params, log):
        return _oddspapi(pipeline.oddspapi_fixtures, params, log)

    def oddspapi_history(params, log):
        if params.get("retry_empty"):
            return _oddspapi(partial(pipeline.oddspapi_history, retry_empty=True), params, log)
        return _oddspapi(pipeline.oddspapi_history, params, log)

    def backup_step(reason):
        def step(params, log):
            path = backup.create_backup(reason)
            return f"{path.name} ({path.stat().st_size / 1e6:.1f} MB)"

        return step

    def backtest(params, log):
        from quotenfabrik.analytics.picks import build_picks
        from quotenfabrik.analytics.service import run_backtest

        out = []
        for league_id in _target_leagues(params):
            lg = app_config.league(league_id)
            first = current_season() - CUP_BACKTEST_SEASONS + 1 if lg.kind == "cup" else lg.first_season + 1
            seasons = list(range(min(first, current_season()), current_season() + 1))
            log(f"Liga {league_id}: Saisons {seasons[0]}–{seasons[-1]}")
            result = run_backtest(engine, league_id, seasons)
            picks = build_picks(engine, league_id, result["model_run_id"])["picks"]
            out.append(f"Liga {league_id}: {result.get('matches', 0)} Spiele, {picks} Tipps")
        return "; ".join(out)

    def forecast(params, log):
        from quotenfabrik.analytics.picks import build_picks
        from quotenfabrik.analytics.service import run_forecast

        out = []
        for league_id in _target_leagues(params):
            result = run_forecast(engine, league_id)
            if "model_run_id" in result:
                build_picks(engine, league_id, result["model_run_id"])
            out.append(f"Liga {league_id}: {result.get('fixtures', 0)} kommende Spiele")
        return "; ".join(out)

    def reports(params, log):
        from quotenfabrik.analytics.picks_report import write_report
        from quotenfabrik.analytics.service import run_evaluation
        from quotenfabrik.reports import EVALUATION_REPORT, PICKS_REPORT, report_path

        league_id = params["league_id"]
        seasons = list(range(max(app_config.league(league_id).first_season + 2, current_season() - 4),
                             current_season() + 1))  # fmt: skip
        if not seasons:
            raise StepSkipped("zu wenig Saisons für eine Evaluation (mindestens 3 nötig)")
        run_evaluation(engine, league_id, seasons, report_path=report_path(EVALUATION_REPORT, league_id))
        write_report(engine, league_id, 2021, report_path(PICKS_REPORT, league_id))
        return f"Evaluation {seasons[0]}–{seasons[-1]} und Tipp-Bericht geschrieben"

    def picks(params, log):
        from quotenfabrik.analytics.picks import build_picks

        return "; ".join(
            f"Liga {lid}: {build_picks(engine, lid)['picks']} Tipps" for lid in _target_leagues(params)
        )

    return {
        "football_data": football_data,
        "api_football": api_football,
        "map_teams": map_teams,
        "results": results,
        "oddspapi_fixtures": oddspapi_fixtures,
        "oddspapi_history": oddspapi_history,
        "backup_data": backup_step("nach_import"),
        "backtest": backtest,
        "forecast": forecast,
        "reports": reports,
        "picks": picks,
        "backup": lambda params, log: backup_step("komplett" if params.get("league_id") else "manuell")(
            params, log
        ),
    }


# --------------------------------------------------------------------------- planning


def estimate_requests(seasons: list[int], matches_per_season: int = 380) -> dict:
    """Rough API-Football cost of importing a league (upper bound: 20 teams / 380 matches per season)."""
    per = {
        "fixtures": len(seasons),
        "details": len(seasons) * -(-matches_per_season // 20),
        "half_stats": sum(matches_per_season for s in seasons if s >= 2024),
        "injuries": sum(1 for s in seasons if s >= 2021),
    }
    return {"total": sum(per.values()), **per}
