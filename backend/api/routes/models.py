from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
import httpx
from backend.config import get_settings, Settings
from backend.core.venice_api_client import VeniceAPIClient

router = APIRouter()


def get_venice_client(settings: Settings = Depends(get_settings)) -> VeniceAPIClient:
    return VeniceAPIClient(settings.VENICE_ADMIN_KEY)


@router.get("/models")
async def get_models(
    client: VeniceAPIClient = Depends(get_venice_client)
):
    try:
        response = client.get("/models")
        data = response.json()
        
        models = data.get("data", [])
        model_types = set()
        for model in models:
            model_type = model.get("type", "unknown")
            model_types.add(model_type)
        
        return {
            "models": models,
            "count": len(models),
            "types": list(model_types)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/{model_id}")
async def get_model(
    model_id: str,
    client: VeniceAPIClient = Depends(get_venice_client)
):
    try:
        response = client.get("/models")
        data = response.json()
        
        for model in data.get("data", []):
            if model.get("id") == model_id:
                return model
        
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))