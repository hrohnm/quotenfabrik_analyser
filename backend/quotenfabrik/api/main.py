"""FastAPI application. Routers for analyses follow in phase 2/3."""

from fastapi import FastAPI
from sqlalchemy import text

from quotenfabrik.db import get_engine

app = FastAPI(title="Quotenfabrik Analyser", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    with get_engine().connect() as conn:
        conn.execute(text("select 1"))
    return {"status": "ok"}
