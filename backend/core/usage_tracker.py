"""
Module for tracking Venice API usage metrics including overall balance and per-key usage.
Web-optimized version without Qt dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Optional, Any
import logging
from datetime import datetime, timezone, timedelta

import httpx

from backend.core.venice_api_client import VeniceAPIClient
from backend.config import get_settings
from backend.core.billing_pagination import (
    BillingUsageDeprecated,
    UsageHistoryUnavailable,
    walk_billing_usage_history,
    walk_billing_usage_legacy,
)

# Re-export for callers that import the names from this module.
__all__ = [
    "VeniceUpstreamError",
    "BillingUsageDeprecated",
    "UsageHistoryUnavailable",
    "UsageTracker",
    "UsageWorker",
    "UsageMetrics",
    "APIKeyUsage",
    "BalanceInfo",
    "_net_usage_from_entries",
]

settings = get_settings()
logger = logging.getLogger(__name__)


class VeniceUpstreamError(Exception):
    """Raised when the Venice API responds with an unexpected HTTP status
    or cannot be reached. Callers should map this to HTTP 502/504. Carries
    `status_code` when known so the upstream status can be surfaced.
    """

    def __init__(self, message: str, *, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class UsageMetrics:
    """Tracks usage metrics for a specific time period"""
    diem: float
    usd: float


@dataclass
class APIKeyUsage:
    """Represents usage data for a single API key"""
    id: str
    name: str
    usage: UsageMetrics
    created_at: str
    is_active: bool
    last_used_at: Optional[str] = None
    api_key_type: Optional[str] = None
    consumption_limits_usd: Optional[float] = None
    consumption_limits_diem: Optional[float] = None
    limit_period: Optional[str] = None
    expires_at: Optional[str] = None
    last6_chars: Optional[str] = None
    current_period_usage_usd: Optional[str] = None
    current_period_usage_diem: Optional[str] = None


@dataclass
class BalanceInfo:
    """Tracks current balance information and daily limits"""
    diem: float
    usd: float
    daily_diem_limit: float = 100.0
    daily_usd_limit: float = 25.0
    next_epoch_begins: Optional[str] = None


def _net_usage_from_entries(entries: List[Dict[str, Any]]) -> Dict[str, float]:
    """Net billing amounts: charges are negative, refunds positive. Return positive usage.

    Tracks DIEM, USD, and bundled/legacy credits (BUNDLED_CREDITS, VCU) as
    separate buckets. Do NOT mix currencies 1:1 — callers should display each
    bucket on its own axis.
    """
    totals = {"diem": 0.0, "usd": 0.0, "bundled_credits": 0.0}
    for entry in entries:
        currency = (entry.get("currency") or "").upper()
        amount = float(entry.get("amount", 0))
        if currency == "DIEM":
            totals["diem"] -= amount
        elif currency == "USD":
            totals["usd"] -= amount
        elif currency in ("BUNDLED_CREDITS", "VCU"):
            # Track bundled/legacy credits separately — do not mix into diem.
            totals["bundled_credits"] -= amount
        # Unknown currencies are ignored (logged elsewhere if needed).
    return totals


# Billing-pagination exceptions are imported from backend.core.billing_pagination
# above. They are re-exported via __all__ for callers that import them from
# this module's stable name.


class UsageTracker:
    """
    Service class for fetching Venice API usage data.
    Optimized for web backend without Qt dependencies.
    """

    def __init__(self, admin_key: str, api_client: Optional[VeniceAPIClient] = None):
        self.admin_key = admin_key
        self.api_client = api_client or VeniceAPIClient(admin_key)

    async def fetch_rate_limits(self) -> BalanceInfo:
        try:
            data = await self.api_client.get_json("/api_keys/rate_limits")
            payload = data.get("data", {})
            balances = payload.get("balances", {})
            next_epoch = payload.get("nextEpochBegins", "")

            return BalanceInfo(
                diem=float(balances.get("DIEM", 0)),
                usd=float(balances.get("USD", 0)),
                daily_diem_limit=settings.DEFAULT_DAILY_DIEM_LIMIT,
                daily_usd_limit=settings.DEFAULT_DAILY_USD_LIMIT,
                next_epoch_begins=next_epoch,
            )
        except httpx.HTTPStatusError as e:
            raise VeniceUpstreamError(
                f"Venice /api_keys/rate_limits returned {e.response.status_code if e.response else '?'}",
                status_code=e.response.status_code if e.response else None,
            ) from e
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            raise VeniceUpstreamError(
                f"Venice /api_keys/rate_limits unreachable: {e}",
            ) from e

    async def fetch_billing_entries(
        self,
        start_datetime: str,
        end_datetime: str,
        sort_order: str = "desc",
        currency: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch billing entries for a window, preferring /billing/usage-history.

        Falls back to /billing/usage when the new endpoint is unavailable
        (older accounts). Raises BillingUsageDeprecated if /billing/usage
        returns 410 — the caller should surface this to the user.
        """
        try:
            return await walk_billing_usage_history(
                self.api_client,
                start_datetime,
                end_datetime,
                currency=currency,
            )
        except UsageHistoryUnavailable as exc:
            logger.info(
                "Falling back to /billing/usage (history unavailable: %s)",
                exc,
            )
            return await walk_billing_usage_legacy(
                self.api_client,
                start_datetime,
                end_datetime,
                sort_order=sort_order,
            )

    async def get_epoch_usage(self) -> Dict:
        """Query billing usage from the start of the current epoch to now.

        Uses nextEpochBegins from the rate limits endpoint to determine epoch start.
        Returns usage totals plus the epoch_start datetime string.

        Prefers /billing/usage-history (cursor-paginated, no rate limit) and
        falls back to /billing/usage for legacy accounts.
        """
        try:
            rl_data = await self.api_client.get_json("/api_keys/rate_limits")
            payload = rl_data.get("data", {})
            next_epoch_str = payload.get("nextEpochBegins", "")

            if next_epoch_str:
                next_epoch = datetime.fromisoformat(next_epoch_str.replace("Z", "+00:00"))
                epoch_start = next_epoch - timedelta(hours=settings.EPOCH_LENGTH_HOURS)
            else:
                # Fallback: midnight UTC today
                epoch_start = datetime.now(timezone.utc).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )

            epoch_start_str = epoch_start.strftime("%Y-%m-%dT%H:%M:%SZ")
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            entries = await self.fetch_billing_entries(epoch_start_str, now_str)
            totals = _net_usage_from_entries(entries)

            return {
                "diem": totals["diem"],
                "usd": totals["usd"],
                "bundled_credits": totals["bundled_credits"],
                "epoch_start": epoch_start_str,
                "next_epoch": next_epoch_str,
            }
        except httpx.HTTPStatusError as e:
            raise VeniceUpstreamError(
                f"Venice API (rate-limits or billing/usage-history) returned {e.response.status_code if e.response else '?'}",
                status_code=e.response.status_code if e.response else None,
            ) from e
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            raise VeniceUpstreamError(
                "Venice API (rate-limits or billing/usage-history) unreachable",
            ) from e

    async def get_daily_usage(self, target_date: Optional[str] = None) -> Dict[str, float]:
        try:
            if target_date is None:
                target_date = datetime.now(timezone.utc).date().isoformat()

            start_datetime = f"{target_date}T00:00:00Z"
            end_datetime = f"{target_date}T23:59:59Z"

            entries = await self.fetch_billing_entries(start_datetime, end_datetime)
            totals = _net_usage_from_entries(entries)

            return {
                "diem": totals["diem"],
                "usd": totals["usd"],
                "bundled_credits": totals["bundled_credits"],
                "date": target_date,
            }
        except httpx.HTTPStatusError as e:
            raise VeniceUpstreamError(
                f"Venice /billing/usage-history (daily) returned {e.response.status_code if e.response else '?'}",
                status_code=e.response.status_code if e.response else None,
            ) from e
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            raise VeniceUpstreamError(
                f"Venice /billing/usage-history (daily) unreachable: {e}",
            ) from e

    async def fetch_api_keys_with_daily_usage(self) -> List[APIKeyUsage]:
        try:
            keys_data = await self.api_client.get_json("/api_keys")

            api_keys: List[APIKeyUsage] = []
            for key_data in keys_data.get("data", []):
                key_id = key_data.get("id", "unknown")
                usage_data = key_data.get("usage", {}).get("trailingSevenDays", {})
                metrics = UsageMetrics(
                    diem=float(usage_data.get("diem", 0)),
                    usd=float(usage_data.get("usd", 0)),
                )
                consumption_limits = key_data.get("consumptionLimits") or {}
                current_period = key_data.get("currentPeriodUsage") or {}
                api_keys.append(
                    APIKeyUsage(
                        id=key_id,
                        name=key_data.get("description", f"Key {key_id[-8:]}"),
                        usage=metrics,
                        created_at=key_data.get("createdAt", "2025-01-01T00:00:00Z"),
                        is_active=key_data.get("isActive", True),
                        last_used_at=key_data.get("lastUsedAt"),
                        api_key_type=key_data.get("apiKeyType"),
                        consumption_limits_usd=consumption_limits.get("usd"),
                        consumption_limits_diem=consumption_limits.get("diem"),
                        limit_period=key_data.get("limitPeriod"),
                        expires_at=key_data.get("expiresAt"),
                        last6_chars=key_data.get("last6Chars"),
                        current_period_usage_usd=current_period.get("usd"),
                        current_period_usage_diem=current_period.get("diem"),
                    )
                )
            return api_keys
        except httpx.HTTPStatusError as e:
            raise VeniceUpstreamError(
                f"Venice /api_keys returned {e.response.status_code if e.response else '?'}",
                status_code=e.response.status_code if e.response else None,
            ) from e
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            raise VeniceUpstreamError(
                f"Venice /api_keys unreachable: {e}",
            ) from e


class UsageWorker:
    """
    Compatibility class that wraps UsageTracker.
    Provides the same interface as the Qt-based UsageWorker.
    """

    def __init__(self, admin_key: str, parent=None):
        self.admin_key = admin_key
        self.api_client = VeniceAPIClient(admin_key)
        self._tracker = UsageTracker(admin_key, self.api_client)

    async def fetch_rate_limits(self) -> BalanceInfo:
        return await self._tracker.fetch_rate_limits()

    async def get_daily_usage(self, target_date: Optional[str] = None) -> Dict[str, float]:
        return await self._tracker.get_daily_usage(target_date)

    async def fetch_api_keys_with_daily_usage(self) -> List[APIKeyUsage]:
        return await self._tracker.fetch_api_keys_with_daily_usage()
