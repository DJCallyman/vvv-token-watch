"""Tests for the natural-language assistant endpoint."""

from __future__ import annotations

import json

import pytest
from starlette.requests import Request

from backend.api.routes import assistant as assistant_routes
from backend.tests.conftest import FakeVeniceAPIClient, FakeResponse


def make_json_request(payload: dict) -> Request:
    body = json.dumps(payload).encode()
    sent = False

    async def receive() -> dict:
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/assistant/query",
            "headers": [(b"content-type", b"application/json")],
        },
        receive,
    )


@pytest.mark.asyncio
async def test_query_assistant_accepts_json_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeVeniceAPIClient()
    client.queue(
        "/chat/completions",
        [
            FakeResponse(
                json_data={
                    "choices": [
                        {"message": {"content": "Your balance is healthy."}}
                    ]
                }
            )
        ],
    )
    monkeypatch.setattr(assistant_routes, "get_client", lambda settings: client)

    result = await assistant_routes.query_assistant(
        make_json_request({"query": "What is my balance?", "history": []}),
        settings=object(),
    )

    assert result["answer"] == "Your balance is healthy."
    assert client.calls[0][1] == "/chat/completions"
    assert client.calls[0][3]["messages"][-1] == {
        "role": "user",
        "content": "What is my balance?",
    }
