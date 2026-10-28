"""Schema ``analytics``: model runs, predictions, patterns and evaluations."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from quotenfabrik.models.base import Base

ANALYTICS = {"schema": "analytics"}


class ModelRun(Base):
    __tablename__ = "model_runs"
    __table_args__ = ANALYTICS

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    kind: Mapped[str] = mapped_column(Text)  # 'forecast', 'backtest' or 'evaluation'
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
    # time the prediction refers to (model fitted on data before it); backtests: first kickoff of the matchday
    predicted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    outcome: Mapped[bool | None] = mapped_column(Boolean)  # set once the match is finished (qf model settle)


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


class Pick(Base):
    """Suggested picks per fixture and profile (``qf picks build``); the outcome comes from the prediction."""

    __tablename__ = "picks"
    __table_args__ = (Index(None, "fixture_id"), Index(None, "model_run_id", "profile"), ANALYTICS)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    model_run_id: Mapped[int] = mapped_column(ForeignKey("analytics.model_runs.id", ondelete="CASCADE"))
    prediction_id: Mapped[int] = mapped_column(ForeignKey("analytics.predictions.id", ondelete="CASCADE"))
    fixture_id: Mapped[int] = mapped_column(ForeignKey("core.fixtures.id"))
    profile: Mapped[str] = mapped_column(Text)  # 'sicher', 'ausgewogen', 'mutig'
    rank: Mapped[int] = mapped_column(Integer)
    market_group: Mapped[str] = mapped_column(Text)
    market: Mapped[str] = mapped_column(Text)
    selection: Mapped[str] = mapped_column(Text)
    line: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    probability: Mapped[float] = mapped_column(Float)
    base_rate: Mapped[float | None] = mapped_column(Float)  # league frequency (3 seasons before the matchday)
    score: Mapped[float] = mapped_column(Float)
    reasons: Mapped[list | None] = mapped_column(JSONB(none_as_null=True))  # supporting pattern signals


class FrozenRun(Base):
    """Forecast run shown and settled for a fixture once its day is frozen (``qf day freeze``)."""

    __tablename__ = "frozen_runs"
    __table_args__ = ANALYTICS

    fixture_id: Mapped[int] = mapped_column(ForeignKey("core.fixtures.id"), primary_key=True)
    model_run_id: Mapped[int] = mapped_column(ForeignKey("analytics.model_runs.id", ondelete="CASCADE"))
    frozen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DayCombo(Base):
    """Daily combo as published on the day (legs with odds and probabilities at freezing time)."""

    __tablename__ = "day_combos"
    __table_args__ = ANALYTICS

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    kind: Mapped[str] = mapped_column(Text, primary_key=True)
    frozen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    odds: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    probability: Mapped[float] = mapped_column(Float)
    real_odds: Mapped[bool] = mapped_column(Boolean)
    legs: Mapped[list] = mapped_column(JSONB)


class DecisionModel(Base):
    """Fitted Tippschein decision model per decision (coefficients, scaling, confidence table, metrics)."""

    __tablename__ = "decision_models"
    __table_args__ = ANALYTICS

    decision: Mapped[str] = mapped_column(Text, primary_key=True)
    fitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    payload: Mapped[dict] = mapped_column(JSONB)


class DecisionProb(Base):
    """Tippschein: probability per selection and confidence (0-100) of one decision for a prediction run."""

    __tablename__ = "decision_probs"
    __table_args__ = ANALYTICS

    model_run_id: Mapped[int] = mapped_column(
        ForeignKey("analytics.model_runs.id", ondelete="CASCADE"), primary_key=True
    )
    fixture_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    decision: Mapped[str] = mapped_column(Text, primary_key=True)
    probabilities: Mapped[dict] = mapped_column(JSONB)
    confidence: Mapped[float | None] = mapped_column(Float)


class ValueTip(Base):
    """Value tip as shown on its day (``qf picks freeze``): our and the market's probability, Betano odds."""

    __tablename__ = "value_tips"
    __table_args__ = ANALYTICS

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    fixture_id: Mapped[int] = mapped_column(BigInteger, index=True)
    market: Mapped[str] = mapped_column(Text)
    selection: Mapped[str] = mapped_column(Text)
    line: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    probability: Mapped[float] = mapped_column(Float)  # blend used for the edge
    p_model: Mapped[float] = mapped_column(Float)
    p_market: Mapped[float | None] = mapped_column(Float)
    odds: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    edge: Mapped[float] = mapped_column(Float)
    frozen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
