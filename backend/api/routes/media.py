"""Voice alerts, daily briefings, and video market recaps (Phase 3)."""

from __future__ import annotations

import base64
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import Settings, get_settings
from backend.core import media, venicestats_client
from backend.database import get_db
from backend.limiter import limiter
from backend.models.db import AlertEvent
from backend.services import signal_service

logger = logging.getLogger(__name__)
router = APIRouter()

_SAFE_FILENAME = re.compile(r"^[A-Za-z0-9._-]{1,120}$")


class BriefingRequest(BaseModel):
    text: Optional[str] = Field(None, max_length=4000)
    voice: Optional[str] = Field(None, max_length=32)


class VideoRecapRequest(BaseModel):
    prompt: Optional[str] = Field(None, max_length=2000)
    duration: str = Field("5s", pattern="^(5s|10s)$")
    resolution: str = Field("720p", pattern="^(480p|720p|1080p)$")


def _api_key(settings: Settings) -> str:
    key = settings.VENICE_API_KEY or settings.VENICE_ADMIN_KEY
    if not key:
        raise HTTPException(400, "No Venice API key configured")
    return key


def _media_dir(settings: Settings) -> Path:
    target = Path(settings.DATA_DIR) / "media"
    target.mkdir(parents=True, exist_ok=True)
    return target


async def _build_briefing_text(
    db: AsyncSession,
    settings: Settings,
) -> str:
    parts: list[str] = ["VVV Token Watch daily briefing."]
    try:
        metrics = await venicestats_client.get_metrics(settings)
        vvv = metrics.get("vvvPrice")
        diem = metrics.get("diemPrice")
        if isinstance(vvv, (int, float)):
            parts.append(f"VVV is trading at {vvv:.4f} US dollars.")
        if isinstance(diem, (int, float)):
            parts.append(f"DIEM is trading at {diem:.4f} US dollars.")
    except Exception:
        parts.append("Live prices are currently unavailable.")
    try:
        signals = await signal_service.list_signals(db, limit=5)
        if signals:
            latest = signals[0]
            parts.append(
                f"The latest AI signal is {latest.direction} with "
                f"{latest.confidence:.0f} percent confidence."
            )
            if latest.rationale:
                parts.append(latest.rationale[:400])
        else:
            parts.append("No AI signals have been recorded yet.")
    except Exception:
        logger.exception("Failed to build briefing signal context")
    parts.append("This briefing is informational only and is not financial advice.")
    return " ".join(parts)


@router.post("/tts/briefing")
@limiter.limit("10/hour")
async def generate_briefing(
    request: Request,
    body: BriefingRequest,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
):
    """Generate a spoken daily briefing via Venice TTS."""
    text = (body.text or "").strip() or await _build_briefing_text(db, settings)
    if len(text) > 4096:
        raise HTTPException(422, "Briefing text exceeds the 4096 character TTS limit")
    try:
        audio = await media.generate_speech(
            _api_key(settings),
            text,
            voice=body.voice or settings.TTS_VOICE,
            model=settings.TTS_MODEL,
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f"Venice TTS failed: {exc.response.status_code}") from exc
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        raise HTTPException(504, "Venice TTS is temporarily unavailable") from exc
    except Exception as exc:
        logger.exception("Briefing generation failed")
        raise HTTPException(500, "Failed to generate briefing") from exc
    return {
        "text": text,
        "audio_b64": base64.b64encode(audio).decode("ascii"),
        "mime": "audio/mpeg",
        "voice": body.voice or settings.TTS_VOICE,
        "model": settings.TTS_MODEL,
    }


@router.post("/tts/alert/{event_id}")
@limiter.limit("30/hour")
async def generate_alert_voice(
    request: Request,
    event_id: int,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
):
    """Generate speech for a specific alert event."""
    event = await db.get(AlertEvent, event_id)
    if event is None:
        raise HTTPException(404, f"Event {event_id} not found")
    text = f"Alert. {event.message}"
    try:
        audio = await media.generate_speech(
            _api_key(settings),
            text,
            voice=settings.TTS_VOICE,
            model=settings.TTS_MODEL,
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f"Venice TTS failed: {exc.response.status_code}") from exc
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        raise HTTPException(504, "Venice TTS is temporarily unavailable") from exc
    except Exception as exc:
        logger.exception("Alert voice generation failed")
        raise HTTPException(500, "Failed to generate alert voice") from exc
    return {
        "event_id": event.id,
        "text": text,
        "audio_b64": base64.b64encode(audio).decode("ascii"),
        "mime": "audio/mpeg",
    }


def _build_video_prompt(direction: str, confidence: float, summary: str, price: Optional[float]) -> str:
    price_line = f" A price ticker shows ${price:.4f}." if isinstance(price, (int, float)) else ""
    return (
        "Cinematic dark-mode financial market recap for the VVV and DIEM crypto tokens. "
        f"Headline sentiment is {direction} with {confidence:.0f}% confidence.{price_line} "
        f"{summary[:300]} "
        "Style: abstract candlestick charts, glowing indigo and teal accents on a deep navy "
        "background, smooth camera motion, no text overlays, no financial advice."
    )


@router.post("/video/recap")
@limiter.limit("3/day")
async def queue_video_recap(
    request: Request,
    body: VideoRecapRequest,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
):
    """Queue an asynchronous video market recap."""
    prompt = (body.prompt or "").strip()
    if not prompt:
        direction, confidence, summary, price = "neutral", 0.0, "", None
        try:
            signals = await signal_service.list_signals(db, limit=1)
            if signals:
                latest = signals[0]
                direction = latest.direction
                confidence = latest.confidence
                summary = latest.rationale
                price = latest.entry_price_usd
        except Exception:
            logger.exception("Failed to load signal context for video recap")
        try:
            metrics = await venicestats_client.get_metrics(settings)
            latest_price = metrics.get("vvvPrice")
            if isinstance(latest_price, (int, float)):
                price = float(latest_price)
        except Exception:
            logger.warning("Price context unavailable for video recap")
        prompt = _build_video_prompt(direction, confidence, summary, price)
    try:
        data = await media.queue_video(
            _api_key(settings),
            prompt=prompt,
            model=settings.VIDEO_MODEL,
            duration=body.duration,
            resolution=body.resolution,
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f"Venice video queue failed: {exc.response.status_code}") from exc
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        raise HTTPException(504, "Venice video service is temporarily unavailable") from exc
    except Exception as exc:
        logger.exception("Video recap queue failed")
        raise HTTPException(500, "Failed to queue video recap") from exc
    queue_id = data.get("queue_id") or data.get("id") or data.get("queueId")
    if not queue_id:
        raise HTTPException(502, "Video queue response did not include a queue id")
    return {
        "queue_id": queue_id,
        "model": settings.VIDEO_MODEL,
        "prompt": prompt,
        "status": "queued",
    }


@router.get("/video/recap/{queue_id}")
@limiter.limit("120/hour")
async def retrieve_video_recap(
    request: Request,
    queue_id: str,
    model: Optional[str] = None,
    settings: Settings = Depends(get_settings),
):
    """Poll a queued video. Saves completed media locally and returns a URL."""
    if not _SAFE_FILENAME.match(queue_id):
        raise HTTPException(400, "Invalid queue id")
    model_id = model or settings.VIDEO_MODEL
    try:
        status, video_bytes, metadata = await media.retrieve_video(
            _api_key(settings), model=model_id, queue_id=queue_id
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f"Venice video retrieve failed: {exc.response.status_code}") from exc
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        raise HTTPException(504, "Venice video service is temporarily unavailable") from exc
    except Exception as exc:
        logger.exception("Video recap retrieval failed")
        raise HTTPException(500, "Failed to retrieve video recap") from exc

    response: dict[str, Any] = {"queue_id": queue_id, "model": model_id, "status": status}
    if metadata:
        response["metadata"] = metadata
    if status == "completed" and video_bytes:
        filename = f"recap-{queue_id}.mp4"
        target = _media_dir(settings) / filename
        target.write_bytes(video_bytes)
        response["video_url"] = f"/api/video/file/{filename}"
        response["generated_at"] = datetime.now(timezone.utc).isoformat()
        response["bytes"] = len(video_bytes)
    return response


@router.get("/video/file/{filename}")
async def get_video_file(
    filename: str,
    settings: Settings = Depends(get_settings),
):
    if not _SAFE_FILENAME.match(filename):
        raise HTTPException(400, "Invalid filename")
    target = _media_dir(settings) / filename
    if not target.is_file():
        raise HTTPException(404, "Video not found")
    return FileResponse(target, media_type="video/mp4", filename=filename)
