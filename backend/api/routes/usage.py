import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import Settings, get_settings
from backend.core.usage_tracker import UsageTracker
from backend.core.venice_api_client import VeniceAPIClient
from backend.database import get_db
from backend.services.usage_history_service import get_usage_trends, record_usage_snapshot

logger = logging.getLogger(__name__)
router = APIRouter()


def get_venice_client(settings: Settings = Depends(get_settings)) -> VeniceAPIClient:
    return VeniceAPIClient(settings.VENICE_ADMIN_KEY)


@router.get("/daily")
async def get_daily_usage(
    target_date: Optional[str] = None,
    client: VeniceAPIClient = Depends(get_venice_client),
    db: AsyncSession = Depends(get_db),
):
    try:
        tracker = UsageTracker(client.api_key, client)
        result = await tracker.get_daily_usage(target_date)
        try:
            await record_usage_snapshot(
                db,
                scope="daily",
                diem=float(result.get("diem", 0)),
                usd=float(result.get("usd", 0)),
                bundled_credits=float(result.get("bundled_credits", 0)),
                target_date=result.get("date"),
            )
        except Exception:
            logger.exception("Failed to persist daily usage snapshot")
        return result
    except Exception:
        logger.exception("Failed to fetch daily usage")
        raise HTTPException(status_code=500, detail="Failed to fetch daily usage")


@router.get("/epoch")
async def get_epoch_usage(
    client: VeniceAPIClient = Depends(get_venice_client),
    db: AsyncSession = Depends(get_db),
):
    try:
        tracker = UsageTracker(client.api_key, client)
        result = await tracker.get_epoch_usage()
        try:
            await record_usage_snapshot(
                db,
                scope="epoch",
                diem=float(result.get("diem", 0)),
                usd=float(result.get("usd", 0)),
                bundled_credits=float(result.get("bundled_credits", 0)),
                epoch_start=result.get("epoch_start"),
                next_epoch=result.get("next_epoch"),
            )
        except Exception:
            logger.exception("Failed to persist epoch usage snapshot")
        return result
    except Exception:
        logger.exception("Failed to fetch epoch usage")
        raise HTTPException(status_code=500, detail="Failed to fetch epoch usage")


@router.get("/keys")
async def get_api_keys_usage(
    client: VeniceAPIClient = Depends(get_venice_client)
):
    try:
        tracker = UsageTracker(client.api_key, client)
        keys_usage = await tracker.fetch_api_keys_with_daily_usage()

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
    except Exception:
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

        data = await client.get_json("/billing/usage", params=params)

        return {
            "data": data.get("data", []),
            "pagination": data.get("pagination", {}),
            "start_date": start_date,
            "end_date": end_date
        }
    except Exception:
        logger.exception("Failed to fetch usage history")
        raise HTTPException(status_code=500, detail="Failed to fetch usage history")


@router.get("/history/trends")
async def get_usage_history_trends(
    scope: str = Query("epoch", pattern="^(epoch|daily)$"),
    limit: int = Query(500, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
):
    """Return persisted usage snapshots for trend charts."""
    try:
        points = await get_usage_trends(db, scope=scope, limit=limit)
        return {"scope": scope, "count": len(points), "data": points}
    except Exception:
        logger.exception("Failed to fetch usage trends")
        raise HTTPException(status_code=500, detail="Failed to fetch usage trends")
