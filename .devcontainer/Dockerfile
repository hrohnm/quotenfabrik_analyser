FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

# The base image ships a Yarn apt repository whose signing key has expired (NO_PUBKEY 62D54FD4003F6525).
# Every "apt-get update" - also inside dev container features - fails until it is removed.
RUN rm -f /etc/apt/sources.list.d/yarn.list

# PostgreSQL 16 client tools (pg_dump / pg_restore for seed import/export and backups)
COPY install-pg-client.sh /tmp/install-pg-client.sh
RUN bash /tmp/install-pg-client.sh && rm /tmp/install-pg-client.sh
