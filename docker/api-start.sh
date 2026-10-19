#!/usr/bin/env bash
# API container: wait for the database, apply migrations (stamp the seed revision first), then serve.
set -euo pipefail
bash /app/scripts/ensure_schema.sh
exec uvicorn quotenfabrik.api.main:app --host 0.0.0.0 --port 8000
