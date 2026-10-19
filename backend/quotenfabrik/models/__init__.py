"""SQLAlchemy models. Importing this package registers all tables on ``Base.metadata``."""

from quotenfabrik.models.base import Base
from quotenfabrik.models.core import (
    BetType,
    Bookmaker,
    Fixture,
    FixtureEvent,
    FixtureLineup,
    FixturePlayerStats,
    FixtureTeamStats,
    HistoricalMatch,
    Injury,
    League,
    OddsSnapshot,
    Player,
    Team,
    TeamAlias,
    Venue,
)
from quotenfabrik.models.raw import ApiResponse, FootballDataFile

__all__ = [
    "ApiResponse",
    "Base",
    "BetType",
    "Bookmaker",
    "Fixture",
    "FixtureEvent",
    "FixtureLineup",
    "FixturePlayerStats",
    "FixtureTeamStats",
    "FootballDataFile",
    "HistoricalMatch",
    "Injury",
    "League",
    "OddsSnapshot",
    "Player",
    "Team",
    "TeamAlias",
    "Venue",
]
