"""Database helpers shared by the ingest jobs."""

import hashlib
import json
from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy import Engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from quotenfabrik.models import ApiResponse
from quotenfabrik.sources.api_football import ApiResult

CHUNK = 1000


def upsert(
    session: Session,
    model: type,
    rows: Sequence[dict[str, Any]],
    *,
    update: bool = True,
    exclude_from_update: Iterable[str] = (),
    conflict_columns: Sequence[str] | None = None,
) -> None:
    """INSERT ... ON CONFLICT (primary key or ``conflict_columns``) DO UPDATE/NOTHING, in chunks."""
    if not rows:
        return
    table = model.__table__
    pk = list(conflict_columns or [c.name for c in table.primary_key.columns])
    for start in range(0, len(rows), CHUNK):
        chunk = rows[start : start + CHUNK]
        stmt = insert(table).values(list(chunk))
        excluded = set(pk) | set(exclude_from_update)
        columns = [c for c in chunk[0] if c not in excluded]
        if update and columns:
            stmt = stmt.on_conflict_do_update(index_elements=pk, set_={c: stmt.excluded[c] for c in columns})
        else:
            stmt = stmt.on_conflict_do_nothing(index_elements=pk)
        session.execute(stmt)


def raw_response_saver(engine: Engine):
    """Hook for ApiFootballClient: stores every response in its own transaction.

    Raw data is kept even if processing of that response fails later on.
    """

    def save(result: ApiResult) -> None:
        if result.endpoint == "status":
            return  # account data, no football data
        body = json.dumps(result.payload, sort_keys=True, separators=(",", ":"))
        with Session(engine) as session, session.begin():
            session.add(
                ApiResponse(
                    endpoint=result.endpoint,
                    params={k: str(v) for k, v in result.params.items()},
                    status_code=result.status_code,
                    quota_remaining=result.quota_remaining,
                    payload=result.payload,
                    payload_hash=hashlib.sha256(body.encode()).hexdigest(),
                )
            )

    return save
