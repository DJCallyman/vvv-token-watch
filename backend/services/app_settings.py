"""Persistence and resolution for safe runtime application settings."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import Settings
from backend.models.db import AppSettings


SETTING_KEYS = (
    "coingecko_holding_amount",
    "diem_holding_amount",
    "vvv_holding_source",
    "vvv_wallet_address",
    "benchmark_max_cost_usd",
    "benchmark_enable_billing_reconciliation",
    "benchmark_judge_model",
    "refresh_interval_seconds",
    "in_app_notifications_enabled",
    "display_currency",
    "timezone",
    "dashboard_layout",
)


def environment_defaults(settings: Settings) -> dict[str, Any]:
    return {
        "coingecko_holding_amount": settings.COINGECKO_HOLDING_AMOUNT,
        "diem_holding_amount": settings.DIEM_HOLDING_AMOUNT,
        "vvv_holding_source": "manual",
        "vvv_wallet_address": "",
        "benchmark_max_cost_usd": settings.BENCHMARK_MAX_COST_USD,
        "benchmark_enable_billing_reconciliation": settings.BENCHMARK_ENABLE_BILLING_RECONCILIATION,
        "benchmark_judge_model": settings.BENCHMARK_JUDGE_MODEL,
        "refresh_interval_seconds": 60,
        "in_app_notifications_enabled": True,
        "display_currency": "USD",
        "timezone": "local",
        "dashboard_layout": ["balance", "usage", "prices", "usage_leaderboard"],
    }


async def get_effective_settings(db: AsyncSession, settings: Settings) -> dict[str, Any]:
    result = await db.execute(select(AppSettings).where(AppSettings.id == 1))
    stored = result.scalar_one_or_none()
    values = {}
    if stored:
        try:
            values = json.loads(stored.values)
        except (TypeError, json.JSONDecodeError):
            values = {}
    effective = environment_defaults(settings)
    effective.update({key: values[key] for key in SETTING_KEYS if key in values})
    return effective


async def update_settings(
    db: AsyncSession, settings: Settings, updates: dict[str, Any]
) -> dict[str, Any]:
    result = await db.execute(select(AppSettings).where(AppSettings.id == 1))
    stored = result.scalar_one_or_none()
    values: dict[str, Any] = {}
    if stored:
        try:
            values = json.loads(stored.values)
        except (TypeError, json.JSONDecodeError):
            values = {}
    values.update({key: value for key, value in updates.items() if key in SETTING_KEYS})
    if stored is None:
        stored = AppSettings(id=1, values=json.dumps(values))
        db.add(stored)
    else:
        stored.values = json.dumps(values)
    await db.commit()
    return await get_effective_settings(db, settings)


async def reset_settings(db: AsyncSession, settings: Settings) -> dict[str, Any]:
    result = await db.execute(select(AppSettings).where(AppSettings.id == 1))
    stored = result.scalar_one_or_none()
    if stored:
        await db.delete(stored)
        await db.commit()
    return environment_defaults(settings)