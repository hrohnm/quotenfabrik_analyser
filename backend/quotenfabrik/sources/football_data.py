"""Download and normalize football-data.co.uk season CSVs."""

import csv
import io
import math
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

BASE_URL = "https://www.football-data.co.uk/mmz4281"

# Normalized column -> candidate source columns (first non-empty wins). Column names changed over the years.
ODDS_COLUMNS: dict[str, tuple[str, ...]] = {
    "b365_h": ("B365H",), "b365_d": ("B365D",), "b365_a": ("B365A",),
    "ps_h": ("PSH", "PH"), "ps_d": ("PSD", "PD"), "ps_a": ("PSA", "PA"),
    "avg_h": ("AvgH", "BbAvH"), "avg_d": ("AvgD", "BbAvD"), "avg_a": ("AvgA", "BbAvA"),
    "max_h": ("MaxH", "BbMxH"), "max_d": ("MaxD", "BbMxD"), "max_a": ("MaxA", "BbMxA"),
    "b365c_h": ("B365CH",), "b365c_d": ("B365CD",), "b365c_a": ("B365CA",),
    "psc_h": ("PSCH",), "psc_d": ("PSCD",), "psc_a": ("PSCA",),
    "avgc_h": ("AvgCH",), "avgc_d": ("AvgCD",), "avgc_a": ("AvgCA",),
    "b365_o25": ("B365>2.5",), "b365_u25": ("B365<2.5",),
    "ps_o25": ("P>2.5",), "ps_u25": ("P<2.5",),
    "avg_o25": ("Avg>2.5", "BbAv>2.5"), "avg_u25": ("Avg<2.5", "BbAv<2.5"),
    "b365c_o25": ("B365C>2.5",), "b365c_u25": ("B365C<2.5",),
    "psc_o25": ("PC>2.5",), "psc_u25": ("PC<2.5",),
    "avgc_o25": ("AvgC>2.5",), "avgc_u25": ("AvgC<2.5",),
}  # fmt: skip

INT_COLUMNS: dict[str, str] = {
    "ft_home": "FTHG", "ft_away": "FTAG", "ht_home": "HTHG", "ht_away": "HTAG",
    "hs": "HS", "as_": "AS", "hst": "HST", "ast": "AST", "hc": "HC", "ac": "AC",
    "hf": "HF", "af": "AF", "hy": "HY", "ay": "AY", "hr": "HR", "ar": "AR",
}  # fmt: skip

DECIMAL_COLUMNS: dict[str, str] = {"hxg": "HxG", "axg": "AxG"}


@dataclass
class FootballDataRow:
    values: dict[str, Any]  # normalized columns of core.historical_matches
    raw: dict[str, str]


def season_code(season_start_year: int) -> str:
    """2025 -> '2526' (season 2025/26)."""
    return f"{season_start_year % 100:02d}{(season_start_year + 1) % 100:02d}"


def season_url(season_start_year: int, league_code: str) -> str:
    return f"{BASE_URL}/{season_code(season_start_year)}/{league_code}.csv"


def download(season_start_year: int, league_code: str, client: httpx.Client | None = None) -> bytes:
    own = client is None
    client = client or httpx.Client(timeout=60.0, follow_redirects=True)
    try:
        resp = client.get(season_url(season_start_year, league_code))
        resp.raise_for_status()
        return resp.content
    finally:
        if own:
            client.close()


def parse(content: bytes, league_code: str, season: str) -> list[FootballDataRow]:
    text = content.decode("utf-8-sig", errors="replace")
    rows: list[FootballDataRow] = []
    for raw in csv.DictReader(io.StringIO(text)):
        raw = {k.strip(): (v or "").strip() for k, v in raw.items() if k}
        if not raw.get("HomeTeam") or not raw.get("Date"):
            continue  # trailing empty lines
        values: dict[str, Any] = {
            "league_code": league_code,
            "season_code": season,
            "match_date": _parse_date(raw["Date"]),
            "kickoff_local": _parse_time(raw.get("Time", "")),
            "home_alias": raw["HomeTeam"],
            "away_alias": raw["AwayTeam"],
        }
        for col, src in INT_COLUMNS.items():
            values[col] = _to_int(raw.get(src))
        for col, src in DECIMAL_COLUMNS.items():
            values[col] = _to_decimal(raw.get(src))
        for col, sources in ODDS_COLUMNS.items():
            values[col] = next((d for s in sources if (d := _to_decimal(raw.get(s))) is not None), None)
        rows.append(FootballDataRow(values=values, raw=raw))
    return rows


def _parse_date(value: str) -> date:
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unknown date format: {value!r}")


def _parse_time(value: str) -> time | None:
    try:
        return datetime.strptime(value, "%H:%M").time() if value else None
    except ValueError:
        return None


def _to_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def _to_decimal(value: str | None) -> Decimal | None:
    if not value:
        return None
    try:
        number = Decimal(value)
    except InvalidOperation:
        return None
    return number if math.isfinite(number) else None
