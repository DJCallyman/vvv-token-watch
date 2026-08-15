"""Regression tests for the market insights endpoint."""

from __future__ import annotations

import os

os.environ.setdefault("VENICE_ADMIN_KEY", "test-key")
os.environ.setdefault("APP_PASSWORD", "test-password")
os.environ.setdefault("ALLOW_INSECURE_NO_AUTH", "true")

from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.api.routes import insights as insights_routes
from backend.limiter import limiter


class FakeInsightClient:
    async def post_json(self, endpoint, data, timeout):
        if endpoint == "/augment/search":
            return {}
        return {"model": "fake-model"}


def test_analyze_accepts_json_body_with_rate_limiter(monkeypatch) -> None:
    fake_client = FakeInsightClient()
    monkeypatch.setattr(insights_routes, "get_client", lambda settings: fake_client)
    monkeypatch.setattr(insights_routes, "normalize_search", lambda response: [])
    monkeypatch.setattr(
        insights_routes,
        "extract_chat_text",
        lambda response: '{"summary":"ok","sentiment":"neutral","key_events":[],"risks":[],"confidence":50,"sources":[]}',
    )

    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.dependency_overrides[insights_routes.get_settings] = lambda: object()
    app.include_router(insights_routes.router, prefix="/api")

    with TestClient(app) as client:
        response = client.post(
            "/api/insights/analyze",
            json={"prices": {}, "usage": {}},
        )

    assert response.status_code == 200, response.text
    assert response.json()["analysis"]["summary"] == "ok"
