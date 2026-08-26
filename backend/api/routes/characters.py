"""Proxy Venice character discovery and detail endpoints.

The proxy forwards the Venice ``GET /characters`` and
``GET /characters/{slug}`` endpoints to the character browser.

Venice lists these endpoints as a Preview API. Keep this proxy thin because
the response fields can change. Venice addresses characters by slug, such as
``alan-watts``, not by ID. A Bearer API key is required. Authenticated
requests include ``stats.userRating``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import Response

from backend.config import Settings, get_settings
from backend.core.venice_api_client import VeniceAPIClient

logger = logging.getLogger(__name__)
router = APIRouter()


def get_venice_client(settings: Settings = Depends(get_settings)) -> VeniceAPIClient:
    # Public character discovery works with any inference key; fall back to
    # admin if the regular key isn't configured.
    return VeniceAPIClient(settings.VENICE_API_KEY or settings.VENICE_ADMIN_KEY)


def _map_error(e: httpx.HTTPStatusError) -> HTTPException:
    status = e.response.status_code if e.response is not None else 502
    if status >= 500:
        return HTTPException(
            status_code=502,
            detail=f"Venice API error: {status} {e}",
        )
    return HTTPException(status_code=status, detail=str(e))


@router.get("/characters")
async def list_characters(
    search: Optional[str] = Query(None, max_length=200, description="Search by name/description/hashtags"),
    tags: Optional[List[str]] = Query(None, max_length=20, description="Filter by tag names (repeat param)"),
    categories: Optional[List[str]] = Query(None, max_length=20, description="Filter by categories (repeat param)"),
    modelId: Optional[List[str]] = Query(None, max_length=20, alias="modelId", description="Filter by model id(s)"),
    isAdult: Optional[str] = Query(None, pattern="^(true|false)$"),
    isPro: Optional[str] = Query(None, pattern="^(true|false)$"),
    isWebEnabled: Optional[str] = Query(None, pattern="^(true|false)$"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sortBy: Optional[str] = Query(
        None,
        pattern="^(featured|highestRating|highlyRated|highlyRatedAndRecent|imports|mostRecent|ratingCount)$",
    ),
    sortOrder: Optional[str] = Query(None, pattern="^(asc|desc)$"),
    client: VeniceAPIClient = Depends(get_venice_client),
):
    """Forward ``GET /characters`` with validation for filter values.

    Keep the filter set open because Venice can add new filters.
    """
    params: Dict[str, Any] = {}
    if search:
        params["search"] = search
    if tags:
        # Venice accepts comma-separated repeated values; serialize accordingly.
        params["tags"] = tags
    if categories:
        params["categories"] = categories
    if modelId:
        params["modelId"] = modelId
    if isAdult:
        params["isAdult"] = isAdult
    if isPro:
        params["isPro"] = isPro
    if isWebEnabled:
        params["isWebEnabled"] = isWebEnabled
    params["limit"] = limit
    params["offset"] = offset
    if sortBy:
        params["sortBy"] = sortBy
    if sortOrder:
        params["sortOrder"] = sortOrder

    try:
        return await client.get_json("/characters", params=params)
    except httpx.HTTPStatusError as e:
        logger.warning("Upstream Venice API error listing characters: %s", e)
        raise _map_error(e) from e
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning("Upstream Venice API unreachable listing characters: %s", e)
        raise HTTPException(status_code=504, detail=f"Venice API unreachable: {e}") from e
    except Exception:
        logger.exception("Failed to list characters")
        raise HTTPException(status_code=500, detail="Failed to list characters")


@router.get("/characters/{slug}/photo")
async def get_character_photo(
    slug: str = Path(..., description="The character slug (e.g. 'alan-watts')"),
    client: VeniceAPIClient = Depends(get_venice_client),
):
    """Serve a character photo from this origin.

    This avoids cross-origin resource policy blocks from the upstream host.
    """
    try:
        character = await client.get_json(f"/characters/{slug}")
        photo_url = (character.get("data") or {}).get("photoUrl")
        parsed_url = urlparse(photo_url or "")
        if parsed_url.scheme != "https" or parsed_url.netloc != "outerface.venice.ai":
            raise HTTPException(status_code=404, detail="Character photo not available")

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as http_client:
            photo_response = await http_client.get(
                photo_url,
                headers={
                    "Accept": "image/*",
                    "Referer": "https://outerface.venice.ai/",
                    "User-Agent": "Mozilla/5.0",
                },
            )
        photo_response.raise_for_status()
        content_type = photo_response.headers.get("content-type", "").split(";", 1)[0]
        if not content_type.startswith("image/"):
            raise HTTPException(status_code=502, detail="Character photo response was not an image")

        return Response(
            content=photo_response.content,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=3600"},
        )
    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        status = e.response.status_code if e.response is not None else 502
        if status == 404:
            raise HTTPException(status_code=404, detail="Character photo not found") from e
        raise HTTPException(status_code=502, detail="Failed to fetch character photo") from e
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning("Upstream Venice API unreachable fetching photo for %s: %s", slug, e)
        raise HTTPException(status_code=504, detail="Venice character photo unavailable") from e
    except Exception:
        logger.exception("Failed to fetch photo for character %s", slug)
        raise HTTPException(status_code=500, detail="Failed to fetch character photo")


@router.get("/characters/{slug}")
async def get_character(
    slug: str = Path(..., description="The character slug (e.g. 'alan-watts')"),
    client: VeniceAPIClient = Depends(get_venice_client),
):
    """Forward ``GET /characters/{slug}`` by URL slug.

    Venice does not address characters by UUID.
    """
    try:
        return await client.get_json(f"/characters/{slug}")
    except httpx.HTTPStatusError as e:
        status = e.response.status_code if e.response is not None else 502
        if status == 404:
            raise HTTPException(status_code=404, detail=f"Character '{slug}' not found") from e
        logger.warning("Upstream Venice API error fetching character %s: %s", slug, e)
        raise _map_error(e) from e
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning("Upstream Venice API unreachable fetching character: %s", e)
        raise HTTPException(status_code=504, detail=f"Venice API unreachable: {e}") from e
    except Exception:
        logger.exception("Failed to fetch character %s", slug)
        raise HTTPException(status_code=500, detail="Failed to fetch character")
