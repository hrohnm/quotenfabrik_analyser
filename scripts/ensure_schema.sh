#!/usr/bin/env bash
# Waits for PostgreSQL and brings the schema to the current migration.
# A database restored from the seed has the tables of the seed's revision but no alembic version
# -> stamp that revision (seed/quotenfabrik_seed.revision), then upgrade to head.
set -euo pipefail
cd "$(dirname "$0")/../backend"
PY=.venv/bin/python

# prints why the connection fails (e.g. "password authentication failed"), never the URL (it holds the password)
CHECK='
import sys
from sqlalchemy.exc import OperationalError
from quotenfabrik.db import get_engine
try:
    get_engine().connect().close()
except OperationalError as e:
    lines = [ln.strip() for ln in str(e.orig).splitlines() if ln.strip()]
    sys.exit(lines[-1] if lines else type(e.orig).__name__)
except Exception as e:
    sys.exit(f"{type(e).__name__} (DATABASE_URL ungueltig? Passwort nur aus Buchstaben und Ziffern)")
'
for i in $(seq 1 300); do   # up to 10 minutes (seed restore on first start)
  if err=$($PY -c "$CHECK" 2>&1); then break; fi
  if (( i % 15 == 1 )); then echo "Warte auf die Datenbank: $err"; fi   # every 30 seconds
  sleep 2
done

state=$($PY - <<'PY'
from sqlalchemy import text
from quotenfabrik.db import get_engine
with get_engine().connect() as c:
    has_core = c.execute(text("select 1 from information_schema.tables where table_schema='core' and table_name='fixtures'")).first()
    has_version = c.execute(text("select 1 from information_schema.tables where table_schema='public' and table_name='alembic_version'")).first()
    has_data = has_core and c.execute(text("select 1 from core.fixtures limit 1")).first()
if has_core and not has_version:
    print("seeded")
elif not has_data:
    print("empty")
else:
    print("migrate")
PY
)
SEED=../seed/quotenfabrik_seed.dump
if [[ "$state" == "empty" && -f "$SEED" ]]; then
  # No data (e.g. a failed or interrupted seed import): restore the seed instead of starting with empty tables
  if command -v pg_restore >/dev/null; then
    echo "Datenbank ohne Daten -> Seed wird eingespielt (1-2 Minuten)"
    .venv/bin/qf seed import --force
    exit 0
  fi
  echo "Datenbank ohne Daten, aber pg_restore fehlt (PostgreSQL-Client 16 installieren) -> nur Schema anlegen"
fi
if [[ "$state" == "seeded" ]]; then
  rev=$($PY -c "from quotenfabrik.seed import seed_revision; print(seed_revision())")
  echo "Seed erkannt -> alembic stamp $rev"
  .venv/bin/alembic stamp "$rev"
fi
.venv/bin/alembic upgrade head
