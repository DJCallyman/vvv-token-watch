"""Tests for Phase 3 AI features: X sentiment, media helpers, and video."""

from __future__ import annotations

import base64
import json

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.requests import Request

from backend.api.routes import media as media_routes
from backend.api.routes import sentiment as sentiment_routes
from backend.core import media
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


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/sentiment/x",
            "headers": [],
            "client": ("127.0.0.1", 1234),
        }
    )


def _chat_response(payload: dict) -> dict:
    return {"choices": [{"message": {"content": json.dumps(payload)}}]}


@pytest.mark.asyncio
async def test_x_sentiment_scores_and_records_signal(session, monkeypatch):
    from backend.tests.conftest import FakeResponse, FakeVeniceAPIClient

    fake = FakeVeniceAPIClient()
    fake.queue("augment/search", [FakeResponse(json_data={"data": [
        {"title": "VVV pumping", "url": "https://x.com/post/1", "snippet": "bullish"},
    ]})])
    fake.queue("chat/completions", [FakeResponse(json_data=_chat_response({
        "direction": "bullish",
        "confidence": 81,
        "summary": "Chatter is positive.",
        "drivers": ["staking news"],
    }))])

    monkeypatch.setattr(sentiment_routes, "get_client", lambda settings: fake)
    result = await sentiment_routes.analyze_x_sentiment(
        _request(),
        sentiment_routes.SentimentRequest(query="VVV", record_signal=True),
        settings=type("S", (), {"ASSISTANT_MODEL": "m"})(),
        db=session,
    )
    assert result["direction"] == "bullish"
    assert result["confidence"] == 81
    assert result["signal_id"] is not None
    signals = await signal_service.list_signals(session, limit=5)
    assert signals[0].kind == "x_sentiment"
    assert signal_service.signal_dict(signals[0])["sources"] == ["https://x.com/post/1"]


@pytest.mark.asyncio
async def test_x_sentiment_normalizes_unknown_direction(session, monkeypatch):
    from backend.tests.conftest import FakeResponse, FakeVeniceAPIClient

    fake = FakeVeniceAPIClient()
    fake.queue("augment/search", [FakeResponse(json_data={"data": []})])
    fake.queue("chat/completions", [FakeResponse(json_data=_chat_response({
        "direction": "moon",
        "confidence": 500,
        "summary": "",
    }))])
    monkeypatch.setattr(sentiment_routes, "get_client", lambda settings: fake)
    result = await sentiment_routes.analyze_x_sentiment(
        _request(),
        sentiment_routes.SentimentRequest(query="DIEM", record_signal=False),
        settings=type("S", (), {"ASSISTANT_MODEL": "m"})(),
        db=session,
    )
    assert result["direction"] == "neutral"
    assert result["confidence"] == 100.0
    assert result["signal_id"] is None


# ---------------------------------------------------------------------------
# Media helpers
# ---------------------------------------------------------------------------


def test_build_video_prompt_includes_price_and_direction():
    prompt = media_routes._build_video_prompt("bullish", 72.0, "Momentum.", 1.2345)
    assert "bullish" in prompt
    assert "$1.2345" in prompt
    assert "no financial advice" in prompt


@pytest.mark.asyncio
async def test_briefing_text_uses_prices_and_signals(session, monkeypatch):
    from backend.core import venicestats_client

    async def fake_metrics(settings=None):
        return {"vvvPrice": 1.5, "diemPrice": 2.5}

    monkeypatch.setattr(venicestats_client, "get_metrics", fake_metrics)
    await signal_service.record_signal(
        session, kind="analysis", direction="bullish", confidence=66, rationale="Up only."
    )
    text = await media_routes._build_briefing_text(
        session, type("S", (), {})()
    )
    assert "1.5000" in text
    assert "bullish" in text
    assert "not financial advice" in text


@pytest.mark.asyncio
async def test_generate_speech_returns_audio_bytes():
    class FakeResponse:
        status_code = 200
        content = b"audio-bytes"

    class FakeClient:
        async def post(self, endpoint, data=None, timeout=0):
            assert endpoint == "/audio/speech"
            assert data["input"] == "hello"
            assert data["model"] == "tts-kokoro"
            return FakeResponse()

    audio = await media.generate_speech(
        "key", "hello", voice="af_sky", model="tts-kokoro", client=FakeClient()
    )
    assert audio == b"audio-bytes"


@pytest.mark.asyncio
async def test_queue_video_payload_and_retrieve_binary():
    class FakeClient:
        def __init__(self):
            self.payloads = []

        async def post_json(self, endpoint, data=None, timeout=0):
            self.payloads.append((endpoint, data))
            return {"queue_id": "q-1"}

        async def post(self, endpoint, data=None, timeout=0):
            class R:
                status_code = 200
                content = b"\x00\x00\x00\x18ftypmp42"
                headers = {"content-type": "video/mp4"}

            return R()

    client = FakeClient()
    result = await media.queue_video(
        "key", prompt="recap", model="wan", client=client
    )
    assert result["queue_id"] == "q-1"
    assert client.payloads[0][0] == "/video/queue"
    assert client.payloads[0][1]["aspect_ratio"] == "16:9"

    status, data, metadata = await media.retrieve_video(
        "key", model="wan", queue_id="q-1", client=client
    )
    assert status == "completed"
    assert data.startswith(b"\x00\x00\x00\x18ftyp")


def test_audio_data_url_prefix():
    url = media.audio_data_url(base64.b64decode(base64.b64encode(b"abc")))
    assert url.startswith("data:audio/mp3;base64,")
