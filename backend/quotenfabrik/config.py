"""Application settings, read from environment variables (and an optional .env file)."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[2]

CsvInts = Annotated[list[int], NoDecode]
CsvStrs = Annotated[list[str], NoDecode]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_REPO_ROOT / ".env", _REPO_ROOT / "backend" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    api_football_key: str = Field(default="", alias="API_FOOTBALL_KEY")
    api_football_base_url: str = Field(
        default="https://v3.football.api-sports.io", alias="API_FOOTBALL_BASE_URL"
    )
    database_url: str = Field(
        default="postgresql+psycopg://qf:qf@localhost:5432/quotenfabrik", alias="DATABASE_URL"
    )

    # Leagues in scope: API-Football ids and the matching football-data.co.uk codes (same order).
    leagues: CsvInts = Field(default=[78], alias="QF_LEAGUES")
    fd_leagues: CsvStrs = Field(default=["D1"], alias="QF_FD_LEAGUES")

    # API-Football throttling: Pro plan allows 300 req/min; stay far below to avoid firewall blocks.
    api_max_rps: float = Field(default=4.0, alias="QF_API_MAX_RPS")
    # Daily requests that bulk jobs never touch (kept free for odds snapshots etc.).
    api_quota_reserve: int = Field(default=500, alias="QF_API_QUOTA_RESERVE")

    # Archived bookmakers: Betano (target), Pinnacle (reference), Bet365 (fallback for missing markets).
    odds_bookmakers: CsvInts = Field(default=[32, 4, 8], alias="QF_ODDS_BOOKMAKERS")

    # OddsPapi: source for Betano odds. Free plan = 250 billable requests per month.
    oddspapi_api_key: str = Field(
        default="", validation_alias=AliasChoices("ODDSPAPI_API_KEY", "API_OddsPap")
    )
    oddspapi_base_url: str = Field(default="https://api.oddspapi.io/v4", alias="ODDSPAPI_BASE_URL")
    # OddsPapi tournament ids, same order as ``leagues`` (35 = Bundesliga).
    oddspapi_tournaments: CsvInts = Field(default=[35], alias="QF_ODDSPAPI_TOURNAMENTS")
    # Bookmaker slugs for odds history (max 3 per request): Betano DE (target) and Pinnacle (reference).
    oddspapi_bookmakers: CsvStrs = Field(default=["betano.de", "pinnacle"], alias="QF_ODDSPAPI_BOOKMAKERS")
    # Billable requests per month that are never used (left for manual checks).
    oddspapi_request_reserve: int = Field(default=20, alias="QF_ODDSPAPI_REQUEST_RESERVE")

    @field_validator("leagues", "odds_bookmakers", "oddspapi_tournaments", mode="before")
    @classmethod
    def _split_ints(cls, value: object) -> object:
        if isinstance(value, str):
            return [int(v) for v in value.split(",") if v.strip()]
        return value

    @field_validator("fd_leagues", "oddspapi_bookmakers", mode="before")
    @classmethod
    def _split_strs(cls, value: object) -> object:
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        return value

    def fd_code_for(self, league_id: int) -> str:
        return dict(zip(self.leagues, self.fd_leagues, strict=True))[league_id]

    def oddspapi_tournament_for(self, league_id: int) -> int:
        return dict(zip(self.leagues, self.oddspapi_tournaments, strict=True))[league_id]


@lru_cache
def get_settings() -> Settings:
    return Settings()
