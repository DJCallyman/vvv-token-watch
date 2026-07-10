"""Persist and query price snapshots for historical charts."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.db import PriceSnapshot

logger = logging.getLogger(__name__)


async def record_price_snapshot(
    db: AsyncSession,
    *,
    token_id: str,
    price_usd: Optional[float] = None,
    price_aud: Optional[float] = None,
    market_cap: Optional[float] = None,
    change_24h: Optional[float] = None,
) -> PriceSnapshot:
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
    since = datetime.now(timezone.utc) - _range_to_delta(range_key)
    stmt = (
        select(PriceSnapshot)
        .where(
            PriceSnapshot.token_id == token_id,
            PriceSnapshot.timestamp >= since,
        )
        .order_by(PriceSnapshot.timestamp.asc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
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
