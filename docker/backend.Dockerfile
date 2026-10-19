# Backend image for the API and the cron container (FastAPI, qf CLI, pg_dump 16 for backups, supercronic).
FROM ubuntu:24.04

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 DEBIAN_FRONTEND=noninteractive \
    PATH=/app/backend/.venv/bin:$PATH

# Ubuntu 24.04 ships Python 3.12 and the PostgreSQL 16 client (pg_dump/pg_restore for backups, same major as the db)
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv postgresql-client-16 curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# cron for containers: passes the environment to jobs and never starts a job twice in parallel
ARG SUPERCRONIC_VERSION=v0.2.33
ARG TARGETARCH
RUN curl -fsSL -o /usr/local/bin/supercronic \
      "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-${TARGETARCH:-amd64}" \
    && chmod +x /usr/local/bin/supercronic

# editable install: paths like backups/ and docs/ resolve relative to /app (same layout as the repository)
WORKDIR /app/backend
COPY backend/pyproject.toml backend/alembic.ini ./
COPY backend/alembic ./alembic
COPY backend/quotenfabrik ./quotenfabrik
RUN python3 -m venv .venv && .venv/bin/pip install -e . && mkdir -p /app/backups /app/docs

COPY scripts/ensure_schema.sh /app/scripts/ensure_schema.sh
# schema revision of the seed in the db image: migrations start from there after the first restore
COPY seed/quotenfabrik_seed.revision /app/seed/
COPY docker/api-start.sh docker/crontab /app/docker/

EXPOSE 8000
CMD ["bash", "/app/docker/api-start.sh"]
