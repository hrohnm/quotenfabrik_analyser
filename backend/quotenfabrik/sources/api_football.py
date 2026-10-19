"""HTTP client for API-Football v3 with throttling, quota guard and retries.

The client only fetches. Persisting the raw response is done by the caller via ``on_response`` so that
every response lands in ``raw.api_responses`` before it is processed.
"""

import logging
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

import httpx

from quotenfabrik.config import Settings

log = logging.getLogger(__name__)

RETRY_STATUS = {429, 499, 500, 502, 503, 504}


class ApiFootballError(RuntimeError):
    pass


class QuotaExhausted(ApiFootballError):
    pass


@dataclass
class ApiResult:
    endpoint: str
    params: dict[str, Any]
    status_code: int
    payload: dict[str, Any]
    quota_remaining: int | None
    minute_remaining: int | None


ResponseHook = Callable[[ApiResult], None]


class ApiFootballClient:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        on_response: ResponseHook | None = None,
        transport: httpx.BaseTransport | None = None,
        max_retries: int = 4,
    ) -> None:
        if settings is None:
            from quotenfabrik.app_config import effective_settings  # reserves from the configuration page

            settings = effective_settings()
        self.settings = settings
        if not self.settings.api_football_key:
            raise ApiFootballError("API_FOOTBALL_KEY is not set")
        self._http = httpx.Client(
            base_url=self.settings.api_football_base_url,
            headers={"x-apisports-key": self.settings.api_football_key},
            timeout=30.0,
            transport=transport,
        )
        self._min_interval = 1.0 / self.settings.api_max_rps
        self._last_call = 0.0
        self._max_retries = max_retries
        self.on_response = on_response
        self.quota_remaining: int | None = None
        self.requests_made = 0

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "ApiFootballClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------ core
    def _throttle(self) -> None:
        wait = self._last_call + self._min_interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    def _guard_quota(self, use_reserve: bool) -> None:
        if self.quota_remaining is None:
            return
        floor = 0 if use_reserve else self.settings.api_quota_reserve
        if self.quota_remaining <= floor:
            raise QuotaExhausted(
                f"Daily quota guard hit: {self.quota_remaining} requests left (reserve {floor})"
            )

    def get(
        self, endpoint: str, params: dict[str, Any] | None = None, *, use_reserve: bool = False
    ) -> ApiResult:
        """GET one endpoint. ``use_reserve`` lets small, time-critical jobs (odds) dip into the reserve."""
        params = {k: v for k, v in (params or {}).items() if v is not None}
        endpoint = endpoint.strip("/")
        if endpoint != "status":
            self._guard_quota(use_reserve)

        for attempt in range(self._max_retries + 1):
            self._throttle()
            try:
                resp = self._http.get(f"/{endpoint}", params=params)
            except httpx.TransportError as exc:
                if attempt == self._max_retries:
                    raise ApiFootballError(f"{endpoint} {params}: {exc}") from exc
                time.sleep(2 ** (attempt + 1))
                continue
            if resp.status_code in RETRY_STATUS and attempt < self._max_retries:
                log.warning("API-Football %s returned %s, retrying", endpoint, resp.status_code)
                time.sleep(2 ** (attempt + 1))
                continue
            break

        self.requests_made += 1
        quota = _int_header(resp, "x-ratelimit-requests-remaining")
        if quota is not None:
            self.quota_remaining = quota
        if resp.status_code != 200:
            raise ApiFootballError(f"{endpoint} {params}: HTTP {resp.status_code} {resp.text[:200]}")

        payload = resp.json()
        result = ApiResult(
            endpoint=endpoint,
            params=params,
            status_code=resp.status_code,
            payload=payload,
            quota_remaining=quota,
            minute_remaining=_int_header(resp, "x-ratelimit-remaining"),
        )
        # API-Football reports errors with HTTP 200 and a non-empty "errors" field.
        errors = payload.get("errors")
        if errors:
            raise ApiFootballError(f"{endpoint} {params}: {errors}")
        if self.on_response:
            self.on_response(result)
        return result

    def get_all_pages(
        self, endpoint: str, params: dict[str, Any] | None = None, *, use_reserve: bool = False
    ) -> Iterator[ApiResult]:
        """Iterate over every page of a paginated endpoint (odds, players, ...)."""
        page = 1
        while True:
            result = self.get(endpoint, {**(params or {}), "page": page}, use_reserve=use_reserve)
            yield result
            paging = result.payload.get("paging") or {}
            if page >= int(paging.get("total") or 1):
                return
            page += 1

    def status(self) -> dict[str, Any]:
        """Account status; does not count against the daily quota."""
        response = self.get("status").payload["response"]
        requests = response.get("requests") or {}
        if "limit_day" in requests and "current" in requests:
            self.quota_remaining = requests["limit_day"] - requests["current"]
        return response


def _int_header(resp: httpx.Response, name: str) -> int | None:
    value = resp.headers.get(name)
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None
