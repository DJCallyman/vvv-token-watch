import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from backend.config import get_settings, Settings
from backend.core.model_cache import ModelCacheManager
from backend.core.venice_api_client import VeniceAPIClient

logger = logging.getLogger(__name__)
router = APIRouter()


def get_venice_client(settings: Settings = Depends(get_settings)) -> VeniceAPIClient:
    # Prefer regular key for public /models; fall back to admin.
    api_key = settings.VENICE_API_KEY or settings.VENICE_ADMIN_KEY
    return VeniceAPIClient(api_key)


def get_model_cache(request: Request) -> ModelCacheManager:
    cache = getattr(request.app.state, "model_cache", None)
    if cache is None:
        # Lifespan failed to initialize the cache — surface a clear error so we
        # don't silently fall back to per-request file I/O.
        raise HTTPException(
            status_code=503,
            detail="Model cache unavailable (not initialized)",
        )
    return cache


@router.get("/models")
async def get_models(
    cache: ModelCacheManager = Depends(get_model_cache),
):
    try:
        await cache.fetch_models()

        # Prefer full Venice model objects so the UI can render type-specific
        # table columns (capabilities, privacy, quantization, constraints, etc.).
        raw_models = cache.get_all_raw_models()
        if raw_models:
            model_types = {
                model.get("type")
                for model in raw_models
                if model.get("type")
            }
            return {
                "models": raw_models,
                "count": len(raw_models),
                "types": sorted(model_types),
            }

        models = cache.get_all_models()
        model_types = {model.model_type for model in models.values() if model.model_type}

        return {
            "models": list(models.values()),
            "count": len(models),
            "types": sorted(model_types),
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch models")
        raise HTTPException(status_code=500, detail="Failed to fetch models")


@router.get("/models/traits")
async def get_model_traits(
    client: VeniceAPIClient = Depends(get_venice_client),
):
    """Passthrough of Venice GET /models/traits (trait → model ID mappings)."""
    try:
        return await client.get_json("/models/traits")
    except httpx.HTTPStatusError as e:
        logger.warning("Upstream error in /models/traits: %s", e)
        raise HTTPException(
            status_code=502,
            detail=f"Venice API error: {e.response.status_code if e.response else '?'}",
        ) from e
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning("Upstream unreachable in /models/traits: %s", e)
        raise HTTPException(status_code=504, detail=f"Venice API unreachable: {e}") from e
    except Exception:
        logger.exception("Failed to fetch model traits")
        raise HTTPException(status_code=500, detail="Failed to fetch model traits")


@router.get("/models/{model_id}")
async def get_model(
    model_id: str,
    cache: ModelCacheManager = Depends(get_model_cache),
):
    try:
        await cache.fetch_models()
        model = cache.get_model(model_id)

        if model is None:
            raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

        raw = cache.get_raw_model_data(model_id)
        return raw if raw is not None else model
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch model")
        raise HTTPException(status_code=500, detail="Failed to fetch model")
