"""Structured, on-demand market analysis using Venice chat and web search."""

from __future__ import annotations

import asyncio
import json
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError

from backend.api.routes.ai_common import extract_chat_text, get_client, normalize_search
from backend.config import Settings, get_settings
from backend.core.decisions import (
    JEV_MODEL,
    safe_evaluate_decisions,
)
from backend.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter()


class InsightRequest(BaseModel):
    prices: dict = Field(default_factory=dict)
    usage: dict = Field(default_factory=dict)


def _build_market_questions() -> dict:
    """Typed questions for the Jev evaluation of market state.

    Kept here (not in backend.core.decisions) because they are insights-specific.
    """
    return {
        "sentiment": {
            "type": "score",
            "instructions": "Based on the prices, usage, and news, what is the current market sentiment for VVV and DIEM?",
            "criteria": ["Bearish", "Neutral", "Bullish"],
        },
        "is_high_risk": {
            "type": "noul",
            "instructions": "Does the current state suggest elevated downside risk for VVV/DIEM holders?",
            "criteria": {
                "true": "Signals materially favor a decline or loss of value",
                "false": "No strong signals of imminent downside",
            },
        },
        "market_phase": {
            "type": "choice",
            "instructions": "Which market phase best describes the current state?",
            "criteria": {
                "accumulation": "Prices flat or falling while interest quietly builds",
                "consolidation": "Prices moving sideways with no clear trend",
                "uptrend": "Prices rising with sustained momentum",
                "downtrend": "Prices falling with sustained momentum",
                "unclear": "Mixed or insufficient signals",
            },
        },
        "news_supports_bullish": {
            "type": "noul",
            "instructions": "Do the fetched news articles materially support a bullish outlook?",
            "criteria": {
                "true": "Most news is positive for VVV/DIEM prospects",
                "false": "News is negative or does not support a bullish case",
            },
        },
    }


@router.post("/insights/analyze")
@limiter.limit("10/hour")
async def analyze(request: Request, settings: Settings = Depends(get_settings)):
    try:
        raw_body = await request.json()
        body = InsightRequest.model_validate(raw_body if isinstance(raw_body, dict) else {})
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid JSON body: {exc}") from exc

    client = get_client(settings)
    try:
        search = await client.post_json("/augment/search", data={"query": "VVV DIEM Venice AI crypto latest", "limit": 10}, timeout=30)
        articles = normalize_search(search)
        state = {"prices": body.prices, "usage": body.usage, "news": articles}
        prompt = json.dumps(state, default=str)

        async def _chat_analysis():
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
            return analysis, completion.get("model") if isinstance(completion, dict) else None

        # Chat prose analysis and Jev typed judgments run independently against
        # the same state. Jev failure degrades silently (decisions=None).
        chat_result, decisions_pair = await asyncio.gather(
            _chat_analysis(),
            safe_evaluate_decisions(client, state, _build_market_questions(), model=JEV_MODEL),
            return_exceptions=True,
        )
        if isinstance(chat_result, BaseException):
            raise chat_result
        analysis, chat_model = chat_result
        decisions, decisions_error = decisions_pair
        # "ok" when judgments came back; otherwise a stable "unavailable" status
        # the UI can surface as a subtle hint. Never a hard failure.
        decisions_status = "ok" if decisions is not None else "unavailable"
        return {
            "analysis": analysis,
            "articles": articles,
            "model": chat_model,
            "decisions": decisions.model_dump() if decisions is not None else None,
            "decisions_status": decisions_status,
        }
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, "Venice analysis failed") from exc
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        raise HTTPException(504, "Venice analysis is temporarily unavailable") from exc
    except Exception as exc:
        logger.exception("Market analysis failed")
        raise HTTPException(500, "Failed to generate market analysis") from exc
