"""Structured AI signal history endpoints (Phase 3)."""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import Settings, get_settings
from backend.core import venicestats_client
from backend.core.venicestats_client import VeniceStatsError
from backend.database import get_db
from backend.services import signal_service

logger = logging.getLogger(__name__)
router = APIRouter()


class SignalCreate(BaseModel):
    kind: str = Field("manual", pattern="^(sentiment|x_sentiment|manual|analysis)$")
    subject: str = Field("vvv", min_length=1, max_length=32)
    direction: str = Field(..., pattern="^(bullish|bearish|neutral)$")
    confidence: float = Field(..., ge=0, le=100)
    rationale: str = Field("", max_length=4000)
    sources: List[str] = Field(default_factory=list, max_length=50)
    metrics: dict = Field(default_factory=dict)
    entry_price_usd: Optional[float] = Field(None, ge=0)


class SignalEvaluate(BaseModel):
    current_price_usd: Optional[float] = Field(None, ge=0)


@router.get("/signals")
async def list_signals(
    limit: int = Query(50, ge=1, le=200),
    subject: Optional[str] = Query(None, max_length=32),
    kind: Optional[str] = Query(None, pattern="^(sentiment|x_sentiment|manual|analysis)$"),
    db: AsyncSession = Depends(get_db),
):
    try:
        rows = await signal_service.list_signals(
            db, limit=limit, subject=subject, kind=kind
        )
        return {
            "signals": [signal_service.signal_dict(row) for row in rows],
            "count": len(rows),
        }
    except Exception:
        logger.exception("Failed to list signals")
        raise HTTPException(500, "Failed to list signals")


@router.post("/signals", status_code=201)
async def create_signal(
    body: SignalCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        row = await signal_service.record_signal(
            db,
            kind=body.kind,
            subject=body.subject,
            direction=body.direction,
            confidence=body.confidence,
            rationale=body.rationale,
            sources=body.sources,
            metrics=body.metrics,
            entry_price_usd=body.entry_price_usd,
        )
        return signal_service.signal_dict(row)
    except Exception:
        logger.exception("Failed to record signal")
        raise HTTPException(500, "Failed to record signal")


@router.post("/signals/{signal_id}/evaluate")
async def evaluate_signal(
    signal_id: int,
    body: SignalEvaluate,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Evaluate a signal against a supplied or freshly fetched VVV price."""
    try:
        current = body.current_price_usd
        if current is None:
            try:
                metrics = await venicestats_client.get_metrics(settings)
                latest = metrics.get("vvvPrice")
                if isinstance(latest, (int, float)):
                    current = float(latest)
            except VeniceStatsError:
                current = None
        row = await signal_service.evaluate_signal(db, signal_id, current)
        if row is None:
            raise HTTPException(404, f"Signal {signal_id} not found")
        return signal_service.signal_dict(row)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to evaluate signal")
        raise HTTPException(500, "Failed to evaluate signal")
