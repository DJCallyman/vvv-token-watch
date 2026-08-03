"""Tests for backend.services.alert_engine (Phase 4.5)."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.config import get_settings
from backend.database import Base
from backend.models.db import AlertConfig, AlertEvent
from backend.services.alert_engine import (
    _compare,
    acknowledge_event,
    create_alert_config,
    delete_alert_config,
    evaluate_alerts,
    list_alert_events,
    update_alert_config,
)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_compare_gte():
    assert _compare(80, 75, "gte") is True
    assert _compare(70, 75, "gte") is False
    assert _compare(75, 75, "gte") is True


def test_compare_lte():
    assert _compare(10, 25, "lte") is True
    assert _compare(30, 25, "lte") is False
    assert _compare(25, 25, "lte") is True


def test_compare_defaults_to_gte():
    """Anything other than 'lte' is treated as gte (per implementation)."""
    assert _compare(1, 0, "anything-else") is True
    assert _compare(-1, 0, "anything-else") is False


# ---------------------------------------------------------------------------
# Async DB-backed tests (in-memory SQLite)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_and_list_alert_config(session):
    cfg = await create_alert_config(
        session,
        name="diem high",
        alert_type="usage_percent",
        metric="diem_usage_percent",
        threshold=80.0,
        comparison="gte",
    )
    assert cfg.id is not None

    rows = await list_alert_events(session, unacknowledged_only=False, limit=10)
    assert rows == []  # no events yet


@pytest.mark.asyncio
async def test_update_alert_config_partial(session):
    cfg = await create_alert_config(
        session,
        name="diem high",
        alert_type="usage_percent",
        metric="diem_usage_percent",
        threshold=80.0,
    )
    updated = await update_alert_config(session, cfg.id, threshold=95.0)
    assert updated is not None
    assert updated.threshold == 95.0
    assert updated.name == "diem high"  # untouched


@pytest.mark.asyncio
async def test_delete_alert_config(session):
    cfg = await create_alert_config(
        session,
        name="to-delete",
        alert_type="usage_percent",
        metric="diem_usage_percent",
        threshold=80.0,
    )
    assert await delete_alert_config(session, cfg.id) is True
    assert await delete_alert_config(session, cfg.id) is False


@pytest.mark.asyncio
async def test_evaluate_alerts_creates_event_on_threshold_breach(session):
    cfg = await create_alert_config(
        session,
        name="diem high",
        alert_type="usage_percent",
        metric="diem_usage_percent",
        threshold=80.0,
    )
    events = await evaluate_alerts(session, {"diem_usage_percent": 90.0})
    assert len(events) == 1
    assert events[0].value == pytest.approx(90.0)
    assert events[0].alert_config_id == cfg.id


@pytest.mark.asyncio
async def test_evaluate_alerts_dedup_unacknowledged(session):
    """BUG-01: do not flood — at most one unacknowledged event per config."""
    cfg = await create_alert_config(
        session,
        name="diem high",
        alert_type="usage_percent",
        metric="diem_usage_percent",
        threshold=80.0,
    )
    first = await evaluate_alerts(session, {"diem_usage_percent": 90.0})
    second = await evaluate_alerts(session, {"diem_usage_percent": 95.0})
    assert len(first) == 1
    assert len(second) == 0  # dedup'd

    events = await list_alert_events(session, unacknowledged_only=True)
    assert len(events) == 1


@pytest.mark.asyncio
async def test_evaluate_alerts_respects_cooldown(session):
    """ALERT_COOLDOWN_SECONDS: after acknowledge, do not re-create within window."""
    await create_alert_config(
        session,
        name="vvv low",
        alert_type="price_threshold",
        metric="vvv_price_usd",
        threshold=100.0,
        comparison="lte",  # fire when price <= 100 (below threshold)
    )
    first = await evaluate_alerts(session, {"vvv_price_usd": 50.0})
    assert len(first) == 1
    await acknowledge_event(session, first[0].id)

    # Same value inside the cooldown window — should be suppressed.
    second = await evaluate_alerts(session, {"vvv_price_usd": 50.0})
    assert len(second) == 0


@pytest.mark.asyncio
async def test_evaluate_alerts_below_threshold_no_event(session):
    await create_alert_config(
        session,
        name="diem high",
        alert_type="usage_percent",
        metric="diem_usage_percent",
        threshold=80.0,
    )
    events = await evaluate_alerts(session, {"diem_usage_percent": 50.0})
    assert events == []


@pytest.mark.asyncio
async def test_evaluate_alerts_metric_not_in_metrics(session):
    await create_alert_config(
        session,
        name="diem high",
        alert_type="usage_percent",
        metric="diem_usage_percent",
        threshold=80.0,
    )
    # Caller did not provide the metric — no event.
    events = await evaluate_alerts(session, {"usd_usage_percent": 95.0})
    assert events == []


@pytest.mark.asyncio
async def test_evaluate_alerts_lte(session):
    """lte comparison: fire when value <= threshold (e.g. balance low)."""
    await create_alert_config(
        session,
        name="diem low",
        alert_type="balance_threshold",
        metric="diem_balance",
        threshold=10.0,
        comparison="lte",
    )
    events = await evaluate_alerts(session, {"diem_balance": 5.0})
    assert len(events) == 1
