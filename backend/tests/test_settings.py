from __future__ import annotations

import asyncio
import os

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.api.routes import settings as settings_routes
from backend.config import Settings, get_settings
from backend.database import Base, _run_schema_migrations, get_db
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


# ---------------------------------------------------------------------------
# /api/settings route behavior (SQLite-backed TestClient)
# ---------------------------------------------------------------------------


@pytest.fixture
def settings_api(tmp_path):
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'settings.db'}"

    async def _prepare():
        engine = create_async_engine(db_url)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_prepare())

    app = FastAPI()
    app.include_router(settings_routes.router, prefix="/api")

    async def override_db():
        engine = create_async_engine(db_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            yield session
        await engine.dispose()

    test_settings = Settings(VENICE_ADMIN_KEY="test-admin-key")
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: test_settings

    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_settings_route_reads_defaults(settings_api):
    response = settings_api.get("/api/settings")
    assert response.status_code == 200
    body = response.json()
    assert body["refresh_interval_seconds"] == 60
    assert body["display_currency"] == "USD"
    assert body["dashboard_layout"] == [
        "balance", "usage", "prices", "usage_leaderboard"
    ]


def test_settings_route_rejects_invalid_refresh_interval(settings_api):
    response = settings_api.patch("/api/settings", json={"refresh_interval_seconds": 14})
    assert response.status_code == 422
    assert settings_api.get("/api/settings").json()["refresh_interval_seconds"] == 60


def test_settings_route_persists_and_resets(settings_api):
    update = settings_api.patch(
        "/api/settings",
        json={
            "refresh_interval_seconds": 300,
            "display_currency": "AUD",
            "dashboard_layout": ["prices", "balance", "usage", "usage_leaderboard"],
        },
    )
    assert update.status_code == 200
    assert update.json()["refresh_interval_seconds"] == 300

    reloaded = settings_api.get("/api/settings").json()
    assert reloaded["display_currency"] == "AUD"
    assert reloaded["dashboard_layout"][0] == "prices"

    reset = settings_api.post("/api/settings/reset")
    assert reset.status_code == 200
    assert reset.json()["display_currency"] == "USD"
    assert reset.json()["refresh_interval_seconds"] == 60


# ---------------------------------------------------------------------------
# PostgreSQL-backed persistence (gated on a disposable database)
# ---------------------------------------------------------------------------


POSTGRES_SETTINGS_URL = os.getenv("SETTINGS_TEST_DATABASE_URL") or os.getenv(
    "MIGRATION_TEST_DATABASE_URL"
)


@pytest.mark.asyncio
@pytest.mark.skipif(
    not POSTGRES_SETTINGS_URL,
    reason="Set SETTINGS_TEST_DATABASE_URL to a disposable PostgreSQL database",
)
async def test_settings_persist_across_postgresql_sessions():
    assert POSTGRES_SETTINGS_URL is not None
    engine = create_async_engine(POSTGRES_SETTINGS_URL)
    settings = Settings(VENICE_ADMIN_KEY="test-admin-key")

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
            await connection.run_sync(_run_schema_migrations)

        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            saved = await update_settings(
                session,
                settings,
                {"refresh_interval_seconds": 900, "display_currency": "AUD"},
            )
            assert saved["refresh_interval_seconds"] == 900

        await engine.dispose()
        engine = create_async_engine(POSTGRES_SETTINGS_URL)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            loaded = await get_effective_settings(session, settings)
            assert loaded["refresh_interval_seconds"] == 900
            assert loaded["display_currency"] == "AUD"
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
        await engine.dispose()
