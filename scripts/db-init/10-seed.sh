#!/usr/bin/env bash
# Runs once when the PostgreSQL container initialises an empty data directory (docker-entrypoint-initdb.d).
# Restores the repository seed so a fresh environment starts with all data.
set -euo pipefail
SEED=${SEED_FILE:-/seed/quotenfabrik_seed.dump}
if [[ -f "$SEED" ]]; then
  echo "Quotenfabrik: Seed wird eingespielt ($SEED) ..."
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges --exit-on-error "$SEED"
  echo "Quotenfabrik: Seed eingespielt."
else
  echo "Quotenfabrik: kein Seed gefunden, Datenbank bleibt leer."
fi
