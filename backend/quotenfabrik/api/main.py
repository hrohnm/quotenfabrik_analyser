"""FastAPI application (REST API for the private frontend)."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from quotenfabrik.api.routers import admin, explorer, fixtures, meta, stats
from quotenfabrik.db import get_engine

app = FastAPI(title="Quotenfabrik Analyser", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST", "PUT", "PATCH"],
    allow_headers=["*"],
)
for router in (meta.router, fixtures.router, explorer.router, stats.router, admin.router):
    app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    with get_engine().connect() as conn:
        conn.execute(text("select 1"))
    return {"status": "ok"}
