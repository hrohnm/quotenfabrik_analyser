"""Seed: snapshot of the database (schemas raw, core, analytics) as a compressed pg_dump file.

The seed lets a fresh environment start with all imported data and computed predictions without new API
requests. Excluded: ``raw.oddspapi_responses`` (gzip blobs, ~60 MB, re-fetchable for free).
"""

import shutil
import subprocess
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url

from quotenfabrik.config import get_settings
from quotenfabrik.db import get_engine

SEED_FILE = Path(__file__).resolve().parents[2] / "seed" / "quotenfabrik_seed.dump"
# Alembic revision of the schema inside the dump: after a restore the DB is stamped with it and then upgraded
SEED_REVISION_FILE = SEED_FILE.with_suffix(".revision")
DEFAULT_SEED_REVISION = "0004"
SCHEMAS = ("raw", "core", "analytics")
EXCLUDE_DATA = ("raw.oddspapi_responses",)


def _libpq_url() -> str:
    url = make_url(get_settings().database_url).set(drivername="postgresql")
    return url.render_as_string(hide_password=False)


def _binary(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(
            f"{name} nicht gefunden. PostgreSQL-Client-Tools (Version 16) installieren oder das Skript "
            "scripts/seed_import.sh (Docker) verwenden."
        )
    return path


def export_seed(path: Path = SEED_FILE) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        _binary("pg_dump"),
        "-d",
        _libpq_url(),
        "-Fc",
        "-Z9",
        "--no-owner",
        "--no-privileges",
        "-f",
        str(path),
    ]
    for schema in SCHEMAS:
        cmd += ["-n", schema]
    for table in EXCLUDE_DATA:
        cmd += [f"--exclude-table-data={table}"]
    subprocess.run(cmd, check=True)
    with get_engine().connect() as conn:
        revision = conn.execute(text("select version_num from public.alembic_version")).scalar_one()
    path.with_suffix(".revision").write_text(f"{revision}\n", encoding="utf-8")
    return path


def require_tools(*names: str) -> None:
    """Fails early (before anything is dropped) if the PostgreSQL client tools are missing."""
    for name in names:
        _binary(name)


def database_is_empty() -> bool:
    with get_engine().connect() as conn:
        return not conn.execute(
            text("select 1 from information_schema.schemata where schema_name = any(:s)"),
            {"s": list(SCHEMAS)},
        ).first()


def drop_schemas() -> None:
    with get_engine().begin() as conn:
        for schema in SCHEMAS:
            conn.execute(text(f"drop schema if exists {schema} cascade"))
        conn.execute(text("drop table if exists public.alembic_version"))


def import_seed(path: Path = SEED_FILE) -> None:
    """Restores the seed into an empty database, stamps the dump's revision and upgrades to head."""
    subprocess.run(
        [
            _binary("pg_restore"),
            "-d",
            _libpq_url(),
            "--no-owner",
            "--no-privileges",
            "--exit-on-error",
            str(path),
        ],
        check=True,
    )
    migrate_seeded(seed_revision(path))


def seed_revision(path: Path = SEED_FILE) -> str:
    rev_file = path.with_suffix(".revision")
    return rev_file.read_text(encoding="utf-8").strip() if rev_file.exists() else DEFAULT_SEED_REVISION


def migrate_seeded(revision: str) -> None:
    """Marks a restored dump with its schema revision and applies all newer migrations."""
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.stamp(cfg, revision)
    command.upgrade(cfg, "head")
