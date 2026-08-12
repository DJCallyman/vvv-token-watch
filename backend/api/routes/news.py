"""Fresh Venice web-search results for VVV and DIEM."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from backend.api.routes.ai_common import get_client, normalize_search, unwrap_data
from backend.config import Settings, get_settings
from backend.core.cache import TtlCache
from backend.core.venice_api_client import VeniceAPIClient
from backend.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter()
_cache = TtlCache(max_size=128)


@router.get("/news")
@limiter.limit("30/hour")
async def get_news(request: Request, refresh: bool = False, settings: Settings = Depends(get_settings)):
    if not refresh:
        cached = _cache.get("news")
        if cached is not None:
            return cached
    client = get_client(settings)
    try:
        payload = await client.post_json("/augment/search", data={
            "query": "VVV Venice AI token DIEM crypto latest news",
            "limit": 20,
        }, timeout=30)
        articles = normalize_search(payload)
        result = {"articles": articles, "count": len(articles), "source": "Venice web search"}
        _cache.set("news", result, ttl=900)
        return result
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f"Venice search failed: {exc.response.status_code}") from exc
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        raise HTTPException(504, "Venice search is temporarily unavailable") from exc
    except Exception as exc:
        logger.exception("News search failed")
        raise HTTPException(500, "Failed to load news") from exc


@router.get("/news/article")
@limiter.limit("60/hour")
async def get_article(request: Request, url: str = Query(..., min_length=8), settings: Settings = Depends(get_settings)):
    key = f"article:{url}"
    cached = _cache.get(key)
    if cached is not None:
        return cached
    try:
        payload = await get_client(settings).post_json("/augment/scrape", data={"url": url}, timeout=30)
        value = unwrap_data(payload)
        if isinstance(value, dict):
            content = value.get("markdown") or value.get("content") or value.get("text") or ""
            title = value.get("title") or url
        else:
            content, title = str(value), url
        result = {"url": url, "title": title, "content": content}
        _cache.set(key, result, ttl=3600)
        return result
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, "Unable to retrieve article") from exc
    except Exception as exc:
        logger.exception("Article scrape failed")
        raise HTTPException(500, "Failed to retrieve article") from exc
