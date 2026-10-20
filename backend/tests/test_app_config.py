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


def test_ratings_leagues_are_kept_out_of_full_league_lists(monkeypatch):
    rows = [
        (78, "Bundesliga", "Germany", "D1", 35, 2015, True, "full"),
        (39, "Premier League", "England", None, None, 2017, True, "ratings"),
        (88, "Eredivisie", "Netherlands", None, None, 2017, False, "ratings"),
        (2, "UEFA Champions League", "Europa", None, None, 2016, True, "cup"),
    ]
    monkeypatch.setattr(app_config, "_query", lambda sql, engine=None: rows)
    app_config.invalidate()
    assert app_config.league_ids() == [78]  # frontend, forecasts, odds snapshots, cron updates
    assert [lg.id for lg in app_config.ratings_leagues()] == [39]  # inactive ratings league is left out
    assert [lg.id for lg in app_config.cup_leagues()] == [2]
    assert [lg.id for lg in app_config.all_leagues()] == [78, 39, 88, 2]
    assert jobs.steps_for("add_ratings", {}) == ["results", "backup_data"]


def test_presets_are_verified_european_top_divisions():
    import json

    from quotenfabrik.api.routers.admin import PRESETS_FILE

    data = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
    assert [c["id"] for c in data["cups"]] == [2, 3, 848]  # Champions, Europa, Conference League
    leagues = data["leagues"]
    by_id = {lg["id"]: lg for lg in leagues}
    assert len(by_id) == len(leagues) >= 20
    assert by_id[39]["name"] == "Premier League" and by_id[39]["country"] == "England"
    assert by_id[218]["country"] == "Austria"
    assert all(lg["seasons_from"] <= 2018 for lg in leagues)


def test_load_matches_all_rounds(engine):
    """Results-only leagues keep championship/relegation rounds (no matchday) for the strength scale."""
    from quotenfabrik.analytics.data import load_leagues, load_matches

    with engine.begin() as conn:
        conn.execute(
            text("insert into core.leagues (id, name, country) values (179, 'Premiership', 'Scotland')")
        )
        for tid in (1, 2):
            conn.execute(
                text("insert into core.teams (id, name) values (:i, :n)"), {"i": tid, "n": f"T{tid}"}
            )
        for fid, rnd in ((1, "Regular Season - 33"), (2, "Championship Round - 1")):
            conn.execute(text(
                """insert into core.fixtures (id, league_id, season, round, matchday, kickoff_utc, status,
                       home_team_id, away_team_id, ft_home, ft_away, ht_home, ht_away, updated_at)
                   values (:id, 179, 2025, :r, null, now(), 'FT', 1, 2, 1, 0, 0, 0, now())"""), {"id": fid, "r": rnd})  # fmt: skip
    assert list(load_matches(engine, 179)["fixture_id"]) == [1]
    assert sorted(load_matches(engine, 179, all_rounds=True)["fixture_id"]) == [1, 2]
    assert sorted(load_leagues(engine, [179], all_rounds={179})["fixture_id"]) == [1, 2]
