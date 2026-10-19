#!/usr/bin/env bash
# Spielt seed/quotenfabrik_seed.dump in die PostgreSQL-Datenbank des Docker-Compose-Dienstes "db" ein.
# Alternative ohne Docker: cd backend && qf seed import  (benötigt pg_restore 16 lokal)
set -euo pipefail
cd "$(dirname "$0")/.."

SEED=seed/quotenfabrik_seed.dump
DB_USER=${POSTGRES_USER:-qf}
DB_NAME=${POSTGRES_DB:-quotenfabrik}

docker compose up -d db
until docker compose exec -T db pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; do sleep 1; done

if [[ "${1:-}" == "--force" ]]; then
  docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" -qc \
    "drop schema if exists raw cascade; drop schema if exists core cascade; drop schema if exists analytics cascade; drop table if exists public.alembic_version;"
fi

docker compose exec -T db pg_restore -U "$DB_USER" -d "$DB_NAME" --no-owner --no-privileges --exit-on-error < "$SEED"
(cd backend && alembic stamp head)
echo "Seed eingespielt."
