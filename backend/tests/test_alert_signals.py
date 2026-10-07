"""Tests for Slice 2.2 signal alerts (rate of change + anomaly)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.database import Base
from backend.services import alert_engine
from backend.services.alert_engine import (
    acknowledge_event,
    compute_anomaly_zscore,
    compute_rate_of_change,
    create_alert_config,
    evaluate_alerts,
    evaluate_alerts_detailed,
    validate_alert_definition,
)


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        yield s
    await engine.dispose()


def _points(values, *, start=None, step_seconds=60):
    start = start or datetime.now(timezone.utc) - timedelta(minutes=len(values))
    return [
        {"timestamp": (start + timedelta(seconds=index * step_seconds)).isoformat(), "value": value}
        for index, value in enumerate(values)
    ]


# ---------------------------------------------------------------------------
# Pure signal math
# ---------------------------------------------------------------------------


def test_rate_of_change_fires_for_reference_inside_window():
    now = datetime.now(timezone.utc)
    points = [
        {"timestamp": (now - timedelta(minutes=30)).isoformat(), "value": 100},
        {"timestamp": (now - timedelta(minutes=20)).isoformat(), "value": 101},
        {"timestamp": now.isoformat(), "value": 110},
    ]
    roc = compute_rate_of_change(
        points, window_seconds=900, latest_value=110, latest_timestamp=now
    )
    assert roc == pytest.approx((110 - 101) / 101 * 100)


def test_rate_of_change_returns_none_without_reference_point():
    now = datetime.now(timezone.utc)
    points = [
        {"timestamp": (now - timedelta(seconds=60)).isoformat(), "value": 100},
        {"timestamp": now.isoformat(), "value": 110},
    ]
    # Window requires a point at/before now-3600s; the series starts 60s ago.
    assert compute_rate_of_change(
        points, window_seconds=3600, latest_value=110, latest_timestamp=now
    ) is None


def test_rate_of_change_returns_none_for_zero_reference():
    now = datetime.now(timezone.utc)
    points = [
        {"timestamp": (now - timedelta(hours=2)).isoformat(), "value": 0},
        {"timestamp": now.isoformat(), "value": 5},
    ]
    assert compute_rate_of_change(
        points, window_seconds=3600, latest_value=5, latest_timestamp=now
    ) is None


def test_anomaly_requires_minimum_samples():
    assert compute_anomaly_zscore([1, 2, 3], min_samples=10, latest_value=50) is None


def test_anomaly_returns_none_for_zero_variance():
    values = [5.0] * 12
    assert compute_anomaly_zscore(values, min_samples=10, latest_value=99.0) is None


def test_anomaly_zscore_is_deterministic():
    values = _points([10, 11, 9, 10, 11, 9, 10, 11, 9, 10, 11, 9])
    z = compute_anomaly_zscore(values, min_samples=10, latest_value=12)
    assert z is not None
    assert z > 0


def test_validate_alert_definition():
    assert validate_alert_definition("rate_of_change", "vvv_price_usd") is None
    assert validate_alert_definition("anomaly", "diem_balance", min_samples=5) is None
    assert validate_alert_definition("rate_of_change", "vvv_price_usd", window_seconds=10) is not None
    assert validate_alert_definition("usage_percent", "vvv_price_usd") is not None
    assert validate_alert_definition("anomaly", "vvv_price_usd", min_samples=1) is not None


# ---------------------------------------------------------------------------
# DB-backed evaluation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_of_change_triggers_and_dedupes(session, monkeypatch):
    monkeypatch.setattr(alert_engine, "get_settings", lambda: type("S", (), {"ALERT_COOLDOWN_SECONDS": 0})())
    await create_alert_config(
        session,
        name="pump",
        alert_type="rate_of_change",
        metric="vvv_price_usd",
        threshold=5.0,
        window_seconds=900,
    )
    now = datetime.now(timezone.utc)
    history = {
        "vvv_price_usd": [
            {"timestamp": (now - timedelta(minutes=30)).isoformat(), "value": 100},
            {"timestamp": (now - timedelta(minutes=20)).isoformat(), "value": 101},
            {"timestamp": now.isoformat(), "value": 110},
        ]
    }

    first = await evaluate_alerts(session, {"vvv_price_usd": 110}, history)
    second = await evaluate_alerts(session, {"vvv_price_usd": 110}, history)
    assert len(first) == 1
    assert len(second) == 0  # unacknowledged event blocks duplicates
    assert "rate of change" in first[0].message


@pytest.mark.asyncio
async def test_rate_of_change_insufficient_history_is_skipped(session, monkeypatch):
    monkeypatch.setattr(alert_engine, "get_settings", lambda: type("S", (), {"ALERT_COOLDOWN_SECONDS": 0})())
    await create_alert_config(
        session,
        name="pump",
        alert_type="rate_of_change",
        metric="vvv_price_usd",
        threshold=5.0,
        window_seconds=900,
    )
    events, skipped = await evaluate_alerts_detailed(
        session, {"vvv_price_usd": 110}, {"vvv_price_usd": _points([110])}
    )
    assert events == []
    assert skipped and skipped[0]["reason"] == "insufficient_history"


@pytest.mark.asyncio
async def test_anomaly_triggers_and_rearms_after_ack(session, monkeypatch):
    monkeypatch.setattr(alert_engine, "get_settings", lambda: type("S", (), {"ALERT_COOLDOWN_SECONDS": 0})())
    await create_alert_config(
        session,
        name="spike",
        alert_type="anomaly",
        metric="diem_price_usd",
        threshold=2.0,
        min_samples=10,
    )
    baseline = [10, 11, 9, 10, 11, 9, 10, 11, 9, 10, 11, 9]
    history = {"diem_price_usd": _points(baseline)}

    events = await evaluate_alerts(session, {"diem_price_usd": 20.0}, history)
    assert len(events) == 1
    await acknowledge_event(session, events[0].id)

    # Cooldown is 0, so a still-breaching value re-arms immediately after ack.
    rearmed = await evaluate_alerts(session, {"diem_price_usd": 20.0}, history)
    assert len(rearmed) == 1


@pytest.mark.asyncio
async def test_anomaly_below_threshold_no_event(session, monkeypatch):
    monkeypatch.setattr(alert_engine, "get_settings", lambda: type("S", (), {"ALERT_COOLDOWN_SECONDS": 0})())
    await create_alert_config(
        session,
        name="spike",
        alert_type="anomaly",
        metric="diem_price_usd",
        threshold=5.0,
        min_samples=10,
    )
    baseline = [10, 11, 9, 10, 11, 9, 10, 11, 9, 10, 11, 9]
    events = await evaluate_alerts(
        session, {"diem_price_usd": 11.0}, {"diem_price_usd": _points(baseline)}
    )
    assert events == []


@pytest.mark.asyncio
async def test_threshold_alerts_still_work_with_history_argument(session, monkeypatch):
    monkeypatch.setattr(alert_engine, "get_settings", lambda: type("S", (), {"ALERT_COOLDOWN_SECONDS": 0})())
    await create_alert_config(
        session,
        name="high usage",
        alert_type="usage_percent",
        metric="diem_usage_percent",
        threshold=80.0,
    )
    events = await evaluate_alerts(
        session, {"diem_usage_percent": 90.0}, {"diem_usage_percent": _points([1, 2, 3])}
    )
    assert len(events) == 1
