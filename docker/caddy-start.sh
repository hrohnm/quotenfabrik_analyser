#!/bin/sh
# The app has no login of its own: refuse to start without a password (anyone could spend API quota).
set -eu
if [ -z "${QF_LOGIN_PASSWORD:-}" ]; then
  echo "QF_LOGIN_PASSWORD ist nicht gesetzt – der Zugang startet nicht ohne Passwort." >&2
  exit 1
fi
QF_LOGIN_HASH=$(caddy hash-password --plaintext "$QF_LOGIN_PASSWORD")
export QF_LOGIN_HASH
exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
