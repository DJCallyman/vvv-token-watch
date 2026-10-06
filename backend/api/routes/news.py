"""Fresh Venice web-search results, semantic search, and RAG for VVV/DIEM."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.api.routes.ai_common import (
    extract_chat_text,
    get_client,
    normalize_search,
    unwrap_data,
)
from backend.config import Settings, get_settings
from backend.core.cache import TtlCache
from backend.core.embeddings import EmbeddingError, rank_by_similarity
from backend.core.venice_api_client import VeniceAPIClient
from backend.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter()
_cache = TtlCache(max_size=128)


class NewsSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=300)
    top_k: int = Field(5, ge=1, le=20)


class NewsAskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)
    top_k: int = Field(5, ge=1, le=10)


async def fetch_news(settings: Settings, refresh: bool = False) -> Dict[str, Any]:
    if not refresh:
        cached = _cache.get("news")
        if cached is not None:
            return cached
    client = get_client(settings)
    payload = await client.post_json("/augment/search", data={
        "query": "VVV Venice AI token DIEM crypto latest news",
        "limit": 20,
    }, timeout=30)
    articles = normalize_search(payload)
    result = {"articles": articles, "count": len(articles), "source": "Venice web search"}
    _cache.set("news", result, ttl=900)
    return result


@router.get("/news")
@limiter.limit("30/hour")
async def get_news(request: Request, refresh: bool = False, settings: Settings = Depends(get_settings)):
    try:
        return await fetch_news(settings, refresh=refresh)
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


def _article_text(article: Dict[str, Any]) -> str:
    return " ".join(
        str(part)
        for part in (article.get("title"), article.get("snippet"), article.get("source"))
        if part
    )


async def semantic_search(
    settings: Settings,
    query: str,
    top_k: int,
) -> List[Dict[str, Any]]:
    news = await fetch_news(settings)
    articles = news.get("articles", [])
    if not articles:
        return []
    client = get_client(settings)
    try:
        ranked = await rank_by_similarity(
            client,
            settings.EMBEDDING_MODEL,
            query,
            [_article_text(article) for article in articles],
            top_k=top_k,
        )
    except EmbeddingError as exc:
        raise HTTPException(502, f"Embeddings unavailable: {exc}") from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f"Venice embeddings failed: {exc.response.status_code}") from exc
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        raise HTTPException(504, "Venice embeddings are temporarily unavailable") from exc
    return [
        {**articles[index], "score": round(score, 4)}
        for index, score in ranked
        if 0 <= index < len(articles)
    ]


@router.post("/news/search")
@limiter.limit("30/hour")
async def search_news(
    request: Request,
    body: NewsSearchRequest,
    settings: Settings = Depends(get_settings),
):
    """Semantic search over the cached news set using Venice embeddings."""
    results = await semantic_search(settings, body.query, body.top_k)
    return {
        "query": body.query,
        "results": results,
        "count": len(results),
        "model": settings.EMBEDDING_MODEL,
        "source": "Venice embeddings over Venice web-search results",
    }


@router.post("/news/ask")
@limiter.limit("20/hour")
async def ask_news(
    request: Request,
    body: NewsAskRequest,
    settings: Settings = Depends(get_settings),
):
    """Retrieval-augmented answer grounded in the retrieved articles."""
    results = await semantic_search(settings, body.question, body.top_k)
    if not results:
        return {
            "answer": "No indexed news articles are available to answer this question.",
            "sources": [],
            "retrieved": [],
        }
    context = json.dumps(
        [
            {"title": article.get("title"), "url": article.get("url"), "snippet": article.get("snippet")}
            for article in results
        ],
        default=str,
    )
    client = get_client(settings)
    try:
        completion = await client.post_json(
            "/chat/completions",
            data={
                "model": settings.ASSISTANT_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Answer the question using only the supplied news articles. "
                            "Cite sources inline as markdown links. If the articles do not "
                            "contain the answer, say so. Do not give financial advice."
                        ),
                    },
                    {"role": "user", "content": f"Question: {body.question}\n\nArticles:\n{context}"},
                ],
                "max_tokens": 800,
                "temperature": 0.2,
                "venice_parameters": {
                    "include_venice_system_prompt": False,
                    "enable_web_search": "off",
                },
            },
            timeout=60,
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f"Venice chat failed: {exc.response.status_code}") from exc
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        raise HTTPException(504, "Venice chat is temporarily unavailable") from exc
    return {
        "answer": extract_chat_text(completion),
        "sources": [article.get("url") for article in results if article.get("url")],
        "retrieved": results,
        "model": settings.ASSISTANT_MODEL,
    }
