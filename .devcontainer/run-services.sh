#!/usr/bin/env bash
# Waits for the one-time setup, then starts API (8000) and frontend (3000) if they are not running yet.
cd "$(dirname "$0")/.."
REPO=$(pwd)
MARKER="$HOME/.quotenfabrik-setup-done"

# fd 9 holds the lock; services are started in their own session (setsid -f) without fd 9 (9>&-),
# so the lock is released when this script ends
exec 9>/tmp/qf-services.lock
flock -n 9 || { echo "$(date -Is) Start läuft bereits in einem anderen Prozess."; exit 0; }

echo "$(date -Is) Warte auf Setup (post-create) ..."
for _ in $(seq 1 360); do
  [[ -f "$MARKER" ]] && break
  sleep 5
done
if [[ ! -f "$MARKER" ]]; then
  echo "$(date -Is) Setup nicht fertig geworden – bitte 'bash .devcontainer/post-create.sh' ausführen."
  exit 1
fi

bash scripts/ensure_schema.sh || echo "$(date -Is) Hinweis: ensure_schema fehlgeschlagen (DB erreichbar?)"

if curl -sf http://127.0.0.1:8000/health >/dev/null; then
  echo "$(date -Is) API läuft bereits."
else
  echo "$(date -Is) Starte API ..."
  setsid -f nohup "$REPO/backend/.venv/bin/uvicorn" quotenfabrik.api.main:app --app-dir "$REPO/backend" \
    --host 0.0.0.0 --port 8000 >>/tmp/api.log 2>&1 </dev/null 9>&-
fi

if curl -s -o /dev/null http://127.0.0.1:3000; then
  echo "$(date -Is) Frontend läuft bereits."
else
  echo "$(date -Is) Starte Frontend ..."
  setsid -f nohup bash -c 'cd "$1" && exec npm run dev -- --hostname 0.0.0.0 --port 3000' _ \
    "$REPO/frontend-private" >>/tmp/frontend.log 2>&1 </dev/null 9>&-
fi

for _ in $(seq 1 60); do
  if curl -sf http://127.0.0.1:8000/health >/dev/null && curl -s -o /dev/null http://127.0.0.1:3000; then
    echo "$(date -Is) API und Frontend laufen: Port 3000 öffnen."
    exit 0
  fi
  sleep 2
done
echo "$(date -Is) Dienste antworten noch nicht – siehe /tmp/api.log und /tmp/frontend.log"
