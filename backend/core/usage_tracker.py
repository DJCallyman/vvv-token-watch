"""
Module for tracking Venice API usage metrics including overall balance and per-key usage.
Web-optimized version without Qt dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Optional, Any
import logging
from datetime import datetime, timezone, timedelta

from backend.core.venice_api_client import VeniceAPIClient
from backend.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


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


@dataclass
class BalanceInfo:
    """Tracks current balance information and daily limits"""
    diem: float
    usd: float
    daily_diem_limit: float = 100.0
    daily_usd_limit: float = 25.0
    next_epoch_begins: Optional[str] = None


def _net_usage_from_entries(entries: List[Dict[str, Any]]) -> Dict[str, float]:
    """Net billing amounts: charges are negative, refunds positive. Return positive usage."""
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
    return totals


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
        except Exception as e:
            raise Exception(f"Failed to fetch rate limits: {e}") from e

    async def _paginate_billing_usage(
        self,
        start_datetime: str,
        end_datetime: str,
        sort_order: str = "desc",
    ) -> List[Dict[str, Any]]:
        """Paginate /billing/usage with API_MAX_PAGES safety cap."""
        entries: List[Dict[str, Any]] = []
        page = 1
        max_pages = settings.API_MAX_PAGES

        while page <= max_pages:
            params = {
                "startDate": start_datetime,
                "endDate": end_datetime,
                "limit": settings.API_PAGE_SIZE,
                "sortOrder": sort_order,
                "page": page,
            }
            response = await self.api_client.get("/billing/usage", params=params)
            if response.status_code >= 400:
                response.raise_for_status()
            payload = response.json()
            page_entries = payload.get("data", [])
            entries.extend(page_entries)

            pagination = payload.get("pagination", {})
            total_pages = int(
                pagination.get(
                    "totalPages",
                    response.headers.get("x-pagination-total-pages", 1),
                )
            )
            if page >= total_pages:
                break
            page += 1
        else:
            logger.warning(
                "billing/usage pagination hit API_MAX_PAGES=%s (%s → %s); totals may be incomplete",
                max_pages,
                start_datetime,
                end_datetime,
            )

        return entries

    async def get_epoch_usage(self) -> Dict:
        """Query billing usage from the start of the current epoch to now.

        Uses nextEpochBegins from the rate limits endpoint to determine epoch start.
        Returns usage totals plus the epoch_start datetime string.
        """
        try:
            rl_data = await self.api_client.get_json("/api_keys/rate_limits")
            payload = rl_data.get("data", {})
            next_epoch_str = payload.get("nextEpochBegins", "")

            if next_epoch_str:
                next_epoch = datetime.fromisoformat(next_epoch_str.replace("Z", "+00:00"))
                epoch_start = next_epoch - timedelta(days=1)
            else:
                # Fallback: midnight UTC today
                epoch_start = datetime.now(timezone.utc).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )

            epoch_start_str = epoch_start.strftime("%Y-%m-%dT%H:%M:%SZ")
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            entries = await self._paginate_billing_usage(epoch_start_str, now_str)
            totals = _net_usage_from_entries(entries)

            return {
                "diem": totals["diem"],
                "usd": totals["usd"],
                "bundled_credits": totals["bundled_credits"],
                "epoch_start": epoch_start_str,
                "next_epoch": next_epoch_str,
            }
        except Exception as e:
            raise Exception(f"Failed to fetch epoch usage: {e}") from e

    async def get_daily_usage(self, target_date: Optional[str] = None) -> Dict[str, float]:
        try:
            if target_date is None:
                target_date = datetime.now(timezone.utc).date().isoformat()

            start_datetime = f"{target_date}T00:00:00Z"
            end_datetime = f"{target_date}T23:59:59Z"

            entries = await self._paginate_billing_usage(start_datetime, end_datetime)
            totals = _net_usage_from_entries(entries)

            return {
                "diem": totals["diem"],
                "usd": totals["usd"],
                "bundled_credits": totals["bundled_credits"],
                "date": target_date,
            }
        except Exception as e:
            raise Exception(f"Failed to fetch daily usage: {e}") from e

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
                api_keys.append(
                    APIKeyUsage(
                        id=key_id,
                        name=key_data.get("description", f"Key {key_id[-8:]}"),
                        usage=metrics,
                        created_at=key_data.get("createdAt", "2025-01-01T00:00:00Z"),
                        is_active=key_data.get("isActive", True),
                        last_used_at=key_data.get("lastUsedAt"),
                    )
                )
            return api_keys
        except Exception as e:
            raise Exception(f"Failed to fetch keys with daily usage: {e}") from e


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
