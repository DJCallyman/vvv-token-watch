from fastapi import APIRouter, Depends, HTTPException
from backend.core.venice_api_client import VeniceAPIClient
from backend.core.usage_tracker import UsageTracker
from backend.config import get_settings, Settings

router = APIRouter()


def get_venice_client(settings: Settings = Depends(get_settings)) -> VeniceAPIClient:
    return VeniceAPIClient(settings.VENICE_ADMIN_KEY)


@router.get("/balance")
async def get_balance(
    client: VeniceAPIClient = Depends(get_venice_client)
):
    try:
        tracker = UsageTracker(client.api_key)
        balance_info = tracker.fetch_rate_limits()
        
        return {
            "diem": balance_info.diem,
            "usd": balance_info.usd,
            "daily_diem_limit": balance_info.daily_diem_limit,
            "daily_usd_limit": balance_info.daily_usd_limit,
            "next_epoch_begins": balance_info.next_epoch_begins,
            "diem_usage_percent": round((balance_info.diem / balance_info.daily_diem_limit) * 100, 2) if balance_info.daily_diem_limit > 0 else 0,
            "usd_usage_percent": round((balance_info.usd / balance_info.daily_usd_limit) * 100, 2) if balance_info.daily_usd_limit > 0 else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rate-limits")
async def get_rate_limits(
    client: VeniceAPIClient = Depends(get_venice_client)
):
    try:
        response = client.get("/api_keys/rate_limits")
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))