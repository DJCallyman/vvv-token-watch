"""Persist and query price snapshots for historical charts.

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
from backend.models.db import PriceSnapshot

logger = logging.getLogger(__name__)


async def _purge_old_price_snapshots(db: AsyncSession, retention_days: int) -> int:
    if retention_days <= 0:
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    stmt = delete(PriceSnapshot).where(PriceSnapshot.timestamp < cutoff)
    result = await db.execute(stmt)
    await db.commit()
    deleted = result.rowcount or 0
    if deleted:
        logger.info("Purged %s old price snapshots (retention %sd)", deleted, retention_days)
    return deleted


async def record_price_snapshot(
    db: AsyncSession,
    *,
    token_id: str,
    price_usd: Optional[float] = None,
    price_aud: Optional[float] = None,
    market_cap: Optional[float] = None,
    change_24h: Optional[float] = None,
) -> Optional[PriceSnapshot]:
    """Record a price snapshot with dedupe + retention (BUG-04).

    Returns the inserted row, or None if a duplicate (identical values) was skipped.
    """
    settings = get_settings()

    # Dedupe: skip if the last row for this token has identical numeric values.
    last_stmt = (
        select(PriceSnapshot)
        .where(PriceSnapshot.token_id == token_id)
        .order_by(PriceSnapshot.timestamp.desc())
        .limit(1)
    )
    last_res = await db.execute(last_stmt)
    last = last_res.scalars().first()
    if last is not None:
        def _eq(a: Optional[float], b: Optional[float]) -> bool:
            if a is None and b is None:
                return True
            if a is None or b is None:
                return False
            return abs(a - b) < 1e-9

        if (
            _eq(last.price_usd, price_usd)
            and _eq(last.price_aud, price_aud)
            and _eq(last.market_cap, market_cap)
            and _eq(last.change_24h, change_24h)
        ):
            try:
                await _purge_old_price_snapshots(db, settings.SNAPSHOT_RETENTION_DAYS)
            except Exception:
                logger.exception("Purge failed during deduped price snapshot")
            return None

    row = PriceSnapshot(
        token_id=token_id,
        price_usd=price_usd,
        price_aud=price_aud,
        market_cap=market_cap,
        change_24h=change_24h,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    try:
        await _purge_old_price_snapshots(db, settings.SNAPSHOT_RETENTION_DAYS)
    except Exception:
        logger.exception("Purge failed after recording price snapshot")

    logger.debug("Recorded price snapshot token=%s usd=%s", token_id, price_usd)
    return row


def _range_to_delta(range_key: str) -> timedelta:
    mapping = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
    }
    return mapping.get(range_key, timedelta(days=7))


async def get_price_history(
    db: AsyncSession,
    *,
    token_id: str,
    range_key: str = "7d",
    limit: int = 2000,
) -> List[Dict[str, Any]]:
    """Return the most recent price snapshots for the token within the range window.

    BUG-03 fix: order DESC + LIMIT to get newest rows, then reverse to return
    ascending order for charts. The `since` filter (derived from range) already
    excludes data older than the window.
    """
    since = datetime.now(timezone.utc) - _range_to_delta(range_key)
    stmt = (
        select(PriceSnapshot)
        .where(
            PriceSnapshot.token_id == token_id,
            PriceSnapshot.timestamp >= since,
        )
        .order_by(PriceSnapshot.timestamp.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    rows.reverse()  # ascending for the caller
    return [
        {
            "timestamp": row.timestamp.isoformat() if row.timestamp else None,
            "token_id": row.token_id,
            "price_usd": row.price_usd,
            "price_aud": row.price_aud,
            "market_cap": row.market_cap,
            "change_24h": row.change_24h,
        }
        for row in rows
    ]
