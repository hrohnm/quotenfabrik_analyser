"""FastAPI application (REST API for the private frontend)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from quotenfabrik.api.routers import (
    admin,
    bets,
    competitions,
    explorer,
    fixtures,
    league,
    meta,
    players,
    stats,
    teams,
)
from quotenfabrik.db import get_engine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    stats.warm_caches()
    yield


app = FastAPI(title="Quotenfabrik Analyser", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)
for router in (
    meta.router,
    fixtures.router,
    league.router,
    teams.router,
    competitions.router,
    players.router,
    explorer.router,
    stats.router,
    admin.router,
    bets.router,
):
    app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    with get_engine().connect() as conn:
        conn.execute(text("select 1"))
    return {"status": "ok"}
