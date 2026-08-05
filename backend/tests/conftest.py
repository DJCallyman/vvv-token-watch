"""Shared pytest fixtures for backend tests.

Currently provides:
  * ``mock_httpx_client`` — a fake ``httpx.AsyncClient``-shaped object whose
    ``get`` method can be programmed with a queue of (url-condition, response)
    tuples. Used by the billing-pagination tests to simulate cursor walks,
    410/403/404 fallbacks, and max-pages caps without hitting the network.

Note: ``VeniceAPIClient`` in this repo issues ``await client.get(...)`` against
a lazily-initialized ``httpx.AsyncClient`` (added in Phase 3.5). To support
unit tests without monkeypatching the connection pool, the helper exposes a
``FakeVeniceAPIClient`` that the billing tests import directly.
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock

import pytest


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj)


# ---------------------------------------------------------------------------
# Fake httpx-shaped responses for pagination tests
# ---------------------------------------------------------------------------


class FakeResponse:
    """Minimal httpx.Response replacement carrying only what the helpers need."""

    def __init__(
        self,
        *,
        status_code: int = 200,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        text: Optional[str] = None,
    ):
        self.status_code = status_code
        self._json = json_data if json_data is not None else (None if text else {})
        self.headers = headers or {}
        self._text = text
        self.request = MagicMock()

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self) -> Dict[str, Any]:
        if self._json is not None:
            return self._json
        return {}

    def raise_for_status(self) -> None:
        if 400 <= self.status_code < 600:
            import httpx
            request = httpx.Request("GET", "https://example")
            # Build a real httpx.Response carrying JSON-encoded body so
            # callers using e.response.json() can read it for error parsing.
            response_body = self._text if self._text is not None else (
                _json_dumps(self._json) if self._json is not None else ""
            )
            response = httpx.Response(
                self.status_code,
                request=request,
                content=response_body.encode("utf-8") if response_body else b"",
            )
            raise httpx.HTTPStatusError(
                f"{self.status_code}",
                request=request,
                response=response,
            )


# ---------------------------------------------------------------------------
# Programmable async client for billing-pagination tests
# ---------------------------------------------------------------------------


class FakeVeniceAPIClient:
    """Stand-in for ``VeniceAPIClient`` covering GET/POST/PATCH/DELETE.

    Tests program ``responses`` with a list of ``FakeResponse`` instances
    keyed by a URL substring. Routes consume responses in order from the
    matching queue; once a queue is exhausted, the client asserts so tests
    cannot silently diverge.
    """

    def __init__(self) -> None:
        # url_substring -> list of FakeResponse
        self._responses: Dict[str, List[FakeResponse]] = {}
        # method + url_substring -> last observed payload/params
        self.calls: List[Tuple[str, str, Optional[Dict], Optional[Dict]]] = []

    def queue(self, url_substring: str, responses: List[FakeResponse]) -> None:
        self._responses.setdefault(url_substring, []).extend(responses)

    def _pop(self, method: str, endpoint: str) -> FakeResponse:
        target = None
        for key in self._responses:
            if key in endpoint:
                target = key
                break
        assert target is not None, f"No queued response for {method} {endpoint}"
        queue = self._responses[target]
        assert queue, f"Exhausted queue for {method} {target}"
        return queue.pop(0)

    async def get(self, endpoint: str, params: Optional[Dict] = None) -> FakeResponse:
        self.calls.append(("GET", endpoint, params, None))
        return self._pop("GET", endpoint)

    async def get_json(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        timeout: float = 30.0,
        raise_for_status: bool = True,
    ):
        self.calls.append(("GET_JSON", endpoint, params, None))
        resp = self._pop("GET", endpoint)
        if raise_for_status and resp.status_code >= 400:
            resp.raise_for_status()
        return resp.json()

    async def post_json(
        self,
        endpoint: str,
        data: Optional[Dict] = None,
        timeout: float = 30.0,
    ):
        self.calls.append(("POST_JSON", endpoint, None, data))
        resp = self._pop("POST", endpoint)
        if resp.status_code >= 400:
            resp.raise_for_status()
        return resp.json()

    async def post(self, endpoint: str, data: Optional[Dict] = None) -> FakeResponse:
        self.calls.append(("POST", endpoint, None, data))
        return self._pop("POST", endpoint)

    async def put(self, endpoint: str, data: Optional[Dict] = None) -> FakeResponse:
        self.calls.append(("PUT", endpoint, None, data))
        return self._pop("PUT", endpoint)

    async def patch(self, endpoint: str, data: Optional[Dict] = None) -> FakeResponse:
        self.calls.append(("PATCH", endpoint, None, data))
        return self._pop("PATCH", endpoint)

    async def delete(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        timeout: float = 30.0,
    ) -> FakeResponse:
        self.calls.append(("DELETE", endpoint, params, None))
        return self._pop("DELETE", endpoint)


@pytest.fixture
def fake_venice_client() -> FakeVeniceAPIClient:
    return FakeVeniceAPIClient()
