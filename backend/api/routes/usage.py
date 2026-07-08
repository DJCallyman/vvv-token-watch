import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from backend.core.venice_api_client import VeniceAPIClient
from backend.core.usage_tracker import UsageTracker
from backend.config import get_settings, Settings

logger = logging.getLogger(__name__)
router = APIRouter()


def get_venice_client(settings: Settings = Depends(get_settings)) -> VeniceAPIClient:
    return VeniceAPIClient(settings.VENICE_ADMIN_KEY)


@router.get("/daily")
async def get_daily_usage(
    target_date: Optional[str] = None,
    client: VeniceAPIClient = Depends(get_venice_client)
):
    try:
        tracker = UsageTracker(client.api_key)
        result = await asyncio.to_thread(tracker.get_daily_usage, target_date)
        return result
    except Exception as e:
        logger.exception("Failed to fetch daily usage")
        raise HTTPException(status_code=500, detail="Failed to fetch daily usage")


@router.get("/epoch")
async def get_epoch_usage(
    client: VeniceAPIClient = Depends(get_venice_client)
):
    try:
        tracker = UsageTracker(client.api_key)
        result = await asyncio.to_thread(tracker.get_epoch_usage)
        return result
    except Exception as e:
        logger.exception("Failed to fetch epoch usage")
        raise HTTPException(status_code=500, detail="Failed to fetch epoch usage")


@router.get("/keys")
async def get_api_keys_usage(
    client: VeniceAPIClient = Depends(get_venice_client)
):
    try:
        tracker = UsageTracker(client.api_key)
        keys_usage = await asyncio.to_thread(tracker.fetch_api_keys_with_daily_usage)

        return {
            "keys": [
                {
                    "id": key.id,
                    "name": key.name,
                    "diem_usage": key.usage.diem,
                    "usd_usage": key.usage.usd,
                    "created_at": key.created_at,
                    "is_active": key.is_active
                }
                for key in keys_usage
            ]
        }
    except Exception as e:
        logger.exception("Failed to fetch API key usage")
        raise HTTPException(status_code=500, detail="Failed to fetch API key usage")


@router.get("/history")
async def get_usage_history(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    client: VeniceAPIClient = Depends(get_venice_client)
):
    try:
        params = {
            "limit": min(limit, 500),
            "sortOrder": "desc"
        }

        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date

        response = await asyncio.to_thread(client.get, "/billing/usage", params)
        data = response.json()

        return {
            "data": data.get("data", []),
            "pagination": data.get("pagination", {}),
            "start_date": start_date,
            "end_date": end_date
        }
    except Exception as e:
        logger.exception("Failed to fetch usage history")
        raise HTTPException(status_code=500, detail="Failed to fetch usage history")