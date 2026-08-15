"""
Module for tracking Venice API usage metrics including overall balance and per-key usage.
Web-optimized version without Qt dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Optional, Any
import hashlib
import logging
from datetime import date, datetime, timezone, timedelta

import httpx

from backend.core.venice_api_client import VeniceAPIClient
from backend.config import get_settings
from backend.core.billing_pagination import (
    BillingUsageDeprecated,
    UsageHistoryUnavailable,
    fetch_usage_analytics_optional,
    walk_billing_usage_history,
    walk_billing_usage_legacy,
)
from backend.core.cache import TtlCache

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
    "_net_usage_from_analytics",
    "_net_usage_from_entries",
]

settings = get_settings()
logger = logging.getLogger(__name__)
_epoch_usage_cache = TtlCache(max_size=128)


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


def _net_usage_from_analytics(
    payload: Dict[str, Any],
    start_datetime: datetime,
    end_datetime: datetime,
) -> Optional[Dict[str, float]]:
    """Read documented currency totals from the analytics response.

    ``/billing/usage-analytics`` returns positive spend totals rather than
    ledger entries, so no sign inversion is needed here. Return ``None`` for
    an incomplete or malformed response so callers can use the authoritative
    ledger pagination fallback instead.
    """
    if not isinstance(payload, dict):
        return None

    analytics_data = payload.get("data")
    if isinstance(analytics_data, dict):
        payload = analytics_data

    by_date = payload.get("byDate")
    if not isinstance(by_date, list):
        return None

    start_date = start_datetime.date()
    end_date = end_datetime.date()
    totals = {"diem": 0.0, "usd": 0.0, "bundled_credits": 0.0}

    def numeric_value(entry: Dict[str, Any], names: tuple[str, ...]) -> Optional[float]:
        for name in names:
            if name in entry and entry[name] is not None:
                try:
                    return float(entry[name])
                except (TypeError, ValueError):
                    return None
        return None

    for entry in by_date:
        if not isinstance(entry, dict):
            return None

        raw_date = entry.get("date")
        if not isinstance(raw_date, str):
            return None
        try:
            entry_date = date.fromisoformat(raw_date[:10])
        except ValueError:
            return None
        if not start_date <= entry_date <= end_date:
            continue

        usd = numeric_value(entry, ("USD", "usd", "totalUsd"))
        diem = numeric_value(entry, ("DIEM", "diem", "totalDiem"))
        if usd is None or diem is None:
            return None

        totals["usd"] += usd
        totals["diem"] += diem

        bundled = numeric_value(
            entry,
            (
                "BUNDLED_CREDITS",
                "bundledCredits",
                "totalBundledCredits",
                "VCU",
                "vcu",
            ),
        )
        if bundled is not None:
            totals["bundled_credits"] += bundled

    return totals


def _epoch_cache_key(admin_key: str) -> str:
    """Avoid retaining the raw admin key in the process-local cache key."""
    return hashlib.sha256(admin_key.encode("utf-8")).hexdigest()


def _cached_epoch_usage(admin_key: str) -> Optional[Dict[str, Any]]:
    cached = _epoch_usage_cache.get(_epoch_cache_key(admin_key))
    if not isinstance(cached, dict):
        return None

    now = datetime.now(timezone.utc)

    # Do not serve the previous epoch across a boundary if the TTL has not
    # elapsed yet (for example, when the process is polled at midnight UTC).
    next_epoch_str = cached.get("next_epoch")
    if next_epoch_str:
        try:
            next_epoch = datetime.fromisoformat(str(next_epoch_str).replace("Z", "+00:00"))
            if next_epoch.tzinfo is None:
                next_epoch = next_epoch.replace(tzinfo=timezone.utc)
            if next_epoch <= now:
                return None
        except ValueError:
            return None
    else:
        epoch_start_str = cached.get("epoch_start")
        try:
            epoch_start = datetime.fromisoformat(str(epoch_start_str).replace("Z", "+00:00"))
            if epoch_start.tzinfo is None:
                epoch_start = epoch_start.replace(tzinfo=timezone.utc)
            if epoch_start + timedelta(hours=settings.EPOCH_LENGTH_HOURS) <= now:
                return None
        except (TypeError, ValueError):
            return None

    return dict(cached)


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
        Uses the aggregated analytics endpoint when available, then falls back
        to the cursor-paginated ledger. Completed results are cached briefly so
        dashboard polling does not repeat the upstream work on every request.

        Prefers /billing/usage-history (cursor-paginated, no rate limit) and
        falls back to /billing/usage for legacy accounts.
        """
        cached = _cached_epoch_usage(self.admin_key)
        if cached is not None:
            logger.debug("Returning cached epoch usage")
            return cached

        try:
            rl_data = await self.api_client.get_json("/api_keys/rate_limits")
            payload = rl_data.get("data", {})
            next_epoch_str = payload.get("nextEpochBegins", "")

            if next_epoch_str:
                next_epoch = datetime.fromisoformat(next_epoch_str.replace("Z", "+00:00"))
                if next_epoch.tzinfo is None:
                    next_epoch = next_epoch.replace(tzinfo=timezone.utc)
                epoch_start = next_epoch - timedelta(hours=settings.EPOCH_LENGTH_HOURS)
            else:
                # Fallback: midnight UTC today
                epoch_start = datetime.now(timezone.utc).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )

            now = datetime.now(timezone.utc)
            epoch_start_str = epoch_start.strftime("%Y-%m-%dT%H:%M:%SZ")
            now_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")

            analytics = None
            if (
                epoch_start.hour == 0
                and epoch_start.minute == 0
                and epoch_start.second == 0
                and epoch_start.microsecond == 0
            ):
                analytics = await fetch_usage_analytics_optional(
                    self.api_client,
                    epoch_start,
                    now,
                )
            totals = _net_usage_from_analytics(analytics, epoch_start, now) if analytics else None
            if totals is not None:
                logger.info("Epoch usage fetched via /billing/usage-analytics")
            else:
                if analytics is not None:
                    logger.warning(
                        "Ignoring incomplete /billing/usage-analytics response for epoch usage"
                    )
                entries = await self.fetch_billing_entries(epoch_start_str, now_str)
                totals = _net_usage_from_entries(entries)

            result = {
                "diem": totals["diem"],
                "usd": totals["usd"],
                "bundled_credits": totals["bundled_credits"],
                "epoch_start": epoch_start_str,
                "next_epoch": next_epoch_str,
            }
            _epoch_usage_cache.set(
                _epoch_cache_key(self.admin_key),
                result,
                ttl=settings.CACHE_TTL_SECONDS,
            )
            return result
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
