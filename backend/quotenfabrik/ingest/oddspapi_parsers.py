"""Pure functions that turn OddsPapi payloads into rows (no database access)."""

import re
import unicodedata
from datetime import datetime
from decimal import Decimal
from typing import Any

from quotenfabrik.markets import oddspapi_market_group


def parse_ts(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def parse_markets(items: list[dict]) -> list[dict[str, Any]]:
    rows = []
    for m in items or []:
        handicap = m.get("handicap")
        rows.append(
            {
                "id": m["marketId"],
                "name": m.get("marketName") or "",
                "market_type": m.get("marketType") or "",
                "period": m.get("period") or "",
                "handicap": Decimal(str(handicap)) if handicap is not None else None,
                "player_prop": bool(m.get("playerProp")),
                "market_group": oddspapi_market_group(
                    m.get("marketType") or "", m.get("period") or "", handicap
                ),
                "outcomes": {str(o["outcomeId"]): o.get("outcomeName") for o in m.get("outcomes") or []},
            }
        )
    return rows


def parse_fixtures(items: list[dict], now: datetime) -> list[dict[str, Any]]:
    return [
        {
            "id": f["fixtureId"],
            "tournament_id": f["tournamentId"],
            "season_id": f.get("seasonId"),
            "start_time": parse_ts(f["startTime"]),
            "status_id": f.get("statusId"),
            "participant1_id": f["participant1Id"],
            "participant2_id": f["participant2Id"],
            "participant1_name": f.get("participant1Name"),
            "participant2_name": f.get("participant2Name"),
            "updated_at": now,
        }
        for f in items or []
    ]


def parse_history(
    payload: dict[str, Any], tracked_markets: set[int], before: datetime | None = None
) -> list[dict[str, Any]]:
    """Flattens a /historical-odds payload into odds_history rows.

    Keeps only tracked markets and only entries where (price, active) changed against the previous entry
    of the same selection. ``before`` drops entries at or after that time (e.g. in-play prices).
    """
    fixture_id = payload["fixtureId"]
    rows: list[dict[str, Any]] = []
    for bookmaker, bk in (payload.get("bookmakers") or {}).items():
        for market_id, market in (bk.get("markets") or {}).items():
            if int(market_id) not in tracked_markets:
                continue
            for outcome_id, outcome in (market.get("outcomes") or {}).items():
                for player_id, entries in (outcome.get("players") or {}).items():
                    previous = None
                    seen: set[datetime] = set()
                    for entry in sorted(entries or [], key=lambda e: e["createdAt"]):
                        changed_at = parse_ts(entry["createdAt"])
                        if before is not None and changed_at >= before:
                            break
                        if entry.get("price") is None:
                            continue
                        key = (entry["price"], bool(entry.get("active")))
                        if key == previous or changed_at in seen:
                            continue
                        previous = key
                        seen.add(changed_at)
                        rows.append(
                            {
                                "oddspapi_fixture_id": fixture_id,
                                "bookmaker": bookmaker,
                                "market_id": int(market_id),
                                "outcome_id": int(outcome_id),
                                "player_id": int(player_id),
                                "changed_at": changed_at,
                                "price": Decimal(str(entry["price"])),
                                "active": bool(entry.get("active")),
                            }
                        )
    return rows


def parse_player_names(items: list[dict]) -> dict[int, str]:
    """Player id -> name from /odds or /odds-by-tournaments payloads (player markets carry names)."""
    names: dict[int, str] = {}
    for fixture in items or []:
        for bk in (fixture.get("bookmakerOdds") or {}).values():
            for market in (bk.get("markets") or {}).values():
                for outcome in (market.get("outcomes") or {}).values():
                    for player_id, entry in (outcome.get("players") or {}).items():
                        name = (entry or {}).get("playerName")
                        if name and player_id != "0":
                            names[int(player_id)] = name
    return names


# --------------------------------------------------------------------------- team name matching

_GENERIC_TOKENS = {
    "fc", "sv", "sc", "vfb", "vfl", "tsg", "bv", "fsv", "1", "04", "05", "07", "09", "1899", "1846",
    "1848", "1860", "96", "98", "e", "v", "ev", "club", "borussia", "rb", "bayer",
}  # fmt: skip
_SYNONYMS = {"cologne": "koln", "munich": "munchen", "nuremberg": "nurnberg", "monchengladbach": "gladbach"}


def name_tokens(name: str | None) -> set[str]:
    if not name:
        return set()
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    ascii_name = ascii_name.replace("'", "")
    tokens = {_SYNONYMS.get(t, t) for t in re.split(r"[^a-z0-9]+", ascii_name) if t}
    specific = tokens - _GENERIC_TOKENS
    return specific or tokens


def name_similarity(a: str | None, b: str | None) -> float:
    ta, tb = name_tokens(a), name_tokens(b)
    if not ta or not tb:
        return 0.0
    exact = len(ta & tb)
    prefix = sum(1 for x in ta - tb if any(y.startswith(x) or x.startswith(y) for y in tb - ta))
    return (exact + 0.8 * prefix) / max(len(ta), len(tb))
