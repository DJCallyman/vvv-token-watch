from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.api.routes.analytics import get_daily_analytics, get_model_analytics
from backend.core.billing_pagination import walk_billing_usage_history
from backend.tests.conftest import FakeResponse, FakeVeniceAPIClient


@pytest.mark.asyncio
async def test_model_analytics_prefers_usage_history() -> None:
    client = FakeVeniceAPIClient()
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    client.queue(
        "/billing/usage-history",
        [
            FakeResponse(
                json_data={
                    "data": [
                        {
                            "amount": -2.0,
                            "currency": "DIEM",
                            "sku": "test-model-llm-input-mtoken",
                            "timestamp": timestamp,
                            "units": 0.00001,
                            "inferenceDetails": {
                                "requestId": "request-1",
                                "promptTokens": 10,
                                "completionTokens": 5,
                                "inferenceExecutionTime": 1200,
                            },
                        }
                    ],
                    "nextCursor": None,
                }
            )
        ],
    )

    result = await get_model_analytics(days=7, client=client)

    model = result.model_usage["test-model"]
    assert result.source == "billing/usage-history"
    assert result.total_requests == 1
    assert model.requests == 1
    assert model.tokens == 15
    assert model.avg_response_time_ms == 1200
    assert [call[1] for call in client.calls] == ["/billing/usage-history"]


@pytest.mark.asyncio
async def test_daily_analytics_prefers_usage_history() -> None:
    client = FakeVeniceAPIClient()
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    client.queue(
        "/billing/usage-history",
        [
            FakeResponse(
                json_data={
                    "data": [
                        {
                            "amount": -1.5,
                            "currency": "DIEM",
                            "sku": "test-model-llm-input-mtoken",
                            "timestamp": timestamp,
                            "units": 0.00001,
                            "inferenceDetails": {
                                "requestId": "request-1",
                                "promptTokens": 10,
                                "completionTokens": 5,
                                "inferenceExecutionTime": 1200,
                            },
                        }
                    ],
                    "nextCursor": None,
                }
            )
        ],
    )

    result = await get_daily_analytics(days=7, client=client)

    assert result.source == "billing/usage-history"
    assert result.daily_usage[0].requests == 1
    assert result.daily_usage[0].tokens == 15
    assert result.daily_usage[0].cost_diem == 1.5


@pytest.mark.asyncio
async def test_analytics_fallback_maps_documented_daily_currency_fields() -> None:
    client = FakeVeniceAPIClient()
    client.queue(
        "/billing/usage-analytics",
        [
            FakeResponse(
                json_data={
                    "byDate": [
                        {"date": "2026-08-18", "USD": 1.25, "DIEM": 2.5}
                    ]
                }
            )
        ],
    )
    client.queue(
        "/billing/usage-history",
        [FakeResponse(status_code=404)],
    )
    client.queue(
        "/billing/usage",
        [FakeResponse(status_code=410)],
    )

    result = await get_daily_analytics(days=7, client=client)

    daily = result.daily_usage[0]
    assert result.source == "billing/usage-analytics"
    assert daily.requests is None
    assert daily.tokens is None
    assert daily.cost_usd == 1.25
    assert daily.cost_diem == 2.5
    assert daily.cost == 3.75


@pytest.mark.asyncio
async def test_usage_history_rejects_repeated_cursor() -> None:
    client = FakeVeniceAPIClient()
    client.queue(
        "/billing/usage-history",
        [
            FakeResponse(json_data={"data": [], "nextCursor": "repeat"}),
            FakeResponse(json_data={"data": [], "nextCursor": "repeat"}),
        ],
    )

    with pytest.raises(RuntimeError, match="repeated cursor"):
        await walk_billing_usage_history(
            client,
            "2026-08-12T00:00:00Z",
            "2026-08-19T00:00:00Z",
        )
