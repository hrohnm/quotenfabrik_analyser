"""Schema ``analytics``: model runs, predictions, patterns and evaluations."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, Integer, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from quotenfabrik.models.base import Base

ANALYTICS = {"schema": "analytics"}


class ModelRun(Base):
    __tablename__ = "model_runs"
    __table_args__ = ANALYTICS

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    kind: Mapped[str] = mapped_column(Text)  # 'forecast' or 'evaluation'
    model_version: Mapped[str] = mapped_column(Text)
    league_id: Mapped[int] = mapped_column(Integer)
    as_of: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    params: Mapped[dict] = mapped_column(JSONB)
    summary: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (Index(None, "fixture_id", "model_run_id"), ANALYTICS)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    model_run_id: Mapped[int] = mapped_column(ForeignKey("analytics.model_runs.id", ondelete="CASCADE"))
    fixture_id: Mapped[int] = mapped_column(ForeignKey("core.fixtures.id"))
    market_group: Mapped[str] = mapped_column(Text)
    market: Mapped[str] = mapped_column(Text)
    selection: Mapped[str] = mapped_column(Text)  # player id for scorer markets
    line: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    probability: Mapped[float] = mapped_column(Float)
    fair_odd: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))


class PatternResultRow(Base):
    __tablename__ = "pattern_results"
    __table_args__ = (Index(None, "fixture_id", "model_run_id"), ANALYTICS)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    model_run_id: Mapped[int] = mapped_column(ForeignKey("analytics.model_runs.id", ondelete="CASCADE"))
    fixture_id: Mapped[int] = mapped_column(ForeignKey("core.fixtures.id"))
    market_group: Mapped[str] = mapped_column(Text)
    key: Mapped[str] = mapped_column(Text)
    label: Mapped[str] = mapped_column(Text)
    scope: Mapped[str] = mapped_column(Text)
    value: Mapped[float | None] = mapped_column(Float)
    n: Mapped[int | None] = mapped_column(Integer)
    baseline: Mapped[float | None] = mapped_column(Float)
    signal: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict | None] = mapped_column(JSONB)


class Evaluation(Base):
    """Walk-forward metrics per market selection (and summary rows) of an evaluation run."""

    __tablename__ = "evaluations"
    __table_args__ = (Index(None, "model_run_id"), ANALYTICS)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    model_run_id: Mapped[int] = mapped_column(ForeignKey("analytics.model_runs.id", ondelete="CASCADE"))
    market_group: Mapped[str] = mapped_column(Text)
    market: Mapped[str] = mapped_column(Text)
    selection: Mapped[str | None] = mapped_column(Text)
    line: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    n: Mapped[int] = mapped_column(Integer)
    metrics: Mapped[dict] = mapped_column(JSONB)
