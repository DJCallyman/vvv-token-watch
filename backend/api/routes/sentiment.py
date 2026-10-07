"""X/Twitter sentiment tracking through Venice search models (Phase 3)."""

import json
import logging
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.api.routes.ai_common import extract_chat_text, get_client, normalize_search
from backend.config import Settings, get_settings
from backend.core.cache import TtlCache
from backend.database import get_db
from backend.limiter import limiter
from backend.services import signal_service
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter()
_cache = TtlCache(max_size=64)

_VALID_DIRECTIONS = {"bullish", "bearish", "neutral"}


class SentimentRequest(BaseModel):
    query: str = Field(
        "VVV OR DIEM Venice AI crypto",
        min_length=3,
        max_length=200,
    )
    limit: int = Field(15, ge=5, le=25)
    record_signal: bool = True
    entry_price_usd: float | None = Field(None, ge=0)


def _score(posts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate nothing locally: direction/confidence come from the model.

    This function only normalizes the model output; it never invents values.
    """
    return {"post_count": len(posts)}


@router.post("/sentiment/x")
@limiter.limit("20/hour")
async def analyze_x_sentiment(
    request: Request,
    body: SentimentRequest,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
):
    """Search X/Twitter via Venice and produce a structured sentiment signal."""
    cache_key = f"sentiment:{body.query}:{body.limit}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    client = get_client(settings)
    try:
        search = await client.post_json(
            "/augment/search",
            data={
                "query": f"site:x.com OR site:twitter.com {body.query}",
                "limit": body.limit,
            },
            timeout=30,
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f"Venice search failed: {exc.response.status_code}") from exc
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        raise HTTPException(504, "Venice search is temporarily unavailable") from exc

    posts = normalize_search(search)
    context = json.dumps({"query": body.query, "posts": posts}, default=str)
    try:
        completion = await client.post_json(
            "/chat/completions",
            data={
                "model": settings.ASSISTANT_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Score X/Twitter sentiment for the VVV/DIEM tokens. "
                            "Return strict JSON with keys direction (bullish, bearish, "
                            "or neutral), confidence (0-100 number), summary (string), "
                            "and drivers (array of short strings). Base the score only "
                            "on the supplied posts. Do not give financial advice."
                        ),
                    },
                    {"role": "user", "content": context},
                ],
                "max_tokens": 600,
                "temperature": 0.1,
                "venice_parameters": {
                    "include_venice_system_prompt": False,
                    "enable_web_search": "off",
                },
                "response_format": {"type": "json_object"},
            },
            timeout=60,
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f"Venice chat failed: {exc.response.status_code}") from exc
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        raise HTTPException(504, "Venice chat is temporarily unavailable") from exc

    text = extract_chat_text(completion)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = {
            "direction": "neutral",
            "confidence": 0,
            "summary": text,
            "drivers": [],
        }
    direction = str(parsed.get("direction") or "neutral").lower()
    if direction not in _VALID_DIRECTIONS:
        direction = "neutral"
    confidence = parsed.get("confidence")
    confidence = float(confidence) if isinstance(confidence, (int, float)) else 0.0
    confidence = max(0.0, min(100.0, confidence))
    sources = [post["url"] for post in posts if post.get("url")]

    signal_id = None
    if body.record_signal:
        try:
            row = await signal_service.record_signal(
                db,
                kind="x_sentiment",
                subject="vvv",
                direction=direction,
                confidence=confidence,
                rationale=str(parsed.get("summary") or ""),
                sources=sources,
                metrics={
                    "post_count": len(posts),
                    "drivers": parsed.get("drivers") or [],
                },
                entry_price_usd=body.entry_price_usd,
            )
            signal_id = row.id
        except Exception:
            logger.exception("Failed to record X sentiment signal")

    result = {
        "direction": direction,
        "confidence": confidence,
        "summary": parsed.get("summary") or "",
        "drivers": parsed.get("drivers") or [],
        "posts": posts,
        "sources": sources,
        "model": settings.ASSISTANT_MODEL,
        "signal_id": signal_id,
        "source": "Venice web search restricted to x.com/twitter.com",
        "note": (
            "Search-backed sentiment; result quality depends on indexed coverage "
            "and is informational only."
        ),
    }
    _cache.set(cache_key, result, ttl=600)
    return result
