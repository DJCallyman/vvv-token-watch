"""Alert threshold evaluation and event creation."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.db import AlertConfig, AlertEvent

logger = logging.getLogger(__name__)


def _compare(value: float, threshold: float, comparison: str) -> bool:
    if comparison == "lte":
        return value <= threshold
    # default gte
    return value >= threshold


async def list_alert_configs(db: AsyncSession, enabled_only: bool = False) -> List[AlertConfig]:
    stmt = select(AlertConfig).order_by(AlertConfig.id.asc())
    if enabled_only:
        stmt = stmt.where(AlertConfig.enabled.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_alert_config(
    db: AsyncSession,
    *,
    name: str,
    alert_type: str,
    metric: str,
    threshold: float,
    comparison: str = "gte",
    enabled: bool = True,
) -> AlertConfig:
    row = AlertConfig(
        name=name,
        alert_type=alert_type,
        metric=metric,
        threshold=threshold,
        comparison=comparison,
        enabled=enabled,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def update_alert_config(
    db: AsyncSession,
    alert_id: int,
    **fields: Any,
) -> Optional[AlertConfig]:
    row = await db.get(AlertConfig, alert_id)
    if row is None:
        return None
    for key, value in fields.items():
        if value is not None and hasattr(row, key):
            setattr(row, key, value)
    await db.commit()
    await db.refresh(row)
    return row


async def delete_alert_config(db: AsyncSession, alert_id: int) -> bool:
    row = await db.get(AlertConfig, alert_id)
    if row is None:
        return False
    await db.delete(row)
    await db.commit()
    return True


async def list_alert_events(
    db: AsyncSession,
    *,
    unacknowledged_only: bool = False,
    limit: int = 100,
) -> List[AlertEvent]:
    stmt = select(AlertEvent).order_by(AlertEvent.triggered_at.desc()).limit(limit)
    if unacknowledged_only:
        stmt = stmt.where(AlertEvent.acknowledged.is_(False))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def acknowledge_event(db: AsyncSession, event_id: int) -> Optional[AlertEvent]:
    row = await db.get(AlertEvent, event_id)
    if row is None:
        return None
    row.acknowledged = True
    await db.commit()
    await db.refresh(row)
    return row


async def evaluate_alerts(
    db: AsyncSession,
    metrics: Dict[str, float],
) -> List[AlertEvent]:
    """Evaluate enabled alert configs against a metrics map.

    metrics keys examples:
      diem_usage_percent, usd_usage_percent, diem_balance, usd_balance,
      vvv_price_usd, diem_price_usd
    """
    configs = await list_alert_configs(db, enabled_only=True)
    created: List[AlertEvent] = []

    for cfg in configs:
        if cfg.metric not in metrics:
            continue
        value = float(metrics[cfg.metric])
        if not _compare(value, cfg.threshold, cfg.comparison or "gte"):
            continue

        message = (
            f"{cfg.name}: {cfg.metric}={value:.4f} "
            f"{cfg.comparison} {cfg.threshold:.4f}"
        )
        event = AlertEvent(
            alert_config_id=cfg.id,
            message=message,
            value=value,
            acknowledged=False,
        )
        db.add(event)
        created.append(event)

    if created:
        await db.commit()
        for event in created:
            await db.refresh(event)
        logger.info("Created %s alert event(s)", len(created))

    return created
