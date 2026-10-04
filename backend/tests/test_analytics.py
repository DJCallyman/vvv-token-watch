from __future__ import annotations

from datetime import datetime, timezone

import pytest

import backend.api.routes.analytics as analytics_routes
from backend.api.routes.analytics import (
    build_analytics_daily_response,
    build_analytics_model_response,
    get_daily_analytics,
    get_model_analytics,
)
from backend.core.billing_pagination import walk_billing_usage_history
from backend.tests.conftest import FakeResponse, FakeVeniceAPIClient


def test_usage_analytics_generates_cost_recommendations() -> None:
    result = build_analytics_model_response(
        {
            "byModel": [
                {"modelName": "low-cost", "totalUsd": 0.1, "totalDiem": 0, "totalUnits": 1000},
                {"modelName": "high-cost", "totalUsd": 10, "totalDiem": 0, "totalUnits": 1000},
            ]
        },
        days=7,
    )

    recommendation_types = {recommendation.type for recommendation in result.recommendations}
    assert "efficiency" in recommendation_types
    assert "cost" in recommendation_types


@pytest.mark.asyncio
async def test_model_analytics_uses_synced_billing_entries(monkeypatch) -> None:
    client = FakeVeniceAPIClient()
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    entries = [
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
    ]

    async def load_entries(_client, _days):
        return entries, "billing-db"

    monkeypatch.setattr(analytics_routes, "get_billing_entries_from_db", load_entries)

    result = await get_model_analytics(days=7, client=client)

    model = result.model_usage["test-model"]
    assert result.source == "billing-db"
    assert result.total_requests == 1
    assert model.requests == 1
    assert model.tokens == 15
    assert model.avg_response_time_ms == 1200
    assert client.calls == []


@pytest.mark.asyncio
async def test_daily_analytics_uses_synced_billing_entries(monkeypatch) -> None:
    client = FakeVeniceAPIClient()
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    entries = [
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
    ]

    async def load_entries(_client, _days):
        return entries, "billing-db"

    monkeypatch.setattr(analytics_routes, "get_billing_entries_from_db", load_entries)

    result = await get_daily_analytics(days=7, client=client)

    assert result.source == "billing-db"
    assert result.daily_usage[0].requests == 1
    assert result.daily_usage[0].tokens == 15
    assert result.daily_usage[0].cost_diem == 1.5


def test_analytics_daily_builder_maps_documented_currency_fields() -> None:
    result = build_analytics_daily_response(
        {"byDate": [{"date": "2026-08-18", "USD": 1.25, "DIEM": 2.5}]},
        days=7,
    )
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
