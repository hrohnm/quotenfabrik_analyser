"""Configuration page backend: settings validation, league fallback, jobs and backups."""

import pytest
from sqlalchemy import text

from quotenfabrik import app_config, backup, jobs
from quotenfabrik.models import Job


@pytest.fixture(autouse=True)
def no_db_overrides(monkeypatch):
    """Settings without database overrides (defaults only)."""
    monkeypatch.setattr(app_config, "overrides", lambda: {})
    app_config.invalidate()


def test_validate_settings():
    assert app_config.validate({"picks.mutig.min_p": 0.5}) == {"picks.mutig.min_p": 0.5}
    assert app_config.validate({"api.quota_reserve": "300"}) == {"api.quota_reserve": 300}
    with pytest.raises(app_config.SettingsError, match="Unbekannte"):
        app_config.validate({"foo": 1})
    with pytest.raises(app_config.SettingsError, match="erlaubt"):
        app_config.validate({"api.max_rps": 10})
    with pytest.raises(app_config.SettingsError, match="kleiner"):
        app_config.validate({"picks.sicher.min_p": 0.95})
    with pytest.raises(app_config.SettingsError, match="Zahl"):
        app_config.validate({"model.reg": "viel"})
    with pytest.raises(app_config.SettingsError, match="erlaubt sind"):
        app_config.validate({"picks.default_profile": "wild"})


def test_defaults_feed_profiles_and_model():
    from quotenfabrik.analytics.picks import default_profile, profiles
    from quotenfabrik.analytics.poisson import PoissonParams

    assert default_profile() == "ausgewogen"
    assert profiles()["sicher"].min_p == 0.70
    assert app_config.model_params() == PoissonParams()


def test_leagues_fall_back_to_environment(monkeypatch):
    monkeypatch.setattr(app_config, "_query", lambda sql, engine=None: [])
    app_config.invalidate()
    ids = app_config.league_ids()
    assert ids == app_config.get_settings().leagues
    assert app_config.fd_code_for(ids[0]) == app_config.get_settings().fd_leagues[0]
    unknown = app_config.league(999999)
    assert unknown.fd_code is None and unknown.oddspapi_tournament is None


def test_job_definitions_and_estimate():
    assert jobs.steps_for("add_league", {})[0] == "football_data"
    assert "backup_data" in jobs.steps_for("add_league", {})
    assert jobs.steps_for("picks", {}) == ["picks"]
    est = jobs.estimate_requests([2023, 2024], matches_per_season=306)
    assert (
        est["fixtures"] == 2
        and est["details"] == 2 * 16
        and est["half_stats"] == 306
        and est["injuries"] == 2
    )
    assert est["total"] == 2 + 32 + 306 + 2


def test_backup_path_rejects_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(backup, "BACKUP_DIR", tmp_path)
    (tmp_path / "quotenfabrik_1.dump").write_bytes(b"x")
    assert backup.backup_path("quotenfabrik_1.dump") == tmp_path / "quotenfabrik_1.dump"
    assert backup.backup_path("../../etc/passwd") is None
    assert backup.backup_path("missing.dump") is None


def test_prune_keeps_newest(tmp_path, monkeypatch):
    monkeypatch.setattr(backup, "BACKUP_DIR", tmp_path)
    for i in range(4):
        (tmp_path / f"quotenfabrik_2026010{i}_000000_x.dump").write_bytes(b"x")
        (tmp_path / f"quotenfabrik_2026010{i}_000000_x.revision").write_text("0006")
    backup.prune(2)
    assert sorted(p.name for p in tmp_path.glob("*.dump")) == [
        "quotenfabrik_20260102_000000_x.dump",
        "quotenfabrik_20260103_000000_x.dump",
    ]
    assert len(list(tmp_path.glob("*.revision"))) == 2


def test_job_run_records_steps(engine, monkeypatch):
    """Skipped and optional steps do not stop a job; a failing required step does."""
    monkeypatch.setattr(jobs, "get_engine", lambda: engine)
    with engine.begin() as conn:
        conn.execute(text("truncate app.jobs"))

    def skip(params, log):
        raise jobs.StepSkipped("nicht nötig")

    def boom(params, log):
        raise RuntimeError("kaputt")

    def ok(params, log):
        log("Zeile 1")
        return "fertig"

    handlers = {name: ok for name in jobs.STEP_LABELS}
    handlers.update(football_data=skip, reports=boom)
    monkeypatch.setattr(jobs, "_handlers", lambda: handlers)

    job_id = jobs.create("add_league", {"league_id": 1, "first_season": 2025})
    with pytest.raises(jobs.JobConflict):
        jobs.create("picks")
    assert jobs.run(job_id) == "done"
    with engine.connect() as conn:
        job = conn.execute(text("select status, steps from app.jobs where id = :id"), {"id": job_id}).one()
    status = {s["name"]: s["status"] for s in job.steps}
    assert job.status == "done"
    assert (
        status["football_data"] == "skipped" and status["reports"] == "failed" and status["backup"] == "done"
    )
    assert job.steps[1]["log"] == ["Zeile 1"]

    handlers.update(api_football=boom)
    job_id = jobs.create("add_league", {"league_id": 1, "first_season": 2025})
    assert jobs.run(job_id) == "failed"
    with engine.connect() as conn:
        steps = conn.execute(text("select steps from app.jobs where id = :id"), {"id": job_id}).scalar_one()
    assert [s["status"] for s in steps][:3] == ["skipped", "failed", "pending"]


def test_stale_job_is_marked_failed(engine, monkeypatch):
    from sqlalchemy.orm import Session

    monkeypatch.setattr(jobs, "get_engine", lambda: engine)
    with Session(engine) as session, session.begin():
        session.execute(text("truncate app.jobs"))
        session.add(Job(kind="backup", params={"pid": 2**22 + 12345}, status="running", steps=[]))
    with Session(engine) as session, session.begin():
        jobs.refresh_stale(session)
    with engine.connect() as conn:
        assert conn.execute(text("select status from app.jobs")).scalar_one() == "failed"
