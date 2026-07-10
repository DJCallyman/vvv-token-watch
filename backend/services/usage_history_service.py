"""Persist usage snapshots for historical trend charts."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.db import UsageSnapshot

logger = logging.getLogger(__name__)


async def record_usage_snapshot(
    db: AsyncSession,
    *,
    scope: str,
    diem: float,
    usd: float,
    bundled_credits: float = 0.0,
    epoch_start: Optional[str] = None,
    next_epoch: Optional[str] = None,
    target_date: Optional[str] = None,
) -> UsageSnapshot:
    row = UsageSnapshot(
        scope=scope,
        diem=diem,
        usd=usd,
        bundled_credits=bundled_credits,
        epoch_start=epoch_start,
        next_epoch=next_epoch,
        target_date=target_date,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    logger.debug("Recorded usage snapshot scope=%s diem=%s usd=%s", scope, diem, usd)
    return row


async def get_usage_trends(
    db: AsyncSession,
    *,
    scope: str = "epoch",
    limit: int = 500,
) -> List[Dict[str, Any]]:
    stmt = (
        select(UsageSnapshot)
        .where(UsageSnapshot.scope == scope)
        .order_by(UsageSnapshot.timestamp.asc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [
        {
            "timestamp": row.timestamp.isoformat() if row.timestamp else None,
            "diem": row.diem,
            "usd": row.usd,
            "bundled_credits": row.bundled_credits,
            "epoch_start": row.epoch_start,
            "next_epoch": row.next_epoch,
            "target_date": row.target_date,
            "scope": row.scope,
        }
        for row in rows
    ]
