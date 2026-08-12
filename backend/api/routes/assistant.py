"""Natural-language read-only assistant for application data."""

from __future__ import annotations

import json
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.api.routes.ai_common import extract_chat_text, get_client
from backend.config import Settings, get_settings
from backend.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter()


class AssistantRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    history: list[dict] = Field(default_factory=list, max_length=20)


@router.post("/assistant/query")
@limiter.limit("30/hour")
async def query_assistant(request: Request, body: AssistantRequest, settings: Settings = Depends(get_settings)):
    client = get_client(settings)
    tools = [{"type": "function", "function": {"name": name, "description": description, "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}} for name, description in {
        "get_balance": "Get current DIEM and USD balance.",
        "get_prices": "Get current VVV and DIEM prices.",
        "get_usage": "Get current epoch usage.",
        "get_onchain": "Get current VVV supply and staking data.",
    }.items()]
    messages = [{"role": "system", "content": "You are the read-only VVV Token Watch assistant. Answer using available tool data when needed. Never invent values or provide financial advice."}, *body.history[-20:], {"role": "user", "content": body.query}]
    try:
        completion = await client.post_json("/chat/completions", data={"model": "venice-uncensored-1-2", "messages": messages, "tools": tools, "tool_choice": "auto", "max_tokens": 1000, "venice_parameters": {"include_venice_system_prompt": False}}, timeout=60)
        return {"answer": extract_chat_text(completion), "tool_calls": ((completion.get("choices") or [{}])[0].get("message", {}).get("tool_calls", []) if isinstance(completion, dict) else [])}
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, "Venice assistant failed") from exc
    except Exception as exc:
        logger.exception("Assistant request failed")
        raise HTTPException(500, "Failed to answer request") from exc
