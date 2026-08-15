"""
Shared Venice billing-pagination helpers.

A single source of truth for walking /billing/usage-history (cursor
pagination) and /billing/usage (numbered pages). Previously this logic
existed twice — once in core/usage_tracker.py and once in
api/routes/analytics.py — and the two implementations had drifted on
timestamp format and exception type.

Public API:
    UsageHistoryUnavailable, BillingUsageDeprecated  — typed exceptions
    carry the upstream status code so callers can map to HTTP 502/410.
    walk_billing_usage_history(...)                  — collect all
                                                       history entries.
    walk_billing_usage_legacy(...)                   — collect all legacy
                                                       entries (numbered
                                                       pages).
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
    """Raised when /billing/usage-history is unavailable (403/404/410) and the
    caller should fall back to /billing/usage.
    """

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


class BillingUsageDeprecated(Exception):
    """Raised when /billing/usage returns 410 Gone. Caller should migrate to
    /billing/usage-history.
    """

    def __init__(self, status_code: int, message: str, replacement: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.replacement = replacement or "/billing/usage-history"


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
    UsageHistoryUnavailable on 403/404/410 so the caller can fall back to
    /billing/usage, and surfaces other errors via the underlying httpx
    exception so the caller can map them to 502/504.
    """
    entries: List[Dict[str, Any]] = []
    cursor: Optional[str] = None
    effective_pages = max_pages if max_pages is not None else settings.API_MAX_PAGES
    effective_size = page_size if page_size is not None else settings.API_PAGE_SIZE

    page = 0
    while page < effective_pages:
        if cursor:
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


async def walk_billing_usage_legacy(
    client: VeniceAPIClient,
    start_datetime: str,
    end_datetime: str,
    *,
    sort_order: str = "desc",
    page_size: Optional[int] = None,
    max_pages: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Walk /billing/usage (numbered pages) with the API_MAX_PAGES cap.

    DEPRECATED upstream: rate-limited to 10 req/min and returns 410 Gone for
    accounts created on or after 2026-07-07. Prefer walk_billing_usage_history.
    """
    entries: List[Dict[str, Any]] = []
    effective_pages = max_pages if max_pages is not None else settings.API_MAX_PAGES
    effective_size = page_size if page_size is not None else settings.API_PAGE_SIZE

    page = 1
    warned_deprecation = False
    while page <= effective_pages:
        params = {
            "startDate": start_datetime,
            "endDate": end_datetime,
            "limit": effective_size,
            "sortOrder": sort_order,
            "page": page,
        }
        response = await client.get("/billing/usage", params=params)
        if response.status_code == 410:
            raise BillingUsageDeprecated(
                410,
                "/billing/usage is no longer available for this account; "
                "use /billing/usage-history",
                replacement="/billing/usage-history",
            )
        # Deprecation header on 2xx: warn once but keep returning data.
        if response.status_code < 400 and not warned_deprecation:
            dep = response.headers.get("Deprecation") or response.headers.get("deprecation")
            link = response.headers.get("Link") or response.headers.get("link")
            if dep:
                logger.warning(
                    "/billing/usage is deprecated (Deprecation: %s, Link: %s); "
                    "switching to /billing/usage-history",
                    dep,
                    link,
                )
                warned_deprecation = True
        if response.status_code >= 400:
            response.raise_for_status()
        payload = response.json()
        entries.extend(payload.get("data", []) or [])

        pagination = payload.get("pagination") or {}
        try:
            total_pages = int(
                pagination.get(
                    "totalPages",
                    response.headers.get("x-pagination-total-pages", 1),
                )
            )
        except (TypeError, ValueError):
            total_pages = 1
        if page >= total_pages:
            break
        page += 1
    else:
        logger.warning(
            "billing/usage pagination hit API_MAX_PAGES=%s (%s → %s); "
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
