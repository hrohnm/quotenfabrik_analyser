import httpx
import pytest

from quotenfabrik.config import Settings
from quotenfabrik.sources.api_football import ApiFootballClient, ApiFootballError, QuotaExhausted


def _settings(**kw) -> Settings:
    return Settings(API_FOOTBALL_KEY="test", QF_API_MAX_RPS=1000, QF_API_QUOTA_RESERVE=10, **kw)


def _client(handler, saved=None) -> ApiFootballClient:
    return ApiFootballClient(
        _settings(),
        transport=httpx.MockTransport(handler),
        on_response=(saved.append if saved is not None else None),
        max_retries=1,
    )


def test_sends_key_and_stores_response():
    saved = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-apisports-key"] == "test"
        assert request.url.params["league"] == "78"
        return httpx.Response(
            200,
            json={"errors": [], "response": [1], "paging": {"current": 1, "total": 1}},
            headers={"x-ratelimit-requests-remaining": "7000"},
        )

    client = _client(handler, saved)
    result = client.get("fixtures", {"league": 78, "season": None})
    assert result.params == {"league": 78}
    assert client.quota_remaining == 7000
    assert len(saved) == 1 and saved[0].endpoint == "fixtures"


def test_errors_in_200_response_raise():
    client = _client(lambda r: httpx.Response(200, json={"errors": {"token": "invalid"}, "response": []}))
    with pytest.raises(ApiFootballError):
        client.get("fixtures")


def test_quota_guard_stops_bulk_but_not_reserve_jobs():
    def handler(request):
        return httpx.Response(
            200, json={"errors": [], "response": []}, headers={"x-ratelimit-requests-remaining": "5"}
        )

    client = _client(handler)
    client.get("fixtures")
    with pytest.raises(QuotaExhausted):
        client.get("fixtures")
    client.get("odds", use_reserve=True)


def test_pagination():
    def handler(request):
        page = int(request.url.params["page"])
        return httpx.Response(
            200, json={"errors": [], "response": [page], "paging": {"current": page, "total": 3}}
        )

    pages = [r.payload["response"][0] for r in _client(handler).get_all_pages("odds", {"league": 78})]
    assert pages == [1, 2, 3]


def test_retries_server_errors(monkeypatch):
    monkeypatch.setattr("quotenfabrik.sources.api_football.time.sleep", lambda s: None)
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(500)
        return httpx.Response(200, json={"errors": [], "response": []})

    _client(handler).get("fixtures")
    assert len(calls) == 2
