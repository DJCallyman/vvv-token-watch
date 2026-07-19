"""Persist usage snapshots for historical trend charts.

BUG-04: request-path writes now dedupe (skip identical consecutive values)
and trigger retention purge based on SNAPSHOT_RETENTION_DAYS.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.models.db import UsageSnapshot

logger = logging.getLogger(__name__)


async def _purge_old_usage_snapshots(db: AsyncSession, retention_days: int) -> int:
    if retention_days <= 0:
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    stmt = delete(UsageSnapshot).where(UsageSnapshot.timestamp < cutoff)
    result = await db.execute(stmt)
    await db.commit()
    deleted = result.rowcount or 0
    if deleted:
        logger.info("Purged %s old usage snapshots (retention %sd)", deleted, retention_days)
    return deleted


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
) -> Optional[UsageSnapshot]:
    """Record a usage snapshot with dedupe + retention (BUG-04).

    Returns the inserted row, or None if a duplicate (identical values) was skipped.
    """
    settings = get_settings()

    # Dedupe: skip if the last row for this scope has identical numeric values.
    last_stmt = (
        select(UsageSnapshot)
        .where(UsageSnapshot.scope == scope)
        .order_by(UsageSnapshot.timestamp.desc())
        .limit(1)
    )
    last_res = await db.execute(last_stmt)
    last = last_res.scalars().first()
    if last is not None:
        if (
            abs((last.diem or 0) - (diem or 0)) < 1e-9
            and abs((last.usd or 0) - (usd or 0)) < 1e-9
            and abs((last.bundled_credits or 0) - (bundled_credits or 0)) < 1e-9
        ):
            # Still run purge occasionally even on skip
            try:
                await _purge_old_usage_snapshots(db, settings.SNAPSHOT_RETENTION_DAYS)
            except Exception:
                logger.exception("Purge failed during deduped usage snapshot")
            return None

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

    # Retention purge
    try:
        await _purge_old_usage_snapshots(db, settings.SNAPSHOT_RETENTION_DAYS)
    except Exception:
        logger.exception("Purge failed after recording usage snapshot")

    logger.debug("Recorded usage snapshot scope=%s diem=%s usd=%s", scope, diem, usd)
    return row


async def get_usage_trends(
    db: AsyncSession,
    *,
    scope: str = "epoch",
    limit: int = 500,
    since: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Return the most recent `limit` snapshots for the given scope.

    BUG-03 fix: we order DESC + LIMIT to get the newest rows, then reverse
    so the caller receives ascending order (suitable for charts). An optional
    `since` filter can be used for scope-aware windows.
    """
    stmt = select(UsageSnapshot).where(UsageSnapshot.scope == scope)
    if since is not None:
        stmt = stmt.where(UsageSnapshot.timestamp >= since)
    stmt = stmt.order_by(UsageSnapshot.timestamp.desc()).limit(limit)

    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    # Reverse so the result is ascending (oldest of the selected window first)
    rows.reverse()

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
