"""Database backups (pg_dump, same format as the seed) under ``backups/``; optionally also replace the seed.

A backup right after an import keeps the fetched API data safe: a new environment restores it with
``qf seed import`` instead of spending API requests again.
"""

import shutil
from datetime import UTC, datetime
from pathlib import Path

from quotenfabrik import app_config
from quotenfabrik.seed import SEED_FILE, export_seed

BACKUP_DIR = Path(__file__).resolve().parents[2] / "backups"


def create_backup(reason: str = "manuell") -> Path:
    """Writes ``backups/quotenfabrik_<UTC time>_<reason>.dump`` (+ ``.revision``), prunes old backups."""
    BACKUP_DIR.mkdir(exist_ok=True)
    slug = "".join(c if c.isalnum() else "_" for c in reason.lower()).strip("_") or "backup"
    path = export_seed(BACKUP_DIR / f"quotenfabrik_{datetime.now(UTC):%Y%m%d_%H%M%S}_{slug}.dump")
    if app_config.get("backup.update_seed") and SEED_FILE.exists():  # the Docker image has no seed dump
        shutil.copyfile(path, SEED_FILE)
        shutil.copyfile(path.with_suffix(".revision"), SEED_FILE.with_suffix(".revision"))
    prune(app_config.get("backup.keep"))
    return path


def list_backups() -> list[dict]:
    if not BACKUP_DIR.exists():
        return []
    files = sorted(BACKUP_DIR.glob("quotenfabrik_*.dump"), reverse=True)
    return [
        {"name": f.name, "size": f.stat().st_size,
         "created_at": datetime.fromtimestamp(f.stat().st_mtime, UTC).isoformat()}
        for f in files
    ]  # fmt: skip


def backup_path(name: str) -> Path | None:
    """Path of an existing backup by file name (no path traversal)."""
    path = BACKUP_DIR / Path(name).name
    return path if path.suffix == ".dump" and path.exists() else None


def prune(keep: int) -> None:
    for old in sorted(BACKUP_DIR.glob("quotenfabrik_*.dump"), reverse=True)[keep:]:
        old.unlink(missing_ok=True)
        old.with_suffix(".revision").unlink(missing_ok=True)
