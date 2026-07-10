import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from backend.config import get_settings, Settings
from backend.core.venice_api_client import VeniceAPIClient
from backend.core.model_cache import ModelCacheManager

logger = logging.getLogger(__name__)
router = APIRouter()


def get_venice_client(settings: Settings = Depends(get_settings)) -> VeniceAPIClient:
    return VeniceAPIClient(settings.VENICE_ADMIN_KEY)


@router.get("/models")
async def get_models(
    client: VeniceAPIClient = Depends(get_venice_client)
):
    try:
        cache = ModelCacheManager(client)
        await asyncio.to_thread(cache.fetch_models)

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
    except Exception as e:
        logger.exception("Failed to fetch models")
        raise HTTPException(status_code=500, detail="Failed to fetch models")


@router.get("/models/{model_id}")
async def get_model(
    model_id: str,
    client: VeniceAPIClient = Depends(get_venice_client)
):
    try:
        cache = ModelCacheManager(client)
        await asyncio.to_thread(cache.fetch_models)
        model = cache.get_model(model_id)

        if model is None:
            raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

        raw = cache.get_raw_model_data(model_id)
        return raw if raw is not None else model
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to fetch model")
        raise HTTPException(status_code=500, detail="Failed to fetch model")