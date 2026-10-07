"""External notification channel and delivery endpoints (Slice 2.4)."""

import logging
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import Settings, get_settings
from backend.database import get_db
from backend.limiter import limiter
from backend.models.db import NotificationChannel
from backend.services import notification_service
from backend.services.notification_service import ChannelValidationError

logger = logging.getLogger(__name__)
router = APIRouter()

ChannelKind = Literal["discord", "slack", "telegram", "webhook", "email", "browser_push"]


class ChannelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    kind: ChannelKind = "discord"
    enabled: bool = True
    webhook_url: Optional[str] = Field(None, max_length=512)
    url: Optional[str] = Field(None, max_length=512)
    telegram_bot_token: Optional[str] = Field(None, max_length=128)
    telegram_chat_id: Optional[str] = Field(None, max_length=64)
    email_to: Optional[str] = Field(None, max_length=254)
    subscription: Optional[Dict[str, Any]] = None


class ChannelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    enabled: Optional[bool] = None
    webhook_url: Optional[str] = Field(None, max_length=512)
    url: Optional[str] = Field(None, max_length=512)
    telegram_bot_token: Optional[str] = Field(None, max_length=128)
    telegram_chat_id: Optional[str] = Field(None, max_length=64)
    email_to: Optional[str] = Field(None, max_length=254)
    subscription: Optional[Dict[str, Any]] = None


def _config_from_body(body: ChannelCreate | ChannelUpdate) -> Optional[Dict[str, Any]]:
    config: Dict[str, Any] = {}
    if body.webhook_url:
        config["webhook_url"] = body.webhook_url
    if body.url:
        config["url"] = body.url
    if body.telegram_bot_token:
        config["bot_token"] = body.telegram_bot_token
    if body.telegram_chat_id:
        config["chat_id"] = body.telegram_chat_id
    if body.email_to:
        config["to"] = body.email_to
    if body.subscription:
        config["subscription"] = body.subscription
    return config or None


@router.get("/notifications/providers")
async def list_providers(settings: Settings = Depends(get_settings)):
    return {
        "providers": [
            {"kind": "discord", "available": True},
            {"kind": "slack", "available": True},
            {"kind": "telegram", "available": True},
            {"kind": "webhook", "available": True},
            {"kind": "email", "available": bool(settings.SMTP_HOST)},
            {"kind": "browser_push", "available": bool(settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY)},
        ]
    }


@router.get("/notifications/vapid-public-key")
async def get_vapid_public_key(settings: Settings = Depends(get_settings)):
    if not (settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY):
        return {"status": "unavailable", "reason": "vapid_keys_not_configured"}
    return {"status": "ok", "key": settings.VAPID_PUBLIC_KEY}


@router.get("/notifications/channels")
async def list_channels(db: AsyncSession = Depends(get_db)):
    try:
        rows = await notification_service.list_channels(db)
        return {
            "channels": [notification_service.channel_public_dict(row) for row in rows],
            "count": len(rows),
        }
    except Exception:
        logger.exception("Failed to list notification channels")
        raise HTTPException(500, "Failed to list notification channels")


@router.post("/notifications/channels", status_code=201)
@limiter.limit("30/hour")
async def create_channel(
    request: Request,
    body: ChannelCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        row = await notification_service.create_channel(
            db,
            name=body.name,
            kind=body.kind,
            config=_config_from_body(body),
            enabled=body.enabled,
        )
        return notification_service.channel_public_dict(row)
    except ChannelValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception:
        logger.exception("Failed to create notification channel")
        raise HTTPException(500, "Failed to create notification channel")


@router.put("/notifications/channels/{channel_id}")
async def update_channel(
    channel_id: int,
    body: ChannelUpdate,
    db: AsyncSession = Depends(get_db),
):
    try:
        row = await notification_service.update_channel(
            db,
            channel_id,
            name=body.name,
            enabled=body.enabled,
            config=_config_from_body(body),
        )
        if row is None:
            raise HTTPException(404, f"Channel {channel_id} not found")
        return notification_service.channel_public_dict(row)
    except HTTPException:
        raise
    except ChannelValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception:
        logger.exception("Failed to update notification channel")
        raise HTTPException(500, "Failed to update notification channel")


@router.delete("/notifications/channels/{channel_id}")
async def delete_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        ok = await notification_service.delete_channel(db, channel_id)
        if not ok:
            raise HTTPException(404, f"Channel {channel_id} not found")
        return {"deleted": True, "id": channel_id}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete notification channel")
        raise HTTPException(500, "Failed to delete notification channel")


@router.post("/notifications/channels/{channel_id}/test")
@limiter.limit("10/hour")
async def test_channel(
    request: Request,
    channel_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        row = await db.get(NotificationChannel, channel_id)
        if row is None:
            raise HTTPException(404, f"Channel {channel_id} not found")
        return await notification_service.send_test_message(row)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to send test notification")
        raise HTTPException(500, "Failed to send test notification")


@router.get("/notifications/deliveries")
async def list_deliveries(
    limit: int = Query(100, ge=1, le=500),
    status: Optional[str] = Query(None, pattern="^(pending|sent|failed|skipped)$"),
    alert_event_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        rows = await notification_service.list_deliveries(
            db, limit=limit, status=status, alert_event_id=alert_event_id
        )
        return {
            "deliveries": [
                notification_service.delivery_dict(delivery, channel)
                for delivery, channel in rows
            ],
            "count": len(rows),
        }
    except Exception:
        logger.exception("Failed to list notification deliveries")
        raise HTTPException(500, "Failed to list notification deliveries")


@router.post("/notifications/deliveries/{delivery_id}/retry")
async def retry_delivery(
    delivery_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await notification_service.retry_delivery(db, delivery_id)
        if result is None:
            raise HTTPException(404, f"Delivery {delivery_id} not found")
        delivery, channel = result
        return notification_service.delivery_dict(delivery, channel)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to retry notification delivery")
        raise HTTPException(500, "Failed to retry notification delivery")


@router.post("/notifications/dispatch")
@limiter.limit("30/minute")
async def dispatch_deliveries(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Process due deliveries. Intended for external pollers."""
    try:
        rows = await notification_service.dispatch_pending(db)
        return {
            "attempted": len(rows),
            "deliveries": [
                notification_service.delivery_dict(row, None) for row in rows
            ],
        }
    except Exception:
        logger.exception("Failed to dispatch notification deliveries")
        raise HTTPException(500, "Failed to dispatch notification deliveries")
