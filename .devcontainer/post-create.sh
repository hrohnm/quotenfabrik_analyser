#!/usr/bin/env bash
# One-time setup of the dev container: dependencies and database schema.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== Backend-Abhängigkeiten"
python -m venv backend/.venv
backend/.venv/bin/pip install -q --upgrade pip
backend/.venv/bin/pip install -q -e "backend[dev]"

echo "== Frontend-Abhängigkeiten"
(cd frontend-private && npm ci --no-audit --no-fund)

echo "== Datenbank"
bash scripts/ensure_schema.sh
