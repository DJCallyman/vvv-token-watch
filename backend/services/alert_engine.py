"""Alert threshold evaluation and event creation.

Slice 2.2 adds two deterministic signal alert types:

* ``rate_of_change`` — percentage change between the latest value and the
  value observed at least ``window_seconds`` ago. Requires at least two
  historical points, one of them at or before the window cutoff. Default
  window is 3600 seconds when the config does not set one.
* ``anomaly`` — z-score of the latest value against the mean and population
  standard deviation of the earlier samples. Requires ``min_samples`` baseline
  points (default 10). When the baseline has zero variance the signal is
  skipped rather than treated as an anomaly.

Both signal types accept an optional ``history`` mapping on the evaluate call:
``{metric: [{"timestamp": iso-or-datetime, "value": number}, ...]}``.
Insufficient history never fires an alert; it is reported as ``skipped`` so
callers can surface the missing-data state.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.models.db import AlertConfig, AlertEvent

logger = logging.getLogger(__name__)

ALERT_TYPES = (
    "usage_percent",
    "balance_threshold",
    "price_threshold",
    "rate_of_change",
    "anomaly",
)

ALLOWED_METRICS: Dict[str, frozenset] = {
    "usage_percent": frozenset({"diem_usage_percent", "usd_usage_percent"}),
    "balance_threshold": frozenset({"diem_balance", "usd_balance"}),
    "price_threshold": frozenset({"vvv_price_usd", "diem_price_usd"}),
    "rate_of_change": frozenset(
        {
            "vvv_price_usd",
            "diem_price_usd",
            "diem_balance",
            "usd_balance",
            "diem_usage_percent",
            "usd_usage_percent",
        }
    ),
    "anomaly": frozenset(
        {
            "vvv_price_usd",
            "diem_price_usd",
            "diem_balance",
            "usd_balance",
            "diem_usage_percent",
            "usd_usage_percent",
        }
    ),
}

DEFAULT_WINDOW_SECONDS = 3600
DEFAULT_MIN_SAMPLES = 10
MAX_HISTORY_POINTS = 5000


def validate_alert_definition(
    alert_type: str,
    metric: str,
    window_seconds: Optional[int] = None,
    min_samples: Optional[int] = None,
) -> Optional[str]:
    """Return a human-readable error when the definition is invalid, else None."""
    if alert_type not in ALLOWED_METRICS:
        return f"Unknown alert type '{alert_type}'"
    if metric not in ALLOWED_METRICS[alert_type]:
        return f"Metric '{metric}' is not valid for alert type '{alert_type}'"
    if alert_type == "rate_of_change":
        if window_seconds is not None and not 60 <= window_seconds <= 2_592_000:
            return "window_seconds must be between 60 and 2592000"
    if alert_type == "anomaly":
        if min_samples is not None and not 2 <= min_samples <= 1000:
            return "min_samples must be between 2 and 1000"
        if window_seconds is not None and not 60 <= window_seconds <= 2_592_000:
            return "window_seconds must be between 60 and 2592000"
    return None


def _compare(value: float, threshold: float, comparison: str) -> bool:
    if comparison == "lte":
        return value <= threshold
    # default gte
    return value >= threshold


def _coerce_timestamp(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _normalize_history(points: Iterable[Any]) -> List[Tuple[datetime, float]]:
    normalized: List[Tuple[datetime, float]] = []
    for point in points:
        if isinstance(point, dict):
            ts = _coerce_timestamp(point.get("timestamp"))
            value = point.get("value")
        else:
            ts = _coerce_timestamp(getattr(point, "timestamp", None))
            value = getattr(point, "value", None)
        if ts is None or not isinstance(value, (int, float)):
            continue
        normalized.append((ts, float(value)))
    normalized.sort(key=lambda item: item[0])
    return normalized[-MAX_HISTORY_POINTS:]


def compute_rate_of_change(
    points: Iterable[Any],
    *,
    window_seconds: int,
    latest_value: Optional[float] = None,
    latest_timestamp: Optional[datetime] = None,
) -> Optional[float]:
    """Return percent change vs the point at/before the window cutoff.

    Returns ``None`` when history is insufficient or the reference value is 0.
    The reference is the most recent point at or before ``latest - window``.
    """
    series = _normalize_history(points)
    if latest_timestamp is not None:
        latest_ts = latest_timestamp if latest_timestamp.tzinfo else latest_timestamp.replace(tzinfo=timezone.utc)
        latest_ts = latest_ts.astimezone(timezone.utc)
    elif series:
        latest_ts = series[-1][0]
    else:
        return None
    if latest_value is None:
        if not series:
            return None
        latest_value = series[-1][1]
    cutoff = latest_ts - timedelta(seconds=max(60, int(window_seconds)))
    reference: Optional[float] = None
    for ts, value in series:
        if ts <= cutoff:
            reference = value
        else:
            break
    if reference is None or not isinstance(latest_value, (int, float)):
        return None
    if reference == 0:
        return None
    return ((float(latest_value) - reference) / abs(reference)) * 100.0


def compute_anomaly_zscore(
    points: Iterable[Any],
    *,
    min_samples: int,
    latest_value: Optional[float] = None,
) -> Optional[float]:
    """Return the z-score of the latest value vs the baseline samples.

    The baseline is every history point except the last one. Requires at
    least ``min_samples`` baseline values and non-zero population standard
    deviation; otherwise returns ``None`` (insufficient history / no variance).
    """
    series = _normalize_history(points)
    if not series:
        return None
    if latest_value is None:
        baseline = [value for _, value in series[:-1]]
        latest_value = series[-1][1]
    else:
        baseline = [value for _, value in series]
    if len(baseline) < max(2, int(min_samples)):
        return None
    if not isinstance(latest_value, (int, float)):
        return None
    mean = sum(baseline) / len(baseline)
    variance = sum((value - mean) ** 2 for value in baseline) / len(baseline)
    stdev = math.sqrt(variance)
    if stdev <= 0:
        return None
    return (float(latest_value) - mean) / stdev


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
    window_seconds: Optional[int] = None,
    min_samples: Optional[int] = None,
) -> AlertConfig:
    row = AlertConfig(
        name=name,
        alert_type=alert_type,
        metric=metric,
        threshold=threshold,
        comparison=comparison,
        enabled=enabled,
        window_seconds=window_seconds,
        min_samples=min_samples,
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
    # Remove delivery rows first so the delete works on databases without
    # enforced FK cascades (e.g. SQLite in tests).
    from sqlalchemy import delete as sa_delete

    from backend.models.db import NotificationDelivery

    event_ids = select(AlertEvent.id).where(AlertEvent.alert_config_id == alert_id)
    await db.execute(
        sa_delete(NotificationDelivery).where(
            NotificationDelivery.alert_event_id.in_(event_ids)
        )
    )
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


async def _event_is_deduped(
    db: AsyncSession,
    cfg: AlertConfig,
    cooldown: int,
) -> bool:
    existing_unack = await db.execute(
        select(AlertEvent)
        .where(AlertEvent.alert_config_id == cfg.id)
        .where(AlertEvent.acknowledged.is_(False))
        .order_by(AlertEvent.triggered_at.desc())
        .limit(1)
    )
    if existing_unack.scalars().first() is not None:
        return True

    if cooldown > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=cooldown)
        recent = await db.execute(
            select(AlertEvent)
            .where(AlertEvent.alert_config_id == cfg.id)
            .where(AlertEvent.triggered_at >= cutoff)
            .order_by(AlertEvent.triggered_at.desc())
            .limit(1)
        )
        if recent.scalars().first() is not None:
            return True
    return False


def _signal_value(
    cfg: AlertConfig,
    metrics: Dict[str, float],
    history: Dict[str, Any],
    latest_timestamp: Optional[datetime],
) -> Tuple[Optional[float], Optional[str], Optional[str]]:
    """Return (signal, skip_reason, unit_label) for signal alert types."""
    points = history.get(cfg.metric) or []
    current = metrics.get(cfg.metric)
    if cfg.alert_type == "rate_of_change":
        window = int(cfg.window_seconds or DEFAULT_WINDOW_SECONDS)
        roc = compute_rate_of_change(
            points,
            window_seconds=window,
            latest_value=float(current) if isinstance(current, (int, float)) else None,
            latest_timestamp=latest_timestamp,
        )
        if roc is None:
            return None, "insufficient_history", "pct"
        return roc, None, "pct"
    if cfg.alert_type == "anomaly":
        min_samples = int(cfg.min_samples or DEFAULT_MIN_SAMPLES)
        zscore = compute_anomaly_zscore(
            points,
            min_samples=min_samples,
            latest_value=float(current) if isinstance(current, (int, float)) else None,
        )
        if zscore is None:
            return None, "insufficient_history", "zscore"
        return zscore, None, "zscore"
    if not isinstance(current, (int, float)):
        return None, "missing_metric", None
    return float(current), None, None


async def evaluate_alerts_detailed(
    db: AsyncSession,
    metrics: Dict[str, float],
    history: Optional[Dict[str, Any]] = None,
    latest_timestamp: Optional[datetime] = None,
) -> Tuple[List[AlertEvent], List[Dict[str, Any]]]:
    """Evaluate enabled alert configurations.

    Returns ``(created_events, skipped)`` where each skipped entry is
    ``{"alert_id": int, "name": str, "metric": str, "reason": str}``.
    """
    configs = await list_alert_configs(db, enabled_only=True)
    created: List[AlertEvent] = []
    skipped: List[Dict[str, Any]] = []
    settings = get_settings()
    cooldown = max(0, int(settings.ALERT_COOLDOWN_SECONDS or 0))
    history = history or {}

    for cfg in configs:
        signal, skip_reason, unit = _signal_value(cfg, metrics, history, latest_timestamp)
        if skip_reason is not None:
            # Legacy threshold alerts simply skip metrics that were not supplied.
            if not (cfg.alert_type in ("rate_of_change", "anomaly")):
                continue
            skipped.append(
                {
                    "alert_id": cfg.id,
                    "name": cfg.name,
                    "metric": cfg.metric,
                    "reason": skip_reason,
                }
            )
            continue
        if signal is None:
            continue
        if not _compare(signal, cfg.threshold, cfg.comparison or "gte"):
            continue
        if await _event_is_deduped(db, cfg, cooldown):
            continue

        if unit == "pct":
            window = int(cfg.window_seconds or DEFAULT_WINDOW_SECONDS)
            message = (
                f"{cfg.name}: rate of change for {cfg.metric} over "
                f"{window}s is {signal:+.2f}% ({cfg.comparison} {cfg.threshold:.2f}%)"
            )
        elif unit == "zscore":
            message = (
                f"{cfg.name}: anomaly z-score for {cfg.metric} is "
                f"{signal:+.2f} ({cfg.comparison} {cfg.threshold:.2f})"
            )
        else:
            message = (
                f"{cfg.name}: {cfg.metric}={signal:.4f} "
                f"{cfg.comparison} {cfg.threshold:.4f}"
            )
        event = AlertEvent(
            alert_config_id=cfg.id,
            message=message,
            value=signal,
            acknowledged=False,
        )
        db.add(event)
        created.append(event)

    if created:
        await db.commit()
        for event in created:
            await db.refresh(event)
        logger.info("Created %s alert event(s)", len(created))

    return created, skipped


async def evaluate_alerts(
    db: AsyncSession,
    metrics: Dict[str, float],
    history: Optional[Dict[str, Any]] = None,
) -> List[AlertEvent]:
    """Evaluate enabled alert configurations against the metrics map.

    The map can contain ``diem_usage_percent``, ``usd_usage_percent``,
    ``diem_balance``, ``usd_balance``, ``vvv_price_usd``, and
    ``diem_price_usd``. Create at most one unacknowledged event per alert.
    Also apply ``ALERT_COOLDOWN_SECONDS`` after an acknowledgment.
    """
    events, _ = await evaluate_alerts_detailed(db, metrics, history)
    return events
