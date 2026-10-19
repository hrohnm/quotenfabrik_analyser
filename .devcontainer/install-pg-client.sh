#!/usr/bin/env bash
# Installs the PostgreSQL 16 client tools (pg_dump / pg_restore) from the official PostgreSQL apt repository.
# Debian bookworm only ships version 15, which cannot read dumps written by pg_dump 16.
# Used by the Dockerfile; in a running Codespace: sudo bash .devcontainer/install-pg-client.sh
set -euo pipefail
if command -v pg_restore >/dev/null && pg_restore --version | grep -q " 16\."; then
  echo "PostgreSQL-Client 16 bereits installiert"
  exit 0
fi
rm -f /etc/apt/sources.list.d/yarn.list  # expired key in the base image breaks apt-get update
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl gnupg
install -d /usr/share/postgresql-common/pgdg
curl -fsSL -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc https://www.postgresql.org/media/keys/ACCC4CF8.asc
echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" \
  > /etc/apt/sources.list.d/pgdg.list
apt-get update
apt-get install -y --no-install-recommends postgresql-client-16
rm -rf /var/lib/apt/lists/*
pg_restore --version
