"""Schema ``core``: normalized facts. Natural keys are API-Football ids."""

from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from quotenfabrik.models.base import Base

CORE = {"schema": "core"}
Odd = Numeric(8, 3)


class League(Base):
    __tablename__ = "leagues"
    __table_args__ = CORE

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(Text)


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = CORE

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(Text)
    logo_url: Mapped[str | None] = mapped_column(Text)


class TeamAlias(Base):
    """Team names used by other sources (e.g. football-data.co.uk) mapped to API team ids."""

    __tablename__ = "team_aliases"
    __table_args__ = CORE

    source: Mapped[str] = mapped_column(Text, primary_key=True)
    alias: Mapped[str] = mapped_column(Text, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("core.teams.id"))
    matched_games: Mapped[int] = mapped_column(Integer, default=0)


class Venue(Base):
    __tablename__ = "venues"
    __table_args__ = CORE

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(Text)


class Player(Base):
    __tablename__ = "players"
    __table_args__ = CORE

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(Text)


class Bookmaker(Base):
    __tablename__ = "bookmakers"
    __table_args__ = CORE

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(Text)


class BetType(Base):
    __tablename__ = "bet_types"
    __table_args__ = CORE

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(Text)
    market_group: Mapped[str | None] = mapped_column(Text)


class Fixture(Base):
    __tablename__ = "fixtures"
    __table_args__ = (Index(None, "league_id", "season", "kickoff_utc"), CORE)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    league_id: Mapped[int] = mapped_column(ForeignKey("core.leagues.id"))
    season: Mapped[int] = mapped_column(Integer)
    round: Mapped[str | None] = mapped_column(Text)
    matchday: Mapped[int | None] = mapped_column(Integer)
    kickoff_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text)
    venue_id: Mapped[int | None] = mapped_column(ForeignKey("core.venues.id"))
    referee: Mapped[str | None] = mapped_column(Text)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("core.teams.id"))
    away_team_id: Mapped[int] = mapped_column(ForeignKey("core.teams.id"))
    ft_home: Mapped[int | None] = mapped_column(Integer)
    ft_away: Mapped[int | None] = mapped_column(Integer)
    ht_home: Mapped[int | None] = mapped_column(Integer)
    ht_away: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Set when events/lineups/statistics/players were loaded for a finished fixture.
    details_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    half_stats_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FixtureTeamStats(Base):
    __tablename__ = "fixture_team_stats"
    __table_args__ = (CheckConstraint("period in ('FT','1H','2H')", name="period"), CORE)

    fixture_id: Mapped[int] = mapped_column(ForeignKey("core.fixtures.id"), primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("core.teams.id"), primary_key=True)
    period: Mapped[str] = mapped_column(Text, primary_key=True)
    shots_total: Mapped[int | None] = mapped_column(Integer)
    shots_on: Mapped[int | None] = mapped_column(Integer)
    shots_off: Mapped[int | None] = mapped_column(Integer)
    shots_blocked: Mapped[int | None] = mapped_column(Integer)
    shots_inside: Mapped[int | None] = mapped_column(Integer)
    shots_outside: Mapped[int | None] = mapped_column(Integer)
    corners: Mapped[int | None] = mapped_column(Integer)
    fouls: Mapped[int | None] = mapped_column(Integer)
    offsides: Mapped[int | None] = mapped_column(Integer)
    possession: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    yellow: Mapped[int | None] = mapped_column(Integer)
    red: Mapped[int | None] = mapped_column(Integer)
    gk_saves: Mapped[int | None] = mapped_column(Integer)
    passes_total: Mapped[int | None] = mapped_column(Integer)
    passes_accurate: Mapped[int | None] = mapped_column(Integer)
    xg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))


class FixtureEvent(Base):
    __tablename__ = "fixture_events"
    __table_args__ = (Index(None, "fixture_id"), Index(None, "player_id"), CORE)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("core.fixtures.id"))
    seq: Mapped[int] = mapped_column(Integer)  # order within the fixture as delivered by the API
    minute: Mapped[int | None] = mapped_column(Integer)
    extra_minute: Mapped[int | None] = mapped_column(Integer)
    team_id: Mapped[int | None] = mapped_column(Integer)
    player_id: Mapped[int | None] = mapped_column(Integer)
    player_name: Mapped[str | None] = mapped_column(Text)
    assist_player_id: Mapped[int | None] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(Text)
    detail: Mapped[str | None] = mapped_column(Text)
    comments: Mapped[str | None] = mapped_column(Text)


class FixtureLineup(Base):
    __tablename__ = "fixture_lineups"
    __table_args__ = CORE

    fixture_id: Mapped[int] = mapped_column(ForeignKey("core.fixtures.id"), primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("core.teams.id"), primary_key=True)
    formation: Mapped[str | None] = mapped_column(Text)
    coach_id: Mapped[int | None] = mapped_column(Integer)
    coach_name: Mapped[str | None] = mapped_column(Text)


class FixturePlayerStats(Base):
    __tablename__ = "fixture_player_stats"
    __table_args__ = (Index(None, "player_id"), CORE)

    fixture_id: Mapped[int] = mapped_column(ForeignKey("core.fixtures.id"), primary_key=True)
    player_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("core.teams.id"))
    is_starter: Mapped[bool | None] = mapped_column(Boolean)
    minutes: Mapped[int | None] = mapped_column(Integer)
    position: Mapped[str | None] = mapped_column(Text)
    grid: Mapped[str | None] = mapped_column(Text)
    rating: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    captain: Mapped[bool | None] = mapped_column(Boolean)
    shots_total: Mapped[int | None] = mapped_column(Integer)
    shots_on: Mapped[int | None] = mapped_column(Integer)
    goals: Mapped[int | None] = mapped_column(Integer)
    assists: Mapped[int | None] = mapped_column(Integer)
    penalties_scored: Mapped[int | None] = mapped_column(Integer)
    penalties_missed: Mapped[int | None] = mapped_column(Integer)
    penalties_won: Mapped[int | None] = mapped_column(Integer)
    key_passes: Mapped[int | None] = mapped_column(Integer)
    offsides: Mapped[int | None] = mapped_column(Integer)
    yellow: Mapped[int | None] = mapped_column(Integer)
    red: Mapped[int | None] = mapped_column(Integer)


class Injury(Base):
    __tablename__ = "injuries"
    __table_args__ = CORE

    fixture_id: Mapped[int] = mapped_column(ForeignKey("core.fixtures.id"), primary_key=True)
    player_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(Integer)
    player_name: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)


class HistoricalMatch(Base):
    """One row per match from football-data.co.uk (results, match stats, 1X2 and O/U 2.5 odds)."""

    __tablename__ = "historical_matches"
    __table_args__ = (
        UniqueConstraint("league_code", "season_code", "match_date", "home_alias", "away_alias"),
        Index(None, "fixture_id"),
        CORE,
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    league_code: Mapped[str] = mapped_column(Text)
    season_code: Mapped[str] = mapped_column(Text)
    match_date: Mapped[date] = mapped_column(Date)
    kickoff_local: Mapped[time | None] = mapped_column(Time)
    home_alias: Mapped[str] = mapped_column(Text)
    away_alias: Mapped[str] = mapped_column(Text)
    fixture_id: Mapped[int | None] = mapped_column(ForeignKey("core.fixtures.id"))
    ft_home: Mapped[int | None] = mapped_column(Integer)
    ft_away: Mapped[int | None] = mapped_column(Integer)
    ht_home: Mapped[int | None] = mapped_column(Integer)
    ht_away: Mapped[int | None] = mapped_column(Integer)
    hs: Mapped[int | None] = mapped_column(Integer)
    as_: Mapped[int | None] = mapped_column("as_", Integer)
    hst: Mapped[int | None] = mapped_column(Integer)
    ast: Mapped[int | None] = mapped_column(Integer)
    hc: Mapped[int | None] = mapped_column(Integer)
    ac: Mapped[int | None] = mapped_column(Integer)
    hf: Mapped[int | None] = mapped_column(Integer)
    af: Mapped[int | None] = mapped_column(Integer)
    hy: Mapped[int | None] = mapped_column(Integer)
    ay: Mapped[int | None] = mapped_column(Integer)
    hr: Mapped[int | None] = mapped_column(Integer)
    ar: Mapped[int | None] = mapped_column(Integer)
    hxg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    axg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    # 1X2 opening / closing
    b365_h: Mapped[Decimal | None] = mapped_column(Odd)
    b365_d: Mapped[Decimal | None] = mapped_column(Odd)
    b365_a: Mapped[Decimal | None] = mapped_column(Odd)
    ps_h: Mapped[Decimal | None] = mapped_column(Odd)
    ps_d: Mapped[Decimal | None] = mapped_column(Odd)
    ps_a: Mapped[Decimal | None] = mapped_column(Odd)
    avg_h: Mapped[Decimal | None] = mapped_column(Odd)
    avg_d: Mapped[Decimal | None] = mapped_column(Odd)
    avg_a: Mapped[Decimal | None] = mapped_column(Odd)
    max_h: Mapped[Decimal | None] = mapped_column(Odd)
    max_d: Mapped[Decimal | None] = mapped_column(Odd)
    max_a: Mapped[Decimal | None] = mapped_column(Odd)
    b365c_h: Mapped[Decimal | None] = mapped_column(Odd)
    b365c_d: Mapped[Decimal | None] = mapped_column(Odd)
    b365c_a: Mapped[Decimal | None] = mapped_column(Odd)
    psc_h: Mapped[Decimal | None] = mapped_column(Odd)
    psc_d: Mapped[Decimal | None] = mapped_column(Odd)
    psc_a: Mapped[Decimal | None] = mapped_column(Odd)
    avgc_h: Mapped[Decimal | None] = mapped_column(Odd)
    avgc_d: Mapped[Decimal | None] = mapped_column(Odd)
    avgc_a: Mapped[Decimal | None] = mapped_column(Odd)
    # Over/Under 2.5 opening / closing
    b365_o25: Mapped[Decimal | None] = mapped_column(Odd)
    b365_u25: Mapped[Decimal | None] = mapped_column(Odd)
    ps_o25: Mapped[Decimal | None] = mapped_column(Odd)
    ps_u25: Mapped[Decimal | None] = mapped_column(Odd)
    avg_o25: Mapped[Decimal | None] = mapped_column(Odd)
    avg_u25: Mapped[Decimal | None] = mapped_column(Odd)
    b365c_o25: Mapped[Decimal | None] = mapped_column(Odd)
    b365c_u25: Mapped[Decimal | None] = mapped_column(Odd)
    psc_o25: Mapped[Decimal | None] = mapped_column(Odd)
    psc_u25: Mapped[Decimal | None] = mapped_column(Odd)
    avgc_o25: Mapped[Decimal | None] = mapped_column(Odd)
    avgc_u25: Mapped[Decimal | None] = mapped_column(Odd)
    raw_row: Mapped[dict] = mapped_column(JSONB)


class OddsSnapshot(Base):
    """Own odds archive. A row is only written when an odd differs from its previous capture."""

    __tablename__ = "odds_snapshots"
    __table_args__ = (Index(None, "fixture_id", "captured_at"), CORE)

    fixture_id: Mapped[int] = mapped_column(ForeignKey("core.fixtures.id"), primary_key=True)
    bookmaker_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bet_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    selection: Mapped[str] = mapped_column(Text, primary_key=True)
    handicap: Mapped[str] = mapped_column(Text, primary_key=True, default="")
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    odd: Mapped[Decimal] = mapped_column(Odd)
    is_main: Mapped[bool | None] = mapped_column(Boolean)
    suspended: Mapped[bool | None] = mapped_column(Boolean)
    api_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# --------------------------------------------------------------------------- OddsPapi (Betano odds)


class OddsPapiFixture(Base):
    __tablename__ = "oddspapi_fixtures"
    __table_args__ = (Index(None, "tournament_id", "start_time"), Index(None, "fixture_id"), CORE)

    id: Mapped[str] = mapped_column(Text, primary_key=True)  # e.g. 'id1000003572513246'
    tournament_id: Mapped[int] = mapped_column(Integer)
    season_id: Mapped[int | None] = mapped_column(Integer)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status_id: Mapped[int | None] = mapped_column(Integer)  # 0 not started, 1 live, 2 finished, 3 cancelled
    participant1_id: Mapped[int] = mapped_column(Integer)
    participant2_id: Mapped[int] = mapped_column(Integer)
    participant1_name: Mapped[str | None] = mapped_column(Text)
    participant2_name: Mapped[str | None] = mapped_column(Text)
    fixture_id: Mapped[int | None] = mapped_column(ForeignKey("core.fixtures.id"))  # API-Football fixture
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    history_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # True once the history was loaded after kickoff (complete incl. closing odds).
    history_final: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class OddsPapiMarket(Base):
    __tablename__ = "oddspapi_markets"
    __table_args__ = CORE

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(Text)
    market_type: Mapped[str] = mapped_column(Text)
    period: Mapped[str] = mapped_column(Text)
    handicap: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    player_prop: Mapped[bool] = mapped_column(Boolean)
    market_group: Mapped[str | None] = mapped_column(Text)  # our market group, NULL = not tracked
    outcomes: Mapped[dict] = mapped_column(JSONB)  # {outcome_id: outcome_name}


class OddsPapiPlayer(Base):
    __tablename__ = "oddspapi_players"
    __table_args__ = CORE

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(Text)
    player_id: Mapped[int | None] = mapped_column(Integer)  # API-Football player (mapping in phase 3)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OddsHistory(Base):
    """Price history per selection from OddsPapi. Only changes of (price, active) are stored."""

    __tablename__ = "odds_history"
    __table_args__ = (Index(None, "oddspapi_fixture_id", "market_id"), CORE)

    oddspapi_fixture_id: Mapped[str] = mapped_column(
        ForeignKey("core.oddspapi_fixtures.id"), primary_key=True
    )
    bookmaker: Mapped[str] = mapped_column(Text, primary_key=True)  # 'betano.de', 'pinnacle'
    market_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    outcome_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 0 = no player market
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    price: Mapped[Decimal] = mapped_column(Odd)
    active: Mapped[bool] = mapped_column(Boolean)
