"""Structured, on-demand market analysis using Venice chat and web search."""

from __future__ import annotations

import json
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.api.routes.ai_common import extract_chat_text, get_client, normalize_search
from backend.config import Settings, get_settings
from backend.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter()


class InsightRequest(BaseModel):
    prices: dict = Field(default_factory=dict)
    usage: dict = Field(default_factory=dict)


@router.post("/insights/analyze")
@limiter.limit("10/hour")
async def analyze(request: Request, body: InsightRequest, settings: Settings = Depends(get_settings)):
    client = get_client(settings)
    try:
        search = await client.post_json("/augment/search", data={"query": "VVV DIEM Venice AI crypto latest", "limit": 10}, timeout=30)
        articles = normalize_search(search)
        prompt = json.dumps({"prices": body.prices, "usage": body.usage, "news": articles}, default=str)
        completion = await client.post_json("/chat/completions", data={
            "model": "venice-uncensored-1-2",
            "messages": [
                {"role": "system", "content": "Analyze VVV and DIEM market context. Return strict JSON with keys summary, sentiment (bullish, bearish, or neutral), key_events (array), risks (array), confidence (number 0-100), and sources (array of URLs). Do not give financial advice."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 1200,
            "temperature": 0.2,
            "venice_parameters": {"include_venice_system_prompt": False, "enable_web_search": "off"},
            "response_format": {"type": "json_object"},
        }, timeout=60)
        text = extract_chat_text(completion)
        try:
            analysis = json.loads(text)
        except json.JSONDecodeError:
            analysis = {"summary": text, "sentiment": "neutral", "key_events": [], "risks": [], "confidence": 0, "sources": [a["url"] for a in articles if a.get("url")]}
        return {"analysis": analysis, "articles": articles, "model": completion.get("model") if isinstance(completion, dict) else None}
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, "Venice analysis failed") from exc
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        raise HTTPException(504, "Venice analysis is temporarily unavailable") from exc
    except Exception as exc:
        logger.exception("Market analysis failed")
        raise HTTPException(500, "Failed to generate market analysis") from exc
