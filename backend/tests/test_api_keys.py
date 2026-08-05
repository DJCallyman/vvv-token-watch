"""Tests for backend.api.routes.api_keys (Venice API key CRUD proxy)."""

from __future__ import annotations

import pytest

from backend.tests.conftest import FakeResponse, FakeVeniceAPIClient
from backend.api.routes import api_keys as api_keys_routes


@pytest.mark.asyncio
async def test_create_api_key_passes_through_secret(
    fake_venice_client: FakeVeniceAPIClient,
) -> None:
    fake_venice_client.queue(
        "/api_keys",
        [
            FakeResponse(
                status_code=201,
                json_data={
                    "data": {
                        "apiKey": "venice_sk_live_super_secret",
                        "apiKeyType": "INFERENCE",
                        "id": "key-123",
                        "description": "test key",
                        "consumptionLimit": {"usd": None, "diem": None},
                        "limitPeriod": "EPOCH",
                        "expiresAt": None,
                    },
                    "success": True,
                },
            ),
        ],
    )

    body = api_keys_routes.ApiKeyCreate(
        apiKeyType="INFERENCE",
        description="test key",
    )
    result = await api_keys_routes.create_api_key(
        body=body, client=fake_venice_client  # type: ignore[arg-type]
    )

    assert result["data"]["apiKey"] == "venice_sk_live_super_secret"
    assert result["data"]["id"] == "key-123"
    assert result["success"] is True

    method, endpoint, _, payload = fake_venice_client.calls[0]
    assert method == "POST_JSON"
    assert endpoint == "/api_keys"
    assert payload["apiKeyType"] == "INFERENCE"
    assert payload["description"] == "test key"


@pytest.mark.asyncio
async def test_create_api_key_forwards_consumption_limit_and_limit_period(
    fake_venice_client: FakeVeniceAPIClient,
) -> None:
    fake_venice_client.queue(
        "/api_keys",
        [
            FakeResponse(
                status_code=200,
                json_data={
                    "data": {"id": "key-2", "apiKey": "sk_x"},
                    "success": True,
                },
            ),
        ],
    )

    body = api_keys_routes.ApiKeyCreate(
        apiKeyType="INFERENCE",
        description="limited",
        consumptionLimit=api_keys_routes.ConsumptionLimit(usd=10),
        limitPeriod="MONTH",
    )
    await api_keys_routes.create_api_key(
        body=body, client=fake_venice_client  # type: ignore[arg-type]
    )

    method, _, _, payload = fake_venice_client.calls[0]
    assert method == "POST_JSON"
    assert payload["consumptionLimit"] == {"usd": 10}
    assert payload["limitPeriod"] == "MONTH"


@pytest.mark.asyncio
async def test_create_api_key_propagates_4xx(
    fake_venice_client: FakeVeniceAPIClient,
) -> None:
    """Upstream 4xx is mapped to a FastAPI HTTPException preserving the status code."""
    from fastapi import HTTPException

    fake_venice_client.queue(
        "/api_keys",
        [FakeResponse(status_code=400, json_data={"error": "Bad description"})],
    )
    body = api_keys_routes.ApiKeyCreate(apiKeyType="INFERENCE", description="x")
    with pytest.raises(HTTPException) as exc_info:
        await api_keys_routes.create_api_key(
            body=body, client=fake_venice_client  # type: ignore[arg-type]
        )
    assert exc_info.value.status_code == 400
    assert "Bad description" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_update_api_key_sends_id_in_body(
    fake_venice_client: FakeVeniceAPIClient,
) -> None:
    fake_venice_client.queue(
        "/api_keys",
        [
            FakeResponse(
                status_code=200,
                json_data={
                    "data": {
                        "id": "key-abc",
                        "apiKeyType": "INFERENCE",
                        "description": "renamed",
                        "consumptionLimits": {"usd": 50, "diem": None},
                        "limitPeriod": "MONTH",
                        "createdAt": "2025-01-01T00:00:00Z",
                        "last6Chars": "ab12cd",
                        "lastUsedAt": None,
                        "expiresAt": None,
                    },
                    "success": True,
                },
            ),
        ],
    )

    body = api_keys_routes.ApiKeyUpdate(
        id="key-abc",
        description="renamed",
    )
    result = await api_keys_routes.update_api_key(
        body=body, client=fake_venice_client  # type: ignore[arg-type]
    )
    assert result["data"]["description"] == "renamed"

    method, endpoint, _, payload = fake_venice_client.calls[0]
    assert method == "PATCH"
    assert endpoint == "/api_keys"
    # ID goes in body, not URL path.
    assert "key-abc" not in endpoint
    assert payload["id"] == "key-abc"
    assert payload["description"] == "renamed"
    # Description-only update: limit fields omitted.
    assert "consumptionLimit" not in payload
    assert "limitPeriod" not in payload


@pytest.mark.asyncio
async def test_update_api_key_includes_consumption_limit_when_provided(
    fake_venice_client: FakeVeniceAPIClient,
) -> None:
    fake_venice_client.queue(
        "/api_keys",
        [FakeResponse(status_code=200, json_data={"data": {"id": "k"}, "success": True})],
    )
    body = api_keys_routes.ApiKeyUpdate(
        id="k",
        consumptionLimit=api_keys_routes.ConsumptionLimit(diem=20.0),
    )
    await api_keys_routes.update_api_key(
        body=body, client=fake_venice_client  # type: ignore[arg-type]
    )
    method, _, _, payload = fake_venice_client.calls[0]
    assert method == "PATCH"
    assert payload["consumptionLimit"] == {"diem": 20.0}


@pytest.mark.asyncio
async def test_delete_api_key_sends_id_as_query_param(
    fake_venice_client: FakeVeniceAPIClient,
) -> None:
    fake_venice_client.queue(
        "/api_keys",
        [FakeResponse(status_code=200, json_data={"success": True})],
    )

    result = await api_keys_routes.delete_api_key(
        id="key-xyz", client=fake_venice_client  # type: ignore[arg-type]
    )
    assert result["success"] is True

    method, endpoint, params, _ = fake_venice_client.calls[0]
    assert method == "DELETE"
    assert endpoint == "/api_keys"
    # ID goes as a query parameter, NOT a URL segment.
    assert "key-xyz" not in endpoint
    assert params == {"id": "key-xyz"}


@pytest.mark.asyncio
async def test_delete_api_key_handles_204_no_content(
    fake_venice_client: FakeVeniceAPIClient,
) -> None:
    fake_venice_client.queue(
        "/api_keys",
        [FakeResponse(status_code=200, json_data=None, text="")],
    )
    result = await api_keys_routes.delete_api_key(
        id="k1", client=fake_venice_client  # type: ignore[arg-type]
    )
    # 200 with empty body should still resolve to a success envelope.
    assert result == {"success": True, "id": "k1"}


@pytest.mark.asyncio
async def test_get_api_key_detail_proxies_path(
    fake_venice_client: FakeVeniceAPIClient,
) -> None:
    fake_venice_client.queue(
        "/api_keys/key-zzz",
        [
            FakeResponse(
                status_code=200,
                json_data={
                    "data": {
                        "id": "key-zzz",
                        "apiKeyType": "ADMIN",
                        "description": "admin key",
                        "consumptionLimits": {"usd": 100, "diem": 200},
                        "limitPeriod": "MONTH",
                        "createdAt": "2025-01-01T00:00:00Z",
                        "last6Chars": "zz1234",
                        "expiresAt": None,
                        "lastUsedAt": None,
                    }
                },
            ),
        ],
    )
    result = await api_keys_routes.get_api_key_detail(
        key_id="key-zzz", client=fake_venice_client  # type: ignore[arg-type]
    )
    assert result["data"]["id"] == "key-zzz"

    method, endpoint, _, _ = fake_venice_client.calls[0]
    assert method in ("GET", "GET_JSON")
    assert endpoint == "/api_keys/key-zzz"


@pytest.mark.asyncio
async def test_get_api_key_detail_surfaces_upstream_errors(
    fake_venice_client: FakeVeniceAPIClient,
) -> None:
    """Upstream 4xx is mapped to HTTPException (FastAPI), not raw httpx errors."""
    from fastapi import HTTPException

    fake_venice_client.queue(
        "/api_keys/missing",
        [FakeResponse(status_code=404, json_data={"error": "Not found"})],
    )
    with pytest.raises(HTTPException) as exc_info:
        await api_keys_routes.get_api_key_detail(
            key_id="missing", client=fake_venice_client  # type: ignore[arg-type]
        )
    assert exc_info.value.status_code == 404
