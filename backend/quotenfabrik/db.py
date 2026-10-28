"""Database engine and session handling."""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from quotenfabrik import json_utils
from quotenfabrik.config import get_settings


def make_engine(url: str) -> Engine:
    """Engine whose JSON(B) serializer turns NaN/±inf into null (PostgreSQL rejects them) and accepts numpy
    values, so a metric of an empty sample can never break an insert."""
    return create_engine(url, pool_pre_ping=True, json_serializer=json_utils.dumps)


@lru_cache
def get_engine(url: str | None = None) -> Engine:
    return make_engine(url or get_settings().database_url)


@contextmanager
def session_scope(engine: Engine | None = None) -> Iterator[Session]:
    """Transactional scope: commit on success, rollback on error."""
    factory = sessionmaker(bind=engine or get_engine(), expire_on_commit=False)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
