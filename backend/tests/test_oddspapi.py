from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest

from quotenfabrik.config import Settings
from quotenfabrik.ingest import oddspapi_parsers as parsers
from quotenfabrik.markets import oddspapi_market_group
from quotenfabrik.sources.oddspapi import OddsPapiClient, OddsPapiError, OddsPapiQuotaExhausted
from tests.conftest import load_json

KICKOFF = datetime(2026, 10, 18, 15, 30, tzinfo=UTC)
SECRET = "secret-key-123"


# --------------------------------------------------------------------------- markets


def test_market_groups_exclude_asian_lines_and_other_markets():
    assert oddspapi_market_group("1x2", "fulltime", 0) == "1x2"
    assert oddspapi_market_group("totals", "fulltime", 2.5) == "totals"
    assert oddspapi_market_group("totals", "fulltime", 2.25) is None
    assert oddspapi_market_group("totals", "fulltime", 3.0) is None
    assert oddspapi_market_group("teamtotals-team2", "p1", 0.5) == "halves"
    assert oddspapi_market_group("spreads-european", "fulltime", 1.0) == "1x2"
    assert oddspapi_market_group("spreads", "fulltime", -0.5) is None  # Asian handicap
    assert oddspapi_market_group("totals-corners", "fulltime", 9.5) is None
    assert oddspapi_market_group("players-anytimegoalscorer", "fulltime", 0) == "scorers"


def test_parse_markets():
    rows = {r["id"]: r for r in parsers.parse_markets(load_json("oddspapi_markets.json"))}
    assert rows[101]["market_group"] == "1x2"
    assert rows[101]["outcomes"] == {"101": "1", "102": "X", "103": "2"}
    groups = {r["market_type"]: r["market_group"] for r in rows.values()}
    assert groups["totals-corners"] is None and groups["spreads"] is None
    assert groups["players-anytimegoalscorer"] == "scorers"


# --------------------------------------------------------------------------- history


def _tracked() -> set[int]:
    return {r["id"] for r in parsers.parse_markets(load_json("oddspapi_markets.json")) if r["market_group"]}


def test_parse_history_keeps_pre_match_changes_of_tracked_markets():
    payload = load_json("oddspapi_history.json")
    rows = parsers.parse_history(payload, _tracked(), before=KICKOFF)
    assert rows
    assert {r["bookmaker"] for r in rows} == {"betano.de", "pinnacle"}
    assert all(r["changed_at"] < KICKOFF for r in rows)
    assert {r["market_id"] for r in rows} <= _tracked()
    assert any(r["player_id"] != 0 for r in rows)  # scorer market
    assert all(isinstance(r["price"], Decimal) for r in rows)
    # consecutive identical (price, active) entries are collapsed
    by_selection: dict[tuple, list] = {}
    for r in rows:
        key = (r["bookmaker"], r["market_id"], r["outcome_id"], r["player_id"])
        by_selection.setdefault(key, []).append((r["changed_at"], r["price"], r["active"]))
    for entries in by_selection.values():
        entries.sort()
        for a, b in zip(entries, entries[1:], strict=False):
            assert (a[1], a[2]) != (b[1], b[2])
    keys = [(*k, t) for k, v in by_selection.items() for t, *_ in v]
    assert len(keys) == len(set(keys))


def test_parse_history_without_cutoff_includes_in_play_prices():
    payload = load_json("oddspapi_history.json")
    assert any(r["changed_at"] >= KICKOFF for r in parsers.parse_history(payload, _tracked()))


def test_parse_player_names():
    payload = [
        {
            "fixtureId": "id1",
            "bookmakerOdds": {
                "betano.de": {
                    "markets": {
                        "10730": {
                            "outcomes": {"10730": {"players": {"1065720": {"playerName": "T. Kleindienst"}}}}
                        },
                        "101": {"outcomes": {"101": {"players": {"0": {"playerName": None}}}}},
                    }
                }
            },
        }
    ]
    assert parsers.parse_player_names(payload) == {1065720: "T. Kleindienst"}


@pytest.mark.parametrize(
    ("oddspapi_name", "api_name"),
    [
        ("1. FC Cologne", "1. FC Köln"),
        ("Bayern Munich", "Bayern München"),
        ("Borussia Monchengladbach", "Borussia Mönchengladbach"),
        ("FSV Mainz", "FSV Mainz 05"),
        ("TSG Hoffenheim", "1899 Hoffenheim"),
        ("SV 07 Elversberg", "SV Elversberg"),
    ],
)
def test_name_similarity_matches_spelling_variants(oddspapi_name, api_name):
    assert parsers.name_similarity(oddspapi_name, api_name) >= 0.8


def test_name_similarity_separates_different_clubs():
    assert parsers.name_similarity("Borussia Dortmund", "Borussia Mönchengladbach") == 0
    assert parsers.name_similarity("Hamburger SV", "Werder Bremen") == 0


# --------------------------------------------------------------------------- client


def _client(handler) -> OddsPapiClient:
    settings = Settings(ODDSPAPI_API_KEY=SECRET, QF_ODDSPAPI_REQUEST_RESERVE=5)
    return OddsPapiClient(settings, transport=httpx.MockTransport(handler), max_retries=2)


def _account(used: int, limit: int = 250) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "current_subscription_id": "s1",
            "subscriptions": [
                {"subscription_id": "s1", "plan": "free", "request_count": used, "request_limit": limit}
            ],
        },
    )


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr("quotenfabrik.sources.oddspapi.time.sleep", lambda s: None)


def test_billable_requests_are_counted_and_guarded():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["apiKey"] == SECRET
        if request.url.path.endswith("/account"):
            return _account(used=243)
        return httpx.Response(200, json=[])

    client = _client(handler)
    client.get("fixtures", {"tournamentId": 35})
    assert client.requests_used == 244 and client.billable_requests_made == 1
    client.get("historical-odds", {"fixtureId": "x"})  # free
    assert client.requests_used == 244
    with pytest.raises(OddsPapiQuotaExhausted):
        client.get("fixtures", {"tournamentId": 35})  # 6 left, reserve 5 -> one more allowed
        client.get("fixtures", {"tournamentId": 35})


def test_rate_limit_is_retried_after_retry_ms():
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(429, json={"error": {"code": "RATE_LIMITED", "retryMs": 3364}})
        return httpx.Response(200, json={"fixtureId": "x", "bookmakers": {}})

    assert _client(handler).get("historical-odds", {"fixtureId": "x"}).payload["fixtureId"] == "x"
    assert len(calls) == 2


def test_rate_limit_waits_longer_than_transport_retries():
    """Another process may hold the shared cooldown: RATE_LIMITED is retried more often than max_retries."""
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) <= 6:  # max_retries is 2
            return httpx.Response(429, json={"code": "RATE_LIMITED", "retryMs": 4188})
        return httpx.Response(200, json={"fixtureId": "x", "bookmakers": {}})

    assert _client(handler).get("historical-odds", {"fixtureId": "x"}).payload["fixtureId"] == "x"
    assert len(calls) == 7

    def always_limited(request):
        return httpx.Response(429, json={"code": "RATE_LIMITED", "retryMs": 10})

    with pytest.raises(OddsPapiError, match="HTTP 429"):
        _client(always_limited).get("historical-odds", {"fixtureId": "x"})


def test_errors_never_contain_the_api_key():
    def handler(request):
        if request.url.path.endswith("/account"):
            return _account(used=0)
        return httpx.Response(400, json={"error": {"message": "bad"}})

    with pytest.raises(OddsPapiError) as exc:
        _client(handler).get("fixtures", {"tournamentId": 35})
    assert SECRET not in str(exc.value)


def test_request_limit_exceeded_raises_quota_error():
    def handler(request):
        if request.url.path.endswith("/account"):
            return _account(used=0)
        return httpx.Response(
            429, json={"message": "Request limit exceeded", "code": "REQUEST_LIMIT_EXCEEDED"}
        )

    with pytest.raises(OddsPapiQuotaExhausted):
        _client(handler).get("fixtures", {"tournamentId": 35})


def test_not_found_is_a_distinct_error():
    from quotenfabrik.sources.oddspapi import OddsPapiNotFound

    client = _client(
        lambda r: httpx.Response(404, json={"message": "No historical odds found.", "code": "NOT_FOUND"})
    )
    with pytest.raises(OddsPapiNotFound):
        client.get("historical-odds", {"fixtureId": "x"})
