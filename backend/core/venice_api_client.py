"""
Venice API Client helper for shared API request functionality.

Async httpx-based client with automatic retry on transient failures.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import logging

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
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
    """
    Async Venice API client with shared configuration and retry logic.

    Uses httpx.AsyncClient. Prefer get_json/post_json helpers which check
    status codes before parsing.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = settings.VENICE_API_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        logger.debug("VeniceAPIClient initialized with key: %s", mask_api_key(api_key))

    def _url(self, endpoint: str) -> str:
        return f"{self.base_url}{endpoint}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((
            httpx.ConnectError,
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.HTTPStatusError,
        )),
        before_sleep=lambda retry_state: logger.warning(
            "Venice API request failed, retrying in %ss... (attempt %s/3)",
            retry_state.next_action.sleep,
            retry_state.attempt_number,
        ),
        reraise=True,
    )
    async def get(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        timeout: float = 30.0,
    ) -> httpx.Response:
        """GET with retry on transient failures. Retries 5xx only."""
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                self._url(endpoint),
                headers=self.headers,
                params=params,
            )
            if response.status_code >= 500:
                response.raise_for_status()
            return response

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((
            httpx.ConnectError,
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.HTTPStatusError,
        )),
        before_sleep=lambda retry_state: logger.warning(
            "Venice API POST failed, retrying in %ss... (attempt %s/3)",
            retry_state.next_action.sleep,
            retry_state.attempt_number,
        ),
        reraise=True,
    )
    async def post(
        self,
        endpoint: str,
        data: Optional[Dict] = None,
        timeout: float = 30.0,
    ) -> httpx.Response:
        """POST with retry on transient failures. Retries 5xx only."""
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                self._url(endpoint),
                headers=self.headers,
                json=data,
            )
            if response.status_code >= 500:
                response.raise_for_status()
            return response

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((
            httpx.ConnectError,
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.HTTPStatusError,
        )),
        before_sleep=lambda retry_state: logger.warning(
            "Venice API PUT failed, retrying in %ss... (attempt %s/3)",
            retry_state.next_action.sleep,
            retry_state.attempt_number,
        ),
        reraise=True,
    )
    async def put(
        self,
        endpoint: str,
        data: Optional[Dict] = None,
        timeout: float = 30.0,
    ) -> httpx.Response:
        """PUT with retry on transient failures. Retries 5xx only."""
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.put(
                self._url(endpoint),
                headers=self.headers,
                json=data,
            )
            if response.status_code >= 500:
                response.raise_for_status()
            return response

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((
            httpx.ConnectError,
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.HTTPStatusError,
        )),
        before_sleep=lambda retry_state: logger.warning(
            "Venice API DELETE failed, retrying in %ss... (attempt %s/3)",
            retry_state.next_action.sleep,
            retry_state.attempt_number,
        ),
        reraise=True,
    )
    async def delete(
        self,
        endpoint: str,
        timeout: float = 30.0,
    ) -> httpx.Response:
        """DELETE with retry on transient failures. Retries 5xx only."""
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.delete(
                self._url(endpoint),
                headers=self.headers,
            )
            if response.status_code >= 500:
                response.raise_for_status()
            return response

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
