#!/usr/bin/env bash
# One-time setup of the dev container: dependencies and database schema.
# Writes a marker when done; .devcontainer/run-services.sh waits for it before starting API and frontend.
set -euo pipefail
cd "$(dirname "$0")/.."
MARKER="$HOME/.quotenfabrik-setup-done"
rm -f "$MARKER"

echo "== Backend-Abhängigkeiten"
python -m venv backend/.venv
backend/.venv/bin/pip install -q --upgrade pip
backend/.venv/bin/pip install -q -e "backend[dev]"

echo "== Frontend-Abhängigkeiten"
(cd frontend-private && npm ci --no-audit --no-fund)

echo "== Datenbank"
bash scripts/ensure_schema.sh

touch "$MARKER"
echo "Setup fertig. API und Frontend starten automatisch (Log: /tmp/qf-services.log)."
bash .devcontainer/start.sh
