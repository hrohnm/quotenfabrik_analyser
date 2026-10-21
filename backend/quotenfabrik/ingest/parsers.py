"""Pure functions that turn API-Football payload items into rows for the ``core`` tables.

No database access here, so the parsing rules can be unit-tested against stored sample responses.
"""

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from quotenfabrik.markets import is_tracked_selection

FINISHED_STATUSES = {"FT", "AET", "PEN", "AWD", "WO"}

TEAM_STAT_TYPES: dict[str, str] = {
    "Shots on Goal": "shots_on",
    "Shots off Goal": "shots_off",
    "Total Shots": "shots_total",
    "Blocked Shots": "shots_blocked",
    "Shots insidebox": "shots_inside",
    "Shots outsidebox": "shots_outside",
    "Fouls": "fouls",
    "Corner Kicks": "corners",
    "Offsides": "offsides",
    "Ball Possession": "possession",
    "Yellow Cards": "yellow",
    "Red Cards": "red",
    "Goalkeeper Saves": "gk_saves",
    "Total passes": "passes_total",
    "Passes accurate": "passes_accurate",
    "expected_goals": "xg",
}
_DECIMAL_STATS = {"possession", "xg"}
_MATCHDAY_RE = re.compile(r"(\d+)\s*$")


def parse_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def matchday_from_round(round_name: str | None) -> int | None:
    if not round_name or not round_name.startswith("Regular Season"):
        return None
    match = _MATCHDAY_RE.search(round_name)
    return int(match.group(1)) if match else None


def parse_fixture(item: dict[str, Any], now: datetime) -> dict[str, Any]:
    """Returns {'league', 'teams', 'venue', 'fixture'} row dicts for one /fixtures response item."""
    fx, league, teams = item["fixture"], item["league"], item["teams"]
    score = item.get("score") or {}
    venue = fx.get("venue") or {}
    ht = score.get("halftime") or {}
    ft = score.get("fulltime") or {}
    goals = item.get("goals") or {}
    status = fx["status"]["short"]
    finished = status in FINISHED_STATUSES
    return {
        "league": {"id": league["id"], "name": league["name"], "country": league.get("country")},
        "teams": [
            {"id": t["id"], "name": t["name"], "logo_url": t.get("logo")}
            for t in (teams["home"], teams["away"])
        ],
        "venue": (
            {"id": venue["id"], "name": venue.get("name"), "city": venue.get("city")}
            if venue.get("id")
            else None
        ),
        "fixture": {
            "id": fx["id"],
            "league_id": league["id"],
            "season": league["season"],
            "round": league.get("round"),
            "matchday": matchday_from_round(league.get("round")),
            "kickoff_utc": parse_datetime(fx["date"]),
            "status": status,
            "venue_id": venue.get("id") or None,  # the API sometimes sends id 0 for unknown venues
            "referee": fx.get("referee"),
            "home_team_id": teams["home"]["id"],
            "away_team_id": teams["away"]["id"],
            # 'fulltime' is only set after the match; 'goals' is the live score.
            "ft_home": ft.get("home") if finished else goals.get("home"),
            "ft_away": ft.get("away") if finished else goals.get("away"),
            "ht_home": ht.get("home"),
            "ht_away": ht.get("away"),
            "updated_at": now,
        },
    }


def to_decimal(value: Any) -> Decimal | None:
    """Lenient decimal conversion: '1.23', '55%', 7.1 -> Decimal; '-', '–', '' and None -> None."""
    if value is None:
        return None
    try:
        number = Decimal(str(value).strip().rstrip("%"))
    except InvalidOperation:
        return None
    return number if number.is_finite() else None


def _stat_value(column: str, value: Any) -> Any:
    if value is None:
        return None
    if column in _DECIMAL_STATS:
        return to_decimal(value)
    if isinstance(value, str):
        value = value.rstrip("%")
        return int(value) if value.isdigit() else None
    return int(value)


def parse_team_stats(fixture_id: int, team_id: int, period: str, stats: list[dict]) -> dict[str, Any]:
    row: dict[str, Any] = {"fixture_id": fixture_id, "team_id": team_id, "period": period}
    row.update(dict.fromkeys(TEAM_STAT_TYPES.values()))
    for entry in stats or []:
        column = TEAM_STAT_TYPES.get(entry.get("type"))
        if column:
            row[column] = _stat_value(column, entry.get("value"))
    return row


def parse_statistics_block(fixture_id: int, block: list[dict]) -> list[dict[str, Any]]:
    """Parses a statistics list (from /fixtures?ids or /fixtures/statistics?half=true)."""
    rows = []
    for team_block in block or []:
        team_id = team_block["team"]["id"]
        for key, period in (("statistics", "FT"), ("statistics_1h", "1H"), ("statistics_2h", "2H")):
            if team_block.get(key):
                rows.append(parse_team_stats(fixture_id, team_id, period, team_block[key]))
    return rows


def parse_events(fixture_id: int, events: list[dict]) -> list[dict[str, Any]]:
    rows = []
    for seq, ev in enumerate(events or []):
        player = ev.get("player") or {}
        assist = ev.get("assist") or {}
        rows.append(
            {
                "fixture_id": fixture_id,
                "seq": seq,
                "minute": (ev.get("time") or {}).get("elapsed"),
                "extra_minute": (ev.get("time") or {}).get("extra"),
                "team_id": (ev.get("team") or {}).get("id"),
                "player_id": player.get("id"),
                "player_name": player.get("name"),
                "assist_player_id": assist.get("id"),
                "type": ev.get("type") or "",
                "detail": ev.get("detail"),
                "comments": ev.get("comments"),
            }
        )
    return rows


def detail_teams(item: dict[str, Any]) -> list[dict[str, Any]]:
    """Teams referenced in the details of a fixture (events, line-ups, statistics, players).

    Usually the two teams of the fixture, but the API occasionally sends another team ID there (seen in old
    European cup fixtures); those teams must exist before the detail rows reference them."""
    teams = {}
    blocks = [e.get("team") for e in item.get("events") or []]
    for key in ("lineups", "statistics", "players"):
        blocks += [b.get("team") for b in item.get(key) or []]
    for t in blocks:
        if t and t.get("id"):
            teams[t["id"]] = {
                "id": t["id"],
                "name": t.get("name") or f"Team {t['id']}",
                "logo_url": t.get("logo"),
            }
    return list(teams.values())


def parse_lineups(fixture_id: int, lineups: list[dict]) -> tuple[list[dict], dict[int, str | None]]:
    """Returns lineup rows and a player_id -> grid position map (grid may be None) for the starting XI."""
    rows, grids = [], {}
    for lineup in lineups or []:
        coach = lineup.get("coach") or {}
        rows.append(
            {
                "fixture_id": fixture_id,
                "team_id": lineup["team"]["id"],
                "formation": lineup.get("formation"),
                "coach_id": coach.get("id"),
                "coach_name": coach.get("name"),
                "colors": colors if isinstance(colors := lineup["team"].get("colors"), dict) else None,
            }
        )
        for entry in lineup.get("startXI") or []:
            player = entry.get("player") or {}
            if player.get("id"):
                grids[player["id"]] = player.get("grid")
    return rows, grids


def parse_lineup_players(fixture_id: int, lineups: list[dict]) -> list[dict]:
    """Starting XI (``sort`` 1–11, with grid) and bench (``sort`` from 101) of both teams."""
    rows = {}
    for lineup in lineups or []:
        team_id = lineup["team"]["id"]
        for starter, key, offset in ((True, "startXI", 0), (False, "substitutes", 100)):
            for i, entry in enumerate(lineup.get(key) or [], start=1):
                player = entry.get("player") or {}
                if not player.get("id") or player["id"] in rows:
                    continue
                rows[player["id"]] = {
                    "fixture_id": fixture_id,
                    "player_id": player["id"],
                    "team_id": team_id,
                    "player_name": player.get("name"),
                    "number": player.get("number"),
                    "pos": player.get("pos"),
                    "grid": player.get("grid") if starter else None,
                    "is_starter": starter,
                    "sort": offset + i,
                }
    return list(rows.values())


def parse_player_stats(
    fixture_id: int, teams: list[dict], starting_xi: dict[int, str | None] | None = None
) -> tuple[list[dict], list[dict]]:
    """Returns (players rows, fixture_player_stats rows).

    ``starting_xi`` (from ``parse_lineups``) decides ``is_starter``; the API's ``games.substitute`` flag is
    not reliable (always false in sampled data). Without lineups ``is_starter`` stays None.
    """
    starting_xi = starting_xi or {}
    players, stats = {}, {}
    for team_block in teams or []:
        team_id = team_block["team"]["id"]
        for entry in team_block.get("players") or []:
            player = entry["player"]
            if not player.get("id"):
                continue
            players[player["id"]] = {"id": player["id"], "name": player.get("name") or ""}
            s = (entry.get("statistics") or [{}])[0]
            games, shots, goals = s.get("games") or {}, s.get("shots") or {}, s.get("goals") or {}
            passes, cards, pen = s.get("passes") or {}, s.get("cards") or {}, s.get("penalty") or {}
            stats[player["id"]] = {
                "fixture_id": fixture_id,
                "player_id": player["id"],
                "team_id": team_id,
                "is_starter": (player["id"] in starting_xi) if starting_xi else None,
                "minutes": games.get("minutes"),
                "position": games.get("position"),
                "grid": starting_xi.get(player["id"]),
                "rating": to_decimal(games.get("rating")),
                "captain": games.get("captain"),
                "shots_total": shots.get("total"),
                "shots_on": shots.get("on"),
                "goals": goals.get("total"),
                "assists": goals.get("assists"),
                "penalties_scored": pen.get("scored"),
                "penalties_missed": pen.get("missed"),
                "penalties_won": pen.get("won"),
                "key_passes": passes.get("key"),
                "offsides": s.get("offsides"),
                "yellow": cards.get("yellow"),
                "red": cards.get("red"),
            }
    return list(players.values()), list(stats.values())


def parse_injuries(items: list[dict]) -> list[dict[str, Any]]:
    rows = {}
    for item in items or []:
        player = item.get("player") or {}
        fixture = item.get("fixture") or {}
        if not player.get("id") or not fixture.get("id"):
            continue
        rows[(fixture["id"], player["id"])] = {
            "fixture_id": fixture["id"],
            "player_id": player["id"],
            "team_id": (item.get("team") or {}).get("id"),
            "player_name": player.get("name"),
            "type": player.get("type"),
            "reason": player.get("reason"),
        }
    return list(rows.values())


def parse_odds(
    items: list[dict], captured_at: datetime, bookmakers: set[int] | None = None
) -> list[dict[str, Any]]:
    """Flattens /odds items into odds rows, keeping only tracked markets and bookmakers."""
    rows: dict[tuple, dict[str, Any]] = {}
    for item in items or []:
        fixture_id = item["fixture"]["id"]
        api_updated = parse_datetime(item.get("update"))
        for bookmaker in item.get("bookmakers") or []:
            if bookmakers is not None and bookmaker["id"] not in bookmakers:
                continue
            for bet in bookmaker.get("bets") or []:
                for value in bet.get("values") or []:
                    selection = str(value.get("value"))
                    handicap = "" if value.get("handicap") is None else str(value["handicap"])
                    if not is_tracked_selection(bet["id"], selection, handicap or None):
                        continue
                    try:
                        odd = Decimal(str(value["odd"]))
                    except (InvalidOperation, KeyError):
                        continue
                    key = (fixture_id, bookmaker["id"], bet["id"], selection, handicap)
                    rows[key] = {
                        "fixture_id": fixture_id,
                        "bookmaker_id": bookmaker["id"],
                        "bet_id": bet["id"],
                        "selection": selection,
                        "handicap": handicap,
                        "captured_at": captured_at,
                        "odd": odd,
                        "is_main": value.get("main"),
                        "suspended": value.get("suspended"),
                        "api_updated_at": api_updated,
                    }
    return list(rows.values())
