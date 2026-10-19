# PostgreSQL 16 with the repository seed: an empty data volume is filled from seed/ on the first start.
FROM postgres:16
COPY seed/quotenfabrik_seed.dump seed/quotenfabrik_seed.revision /seed/
COPY scripts/db-init/ /docker-entrypoint-initdb.d/
