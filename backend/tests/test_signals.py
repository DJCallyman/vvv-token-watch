"""Tests for Phase 3 structured signal history and outcome tracking."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.database import Base
from backend.services import signal_service


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        yield s
    await engine.dispose()


# ---------------------------------------------------------------------------
# Pure outcome evaluation
# ---------------------------------------------------------------------------


def test_bullish_outcome_hit_and_miss():
    hit = signal_service.evaluate_outcome("bullish", 100.0, 105.0)
    assert hit["status"] == "hit"
    miss = signal_service.evaluate_outcome("bullish", 100.0, 95.0)
    assert miss["status"] == "miss"


def test_bearish_outcome_hit_and_miss():
    assert signal_service.evaluate_outcome("bearish", 100.0, 95.0)["status"] == "hit"
    assert signal_service.evaluate_outcome("bearish", 100.0, 105.0)["status"] == "miss"


def test_neutral_uses_documented_band():
    assert signal_service.evaluate_outcome("neutral", 100.0, 100.5)["status"] == "hit"
    assert signal_service.evaluate_outcome("neutral", 100.0, 103.0)["status"] == "miss"
    assert "±1.0%" in signal_service.evaluate_outcome("neutral", 100.0, 103.0)["note"]


def test_missing_prices_stay_pending():
    assert signal_service.evaluate_outcome("bullish", None, 100.0)["status"] == "pending"
    assert signal_service.evaluate_outcome("bullish", 100.0, None)["status"] == "pending"
    assert signal_service.evaluate_outcome("bullish", 0.0, 100.0)["status"] == "pending"


def test_extract_entry_price_shapes():
    assert signal_service.extract_entry_price({"vvv_price_usd": 1.5}) == 1.5
    assert signal_service.extract_entry_price({"vvv": {"usd": 2.5}}) == 2.5
    assert signal_service.extract_entry_price({"diem": {"usd": 1.0}}) is None
    assert signal_service.extract_entry_price(None) is None


# ---------------------------------------------------------------------------
# DB-backed recording and evaluation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_list_and_evaluate_signal(session):
    row = await signal_service.record_signal(
        session,
        kind="analysis",
        direction="bullish",
        confidence=120.0,  # clamped
        rationale="momentum",
        sources=["https://example.com/a"],
        metrics={"key_events": ["listing"]},
        entry_price_usd=100.0,
    )
    assert row.confidence == 100.0
    assert row.outcome_status == "pending"

    listed = await signal_service.list_signals(session, limit=10)
    assert len(listed) == 1
    payload = signal_service.signal_dict(listed[0])
    assert payload["sources"] == ["https://example.com/a"]
    assert payload["metrics"]["key_events"] == ["listing"]

    evaluated = await signal_service.evaluate_signal(session, row.id, 110.0)
    assert evaluated is not None
    assert evaluated.outcome_status == "hit"
    assert evaluated.outcome_value_usd == pytest.approx(110.0)


@pytest.mark.asyncio
async def test_evaluate_signal_with_missing_price_stays_pending(session):
    row = await signal_service.record_signal(
        session, kind="manual", direction="bearish", confidence=50.0
    )
    evaluated = await signal_service.evaluate_signal(session, row.id, None)
    assert evaluated is not None
    assert evaluated.outcome_status == "pending"
    assert evaluated.evaluated_at is None


@pytest.mark.asyncio
async def test_evaluate_missing_signal_returns_none(session):
    assert await signal_service.evaluate_signal(session, 42, 1.0) is None
