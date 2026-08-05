"""API Key management endpoints.

Proxies CRUD operations for Venice API keys to the upstream Venice API.
All write operations require the admin key (configured via VENICE_ADMIN_KEY).

Venice API quirks handled here:
    * ``POST /api_keys`` returns the raw ``apiKey`` secret exactly once —
      pass it through to the caller so the dashboard can display + copy it.
    * ``PATCH /api_keys`` takes the key ID **in the request body**, not in
      the path.
    * ``DELETE /api_keys`` takes the key ID **as a query parameter**, not
      in the path.
    * Request bodies use ``consumptionLimit`` (singular); Venice responses
      use ``consumptionLimits`` (plural). This thin proxy passes through
      whatever Venice returns — naming normalization is the caller's job.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path, Query

from backend.config import Settings, get_settings
from backend.core.venice_api_client import VeniceAPIClient
from backend.models.schemas import ApiKeyCreate, ApiKeyUpdate, ConsumptionLimit

logger = logging.getLogger(__name__)
router = APIRouter()


def get_venice_client(settings: Settings = Depends(get_settings)) -> VeniceAPIClient:
    # API key management requires the admin key; a regular inference key
    # is rejected by the upstream with 401/403.
    return VeniceAPIClient(settings.VENICE_ADMIN_KEY)


def _map_upstream_error(e: httpx.HTTPStatusError) -> HTTPException:
    """Translate a Venice HTTPStatusError into the right FastAPI response.

    4xx errors (including 401, 403, 429) are propagated as-is so the caller
    sees the same status code Venice returned. 5xx errors are mapped to 502
    so the dashboard distinguishes upstream outages from its own failures.
    """
    status = e.response.status_code if e.response is not None else 502
    detail: str
    try:
        body = e.response.json() if e.response is not None else {}
    except Exception:
        body = {}
    if isinstance(body, dict):
        detail = str(body.get("error") or body.get("message") or e)
    else:
        detail = str(e)
    if status >= 500:
        return HTTPException(status_code=502, detail=f"Venice API error: {status} {detail}")
    return HTTPException(status_code=status, detail=detail)


@router.post("/keys", status_code=201)
async def create_api_key(
    body: ApiKeyCreate,
    client: VeniceAPIClient = Depends(get_venice_client),
):
    """Proxy ``POST /api_keys`` to Venice. Returns the full response body,
    which includes the raw ``apiKey`` secret shown to the user on creation."""
    payload: Dict[str, Any] = {"apiKeyType": body.apiKeyType, "description": body.description}
    if body.consumptionLimit is not None:
        payload["consumptionLimit"] = body.consumptionLimit.model_dump(exclude_none=True)
    if body.limitPeriod is not None:
        payload["limitPeriod"] = body.limitPeriod
    if body.expiresAt is not None:
        payload["expiresAt"] = body.expiresAt

    try:
        return await client.post_json("/api_keys", data=payload)
    except httpx.HTTPStatusError as e:
        logger.warning("Upstream Venice API error creating API key: %s", e)
        raise _map_upstream_error(e) from e
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning("Upstream Venice API unreachable creating API key: %s", e)
        raise HTTPException(status_code=504, detail=f"Venice API unreachable: {e}") from e
    except Exception:
        logger.exception("Failed to create API key")
        raise HTTPException(status_code=500, detail="Failed to create API key")


@router.patch("/keys")
async def update_api_key(
    body: ApiKeyUpdate,
    client: VeniceAPIClient = Depends(get_venice_client),
):
    """Proxy ``PATCH /api_keys`` to Venice. The key ID is passed in the body
    (not the URL path) per the upstream API contract."""
    payload: Dict[str, Any] = {"id": body.id}
    if body.description is not None:
        payload["description"] = body.description
    if body.consumptionLimit is not None:
        payload["consumptionLimit"] = body.consumptionLimit.model_dump(exclude_none=True)
    if body.limitPeriod is not None:
        payload["limitPeriod"] = body.limitPeriod
    if body.expiresAt is not None:
        payload["expiresAt"] = body.expiresAt

    try:
        response = await client.patch("/api_keys", data=payload)
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.warning("Upstream Venice API error updating API key %s: %s", body.id, e)
        raise _map_upstream_error(e) from e
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning("Upstream Venice API unreachable updating API key: %s", e)
        raise HTTPException(status_code=504, detail=f"Venice API unreachable: {e}") from e
    except Exception:
        logger.exception("Failed to update API key")
        raise HTTPException(status_code=500, detail="Failed to update API key")


@router.delete("/keys")
async def delete_api_key(
    id: str = Query(..., description="The ID of the API key to delete"),
    client: VeniceAPIClient = Depends(get_venice_client),
):
    """Proxy ``DELETE /api_keys?id=...`` to Venice. The key ID is passed as a
    query parameter (not a URL segment) per the upstream API contract."""
    try:
        response = await client.delete("/api_keys", params={"id": id})
        if response.status_code == 204:
            return {"success": True, "id": id}
        body: Any = {}
        try:
            body = response.json()
        except Exception:
            body = {}
        if not response.is_success:
            err = httpx.HTTPStatusError(
                f"{response.status_code}",
                request=response.request,
                response=response,
            )
            raise _map_upstream_error(err) from err
        if isinstance(body, dict) and "success" in body:
            return body
        return {"success": True, "id": id}
    except httpx.HTTPStatusError as e:
        logger.warning("Upstream Venice API error deleting API key %s: %s", id, e)
        raise _map_upstream_error(e) from e
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning("Upstream Venice API unreachable deleting API key: %s", e)
        raise HTTPException(status_code=504, detail=f"Venice API unreachable: {e}") from e
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete API key")
        raise HTTPException(status_code=500, detail="Failed to delete API key")


@router.get("/keys/{key_id}")
async def get_api_key_detail(
    key_id: str = Path(..., description="The ID of the API key to retrieve"),
    client: VeniceAPIClient = Depends(get_venice_client),
):
    """Proxy ``GET /api_keys/{id}`` to Venice. Returns the key detail payload."""
    try:
        return await client.get_json(f"/api_keys/{key_id}")
    except httpx.HTTPStatusError as e:
        logger.warning("Upstream Venice API error fetching API key %s: %s", key_id, e)
        raise _map_upstream_error(e) from e
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning("Upstream Venice API unreachable fetching API key: %s", e)
        raise HTTPException(status_code=504, detail=f"Venice API unreachable: {e}") from e
    except Exception:
        logger.exception("Failed to fetch API key detail")
        raise HTTPException(status_code=500, detail="Failed to fetch API key detail")
