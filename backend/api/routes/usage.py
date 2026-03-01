from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import datetime, timezone, date
from backend.core.venice_api_client import VeniceAPIClient
from backend.core.usage_tracker import UsageTracker, APIKeyUsage, BalanceInfo
from backend.config import get_settings, Settings

router = APIRouter()


def get_venice_client(settings: Settings = Depends(get_settings)) -> VeniceAPIClient:
    return VeniceAPIClient(settings.VENICE_ADMIN_KEY)


@router.get("/daily")
async def get_daily_usage(
    target_date: Optional[str] = None,
    client: VeniceAPIClient = Depends(get_venice_client)
):
    try:
        if target_date is None:
            target_date = datetime.now(timezone.utc).date().isoformat()
        
        tracker = UsageTracker(client.api_key)
        daily_usage = tracker.get_daily_usage(target_date)
        
        return {
            "date": target_date,
            "diem": daily_usage.get("diem", 0.0),
            "usd": daily_usage.get("usd", 0.0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keys")
async def get_api_keys_usage(
    client: VeniceAPIClient = Depends(get_venice_client)
):
    try:
        tracker = UsageTracker(client.api_key)
        keys_usage = tracker.fetch_api_keys_with_daily_usage()
        
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
        raise HTTPException(status_code=500, detail=str(e))


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
        
        response = client.get("/billing/usage", params=params)
        data = response.json()
        
        return {
            "data": data.get("data", []),
            "pagination": data.get("pagination", {}),
            "start_date": start_date,
            "end_date": end_date
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))