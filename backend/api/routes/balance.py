import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.venice_api_client import VeniceAPIClient
from backend.core.usage_tracker import UsageTracker
from backend.config import get_settings, Settings
from backend.database import get_db
from backend.services import alert_engine

logger = logging.getLogger(__name__)
router = APIRouter()


def get_venice_client(settings: Settings = Depends(get_settings)) -> VeniceAPIClient:
    return VeniceAPIClient(settings.VENICE_ADMIN_KEY)


@router.get("/balance")
async def get_balance(
    client: VeniceAPIClient = Depends(get_venice_client),
    db: AsyncSession = Depends(get_db),
):
    try:
        # Prefer /billing/balance for accurate currency/epoch allocation info.
        billing_payload = await client.get_json("/billing/balance")
        billing = billing_payload.get("data", {})
        balances = billing.get("balances", {})
        consumption_currency = billing.get("consumptionCurrency", "DIEM")
        can_consume = billing.get("canConsume", True)
        diem_epoch_allocation = billing.get("diemEpochAllocation")

        # Fallback to rate-limits endpoint for nextEpochBegins.
        tracker = UsageTracker(client.api_key, client)
        balance_info = await tracker.fetch_rate_limits()

        diem_balance = float(balances.get("DIEM", balance_info.diem))
        usd_balance = float(balances.get("USD", balance_info.usd))

        # Remaining balance as % of allocation (existing field semantics).
        diem_usage_percent = (
            (diem_balance / diem_epoch_allocation * 100)
            if diem_epoch_allocation else
            (diem_balance / balance_info.daily_diem_limit * 100)
            if balance_info.daily_diem_limit else 0.0
        )
        usd_usage_percent = (
            (usd_balance / balance_info.daily_usd_limit * 100)
            if balance_info.daily_usd_limit else 0.0
        )

        # Consumed % of epoch allocation (for usage_percent alerts).
        diem_consumed_percent = (
            max(0.0, 100.0 - diem_usage_percent)
            if diem_epoch_allocation else 0.0
        )

        result = {
            "diem": diem_balance,
            "usd": usd_balance,
            "daily_diem_limit": balance_info.daily_diem_limit,
            "daily_usd_limit": balance_info.daily_usd_limit,
            "diem_usage_percent": diem_usage_percent,
            "usd_usage_percent": usd_usage_percent,
            "next_epoch_begins": balance_info.next_epoch_begins,
            "consumption_currency": consumption_currency,
            "can_consume": can_consume,
            "diem_epoch_allocation": diem_epoch_allocation,
        }

        # Best-effort alert evaluation on each balance poll.
        try:
            await alert_engine.evaluate_alerts(
                db,
                {
                    "diem_balance": diem_balance,
                    "usd_balance": usd_balance,
                    "diem_usage_percent": diem_consumed_percent,
                    "usd_usage_percent": usd_usage_percent,
                },
            )
        except Exception:
            logger.exception("Alert evaluation failed during balance poll")

        return result
    except Exception:
        logger.exception("Failed to fetch balance")
        raise HTTPException(status_code=500, detail="Failed to fetch balance")


@router.get("/rate-limits")
async def get_rate_limits(
    client: VeniceAPIClient = Depends(get_venice_client)
):
    try:
        return await client.get_json("/api_keys/rate_limits")
    except Exception:
        logger.exception("Failed to fetch rate limits")
        raise HTTPException(status_code=500, detail="Failed to fetch rate limits")


@router.get("/rate-limits/log")
async def get_rate_limits_log(
    client: VeniceAPIClient = Depends(get_venice_client)
):
    """Passthrough of Venice GET /api_keys/rate_limits/log (exceedance events)."""
    try:
        return await client.get_json("/api_keys/rate_limits/log")
    except Exception:
        logger.exception("Failed to fetch rate limit log")
        raise HTTPException(status_code=500, detail="Failed to fetch rate limit log")
