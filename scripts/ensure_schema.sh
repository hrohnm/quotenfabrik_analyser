#!/usr/bin/env bash
# Waits for PostgreSQL and brings the schema to the current migration.
# A database restored from the seed has all tables but no alembic version -> "stamp head" instead of "upgrade".
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
  echo "Seed erkannt -> alembic stamp head"
  .venv/bin/alembic stamp head
else
  .venv/bin/alembic upgrade head
fi
