#!/usr/bin/env bash
# Starts PostgreSQL via the official entrypoint, then sets the password of POSTGRES_USER to POSTGRES_PASSWORD.
# The image only applies POSTGRES_PASSWORD when the data volume is initialised; this keeps both in sync when the
# variable is set or changed later (e.g. Hostinger Docker Manager: deploy first, enter variables afterwards).
set -euo pipefail

docker-entrypoint.sh postgres "$@" &
pid=$!
trap 'kill -TERM "$pid" 2>/dev/null; wait "$pid"; exit $?' TERM INT

# TCP is only served by the real server, not by the temporary one used for the first seed restore
until pg_isready -q -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"; do
  kill -0 "$pid" 2>/dev/null || { wait "$pid"; exit $?; }
  sleep 1
done
pw=${POSTGRES_PASSWORD//\'/\'\'}
# local socket connections are trusted inside the container; the password is passed via stdin, not as argument
psql -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<SQL && echo "Quotenfabrik: Passwort von $POSTGRES_USER aus POSTGRES_PASSWORD übernommen."
ALTER USER "$POSTGRES_USER" PASSWORD '$pw';
SQL

wait "$pid"
