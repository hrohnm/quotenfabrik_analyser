#!/usr/bin/env bash
# Starts API and frontend detached from the calling lifecycle command and returns immediately.
# Safe to call repeatedly (postCreate, postStart, postAttach, manually): running services are left alone.
cd "$(dirname "$0")/.."
setsid -f nohup bash .devcontainer/run-services.sh >>/tmp/qf-services.log 2>&1 </dev/null
echo "API: Port 8000 (/docs) · Frontend: Port 3000 · Logs: /tmp/qf-services.log, /tmp/api.log, /tmp/frontend.log"
