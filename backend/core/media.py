"""Venice media helpers: images, speech, and async video (Phase 3)."""

from __future__ import annotations

import base64
import logging
from typing import Any, Dict, Optional, Tuple

import httpx

from backend.core.venice_api_client import VeniceAPIClient

logger = logging.getLogger(__name__)


async def resolve_image_model(api_key: str, client: Optional[VeniceAPIClient] = None) -> str:
    """Discover a current image model via /models/traits; fall back to flux-2-pro."""
    client = client or VeniceAPIClient(api_key)
    try:
        traits = await client.get_json("/models/traits")
        mapping = traits.get("data", traits) if isinstance(traits, dict) else {}
        for key in ("image:fast", "image:default", "image"):
            model_id = mapping.get(key)
            if isinstance(model_id, str) and model_id:
                return model_id
            if isinstance(model_id, dict):
                mid = model_id.get("id") or model_id.get("model")
                if mid:
                    return mid
    except Exception as exc:
        logger.warning("Could not resolve image model from traits: %s", exc)
    return "flux-2-pro"


async def generate_image(
    api_key: str,
    prompt: str,
    *,
    resolution: str = "4K",
    aspect_ratio: str = "16:9",
    client: Optional[VeniceAPIClient] = None,
) -> str:
    """Generate an image and return the first base64 payload."""
    client = client or VeniceAPIClient(api_key)
    model_id = await resolve_image_model(api_key, client)
    payload = {
        "model": model_id,
        "prompt": prompt,
        "resolution": resolution,
        "aspect_ratio": aspect_ratio,
        "format": "png",
        "safe_mode": True,
        "return_binary": False,
    }
    data = await client.post_json("/image/generate", data=payload, timeout=120.0)
    images = data.get("images", []) if isinstance(data, dict) else []
    if not images:
        raise ValueError("Venice image API returned no images")
    return images[0]


async def generate_speech(
    api_key: str,
    text: str,
    *,
    voice: str,
    model: str,
    response_format: str = "mp3",
    client: Optional[VeniceAPIClient] = None,
) -> bytes:
    """Generate speech audio bytes. Input is capped at the documented 4096 chars."""
    client = client or VeniceAPIClient(api_key)
    payload = {
        "input": text[:4096],
        "model": model,
        "voice": voice,
        "response_format": response_format,
        "speed": 1.0,
        "streaming": False,
    }
    response = await client.post("/audio/speech", data=payload, timeout=120.0)
    if response.status_code >= 400:
        response.raise_for_status()
    return response.content


async def queue_video(
    api_key: str,
    *,
    prompt: str,
    model: str,
    duration: str = "5s",
    resolution: str = "720p",
    aspect_ratio: Optional[str] = "16:9",
    client: Optional[VeniceAPIClient] = None,
) -> Dict[str, Any]:
    """Queue an async video generation. Returns the queue metadata."""
    client = client or VeniceAPIClient(api_key)
    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "duration": duration,
        "resolution": resolution,
    }
    if aspect_ratio:
        payload["aspect_ratio"] = aspect_ratio
    data = await client.post_json("/video/queue", data=payload, timeout=60.0)
    if not isinstance(data, dict):
        raise ValueError("Unexpected video queue response")
    return data


async def retrieve_video(
    api_key: str,
    *,
    model: str,
    queue_id: str,
    client: Optional[VeniceAPIClient] = None,
) -> Tuple[str, Optional[bytes], Optional[Dict[str, Any]]]:
    """Retrieve a queued video.

    Returns ``(status, video_bytes, metadata)`` where status is one of
    ``completed``, ``pending``, or ``error``.
    """
    client = client or VeniceAPIClient(api_key)
    response = await client.post(
        "/video/retrieve",
        data={
            "model": model,
            "queue_id": queue_id,
            "delete_media_on_completion": False,
        },
        timeout=120.0,
    )
    if response.status_code >= 400:
        return "error", None, {"error": f"HTTP {response.status_code}"}
    content_type = response.headers.get("content-type", "")
    if "video" in content_type or b"ftyp" in response.content[:20]:
        return "completed", response.content, None
    try:
        data = response.json()
    except Exception:
        if len(response.content) > 1000:
            return "completed", response.content, None
        return "pending", None, None
    if isinstance(data, dict):
        status = str(data.get("status") or "pending").lower()
        if status in ("completed", "complete"):
            return "completed", None, data
        if status in ("failed", "error"):
            return "error", None, data
        return "pending", None, data
    return "pending", None, None


def audio_data_url(audio: bytes, fmt: str = "mp3") -> str:
    return f"data:audio/{fmt};base64,{base64.b64encode(audio).decode('ascii')}"
