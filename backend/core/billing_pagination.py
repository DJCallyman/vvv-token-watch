"""
Shared Venice billing-pagination helpers.

A single source of truth for walking /billing/usage-history (cursor
pagination) and fetching optional usage analytics.

Public API:
    UsageHistoryUnavailable                         — typed exception
                                                       carries the status code.
    walk_billing_usage_history(...)                  — collect all
                                                       history entries.
    fetch_usage_analytics_optional(...)              — best-effort Beta
                                                       /billing/usage-analytics
                                                       fetch; returns None if
                                                       unavailable.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.config import get_settings
from backend.core.venice_api_client import VeniceAPIClient

logger = logging.getLogger(__name__)
settings = get_settings()

# Canonical timestamp format used for both endpoints. The legacy endpoint
# historically returned ".000Z"; modern endpoints accept either. We keep a
# single format to avoid formatting drift between call sites.
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class UsageHistoryUnavailable(Exception):
    """Raised when /billing/usage-history is unavailable (403/404/410)."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


async def walk_billing_usage_history(
    client: VeniceAPIClient,
    start_datetime: str,
    end_datetime: str,
    *,
    currency: Optional[str] = None,
    page_size: Optional[int] = None,
    max_pages: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Walk /billing/usage-history to exhaustion with cursor pagination.

    Filters and page size are supplied only on the first request (with a fresh
    cursor); the API rejects any parameters other than the cursor on
    continuation requests. Raises
    UsageHistoryUnavailable on 403/404/410 and surfaces other errors via
    the underlying httpx exception so callers can map them to 502/504.
    """
    entries: List[Dict[str, Any]] = []
    cursor: Optional[str] = None
    seen_cursors: set[str] = set()
    effective_pages = max_pages if max_pages is not None else settings.API_MAX_PAGES
    effective_size = page_size if page_size is not None else settings.API_PAGE_SIZE

    page = 0
    while page < effective_pages:
        if cursor:
            if cursor in seen_cursors:
                raise RuntimeError("billing/usage-history returned a repeated cursor")
            seen_cursors.add(cursor)
            params: Dict[str, Any] = {"cursor": cursor}
        else:
            params = {"pageSize": effective_size}
            params["startTimestamp"] = start_datetime
            params["endTimestamp"] = end_datetime
            if currency:
                params["currency"] = currency

        response = await client.get("/billing/usage-history", params=params)
        if response.status_code in (403, 404, 410):
            logger.info(
                "/billing/usage-history unavailable (HTTP %s)",
                response.status_code,
            )
            raise UsageHistoryUnavailable(
                response.status_code,
                f"/billing/usage-history unavailable (HTTP {response.status_code})",
            )
        if response.status_code >= 400:
            response.raise_for_status()
        payload = response.json()
        entries.extend(payload.get("data", []) or [])

        cursor = payload.get("nextCursor") or None
        if not cursor:
            break
        page += 1
    else:
        logger.warning(
            "billing/usage-history cursor walk hit API_MAX_PAGES=%s (%s → %s); "
            "totals may be incomplete",
            effective_pages,
            start_datetime,
            end_datetime,
        )

    return entries



async def fetch_usage_analytics_optional(
    client: VeniceAPIClient,
    start_date: datetime,
    end_date: datetime,
) -> Optional[Dict[str, Any]]:
    """Try the Beta /billing/usage-analytics endpoint; return None if unavailable."""
    try:
        params = {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d"),
        }
        response = await client.get("/billing/usage-analytics", params=params)
        if response.status_code == 200:
            return response.json()
    except Exception as exc:
        logger.debug("usage-analytics endpoint unavailable: %s", exc)
    return None
