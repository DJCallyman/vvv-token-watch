"""Structured, on-demand market analysis using Venice chat and web search."""

import asyncio
import json
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.routes.ai_common import extract_chat_text, get_client, normalize_search
from backend.config import Settings, get_settings
from backend.core import media, venicestats_client
from backend.core.decisions import (
    JEV_MODEL,
    safe_evaluate_decisions,
)
from backend.database import get_db
from backend.limiter import limiter
from backend.services import signal_service

logger = logging.getLogger(__name__)
router = APIRouter()


class InsightRequest(BaseModel):
    prices: dict = Field(default_factory=dict)
    usage: dict = Field(default_factory=dict)


class MarketInfographicRequest(BaseModel):
    summary: str = Field("", max_length=2000)
    direction: str = Field("neutral", pattern="^(bullish|bearish|neutral)$")
    confidence: float = Field(0.0, ge=0, le=100)
    key_points: list[str] = Field(default_factory=list, max_length=10)
    sources: list[str] = Field(default_factory=list, max_length=20)


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
async def analyze(
    request: Request,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
):
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

        # Record a structured signal so confidence and outcomes can be tracked.
        signal_id = None
        try:
            confidence = analysis.get("confidence") if isinstance(analysis, dict) else None
            if not isinstance(confidence, (int, float)):
                confidence = 0.0
            sources = analysis.get("sources") if isinstance(analysis, dict) else None
            if not isinstance(sources, list):
                sources = [a["url"] for a in articles if a.get("url")]
            row = await signal_service.record_signal(
                db,
                kind="analysis",
                subject="vvv",
                direction=str(analysis.get("sentiment") or "neutral"),
                confidence=confidence,
                rationale=str(analysis.get("summary") or ""),
                sources=[str(url) for url in sources if url],
                metrics={
                    "key_events": analysis.get("key_events") or [],
                    "risks": analysis.get("risks") or [],
                    "decisions_status": decisions_status,
                },
                entry_price_usd=signal_service.extract_entry_price(body.prices),
            )
            signal_id = row.id
        except Exception:
            logger.exception("Failed to record analysis signal")

        return {
            "analysis": analysis,
            "articles": articles,
            "model": chat_model,
            "decisions": decisions.model_dump() if decisions is not None else None,
            "decisions_status": decisions_status,
            "signal_id": signal_id,
        }
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, "Venice analysis failed") from exc
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        raise HTTPException(504, "Venice analysis is temporarily unavailable") from exc
    except Exception as exc:
        logger.exception("Market analysis failed")
        raise HTTPException(500, "Failed to generate market analysis") from exc


def _build_market_infographic_prompt(
    *,
    direction: str,
    confidence: float,
    summary: str,
    key_points: list[str],
    prices: dict,
    signal_count: int,
) -> str:
    points = "\n".join(f"- {point}" for point in key_points[:6])
    vvv_price = None
    if isinstance(prices, dict):
        vvv = prices.get("vvv")
        if isinstance(vvv, dict):
            vvv_price = vvv.get("usd")
        if vvv_price is None:
            vvv_price = prices.get("vvv_price_usd")
    price_line = f"VVV reference price: ${vvv_price}." if isinstance(vvv_price, (int, float)) else ""
    return (
        "A professional dark-mode 4K market recap infographic titled "
        "'VVV / DIEM Market Signal'. "
        f"Headline sentiment: {direction.upper()} with {confidence:.0f}% model confidence. "
        f"{price_line} Signals tracked: {signal_count}. "
        f"Summary: {summary[:400] or 'No summary supplied.'} "
        f"Key points:\n{points}\n"
        "Include an abstract candlestick chart motif, sentiment gauge, and clean statistic "
        "tiles. Color scheme: dark navy background, indigo accents, green for bullish, "
        "red for bearish, amber for neutral. No photo-realistic elements, no financial advice."
    )


@router.post("/insights/infographic")
@limiter.limit("5/day")
async def generate_market_infographic(
    request: Request,
    body: MarketInfographicRequest,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
):
    """Generate a 4K market infographic from the latest structured signal."""
    api_key = settings.VENICE_API_KEY or settings.VENICE_ADMIN_KEY
    if not api_key:
        raise HTTPException(400, "No Venice API key configured")

    direction = body.direction
    confidence = body.confidence
    summary = body.summary
    key_points = list(body.key_points)
    signal_count = 0
    try:
        signals = await signal_service.list_signals(db, limit=25)
        signal_count = len(signals)
        if not summary and signals:
            latest = signals[0]
            direction = latest.direction
            confidence = latest.confidence
            summary = latest.rationale
            metrics = {}
            try:
                metrics = json.loads(latest.metrics)
            except (TypeError, json.JSONDecodeError):
                metrics = {}
            if not key_points:
                key_points = [str(item) for item in metrics.get("key_events") or []]
    except Exception:
        logger.exception("Failed to load signals for infographic")

    prices: dict = {}
    try:
        metrics = await venicestats_client.get_metrics(settings)
        prices = {"vvv": {"usd": metrics.get("vvvPrice")}}
    except Exception:
        logger.warning("Price context unavailable for infographic")

    prompt = _build_market_infographic_prompt(
        direction=direction,
        confidence=confidence,
        summary=summary,
        key_points=key_points,
        prices=prices,
        signal_count=signal_count,
    )
    try:
        image_b64 = await media.generate_image(api_key, prompt)
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        raise HTTPException(502, f"Venice image API error: {detail}") from exc
    except ValueError as exc:
        raise HTTPException(502, str(exc)) from exc
    except Exception as exc:
        logger.exception("Market infographic generation failed")
        raise HTTPException(500, f"Infographic generation failed: {exc}") from exc
    return {"image_b64": image_b64, "prompt": prompt, "signal_count": signal_count}
