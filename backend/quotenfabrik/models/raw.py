"""Schema ``raw``: unmodified source data. Everything in ``core`` can be rebuilt from here."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, LargeBinary, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from quotenfabrik.models.base import Base


class ApiResponse(Base):
    __tablename__ = "api_responses"
    __table_args__ = (
        Index(None, "endpoint", "fetched_at"),
        Index(None, "params", postgresql_using="gin"),
        {"schema": "raw"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    endpoint: Mapped[str] = mapped_column(Text)
    params: Mapped[dict] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status_code: Mapped[int] = mapped_column(Integer)
    quota_remaining: Mapped[int | None] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSONB)
    payload_hash: Mapped[str] = mapped_column(Text)


class FootballDataFile(Base):
    __tablename__ = "football_data_files"
    __table_args__ = (UniqueConstraint("league_code", "season_code", "sha256"), {"schema": "raw"})

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    league_code: Mapped[str] = mapped_column(Text)
    season_code: Mapped[str] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sha256: Mapped[str] = mapped_column(Text)
    content: Mapped[bytes] = mapped_column(LargeBinary)


class OddsPapiResponse(Base):
    """OddsPapi responses, gzip-compressed (odds histories are ~25 MB of JSON per fixture).

    Odds histories are stored once the fixture is finished (complete history); interim snapshots of
    upcoming fixtures are only processed into ``core.odds_history``.
    """

    __tablename__ = "oddspapi_responses"
    __table_args__ = (Index(None, "endpoint", "fetched_at"), {"schema": "raw"})

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    endpoint: Mapped[str] = mapped_column(Text)
    params: Mapped[dict] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sha256: Mapped[str] = mapped_column(Text)
    content_gzip: Mapped[bytes] = mapped_column(LargeBinary)
