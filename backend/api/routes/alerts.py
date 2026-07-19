"""Alert configuration and event endpoints."""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.limiter import limiter
from backend.services import alert_engine

logger = logging.getLogger(__name__)
router = APIRouter()


class AlertConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    alert_type: str = Field(..., pattern="^(usage_percent|balance_threshold|price_threshold)$")
    metric: str = Field(..., min_length=1, max_length=64)
    threshold: float
    comparison: str = Field("gte", pattern="^(gte|lte)$")
    enabled: bool = True


class AlertConfigUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    alert_type: Optional[str] = Field(None, pattern="^(usage_percent|balance_threshold|price_threshold)$")
    metric: Optional[str] = Field(None, min_length=1, max_length=64)
    threshold: Optional[float] = None
    comparison: Optional[str] = Field(None, pattern="^(gte|lte)$")
    enabled: Optional[bool] = None


class EvaluateRequest(BaseModel):
    metrics: dict[str, float]


def _config_dict(row) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "alert_type": row.alert_type,
        "metric": row.metric,
        "threshold": row.threshold,
        "comparison": row.comparison,
        "enabled": row.enabled,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _event_dict(row) -> dict:
    return {
        "id": row.id,
        "alert_config_id": row.alert_config_id,
        "triggered_at": row.triggered_at.isoformat() if row.triggered_at else None,
        "message": row.message,
        "value": row.value,
        "acknowledged": row.acknowledged,
    }


@router.get("/alerts")
async def list_alerts(
    enabled_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    try:
        rows = await alert_engine.list_alert_configs(db, enabled_only=enabled_only)
        return {"alerts": [_config_dict(r) for r in rows], "count": len(rows)}
    except Exception:
        logger.exception("Failed to list alerts")
        raise HTTPException(500, "Failed to list alerts")


@router.post("/alerts", status_code=201)
async def create_alert(
    body: AlertConfigCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        row = await alert_engine.create_alert_config(
            db,
            name=body.name,
            alert_type=body.alert_type,
            metric=body.metric,
            threshold=body.threshold,
            comparison=body.comparison,
            enabled=body.enabled,
        )
        return _config_dict(row)
    except Exception:
        logger.exception("Failed to create alert")
        raise HTTPException(500, "Failed to create alert")


@router.put("/alerts/{alert_id}")
async def update_alert(
    alert_id: int,
    body: AlertConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    try:
        row = await alert_engine.update_alert_config(
            db,
            alert_id,
            **body.model_dump(exclude_unset=True),
        )
        if row is None:
            raise HTTPException(404, f"Alert {alert_id} not found")
        return _config_dict(row)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to update alert")
        raise HTTPException(500, "Failed to update alert")


@router.delete("/alerts/{alert_id}")
async def delete_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        ok = await alert_engine.delete_alert_config(db, alert_id)
        if not ok:
            raise HTTPException(404, f"Alert {alert_id} not found")
        return {"deleted": True, "id": alert_id}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete alert")
        raise HTTPException(500, "Failed to delete alert")


@router.get("/alerts/events")
async def list_events(
    unacknowledged_only: bool = False,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    try:
        rows = await alert_engine.list_alert_events(
            db, unacknowledged_only=unacknowledged_only, limit=limit
        )
        return {"events": [_event_dict(r) for r in rows], "count": len(rows)}
    except Exception:
        logger.exception("Failed to list alert events")
        raise HTTPException(500, "Failed to list alert events")


@router.get("/alerts/events/unacknowledged")
async def list_unacknowledged_events(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    try:
        rows = await alert_engine.list_alert_events(
            db, unacknowledged_only=True, limit=limit
        )
        return {"events": [_event_dict(r) for r in rows], "count": len(rows)}
    except Exception:
        logger.exception("Failed to list unacknowledged events")
        raise HTTPException(500, "Failed to list unacknowledged events")


@router.post("/alerts/events/{event_id}/acknowledge")
async def acknowledge_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        row = await alert_engine.acknowledge_event(db, event_id)
        if row is None:
            raise HTTPException(404, f"Event {event_id} not found")
        return _event_dict(row)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to acknowledge event")
        raise HTTPException(500, "Failed to acknowledge event")


@router.post("/alerts/evaluate")
@limiter.limit("30/minute")
async def evaluate_alerts(
    request: Request,
    body: EvaluateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Evaluate enabled alerts against provided metrics (used by pollers)."""
    try:
        events = await alert_engine.evaluate_alerts(db, body.metrics)
        return {"created": len(events), "events": [_event_dict(e) for e in events]}
    except Exception:
        logger.exception("Failed to evaluate alerts")
        raise HTTPException(500, "Failed to evaluate alerts")
