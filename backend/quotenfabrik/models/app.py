"""Schema ``app``: settings, configured leagues and background jobs (configuration page)."""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from quotenfabrik.models.base import Base

APP = {"schema": "app"}


class AppSetting(Base):
    """Overrides of the defaults in ``quotenfabrik.app_config.SETTINGS`` (key -> JSON value)."""

    __tablename__ = "settings"
    __table_args__ = APP

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[object] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AppLeague(Base):
    """Leagues in scope. If the table is empty, ``QF_LEAGUES`` & co. from the environment are used."""

    __tablename__ = "leagues"
    __table_args__ = APP

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)  # API-Football league id
    name: Mapped[str] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(Text)
    fd_code: Mapped[str | None] = mapped_column(Text)  # football-data.co.uk code, e.g. "D1"
    oddspapi_tournament: Mapped[int | None] = mapped_column(Integer)
    first_season: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    # 'full' = everything (details, odds, forecasts, picks); 'ratings' = results only, for the strength scale
    kind: Mapped[str] = mapped_column(Text, server_default="full")
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Job(Base):
    """Background job started from the configuration page (``qf jobs run``)."""

    __tablename__ = "jobs"
    __table_args__ = APP

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    kind: Mapped[str] = mapped_column(Text)  # 'add_league', 'models', 'picks', 'backup'
    params: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    status: Mapped[str] = mapped_column(Text, server_default="queued")  # queued, running, done, failed
    steps: Mapped[list] = mapped_column(JSONB, server_default="[]")  # [{name, label, status, message}]
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
