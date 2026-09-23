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

import httpx

from backend.api.routes import insights as insights_routes
from backend.limiter import limiter


class FakeInsightClient:
    """Fake Venice client: records endpoint calls, returns canned responses."""

    def __init__(self):
        self.calls = []

    async def post_json(self, endpoint, data, timeout):
        self.calls.append((endpoint, data))
        if endpoint == "/augment/search":
            return {}
        if endpoint == "/decisions":
            return {
                "model": "jev-latest",
                "answers": {
                    "sentiment": {
                        "type": "score",
                        "score": 1.72,
                        "legend": {"0": "Bearish", "1": "Neutral", "2": "Bullish"},
                        "probabilities": {"0": 0.05, "1": 0.23, "2": 0.72},
                        "confidence": 0.68,
                    },
                    "is_high_risk": {"type": "noul", "noul": 0.18},
                    "market_phase": {
                        "type": "choice",
                        "choice": "accumulation",
                        "probabilities": {"accumulation": 0.51, "consolidation": 0.29, "uptrend": 0.08, "downtrend": 0.07, "unclear": 0.05},
                        "confidence": 0.44,
                    },
                    "news_supports_bullish": {"type": "noul", "noul": 0.61},
                },
                "usage": {"input_tokens": 429, "output_tokens": 73},
            }
        return {"model": "fake-model"}


def _make_app():
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.dependency_overrides[insights_routes.get_settings] = lambda: object()
    app.include_router(insights_routes.router, prefix="/api")
    return app


def _analyze(client):
    return client.post("/api/insights/analyze", json={"prices": {}, "usage": {}})


def test_analyze_accepts_json_body_with_rate_limiter(monkeypatch) -> None:
    fake_client = FakeInsightClient()
    monkeypatch.setattr(insights_routes, "get_client", lambda settings: fake_client)
    monkeypatch.setattr(insights_routes, "normalize_search", lambda response: [])
    monkeypatch.setattr(
        insights_routes,
        "extract_chat_text",
        lambda response: '{"summary":"ok","sentiment":"neutral","key_events":[],"risks":[],"confidence":50,"sources":[]}',
    )

    with TestClient(_make_app()) as client:
        response = _analyze(client)

    assert response.status_code == 200, response.text
    assert response.json()["analysis"]["summary"] == "ok"


def test_analyze_calls_decisions_endpoint_and_returns_normalized_answers(monkeypatch) -> None:
    fake_client = FakeInsightClient()
    monkeypatch.setattr(insights_routes, "get_client", lambda settings: fake_client)
    monkeypatch.setattr(insights_routes, "normalize_search", lambda response: [])
    monkeypatch.setattr(
        insights_routes,
        "extract_chat_text",
        lambda response: '{"summary":"ok","sentiment":"bullish","key_events":[],"risks":[],"confidence":80,"sources":[]}',
    )

    with TestClient(_make_app()) as client:
        response = _analyze(client)

    assert response.status_code == 200, response.text
    decisions_endpoints = [ep for ep, _ in fake_client.calls if ep == "/decisions"]
    assert len(decisions_endpoints) == 1
    decisions_call_data = next(data for ep, data in fake_client.calls if ep == "/decisions")
    assert decisions_call_data["model"] == "jev-latest"
    assert set(decisions_call_data["questions"].keys()) == {"sentiment", "is_high_risk", "market_phase", "news_supports_bullish"}
    payload = response.json()
    assert payload["decisions"] is not None
    assert payload["decisions"]["model"] == "jev-latest"
    answers = payload["decisions"]["answers"]
    assert set(answers.keys()) == {"sentiment", "is_high_risk", "market_phase", "news_supports_bullish"}
    assert answers["sentiment"]["type"] == "score"
    assert answers["sentiment"]["score"] == 1.72
    assert answers["sentiment"]["probabilities"]["2"] == 0.72
    assert answers["is_high_risk"]["type"] == "noul"
    assert answers["is_high_risk"]["noul"] == 0.18
    assert answers["market_phase"]["type"] == "choice"
    assert answers["market_phase"]["choice"] == "accumulation"
    assert answers["news_supports_bullish"]["noul"] == 0.61


def test_analyze_degrades_to_null_decisions_when_jev_unavailable(monkeypatch) -> None:
    class NoDecisionClient(FakeInsightClient):
        async def post_json(self, endpoint, data, timeout):
            if endpoint == "/decisions":
                raise httpx.HTTPStatusError(
                    "401 Unauthorized",
                    request=httpx.Request("POST", "https://api.venice.ai/api/v1/decisions"),
                    response=httpx.Response(401, request=httpx.Request("POST", "https://api.venice.ai/api/v1/decisions")),
                )
            return await super().post_json(endpoint, data, timeout)

    fake_client = NoDecisionClient()
    monkeypatch.setattr(insights_routes, "get_client", lambda settings: fake_client)
    monkeypatch.setattr(insights_routes, "normalize_search", lambda response: [])
    monkeypatch.setattr(
        insights_routes,
        "extract_chat_text",
        lambda response: '{"summary":"ok","sentiment":"neutral","key_events":[],"risks":[],"confidence":50,"sources":[]}',
    )

    with TestClient(_make_app()) as client:
        response = _analyze(client)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["analysis"]["summary"] == "ok"
    assert payload["decisions"] is None
    assert payload["decisions_status"] == "unavailable"


def test_analyze_decisions_status_ok_when_jev_succeeds(monkeypatch) -> None:
    fake_client = FakeInsightClient()
    monkeypatch.setattr(insights_routes, "get_client", lambda settings: fake_client)
    monkeypatch.setattr(insights_routes, "normalize_search", lambda response: [])
    monkeypatch.setattr(
        insights_routes,
        "extract_chat_text",
        lambda response: '{"summary":"ok","sentiment":"neutral","key_events":[],"risks":[],"confidence":50,"sources":[]}',
    )

    with TestClient(_make_app()) as client:
        response = _analyze(client)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["decisions"] is not None
    assert payload["decisions_status"] == "ok"


def test_decisions_retries_once_on_5xx_then_succeeds(monkeypatch) -> None:
    class FlakyThenSuccessClient(FakeInsightClient):
        def __init__(self):
            super().__init__()
            self.decision_attempts = 0

        async def post_json(self, endpoint, data, timeout):
            if endpoint == "/decisions":
                self.decision_attempts += 1
                if self.decision_attempts == 1:
                    raise httpx.HTTPStatusError(
                        "500 Internal Server Error",
                        request=httpx.Request("POST", "https://api.venice.ai/api/v1/decisions"),
                        response=httpx.Response(500, request=httpx.Request("POST", "https://api.venice.ai/api/v1/decisions")),
                    )
            return await super().post_json(endpoint, data, timeout)

    fake_client = FlakyThenSuccessClient()
    monkeypatch.setattr(insights_routes, "get_client", lambda settings: fake_client)
    monkeypatch.setattr(insights_routes, "normalize_search", lambda response: [])
    monkeypatch.setattr(
        insights_routes,
        "extract_chat_text",
        lambda response: '{"summary":"ok","sentiment":"neutral","key_events":[],"risks":[],"confidence":50,"sources":[]}',
    )

    with TestClient(_make_app()) as client:
        response = _analyze(client)

    assert response.status_code == 200, response.text
    assert fake_client.decision_attempts == 2  # one retry after the 500
    assert response.json()["decisions_status"] == "ok"


def test_decisions_no_retry_on_4xx(monkeypatch) -> None:
    class AuthFailClient(FakeInsightClient):
        def __init__(self):
            super().__init__()
            self.decision_attempts = 0

        async def post_json(self, endpoint, data, timeout):
            if endpoint == "/decisions":
                self.decision_attempts += 1
                raise httpx.HTTPStatusError(
                    "401 Unauthorized",
                    request=httpx.Request("POST", "https://api.venice.ai/api/v1/decisions"),
                    response=httpx.Response(401, request=httpx.Request("POST", "https://api.venice.ai/api/v1/decisions")),
                )
            return await super().post_json(endpoint, data, timeout)

    fake_client = AuthFailClient()
    monkeypatch.setattr(insights_routes, "get_client", lambda settings: fake_client)
    monkeypatch.setattr(insights_routes, "normalize_search", lambda response: [])
    monkeypatch.setattr(
        insights_routes,
        "extract_chat_text",
        lambda response: '{"summary":"ok","sentiment":"neutral","key_events":[],"risks":[],"confidence":50,"sources":[]}',
    )

    with TestClient(_make_app()) as client:
        response = _analyze(client)

    assert response.status_code == 200, response.text
    assert fake_client.decision_attempts == 1  # no retry on 4xx
    assert response.json()["decisions"] is None
    assert response.json()["decisions_status"] == "unavailable"


def test_analyze_degrades_to_null_decisions_on_malformed_jev_payload(monkeypatch) -> None:
    class MalformedDecisionClient(FakeInsightClient):
        async def post_json(self, endpoint, data, timeout):
            if endpoint == "/decisions":
                return {"unexpected": "shape"}
            return await super().post_json(endpoint, data, timeout)

    fake_client = MalformedDecisionClient()
    monkeypatch.setattr(insights_routes, "get_client", lambda settings: fake_client)
    monkeypatch.setattr(insights_routes, "normalize_search", lambda response: [])
    monkeypatch.setattr(
        insights_routes,
        "extract_chat_text",
        lambda response: '{"summary":"ok","sentiment":"neutral","key_events":[],"risks":[],"confidence":50,"sources":[]}',
    )

    with TestClient(_make_app()) as client:
        response = _analyze(client)

    assert response.status_code == 200, response.text
    assert response.json()["decisions"] is None


def test_analyze_chat_failure_still_maps_to_502(monkeypatch) -> None:
    class ChatFailureClient(FakeInsightClient):
        async def post_json(self, endpoint, data, timeout):
            if endpoint == "/chat/completions":
                raise httpx.HTTPStatusError(
                    "500 Internal Server Error",
                    request=httpx.Request("POST", "https://api.venice.ai/api/v1/chat/completions"),
                    response=httpx.Response(500, request=httpx.Request("POST", "https://api.venice.ai/api/v1/chat/completions")),
                )
            return await super().post_json(endpoint, data, timeout)

    fake_client = ChatFailureClient()
    monkeypatch.setattr(insights_routes, "get_client", lambda settings: fake_client)
    monkeypatch.setattr(insights_routes, "normalize_search", lambda response: [])

    with TestClient(_make_app()) as client:
        response = _analyze(client)

    assert response.status_code == 502, response.text


def test_shared_state_sent_to_both_chat_and_decisions(monkeypatch) -> None:
    fake_client = FakeInsightClient()
    monkeypatch.setattr(insights_routes, "get_client", lambda settings: fake_client)
    monkeypatch.setattr(insights_routes, "normalize_search", lambda response: [{"title": "T", "url": "https://x", "snippet": "s"}])
    monkeypatch.setattr(
        insights_routes,
        "extract_chat_text",
        lambda response: '{"summary":"ok","sentiment":"neutral","key_events":[],"risks":[],"confidence":50,"sources":[]}',
    )

    with TestClient(_make_app()) as client:
        response = _analyze(client)

    assert response.status_code == 200, response.text
    chat_call = next(data for ep, data in fake_client.calls if ep == "/chat/completions")
    decisions_call = next(data for ep, data in fake_client.calls if ep == "/decisions")
    # The chat user prompt and the Jev state must both reflect the same articles.
    assert '"news"' in chat_call["messages"][1]["content"]
    assert decisions_call["state"]["news"][0]["url"] == "https://x"
