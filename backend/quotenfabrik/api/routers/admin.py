"""Configuration page: settings, leagues (search, add, activate), background jobs, backups, API status.

Requests that cost API quota are only made on explicit user actions (league search: 1 API-Football request;
adding a league: the import job). Everything else (status, tournaments, football-data codes) is free.
"""

import json
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from quotenfabrik import app_config, backup, jobs
from quotenfabrik.api.data import df, records
from quotenfabrik.api.labels import league_logo
from quotenfabrik.config import get_settings
from quotenfabrik.db import get_engine
from quotenfabrik.models import AppLeague, Job, OddsPapiResponse

router = APIRouter(prefix="/api/admin", tags=["admin"])

TOURNAMENTS_FILE = Path(__file__).resolve().parents[2] / "data" / "oddspapi_tournaments.json"
PRESETS_FILE = Path(__file__).resolve().parents[2] / "data" / "european_leagues.json"

# football-data.co.uk codes (main leagues with results and closing odds since 2000s)
FOOTBALL_DATA_CODES = {
    "E0": "England – Premier League", "E1": "England – Championship", "E2": "England – League One",
    "E3": "England – League Two", "EC": "England – National League", "SC0": "Schottland – Premiership",
    "SC1": "Schottland – Championship", "D1": "Deutschland – Bundesliga", "D2": "Deutschland – 2. Bundesliga",
    "I1": "Italien – Serie A", "I2": "Italien – Serie B", "SP1": "Spanien – La Liga", "SP2": "Spanien – Segunda",
    "F1": "Frankreich – Ligue 1", "F2": "Frankreich – Ligue 2", "N1": "Niederlande – Eredivisie",
    "B1": "Belgien – Pro League", "P1": "Portugal – Primeira Liga", "T1": "Türkei – Süper Lig",
    "G1": "Griechenland – Super League",
}  # fmt: skip

_status_cache: dict[str, tuple[float, Any]] = {}
STATUS_TTL_S = 60


# --------------------------------------------------------------------------- status


def _cached(name: str, loader):
    hit = _status_cache.get(name)
    if hit and time.monotonic() - hit[0] < STATUS_TTL_S:
        return hit[1]
    try:
        value = loader()
    except Exception as exc:  # noqa: BLE001 - shown on the page
        value = {"error": f"{type(exc).__name__}: {exc}"}
    _status_cache[name] = (time.monotonic(), value)
    return value


def _api_football_status() -> dict:
    from quotenfabrik.sources.api_football import ApiFootballClient

    with ApiFootballClient() as client:  # /status costs no quota
        r = client.status()
    req = r.get("requests") or {}
    sub = r.get("subscription") or {}
    return {
        "plan": sub.get("plan"),
        "end": sub.get("end"),
        "used": req.get("current"),
        "limit": req.get("limit_day"),
    }


def _oddspapi_status() -> dict:
    from quotenfabrik.sources.oddspapi import OddsPapiClient

    with OddsPapiClient() as client:  # /account is free
        a = client.account()
    return {"plan": a.get("plan"), "used": a.get("request_count"), "limit": a.get("request_limit")}


@router.get("/status")
def status() -> dict:
    s = get_settings()
    with Session(get_engine()) as session, session.begin():
        jobs.refresh_stale(session)
    return {
        "keys": {"api_football": bool(s.api_football_key), "oddspapi": bool(s.oddspapi_api_key)},
        "api_football": _cached("api_football", _api_football_status) if s.api_football_key else None,
        "oddspapi": _cached("oddspapi", _oddspapi_status) if s.oddspapi_api_key else None,
        "backups": backup.list_backups()[:5],
        "settings_reserve": {"api": app_config.get("api.quota_reserve"),
                             "oddspapi": app_config.get("oddspapi.request_reserve")},
    }  # fmt: skip


# --------------------------------------------------------------------------- settings


@router.get("/settings")
def get_settings_page() -> dict:
    values = app_config.all_values()
    return {
        "settings": [
            {"key": d.key, "group": d.group, "label": d.label, "help": d.help, "type": d.type,
             "default": d.default, "min": d.min, "max": d.max, "choices": list(d.choices), "percent": d.percent,
             "value": values[d.key]}
            for d in app_config.SETTINGS
        ]
    }  # fmt: skip


@router.put("/settings")
def put_settings(values: dict[str, Any]) -> dict:
    try:
        app_config.save(values)
    except app_config.SettingsError as exc:
        raise HTTPException(422, str(exc)) from None
    return get_settings_page()


# --------------------------------------------------------------------------- leagues


@router.get("/leagues")
def leagues() -> list[dict]:
    counts = df(
        """select league_id, count(*) as fixtures, min(season) as first_season, max(season) as last_season,
                  count(*) filter (where status in ('FT','AET','PEN','AWD','WO')) as finished
           from core.fixtures group by league_id"""
    ).set_index("league_id")
    out = []
    for lg in app_config.all_leagues():
        c = counts.loc[lg.id] if lg.id in counts.index else None
        out.append({
            "id": lg.id, "name": lg.name, "country": lg.country, "logo": league_logo(lg.id), "fd_code": lg.fd_code,
            "oddspapi_tournament": lg.oddspapi_tournament, "first_season": lg.first_season, "active": lg.active,
            "kind": lg.kind,
            "fixtures": int(c["fixtures"]) if c is not None else 0,
            "finished": int(c["finished"]) if c is not None else 0,
            "seasons": [int(c["first_season"]), int(c["last_season"])] if c is not None else None,
        })  # fmt: skip
    return out


@router.get("/leagues/search")
def search_leagues(q: str) -> list[dict]:
    """API-Football league search – costs 1 request (response stored raw like every API response)."""
    from quotenfabrik.ingest.db_utils import raw_response_saver
    from quotenfabrik.sources.api_football import ApiFootballClient

    if len(q.strip()) < 3:
        raise HTTPException(422, "Mindestens 3 Zeichen")
    if not get_settings().api_football_key:
        raise HTTPException(
            409, "API_FOOTBALL_KEY fehlt (als Umgebungsvariable / Codespaces-Secret hinterlegen)"
        )
    with ApiFootballClient(on_response=raw_response_saver(get_engine())) as client:
        payload = client.get("leagues", {"search": q.strip()}).payload
    configured = {lg.id for lg in app_config.all_leagues()}
    out = []
    for item in payload.get("response", []):
        lg, country, seasons = item["league"], item.get("country") or {}, item.get("seasons") or []
        years = sorted(s["year"] for s in seasons)
        current = next((s["year"] for s in seasons if s.get("current")), years[-1] if years else None)
        events_from = min((s["year"] for s in seasons if (s.get("coverage") or {}).get("fixtures", {}).get("events")),
                          default=None)  # fmt: skip
        out.append({
            "id": lg["id"], "name": lg["name"], "type": lg.get("type"), "logo": lg.get("logo"),
            "country": country.get("name"), "flag": country.get("flag"), "seasons": years, "current": current,
            "details_from": events_from, "configured": lg["id"] in configured,
            "suggested_fd_code": _suggest_fd_code(country.get("name"), lg["name"]),
        })  # fmt: skip
    return sorted(out, key=lambda r: (r["type"] != "League", r["country"] or "", r["name"]))


def _suggest_fd_code(country: str | None, name: str) -> str | None:
    label = f"{country} {name}".lower()
    hints = {
        ("england", "premier league"): "E0", ("england", "championship"): "E1", ("england", "league one"): "E2",
        ("england", "league two"): "E3", ("scotland", "premiership"): "SC0", ("germany", "2. bundesliga"): "D2",
        ("germany", "bundesliga"): "D1", ("italy", "serie a"): "I1", ("italy", "serie b"): "I2",
        ("spain", "la liga"): "SP1", ("spain", "segunda"): "SP2", ("france", "ligue 1"): "F1",
        ("france", "ligue 2"): "F2", ("netherlands", "eredivisie"): "N1", ("belgium", "pro league"): "B1",
        ("portugal", "primeira"): "P1", ("turkey", "süper lig"): "T1", ("greece", "super league"): "G1",
    }  # fmt: skip
    for (c, n), code in hints.items():
        if c in label and n in label:
            return code
    return None


@router.get("/football-data/codes")
def football_data_codes() -> list[dict]:
    return [{"code": k, "label": v} for k, v in FOOTBALL_DATA_CODES.items()]


@router.get("/oddspapi/tournaments")
def oddspapi_tournaments(q: str = "") -> list[dict]:
    """Football tournaments of OddsPapi: latest stored /tournaments response, else the bundled snapshot (free)."""
    with Session(get_engine()) as session:
        raw = session.scalars(
            select(OddsPapiResponse).where(OddsPapiResponse.endpoint == "tournaments")
            .order_by(OddsPapiResponse.fetched_at.desc()).limit(1)
        ).first()  # fmt: skip
    if raw is not None:
        from quotenfabrik.ingest.oddspapi import load_raw

        rows = [{"id": t["tournamentId"], "name": t["tournamentName"], "category": t["categoryName"]}
                for t in load_raw(raw)]  # fmt: skip
    else:
        rows = json.loads(TOURNAMENTS_FILE.read_text(encoding="utf-8"))["tournaments"]
    words = q.lower().split()
    hits = [t for t in rows if all(w in f"{t['category']} {t['name']}".lower() for w in words)]
    return hits[:50]


class NewLeague(BaseModel):
    id: int
    name: str
    country: str | None = None
    fd_code: str | None = None
    oddspapi_tournament: int | None = None
    first_season: int = Field(ge=2010, le=2100)
    last_season: int | None = None


@router.get("/leagues/estimate")
def estimate(first_season: int, last_season: int | None = None) -> dict:
    seasons = list(range(first_season, (last_season or jobs.current_season()) + 1))
    return {"seasons": [seasons[0], seasons[-1]] if seasons else None, **jobs.estimate_requests(seasons)}


@router.post("/leagues")
def add_league(body: NewLeague) -> dict:
    """Stores the league and starts the import job (import -> backup -> models -> reports -> backup)."""
    s = get_settings()
    if not s.api_football_key:
        raise HTTPException(409, "API_FOOTBALL_KEY fehlt – ohne Key können keine Daten geladen werden")
    if body.fd_code and body.fd_code not in FOOTBALL_DATA_CODES:
        raise HTTPException(422, f"Unbekanntes football-data-Kürzel {body.fd_code}")
    with Session(get_engine()) as session, session.begin():
        try:
            jobs.ensure_idle(session)  # before storing the league: no league without its import job
        except jobs.JobConflict as exc:
            raise HTTPException(409, str(exc)) from None
        if session.get(AppLeague, body.id):
            raise HTTPException(409, "Liga ist bereits konfiguriert")
        session.add(AppLeague(id=body.id, name=body.name, country=body.country, fd_code=body.fd_code or None,
                              oddspapi_tournament=body.oddspapi_tournament, first_season=body.first_season,
                              active=True))  # fmt: skip
    app_config.invalidate()
    params = {"league_id": body.id, "first_season": body.first_season,
              "last_season": body.last_season or jobs.current_season()}  # fmt: skip
    return _start("add_league", params)


@router.get("/leagues/presets")
def league_presets() -> list[dict]:
    """European top divisions for the strength scale (bundled list, IDs checked against API-Football)."""
    configured = {lg.id: lg.kind for lg in app_config.all_leagues()}
    data = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
    return [{**lg, "kind": kind, "configured": configured.get(lg["id"])}
            for kind, key in (("cup", "cups"), ("ratings", "leagues")) for lg in data[key]]  # fmt: skip


class NewRatingsLeagues(BaseModel):
    ids: list[int] = Field(min_length=1)
    first_season: int = Field(ge=2010, le=2100)


@router.post("/leagues/ratings")
def add_ratings_leagues(body: NewRatingsLeagues) -> dict:
    """Stores results-only leagues (strength scale) and imports their results: 1 request per season and league."""
    if not get_settings().api_football_key:
        raise HTTPException(409, "API_FOOTBALL_KEY fehlt – ohne Key können keine Daten geladen werden")
    data = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
    presets = {lg["id"]: {**lg, "kind": "ratings"} for lg in data["leagues"]}
    presets |= {lg["id"]: {**lg, "kind": "cup"} for lg in data["cups"]}
    unknown = [i for i in body.ids if i not in presets]
    if unknown:
        raise HTTPException(422, f"Nicht in der Liste der europäischen Ligen: {unknown}")
    with Session(get_engine()) as session, session.begin():
        try:
            jobs.ensure_idle(session)
        except jobs.JobConflict as exc:
            raise HTTPException(409, str(exc)) from None
        new = [i for i in body.ids if session.get(AppLeague, i) is None]
        if not new:
            raise HTTPException(409, "Alle ausgewählten Ligen sind bereits konfiguriert")
        for i in new:
            p = presets[i]
            session.add(AppLeague(id=i, name=p["name"], country=p["country"], first_season=max(body.first_season, p["seasons_from"]),
                                  active=True, kind=p["kind"]))  # fmt: skip
    app_config.invalidate()
    return _start("add_ratings", {"league_ids": new, "first_season": body.first_season,
                                  "last_season": jobs.current_season()})  # fmt: skip


class LeaguePatch(BaseModel):
    active: bool | None = None
    fd_code: str | None = None
    oddspapi_tournament: int | None = None


@router.patch("/leagues/{league_id}")
def patch_league(league_id: int, body: LeaguePatch) -> dict:
    with Session(get_engine()) as session, session.begin():
        lg = session.get(AppLeague, league_id)
        if lg is None:
            raise HTTPException(404, "Liga nicht konfiguriert")
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(lg, field, value)
        if (
            not lg.active
            and lg.kind == "full"
            and not session.scalars(
                select(AppLeague).where(AppLeague.active, AppLeague.kind == "full", AppLeague.id != lg.id)
            ).first()
        ):
            raise HTTPException(409, "Mindestens eine Liga muss aktiv bleiben")
    app_config.invalidate()
    return {"ok": True}


# --------------------------------------------------------------------------- jobs & backups


def _start(kind: str, params: dict) -> dict:
    try:
        job_id = jobs.create(kind, params)
    except jobs.JobConflict as exc:
        raise HTTPException(409, str(exc)) from None
    jobs.spawn(job_id)
    return job(job_id)


class JobRequest(BaseModel):
    kind: str
    league_id: int | None = (
        None  # add_league: re-run the import of a configured league (loads what is missing)
    )
    league_ids: list[int] | None = None  # add_ratings: re-run the results import of these leagues


@router.post("/jobs")
def start_job(body: JobRequest) -> dict:
    if body.kind == "add_ratings":
        known = {lg.id: lg for lg in app_config.all_leagues() if lg.kind in ("ratings", "cup")}
        ids = [i for i in (body.league_ids or []) if i in known]
        if not ids:
            raise HTTPException(404, "Keine konfigurierten Stärke-Ligen angegeben")
        return _start("add_ratings", {"league_ids": ids, "first_season": min(known[i].first_season for i in ids),
                                      "last_season": jobs.current_season()})  # fmt: skip
    if body.kind == "add_league":
        lg = next((lg for lg in app_config.all_leagues() if lg.id == body.league_id), None)
        if lg is None:
            raise HTTPException(404, "Liga nicht konfiguriert")
        if lg.kind in ("ratings", "cup"):
            return _start("add_ratings", {"league_ids": [lg.id], "first_season": lg.first_season,
                                          "last_season": jobs.current_season()})  # fmt: skip
        return _start("add_league", {"league_id": lg.id, "first_season": lg.first_season,
                                     "last_season": jobs.current_season()})  # fmt: skip
    if body.kind not in {"models", "picks", "backup"}:
        raise HTTPException(422, "Erlaubt: add_league, add_ratings, models, picks, backup")
    return _start(body.kind, {})


@router.get("/jobs")
def list_jobs(limit: int = 10) -> list[dict]:
    with Session(get_engine()) as session, session.begin():
        jobs.refresh_stale(session)
    rows = df(
        """select id, kind, params, status, steps, error, created_at, started_at, finished_at
           from app.jobs order by id desc limit :n""",
        n=limit,
    )
    return records(rows)


@router.get("/jobs/{job_id}")
def job(job_id: int) -> dict:
    with Session(get_engine()) as session:
        j = session.get(Job, job_id)
        if j is None:
            raise HTTPException(404, "Job nicht gefunden")
        return {"id": j.id, "kind": j.kind, "params": j.params, "status": j.status, "steps": j.steps,
                "error": j.error, "created_at": j.created_at, "started_at": j.started_at,
                "finished_at": j.finished_at}  # fmt: skip


@router.get("/backups")
def backups() -> list[dict]:
    return backup.list_backups()


@router.get("/backups/{name}")
def download_backup(name: str) -> FileResponse:
    path = backup.backup_path(name)
    if path is None:
        raise HTTPException(404, "Backup nicht gefunden")
    return FileResponse(path, filename=path.name, media_type="application/octet-stream")
