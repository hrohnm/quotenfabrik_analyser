#!/usr/bin/env bash
# Waits for PostgreSQL and brings the schema to the current migration.
# A database restored from the seed has the tables of the seed's revision but no alembic version
# -> stamp that revision (seed/quotenfabrik_seed.revision), then upgrade to head.
set -euo pipefail
cd "$(dirname "$0")/../backend"
PY=.venv/bin/python

for _ in $(seq 1 120); do
  if $PY -c "from quotenfabrik.db import get_engine; get_engine().connect().close()" 2>/dev/null; then break; fi
  sleep 2
done

state=$($PY - <<'PY'
from sqlalchemy import text
from quotenfabrik.db import get_engine
with get_engine().connect() as c:
    has_core = c.execute(text("select 1 from information_schema.tables where table_schema='core' and table_name='fixtures'")).first()
    has_version = c.execute(text("select 1 from information_schema.tables where table_schema='public' and table_name='alembic_version'")).first()
print("seeded" if has_core and not has_version else "migrate")
PY
)
if [[ "$state" == "seeded" ]]; then
  rev=$($PY -c "from quotenfabrik.seed import seed_revision; print(seed_revision())")
  echo "Seed erkannt -> alembic stamp $rev"
  .venv/bin/alembic stamp "$rev"
fi
.venv/bin/alembic upgrade head
