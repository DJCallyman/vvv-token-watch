import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException
from backend.core.venice_api_client import VeniceAPIClient
from backend.core.usage_tracker import UsageTracker
from backend.config import get_settings, Settings

logger = logging.getLogger(__name__)
router = APIRouter()


def get_venice_client(settings: Settings = Depends(get_settings)) -> VeniceAPIClient:
    return VeniceAPIClient(settings.VENICE_ADMIN_KEY)


@router.get("/balance")
async def get_balance(
    client: VeniceAPIClient = Depends(get_venice_client)
):
    try:
        # Prefer /billing/balance for accurate currency/epoch allocation info.
        billing_response = await asyncio.to_thread(client.get, "/billing/balance")
        billing = billing_response.json().get("data", {})
        balances = billing.get("balances", {})
        consumption_currency = billing.get("consumptionCurrency", "DIEM")
        can_consume = billing.get("canConsume", True)
        diem_epoch_allocation = billing.get("diemEpochAllocation")

        # Fallback to rate-limits endpoint for nextEpochBegins.
        tracker = UsageTracker(client.api_key)
        balance_info = await asyncio.to_thread(tracker.fetch_rate_limits)

        diem_usage_percent = (
            (balance_info.diem / diem_epoch_allocation * 100)
            if diem_epoch_allocation else
            (balance_info.diem / balance_info.daily_diem_limit * 100)
            if balance_info.daily_diem_limit else 0.0
        )
        usd_usage_percent = (
            (balance_info.usd / balance_info.daily_usd_limit * 100)
            if balance_info.daily_usd_limit else 0.0
        )

        return {
            "diem": float(balances.get("DIEM", balance_info.diem)),
            "usd": float(balances.get("USD", balance_info.usd)),
            "daily_diem_limit": balance_info.daily_diem_limit,
            "daily_usd_limit": balance_info.daily_usd_limit,
            "diem_usage_percent": diem_usage_percent,
            "usd_usage_percent": usd_usage_percent,
            "next_epoch_begins": balance_info.next_epoch_begins,
            "consumption_currency": consumption_currency,
            "can_consume": can_consume,
            "diem_epoch_allocation": diem_epoch_allocation,
        }
    except Exception as e:
        logger.exception("Failed to fetch balance")
        raise HTTPException(status_code=500, detail="Failed to fetch balance")


@router.get("/rate-limits")
async def get_rate_limits(
    client: VeniceAPIClient = Depends(get_venice_client)
):
    try:
        response = await asyncio.to_thread(client.get, "/api_keys/rate_limits")
        return response.json()
    except Exception as e:
        logger.exception("Failed to fetch rate limits")
        raise HTTPException(status_code=500, detail="Failed to fetch rate limits")