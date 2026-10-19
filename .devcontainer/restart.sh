#!/usr/bin/env bash
# Stops API and frontend (e.g. after git pull with backend changes) and starts both again.
cd "$(dirname "$0")/.."
pkill -f "uvicorn quotenfabrik.api.main" && echo "API gestoppt."
pkill -f "next dev" && echo "Frontend gestoppt."
sleep 2
bash .devcontainer/start.sh
echo "Warte auf die Dienste ..."
for _ in $(seq 1 60); do
  if curl -sf http://127.0.0.1:8000/health >/dev/null && curl -s -o /dev/null http://127.0.0.1:3000; then
    echo "API und Frontend laufen."
    exit 0
  fi
  sleep 2
done
echo "Dienste antworten noch nicht. Letzte Zeilen aus /tmp/api.log:"
tail -n 20 /tmp/api.log
exit 1
