"""Tests for the shared billing pagination helpers (Phase 3.1)."""

from __future__ import annotations

import pytest

from backend.core import billing_pagination as bp
from backend.tests.conftest import FakeResponse, FakeVeniceAPIClient


@pytest.mark.asyncio
async def test_cursor_walk_collects_all_pages() -> None:
    client = FakeVeniceAPIClient()
    client.queue(
        "/billing/usage-history",
        [
            FakeResponse(status_code=200, json_data={
                "data": [{"entry": 1}, {"entry": 2}],
                "nextCursor": "c2",
            }),
            FakeResponse(status_code=200, json_data={
                "data": [{"entry": 3}],
                "nextCursor": "c3",
            }),
            FakeResponse(status_code=200, json_data={
                "data": [{"entry": 4}],
                # no nextCursor — should terminate
            }),
        ],
    )
    entries = await bp.walk_billing_usage_history(
        client, "2025-01-01T00:00:00Z", "2025-01-02T00:00:00Z"
    )
    assert entries == [{"entry": 1}, {"entry": 2}, {"entry": 3}, {"entry": 4}]


@pytest.mark.asyncio
async def test_first_request_omits_cursor_uses_filters() -> None:
    client = FakeVeniceAPIClient()
    client.queue(
        "/billing/usage-history",
        [
            FakeResponse(status_code=200, json_data={
                "data": [{"entry": 1}],
                "nextCursor": "c2",
            }),
            FakeResponse(status_code=200, json_data={"data": [{"entry": 2}]}),
        ],
    )
    entries = await bp.walk_billing_usage_history(
        client, "2025-01-01T00:00:00Z", "2025-01-02T00:00:00Z"
    )
    assert entries == [{"entry": 1}, {"entry": 2}]


@pytest.mark.asyncio
async def test_403_raises_usage_history_unavailable() -> None:
    client = FakeVeniceAPIClient()
    client.queue(
        "/billing/usage-history",
        [FakeResponse(status_code=403, json_data={"error": "forbidden"})],
    )
    with pytest.raises(bp.UsageHistoryUnavailable) as exc_info:
        await bp.walk_billing_usage_history(
            client, "2025-01-01T00:00:00Z", "2025-01-02T00:00:00Z"
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_410_raises_usage_history_unavailable() -> None:
    client = FakeVeniceAPIClient()
    client.queue(
        "/billing/usage-history",
        [FakeResponse(status_code=410, json_data={})],
    )
    with pytest.raises(bp.UsageHistoryUnavailable) as exc_info:
        await bp.walk_billing_usage_history(
            client, "2025-01-01T00:00:00Z", "2025-01-02T00:00:00Z"
        )
    assert exc_info.value.status_code == 410


@pytest.mark.asyncio
async def test_legacy_410_raises_billing_usage_deprecated() -> None:
    client = FakeVeniceAPIClient()
    client.queue(
        "/billing/usage",
        [FakeResponse(status_code=410, json_data={})],
    )
    with pytest.raises(bp.BillingUsageDeprecated) as exc_info:
        await bp.walk_billing_usage_legacy(
            client, "2025-01-01T00:00:00Z", "2025-01-02T00:00:00Z"
        )
    assert exc_info.value.status_code == 410
    assert exc_info.value.replacement == "/billing/usage-history"


@pytest.mark.asyncio
async def test_legacy_walks_until_pagination_done() -> None:
    client = FakeVeniceAPIClient()
    client.queue(
        "/billing/usage",
        [
            FakeResponse(status_code=200, json_data={
                "data": [{"a": 1}],
                "pagination": {"totalPages": 2},
            }),
            FakeResponse(status_code=200, json_data={
                "data": [{"b": 1}],
                "pagination": {"totalPages": 2},
            }),
        ],
    )
    entries = await bp.walk_billing_usage_legacy(
        client, "2025-01-01T00:00:00Z", "2025-01-02T00:00:00Z"
    )
    assert entries == [{"a": 1}, {"b": 1}]


@pytest.mark.asyncio
async def test_max_pages_caps_cursor_walk(monkeypatch) -> None:
    """Verify cursor walk stops after max_pages and returns what it has."""
    monkeypatch.setattr(bp.settings, "API_MAX_PAGES", 2, raising=False)
    client = FakeVeniceAPIClient()
    client.queue(
        "/billing/usage-history",
        [
            FakeResponse(status_code=200, json_data={
                "data": [{"p": 1}],
                "nextCursor": "c2",
            }),
            FakeResponse(status_code=200, json_data={
                "data": [{"p": 2}],
                "nextCursor": "c3",  # exhausted — but max_pages stops us here
            }),
        ],
    )
    entries = await bp.walk_billing_usage_history(
        client, "2025-01-01T00:00:00Z", "2025-01-02T00:00:00Z"
    )
    assert entries == [{"p": 1}, {"p": 2}]


def test_timestamp_format_constant_canonical() -> None:
    """The helper module exposes TIMESTAMP_FORMAT; analytics and usage_tracker
    routes should use this single canonical format string."""
    assert bp.TIMESTAMP_FORMAT == "%Y-%m-%dT%H:%M:%SZ"
