from __future__ import annotations

import pytest
import pytest_asyncio
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.config import Settings
from backend.database import Base
from backend.models.schemas import AppSettingsUpdate
from backend.services.app_settings import (
    get_effective_settings,
    reset_settings,
    update_settings,
)


@pytest_asyncio.fixture
async def settings_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


def test_settings_reject_invalid_refresh_intervals():
    for interval in (14, 901, 1.5):
        with pytest.raises(ValidationError):
            AppSettingsUpdate(refresh_interval_seconds=interval)


def test_settings_reject_invalid_timezone_and_dashboard_layout():
    with pytest.raises(ValidationError):
        AppSettingsUpdate(timezone="Not/A_Timezone")
    with pytest.raises(ValidationError):
        AppSettingsUpdate(dashboard_layout=["balance", "usage", "prices", "prices"])


@pytest.mark.asyncio
async def test_preferences_persist_and_reset(settings_session):
    settings = Settings(VENICE_ADMIN_KEY="test-admin-key")
    updates = AppSettingsUpdate(
        refresh_interval_seconds=300,
        in_app_notifications_enabled=False,
        display_currency="AUD",
        timezone="Australia/Sydney",
        dashboard_layout=["prices", "balance", "usage", "usage_leaderboard"],
    )

    saved = await update_settings(
        settings_session,
        settings,
        updates.model_dump(exclude_none=True),
    )
    loaded = await get_effective_settings(settings_session, settings)

    assert saved == loaded
    assert loaded["refresh_interval_seconds"] == 300
    assert loaded["in_app_notifications_enabled"] is False
    assert loaded["display_currency"] == "AUD"
    assert loaded["timezone"] == "Australia/Sydney"
    assert loaded["dashboard_layout"] == [
        "prices", "balance", "usage", "usage_leaderboard"
    ]

    reset = await reset_settings(settings_session, settings)
    assert reset["refresh_interval_seconds"] == 60
    assert reset["in_app_notifications_enabled"] is True
    assert reset["display_currency"] == "USD"
    assert reset["timezone"] == "local"
    assert reset["dashboard_layout"] == [
        "balance", "usage", "prices", "usage_leaderboard"
    ]
