"""Tests for backend.api.routes.characters (Venice characters proxy)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.tests.conftest import FakeResponse, FakeVeniceAPIClient
from backend.api.routes import characters as characters_routes


@pytest.fixture
def characters_list_payload() -> Dict[str, Any]:
    return {
        "data": [
            {
                "id": "2f460055-7595-4640-9cb6-c442c4c869b0",
                "name": "Alan Watts",
                "slug": "alan-watts",
                "description": "Philosophy and Buddhism.",
                "tags": ["AlanWatts", "Philosophy", "Buddhism"],
                "modelId": "venice-uncensored-1-2",
                "photoUrl": "https://example.com/alan.jpg",
                "shareUrl": "https://venice.ai/c/alan-watts",
                "adult": False,
                "featured": True,
                "webEnabled": True,
                "author": "k3x9q",
                "createdAt": "2024-12-20T21:28:08.934Z",
                "updatedAt": "2024-12-20T21:28:08.934Z",
                "stats": {
                    "averageRating": 4.7,
                    "imports": 112,
                    "ratingCount": 24,
                    "ratingSum": 113,
                    "userRating": None,
                },
            }
        ],
        "object": "list",
    }


@pytest.fixture
def characters_detail_payload() -> Dict[str, Any]:
    return {
        "data": {
            "id": "2f460055-7595-4640-9cb6-c442c4c869b0",
            "name": "Alan Watts",
            "slug": "alan-watts",
            "description": "Philosophy and Buddhism.",
            "tags": ["AlanWatts", "Philosophy", "Buddhism"],
            "modelId": "venice-uncensored-1-2",
            "adult": False,
            "featured": True,
            "webEnabled": True,
            "author": "k3x9q",
            "createdAt": "2024-12-20T21:28:08.934Z",
            "updatedAt": "2024-12-20T21:28:08.934Z",
            "stats": {
                "averageRating": 4.7,
                "imports": 112,
                "ratingCount": 24,
                "ratingSum": 113,
                "userRating": None,
            },
        },
        "object": "character",
    }


def _build_test_app(fake: FakeVeniceAPIClient) -> FastAPI:
    """Construct a tiny FastAPI app with the characters router registered
    and the Venice client dependency overridden with our fake. The TestClient
    forces the Query validators to run before the handler — direct function
    calls cannot, and `Query(None, …)` defaults evaluate to FieldInfo objects
    that bypass ``if x:`` truthiness checks."""
    app = FastAPI()
    app.include_router(characters_routes.router)

    def _override_client():
        return fake

    app.dependency_overrides[characters_routes.get_venice_client] = _override_client
    return app


def test_list_characters_passes_filters(
    characters_list_payload,
) -> None:
    fake = FakeVeniceAPIClient()
    fake.queue(
        "/characters",
        [FakeResponse(status_code=200, json_data=characters_list_payload)],
    )
    app = _build_test_app(fake)
    client = TestClient(app)

    response = client.get(
        "/characters",
        params={
            "search": "alan",
            "tags": "Philosophy",
            "isAdult": "false",
            "isWebEnabled": "true",
            "limit": "20",
            "offset": "10",
            "sortBy": "highestRating",
            "sortOrder": "desc",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["object"] == "list"
    assert len(body["data"]) == 1

    method, endpoint, params, _ = fake.calls[0]
    assert method in ("GET", "GET_JSON")
    assert endpoint == "/characters"
    assert params["search"] == "alan"
    assert params["tags"] == ["Philosophy"]
    assert params["isAdult"] == "false"
    assert params["isWebEnabled"] == "true"
    assert params["limit"] == 20
    assert params["offset"] == 10
    assert params["sortBy"] == "highestRating"
    assert params["sortOrder"] == "desc"


def test_list_characters_omits_unset_filters(
    characters_list_payload,
) -> None:
    fake = FakeVeniceAPIClient()
    fake.queue(
        "/characters",
        [FakeResponse(status_code=200, json_data=characters_list_payload)],
    )
    app = _build_test_app(fake)
    client = TestClient(app)

    response = client.get("/characters")
    assert response.status_code == 200, response.text

    method, endpoint, params, _ = fake.calls[0]
    assert method in ("GET", "GET_JSON")
    assert endpoint == "/characters"
    # With no query params the only defaults are pagination sentinels.
    assert "search" not in params
    assert "tags" not in params
    assert "categories" not in params
    assert "isAdult" not in params
    assert params["limit"] == 50
    assert params["offset"] == 0


def test_list_characters_rejects_invalid_sort_order() -> None:
    fake = FakeVeniceAPIClient()
    app = _build_test_app(fake)
    client = TestClient(app)

    response = client.get("/characters", params={"sortOrder": "invalid"})
    assert response.status_code == 422  # FastAPI validates pattern


def test_list_characters_rejects_out_of_range_limit() -> None:
    fake = FakeVeniceAPIClient()
    app = _build_test_app(fake)
    client = TestClient(app)

    response = client.get("/characters", params={"limit": "1000"})
    assert response.status_code == 422


def test_get_character_proxies_by_slug(
    characters_detail_payload,
) -> None:
    fake = FakeVeniceAPIClient()
    fake.queue(
        "/characters/alan-watts",
        [FakeResponse(status_code=200, json_data=characters_detail_payload)],
    )
    app = _build_test_app(fake)
    client = TestClient(app)

    response = client.get("/characters/alan-watts")
    assert response.status_code == 200, response.text
    assert response.json()["data"]["slug"] == "alan-watts"

    method, endpoint, _, _ = fake.calls[0]
    assert method in ("GET", "GET_JSON")
    assert endpoint == "/characters/alan-watts"


def test_get_character_maps_404_to_friendly_error() -> None:
    fake = FakeVeniceAPIClient()
    fake.queue(
        "/characters/missing",
        [FakeResponse(status_code=404, json_data={"error": "Not found"})],
    )
    app = _build_test_app(fake)
    client = TestClient(app)

    response = client.get("/characters/missing")
    assert response.status_code == 404
    body = response.json()
    assert "missing" in body["detail"]


def test_list_characters_maps_upstream_4xx() -> None:
    fake = FakeVeniceAPIClient()
    fake.queue(
        "/characters",
        [FakeResponse(status_code=403, json_data={"error": "forbidden"})],
    )
    app = _build_test_app(fake)
    client = TestClient(app)

    response = client.get("/characters")
    assert response.status_code == 403


def test_list_characters_maps_upstream_5xx_to_502() -> None:
    fake = FakeVeniceAPIClient()
    fake.queue(
        "/characters",
        [FakeResponse(status_code=500, json_data={"error": "server error"})],
    )
    app = _build_test_app(fake)
    client = TestClient(app)

    response = client.get("/characters")
    assert response.status_code == 502
