"""Regression tests: rate-limited endpoints must keep Pydantic bodies.

SlowAPI's decorator wrapper does not expose the original module's globals to
FastAPI. With ``from __future__ import annotations``, annotations stay as
strings, FastAPI cannot resolve the model, and it silently reclassifies the
``body`` argument as a required *query* parameter. Requests then fail with
``422 query.body: Field required``.

These tests assert the real route table resolves every Pydantic body as a
request body, and that the AI tools endpoints specifically accept JSON bodies.
"""

from fastapi import FastAPI

from backend.api.routes import (
    alerts,
    analytics,
    api_keys,
    assistant,
    balance,
    benchmark,
    characters,
    documents,
    health,
    insights,
    media,
    models,
    news,
    notifications,
    observability,
    onchain,
    prices,
    sentiment,
    settings as settings_routes,
    signals,
    usage,
    wallet,
    watchlists,
)

ROUTER_MODULES = (
    health,
    usage,
    balance,
    prices,
    models,
    api_keys,
    characters,
    analytics,
    benchmark,
    onchain,
    alerts,
    news,
    insights,
    assistant,
    settings_routes,
    notifications,
    watchlists,
    observability,
    wallet,
    signals,
    sentiment,
    media,
    documents,
)

# Endpoints whose bodies were broken by the SlowAPI/forward-ref interaction.
AI_TOOL_PATHS = {
    "/api/sentiment/x",
    "/api/insights/infographic",
    "/api/tts/briefing",
    "/api/video/recap",
    "/api/news/search",
    "/api/news/ask",
    "/api/documents/parse",
    "/api/documents/ask",
    "/api/notifications/channels",
    "/api/wallet/challenge",
    "/api/wallet/verify",
    "/api/alerts/evaluate",
}


def _build_app() -> FastAPI:
    app = FastAPI()
    for module in ROUTER_MODULES:
        app.include_router(module.router, prefix="/api")
    return app


def test_no_pydantic_body_is_misclassified_as_a_query_parameter():
    app = _build_app()
    offenders = []
    for route in app.routes:
        dependant = getattr(route, "dependant", None)
        if dependant is None:
            continue
        for param in dependant.query_params:
            if type(param.type_).__name__ == "ForwardRef":
                offenders.append(
                    f"{route.path} -> query '{param.name}': {param.type_.__forward_arg__}"
                )
    assert offenders == [], (
        "Pydantic bodies fell back to query parameters (likely a "
        f"from __future__ import annotations + limiter regression): {offenders}"
    )


def test_ai_tool_endpoints_classify_body_models_as_request_bodies():
    app = _build_app()
    resolved = {}
    for route in app.routes:
        if route.path not in AI_TOOL_PATHS or "POST" not in route.methods:
            continue
        dependant = getattr(route, "dependant", None)
        if dependant is None:
            continue
        resolved[route.path] = [param.name for param in dependant.body_params]

    assert set(resolved) == AI_TOOL_PATHS
    for path, body_names in resolved.items():
        assert "body" in body_names, f"{path} did not register its Pydantic body"


def test_ai_tool_endpoints_reject_wrong_shaped_bodies_not_query_lookups():
    """A missing body must produce a body validation error (loc starts with
    'body'), never a required query parameter named 'body'."""
    from fastapi.testclient import TestClient

    app = _build_app()
    client = TestClient(app)
    sample_paths = [
        "/api/sentiment/x",
        "/api/insights/infographic",
        "/api/tts/briefing",
        "/api/video/recap",
        "/api/wallet/challenge",
        "/api/documents/parse",
    ]
    for path in sample_paths:
        response = client.post(path)
        assert response.status_code == 422, f"{path} did not require a body"
        locations = [tuple(item["loc"]) for item in response.json()["detail"]]
        assert ("query", "body") not in locations, f"{path} still expects a query param 'body'"
        assert ("body",) in locations, f"{path} did not report a missing request body"
