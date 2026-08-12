"""Small helpers shared by Venice-backed market features."""

from __future__ import annotations

from typing import Any

from backend.config import Settings
from backend.core.venice_api_client import VeniceAPIClient


def get_client(settings: Settings) -> VeniceAPIClient:
    return VeniceAPIClient(settings.VENICE_API_KEY or settings.VENICE_ADMIN_KEY)


def unwrap_data(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def normalize_search(payload: Any) -> list[dict[str, Any]]:
    value = unwrap_data(payload)
    if isinstance(value, dict):
        value = value.get("results") or value.get("documents") or value.get("items") or []
    if not isinstance(value, list):
        return []
    results = []
    for item in value:
        if not isinstance(item, dict):
            continue
        results.append({
            "title": item.get("title") or item.get("name") or "Untitled",
            "url": item.get("url") or item.get("link"),
            "snippet": item.get("snippet") or item.get("description") or item.get("content") or "",
            "date": item.get("date") or item.get("published_at") or item.get("publishedDate"),
            "source": item.get("source") or item.get("domain"),
        })
    return results


def extract_chat_text(payload: Any) -> str:
    choices = payload.get("choices", []) if isinstance(payload, dict) else []
    message = choices[0].get("message", {}) if choices else {}
    content = message.get("content", "")
    return content if isinstance(content, str) else str(content)
