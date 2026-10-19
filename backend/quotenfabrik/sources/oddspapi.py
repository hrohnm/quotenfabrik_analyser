"""HTTP client for OddsPapi v4 (source for Betano odds).

Quota rules (free plan): 250 billable requests per month. ``/historical-odds`` and ``/account`` are free;
``/historical-odds`` has a 5 s cooldown per call. The API key is sent as query parameter and must never
appear in logs or exception messages.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

from quotenfabrik.config import Settings

log = logging.getLogger(__name__)

FREE_ENDPOINTS = {"historical-odds", "account"}
COOLDOWN_S = {"historical-odds": 5.2}
DEFAULT_INTERVAL_S = 1.0


class OddsPapiError(RuntimeError):
    pass


class OddsPapiQuotaExhausted(OddsPapiError):
    pass


class OddsPapiNotFound(OddsPapiError):
    pass


@dataclass
class OddsPapiResult:
    endpoint: str
    params: dict[str, Any]  # without the API key
    status_code: int
    payload: Any
    content: bytes  # raw response body


ResponseHook = Callable[[OddsPapiResult], None]


class OddsPapiClient:
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
        if not self.settings.oddspapi_api_key:
            raise OddsPapiError("ODDSPAPI_API_KEY is not set")
        self._http = httpx.Client(
            base_url=self.settings.oddspapi_base_url, timeout=120.0, transport=transport
        )
        self._last_call: dict[str, float] = {}
        self._max_retries = max_retries
        self.on_response = on_response
        self.requests_used: int | None = None
        self.request_limit: int | None = None
        self.billable_requests_made = 0

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "OddsPapiClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @property
    def requests_remaining(self) -> int | None:
        if self.requests_used is None or self.request_limit is None:
            return None
        return self.request_limit - self.requests_used

    def _throttle(self, endpoint: str) -> None:
        interval = COOLDOWN_S.get(endpoint, DEFAULT_INTERVAL_S)
        wait = self._last_call.get(endpoint, 0.0) + interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last_call[endpoint] = time.monotonic()

    def _guard_quota(self, endpoint: str) -> None:
        if endpoint in FREE_ENDPOINTS:
            return
        if self.requests_remaining is None:
            self.account()
        remaining = self.requests_remaining
        if remaining is not None and remaining <= self.settings.oddspapi_request_reserve:
            raise OddsPapiQuotaExhausted(
                f"OddsPapi monthly quota guard: {remaining} requests left "
                f"(reserve {self.settings.oddspapi_request_reserve})"
            )

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> OddsPapiResult:
        endpoint = endpoint.strip("/")
        params = {k: v for k, v in (params or {}).items() if v is not None}
        self._guard_quota(endpoint)
        for attempt in range(self._max_retries + 1):
            self._throttle(endpoint)
            try:
                resp = self._http.get(
                    f"/{endpoint}", params={**params, "apiKey": self.settings.oddspapi_api_key}
                )
            except httpx.TransportError as exc:
                if attempt == self._max_retries:
                    raise OddsPapiError(f"{endpoint} {params}: {type(exc).__name__}") from None
                time.sleep(2 ** (attempt + 1))
                continue
            if resp.status_code == 429:
                error = _error(resp)
                if error.get("code") == "REQUEST_LIMIT_EXCEEDED":
                    raise OddsPapiQuotaExhausted(f"OddsPapi request limit exceeded ({endpoint})")
                if attempt < self._max_retries:
                    wait_ms = error.get("retryMs") or 5000
                    log.info("OddsPapi %s rate limited, waiting %.1fs", endpoint, wait_ms / 1000)
                    time.sleep(wait_ms / 1000 + 0.2)
                    continue
            elif resp.status_code >= 500 and attempt < self._max_retries:
                time.sleep(2 ** (attempt + 1))
                continue
            break

        if endpoint not in FREE_ENDPOINTS:
            self.billable_requests_made += 1
            if self.requests_used is not None:
                self.requests_used += 1
        if resp.status_code == 404:
            raise OddsPapiNotFound(f"{endpoint} {params}: {_error(resp).get('message', 'not found')}")
        if resp.status_code != 200:
            raise OddsPapiError(f"{endpoint} {params}: HTTP {resp.status_code} {_error(resp)}")
        result = OddsPapiResult(
            endpoint=endpoint,
            params=params,
            status_code=resp.status_code,
            payload=resp.json(),
            content=resp.content,
        )
        if self.on_response and endpoint != "account":
            self.on_response(result)
        return result

    def account(self) -> dict[str, Any]:
        """Subscription and usage (free, never blocked). Updates the quota counters."""
        payload = self.get("account").payload
        subscriptions = payload.get("subscriptions") or []
        current = next(
            (s for s in subscriptions if s.get("subscription_id") == payload.get("current_subscription_id")),
            subscriptions[0] if subscriptions else {},
        )
        self.requests_used = current.get("request_count")
        self.request_limit = current.get("request_limit")
        return {
            "plan": current.get("plan"),
            "request_count": self.requests_used,
            "request_limit": self.request_limit,
            "valid_until": current.get("valid_until"),
            "bookmakers": sorted((current.get("bookmakers") or {}).keys()),
        }


def _error(resp: httpx.Response) -> dict[str, Any]:
    try:
        body = resp.json()
    except ValueError:
        return {}
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict):
        return error
    return body if isinstance(body, dict) else {}
