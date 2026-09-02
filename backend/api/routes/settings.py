"""Authenticated runtime settings endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import Settings, get_settings
from backend.database import get_db
from backend.models.schemas import AppSettingsResponse, AppSettingsUpdate
from backend.services.app_settings import get_effective_settings, reset_settings, update_settings

router = APIRouter()


@router.get("/settings", response_model=AppSettingsResponse)
async def read_settings(
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
):
    return await get_effective_settings(db, settings)


@router.patch("/settings", response_model=AppSettingsResponse)
async def write_settings(
    updates: AppSettingsUpdate,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
):
    return await update_settings(db, settings, updates.model_dump(exclude_none=True))


@router.post("/settings/reset", response_model=AppSettingsResponse)
async def restore_settings(
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
):
    return await reset_settings(db, settings)