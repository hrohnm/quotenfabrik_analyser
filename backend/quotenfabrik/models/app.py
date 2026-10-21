"""Schema ``app``: settings, configured leagues and background jobs (configuration page)."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, Numeric, Text, func
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


class Bet(Base):
    """A placed bet (single or combo) – tracked on the configuration page "Wetten"."""

    __tablename__ = "bets"
    __table_args__ = APP

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    placed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    source: Mapped[str] = mapped_column(Text, server_default="manuell")  # tageskombi | tipps | manuell
    label: Mapped[str] = mapped_column(Text)
    bookmaker: Mapped[str] = mapped_column(Text, server_default="Betano")
    stake: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    odds: Mapped[Decimal] = mapped_column(Numeric(8, 3))
    probability: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(Text, server_default="open")  # open | won | lost | void
    payout: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    payout_manual: Mapped[bool] = mapped_column(
        Boolean, server_default="false"
    )  # entered by hand, not stake × odds


class BankrollTransaction(Base):
    """Bankroll bookings: starting capital, deposits, withdrawals and resets of the evaluation period."""

    __tablename__ = "bankroll_transactions"
    __table_args__ = APP

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    kind: Mapped[str] = mapped_column(Text)  # start | deposit | withdrawal | reset
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default="0")
    note: Mapped[str | None] = mapped_column(Text)


class BetLeg(Base):
    """One tip of a bet; settled automatically from the fixture result (after 90 minutes)."""

    __tablename__ = "bet_legs"
    __table_args__ = APP

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    bet_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("app.bets.id", ondelete="CASCADE"))
    fixture_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("core.fixtures.id"))
    market: Mapped[str | None] = mapped_column(Text)
    selection: Mapped[str | None] = mapped_column(Text)
    line: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    label: Mapped[str] = mapped_column(Text)
    probability: Mapped[float | None] = mapped_column(Float)
    odds: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    outcome: Mapped[bool | None] = mapped_column(Boolean)
