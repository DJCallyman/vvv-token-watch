"""Tests for epoch usage aggregation and its fast paths."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.core import usage_tracker as usage_tracker_module
from backend.core.usage_tracker import (
    UsageTracker,
    APIKeyUsage,
    UsageMetrics,
    _net_usage_from_analytics,
)
from backend.api.routes import usage as usage_routes
from backend.tests.conftest import FakeResponse, FakeVeniceAPIClient


def _current_epoch_fixture() -> tuple[str, str]:
    next_epoch = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ) + timedelta(days=1)
    epoch_date = (next_epoch - timedelta(days=1)).date().isoformat()
    return next_epoch.strftime("%Y-%m-%dT%H:%M:%SZ"), epoch_date


def test_net_usage_from_analytics_sums_documented_date_totals() -> None:
    totals = _net_usage_from_analytics(
        {
            "byDate": [
                {"date": "2025-01-01", "USD": 1.25, "DIEM": 2.5},
                {"date": "2025-01-02", "USD": 0.75, "DIEM": 1.5},
                {"date": "2025-01-03", "USD": 99, "DIEM": 99},
            ]
        },
        usage_tracker_module.datetime.fromisoformat("2025-01-01T00:00:00+00:00"),
        usage_tracker_module.datetime.fromisoformat("2025-01-02T12:00:00+00:00"),
    )

    assert totals == {
        "diem": 4.0,
        "usd": 2.0,
        "bundled_credits": 0.0,
    }


@pytest.mark.asyncio
async def test_api_keys_usage_includes_last_used_at(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeUsageTracker:
        def __init__(self, api_key: str, client: FakeVeniceAPIClient) -> None:
            pass

        async def fetch_api_keys_with_daily_usage(self) -> list[APIKeyUsage]:
            return [
                APIKeyUsage(
                    id="key-1",
                    name="Test key",
                    usage=UsageMetrics(diem=1.0, usd=0.5),
                    created_at="2026-01-01T00:00:00Z",
                    is_active=True,
                    last_used_at="2026-08-18T12:34:56Z",
                )
            ]

    monkeypatch.setattr(usage_routes, "UsageTracker", FakeUsageTracker)
    client = FakeVeniceAPIClient()
    client.api_key = "test"  # type: ignore[attr-defined]

    result = await usage_routes.get_api_keys_usage(
        client=client,
    )

    assert result["keys"][0]["last_used_at"] == "2026-08-18T12:34:56Z"


@pytest.mark.asyncio
async def test_epoch_usage_prefers_analytics_over_ledger(
) -> None:
    usage_tracker_module._epoch_usage_cache.clear()
    next_epoch, epoch_date = _current_epoch_fixture()
    client = FakeVeniceAPIClient()
    client.queue(
        "/api_keys/rate_limits",
        [
            FakeResponse(
                json_data={
                    "data": {"nextEpochBegins": next_epoch}
                }
            )
        ],
    )
    client.queue(
        "/billing/usage-analytics",
        [
            FakeResponse(
                json_data={
                    "byDate": [
                        {"date": epoch_date, "USD": 1.25, "DIEM": 2.5}
                    ]
                }
            )
        ],
    )

    result = await UsageTracker("analytics-key", client).get_epoch_usage()

    assert result["usd"] == 1.25
    assert result["diem"] == 2.5
    assert result["bundled_credits"] == 0.0
    assert [call[1] for call in client.calls] == [
        "/api_keys/rate_limits",
        "/billing/usage-analytics",
    ]


@pytest.mark.asyncio
async def test_epoch_usage_cache_hit_skips_upstream_calls() -> None:
    usage_tracker_module._epoch_usage_cache.clear()
    next_epoch, epoch_date = _current_epoch_fixture()
    first_client = FakeVeniceAPIClient()
    first_client.queue(
        "/api_keys/rate_limits",
        [
            FakeResponse(
                json_data={
                    "data": {"nextEpochBegins": next_epoch}
                }
            )
        ],
    )
    first_client.queue(
        "/billing/usage-analytics",
        [
            FakeResponse(
                json_data={
                    "byDate": [
                        {"date": epoch_date, "USD": 1.0, "DIEM": 2.0}
                    ]
                }
            )
        ],
    )

    expected = await UsageTracker("same-key", first_client).get_epoch_usage()
    second_client = FakeVeniceAPIClient()
    actual = await UsageTracker("same-key", second_client).get_epoch_usage()

    assert actual == expected
    assert second_client.calls == []


@pytest.mark.asyncio
async def test_epoch_usage_falls_back_to_ledger_when_analytics_unavailable() -> None:
    usage_tracker_module._epoch_usage_cache.clear()
    next_epoch, _ = _current_epoch_fixture()
    client = FakeVeniceAPIClient()
    client.queue(
        "/api_keys/rate_limits",
        [
            FakeResponse(
                json_data={
                    "data": {"nextEpochBegins": next_epoch}
                }
            )
        ],
    )
    client.queue(
        "/billing/usage-analytics",
        [FakeResponse(status_code=404, json_data={"error": "not found"})],
    )
    client.queue(
        "/billing/usage-history",
        [
            FakeResponse(
                json_data={
                    "data": [
                        {"currency": "USD", "amount": -1.25},
                        {"currency": "DIEM", "amount": -2.5},
                        {"currency": "BUNDLED_CREDITS", "amount": -0.5},
                    ]
                }
            )
        ],
    )

    result = await UsageTracker("fallback-key", client).get_epoch_usage()

    assert result["usd"] == 1.25
    assert result["diem"] == 2.5
    assert result["bundled_credits"] == 0.5
    assert [call[1] for call in client.calls] == [
        "/api_keys/rate_limits",
        "/billing/usage-analytics",
        "/billing/usage-history",
    ]


@pytest.mark.asyncio
async def test_epoch_usage_falls_back_when_analytics_payload_is_incomplete() -> None:
    usage_tracker_module._epoch_usage_cache.clear()
    next_epoch, epoch_date = _current_epoch_fixture()
    client = FakeVeniceAPIClient()
    client.queue(
        "/api_keys/rate_limits",
        [
            FakeResponse(
                json_data={
                    "data": {"nextEpochBegins": next_epoch}
                }
            )
        ],
    )
    client.queue(
        "/billing/usage-analytics",
        [
            FakeResponse(
                json_data={
                    "byDate": [{"date": epoch_date, "USD": 1.0}]
                }
            )
        ],
    )
    client.queue(
        "/billing/usage-history",
        [
            FakeResponse(
                json_data={
                    "data": [{"currency": "USD", "amount": -3.0}]
                }
            )
        ],
    )

    result = await UsageTracker("incomplete-key", client).get_epoch_usage()

    assert result["usd"] == 3.0
    assert [call[1] for call in client.calls] == [
        "/api_keys/rate_limits",
        "/billing/usage-analytics",
        "/billing/usage-history",
    ]
