#!/usr/bin/env bash
# Starts API (port 8000) and frontend (port 3000) in the background on every container start.
cd "$(dirname "$0")/.."
bash scripts/ensure_schema.sh >/tmp/ensure_schema.log 2>&1 || true
nohup backend/.venv/bin/uvicorn quotenfabrik.api.main:app --app-dir backend --host 0.0.0.0 --port 8000 \
  >/tmp/api.log 2>&1 &
(cd frontend-private && nohup npm run dev -- --hostname 0.0.0.0 --port 3000 >/tmp/frontend.log 2>&1 &)
echo "API: http://localhost:8000/docs  ·  Frontend: http://localhost:3000  (Logs: /tmp/api.log, /tmp/frontend.log)"
