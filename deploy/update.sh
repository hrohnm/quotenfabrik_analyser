#!/usr/bin/env bash
# Aktualisiert die Installation auf dem Server: git pull, Abhängigkeiten, Migrationen, Frontend-Build, Neustart.
# Aufruf als Benutzer qf: bash deploy/update.sh   (sudo-Passwort wird für den Neustart abgefragt)
set -euo pipefail
cd "$(dirname "$0")/.."

busy=$(curl -fsS "http://127.0.0.1:8000/api/admin/jobs?limit=1" 2>/dev/null \
  | python3 -c 'import json, sys; print(any(j["status"] in ("queued", "running") for j in json.load(sys.stdin)))' \
  || echo False)
if [[ "$busy" == "True" ]]; then
  echo "Ein Hintergrund-Job läuft noch (Einstellungen → Hintergrund-Jobs). Update danach ausführen."
  exit 1
fi

git pull --ff-only
backend/.venv/bin/pip install -q -e backend
bash scripts/ensure_schema.sh
(cd frontend-private && npm ci --no-audit --no-fund && npm run build)
sudo systemctl restart qf-api qf-frontend
echo "Update fertig: $(git log --oneline -1)"
