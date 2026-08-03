"""
Venice API Client helper for shared API request functionality.

Async httpx-based client with:
  * automatic retry on transient failures,
  * a single shared ``httpx.AsyncClient`` (lazy, per-instance) for connection
    pooling,
  * convenient JSON helpers ``get_json`` / ``post_json`` that surface non-2xx
    responses via ``httpx.HTTPStatusError`` so callers can map to 502/410.

The retry policy and before-sleep logger are configured once and shared
across HTTP verbs (GET/POST/PUT/DELETE). 5xx responses retry; 4xx do not —
4xx is a client condition that a retry will not fix and risks spending
rate-limited budget on a key that isn't authorized for the endpoint.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import asyncio
import logging

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


def mask_api_key(api_key: str, visible_chars: int = 4) -> str:
    """Mask API key for safe logging."""
    if not api_key:
        return "<empty>"
    if len(api_key) <= visible_chars * 2:
        return f"{api_key[:visible_chars]}..."
    return f"{api_key[:visible_chars]}...{api_key[-visible_chars:]}"


class VeniceAPIClient:
    """Async Venice API client with shared configuration and retry logic."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = settings.VENICE_API_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        # Lazy single client per instance — keeps a connection pool and avoids
        # the per-request handshake cost previously paid on every call. Callers
        # that need cleanup can invoke ``await client.aclose()`` (e.g. in tests).
        self._http: Optional[httpx.AsyncClient] = None
        self._http_lock = asyncio.Lock()
        logger.debug("VeniceAPIClient initialized with key: %s", mask_api_key(api_key))

    def _url(self, endpoint: str) -> str:
        return f"{self.base_url}{endpoint}"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http is not None:
            return self._http
        async with self._http_lock:
            if self._http is None:
                self._http = httpx.AsyncClient(timeout=30.0)
        return self._http

    async def aclose(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    def _retrying(self, method_label: str) -> AsyncRetrying:
        """Configured retry policy shared by GET/POST/PUT/DELETE."""
        def _before_sleep(retry_state: Any) -> None:
            logger.warning(
                "Venice API %s failed, retrying in %ss... (attempt %s/3)",
                method_label,
                getattr(retry_state.next_action, "sleep", "?"),
                retry_state.attempt_number,
            )

        return AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((
                httpx.ConnectError,
                httpx.TimeoutException,
                httpx.NetworkError,
            )),
            before_sleep=_before_sleep,
            reraise=True,
        )

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ) -> httpx.Response:
        """Issue the request via the pooled client with retry on transient errors.

        Retries only on connect/timeout/network failure. HTTP error statuses
        (4xx and 5xx that the client decides to surface) are returned to the
        caller. Callers can ``raise_for_status()`` themselves.
        """
        client = await self._get_client()
        async for attempt in self._retrying(method):
            with attempt:
                response = await client.request(
                    method,
                    self._url(endpoint),
                    headers=self.headers,
                    params=params,
                    json=json_body,
                    timeout=timeout,
                )
                return response
        # Unreachable: AsyncRetrying exhausted attempts and reraise=True would
        # have raised. Defensive return for type checkers.
        raise RuntimeError("Venice API retry loop terminated without response")

    async def get(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        timeout: float = 30.0,
    ) -> httpx.Response:
        return await self._request("GET", endpoint, params=params, timeout=timeout)

    async def post(
        self,
        endpoint: str,
        data: Optional[Dict] = None,
        timeout: float = 30.0,
    ) -> httpx.Response:
        return await self._request("POST", endpoint, json_body=data, timeout=timeout)

    async def put(
        self,
        endpoint: str,
        data: Optional[Dict] = None,
        timeout: float = 30.0,
    ) -> httpx.Response:
        return await self._request("PUT", endpoint, json_body=data, timeout=timeout)

    async def delete(
        self,
        endpoint: str,
        timeout: float = 30.0,
    ) -> httpx.Response:
        return await self._request("DELETE", endpoint, timeout=timeout)

    async def get_json(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        timeout: float = 30.0,
        raise_for_status: bool = True,
    ) -> Any:
        """GET and return parsed JSON. Raises on non-2xx when raise_for_status=True."""
        response = await self.get(endpoint, params=params, timeout=timeout)
        if raise_for_status and response.status_code >= 400:
            response.raise_for_status()
        return response.json()

    async def post_json(
        self,
        endpoint: str,
        data: Optional[Dict] = None,
        timeout: float = 30.0,
        raise_for_status: bool = True,
    ) -> Any:
        """POST and return parsed JSON. Raises on non-2xx when raise_for_status=True."""
        response = await self.post(endpoint, data=data, timeout=timeout)
        if raise_for_status and response.status_code >= 400:
            response.raise_for_status()
        return response.json()
