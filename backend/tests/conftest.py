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
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock

import pytest


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
    ):
        self.status_code = status_code
        self._json = json_data or {}
        self.headers = headers or {}

    def json(self) -> Dict[str, Any]:
        return self._json

    def raise_for_status(self) -> None:
        if 400 <= self.status_code < 600:
            import httpx
            request = httpx.Request("GET", "https://example")
            response = httpx.Response(
                self.status_code,
                request=request,
                text=str(self._json),
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
    """Stand-in for ``VeniceAPIClient`` exposing only .get / .post_json.

    Tests program ``responses`` with a list of (match, response_cls, payload)
    rules. ``match`` is the URL substring (e.g. "/billing/usage-history") and
    a sequence of responses is consumed in order; once exhausted, the
    client raises ``AssertionError`` so tests cannot silently diverge.
    """

    def __init__(self) -> None:
        # url_substring -> list of FakeResponse
        self._responses: Dict[str, List[FakeResponse]] = {}

    def queue(self, url_substring: str, responses: List[FakeResponse]) -> None:
        self._responses.setdefault(url_substring, []).extend(responses)

    async def get(self, endpoint: str, params: Optional[Dict] = None) -> FakeResponse:
        # Find a queue whose key appears in the endpoint path.
        target = None
        for key in self._responses:
            if key in endpoint:
                target = key
                break
        assert target is not None, f"No queued response for {endpoint}"
        queue = self._responses[target]
        assert queue, f"Exhausted queue for {target}"
        return queue.pop(0)

    async def post_json(self, endpoint: str, data: Optional[Dict] = None, timeout: float = 30.0):
        # Onchain RPC tests use post_json; route to get_json semantics for
        # the few tests that need it.
        raise NotImplementedError("FakeVeniceAPIClient.post_json is not wired in tests")


@pytest.fixture
def fake_venice_client() -> FakeVeniceAPIClient:
    return FakeVeniceAPIClient()
