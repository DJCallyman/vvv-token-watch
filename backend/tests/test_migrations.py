from __future__ import annotations

import os

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from backend.database import (
    Base,
    _BASELINE_TABLES,
    _run_schema_migrations,
    _validate_existing_schema,
)
from backend.models import db  # noqa: F401


MIGRATION_TEST_DATABASE_URL = os.getenv("MIGRATION_TEST_DATABASE_URL")

PHASE2_TABLES = (
    "notification_channels",
    "notification_deliveries",
    "watchlist_items",
    "wallet_challenges",
    "wallet_sessions",
    "signal_records",
)


# ---------------------------------------------------------------------------
# Baseline validation (runs without PostgreSQL)
# ---------------------------------------------------------------------------


def _create_baseline_sqlite(tmp_path, tables: set[str]) -> str:
    path = tmp_path / "baseline.db"
    url = f"sqlite:///{path}"
    engine = create_engine(url)
    with engine.begin() as connection:
        for name in sorted(tables):
            Base.metadata.tables[name].create(connection)
    engine.dispose()
    return url


def test_validate_existing_schema_accepts_baseline_without_post_baseline_schema(tmp_path):
    url = _create_baseline_sqlite(tmp_path, _BASELINE_TABLES)
    engine = create_engine(url)
    with engine.connect() as connection:
        # Must not raise: newer tables/columns are added by migrations.
        _validate_existing_schema(connection)
    engine.dispose()


def test_validate_existing_schema_rejects_partial_baseline(tmp_path):
    url = _create_baseline_sqlite(tmp_path, {"usage_snapshots", "price_snapshots"})
    engine = create_engine(url)
    with pytest.raises(RuntimeError) as exc:
        with engine.connect() as connection:
            _validate_existing_schema(connection)
    assert "missing tables" in str(exc.value)
    engine.dispose()


def test_validate_existing_schema_rejects_missing_baseline_columns(tmp_path):
    url = _create_baseline_sqlite(tmp_path, _BASELINE_TABLES)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE alert_configs DROP COLUMN threshold"))
    with pytest.raises(RuntimeError) as exc:
        with engine.connect() as connection:
            _validate_existing_schema(connection)
    assert "alert_configs.threshold" in str(exc.value)
    engine.dispose()


# ---------------------------------------------------------------------------
# Full PostgreSQL migration path (gated)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(
    not MIGRATION_TEST_DATABASE_URL,
    reason="Set MIGRATION_TEST_DATABASE_URL to a disposable PostgreSQL database",
)
async def test_migrations_preserve_data_in_existing_postgresql_database():
    assert MIGRATION_TEST_DATABASE_URL is not None
    engine = create_async_engine(MIGRATION_TEST_DATABASE_URL)

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
            await connection.run_sync(_run_schema_migrations)

            await connection.execute(text(
                "INSERT INTO usage_snapshots "
                "(timestamp, scope, diem, usd, bundled_credits, earned_credits) "
                "VALUES (CURRENT_TIMESTAMP, 'daily', 12.5, 3.25, 1.5, 7.75)"
            ))
            # Simulate an older release: no Alembic version, missing 0002
            # and 0003 schema, but with baseline data preserved.
            await connection.execute(text("DROP TABLE alembic_version"))
            await connection.execute(
                text("ALTER TABLE usage_snapshots DROP COLUMN earned_credits")
            )
            await connection.execute(
                text("ALTER TABLE alert_configs DROP COLUMN IF EXISTS window_seconds")
            )
            await connection.execute(
                text("ALTER TABLE alert_configs DROP COLUMN IF EXISTS min_samples")
            )
            for table in PHASE2_TABLES:
                await connection.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))

            await connection.run_sync(_run_schema_migrations)

            table_names = await connection.run_sync(
                lambda sync_connection: set(inspect(sync_connection).get_table_names())
            )
            assert "alembic_version" in table_names
            assert "billing_entries" in table_names
            for table in PHASE2_TABLES:
                assert table in table_names
            schema_differences = await connection.run_sync(
                lambda sync_connection: compare_metadata(
                    MigrationContext.configure(sync_connection),
                    Base.metadata,
                )
            )
            assert schema_differences == []
            assert "earned_credits" in {
                column["name"]
                for column in await connection.run_sync(
                    lambda sync_connection: inspect(sync_connection).get_columns(
                        "usage_snapshots"
                    )
                )
            }
            assert {"window_seconds", "min_samples"} <= {
                column["name"]
                for column in await connection.run_sync(
                    lambda sync_connection: inspect(sync_connection).get_columns(
                        "alert_configs"
                    )
                )
            }
            row = (
                await connection.execute(text(
                    "SELECT diem, usd, bundled_credits, earned_credits "
                    "FROM usage_snapshots"
                ))
            ).one()
            assert tuple(row) == (12.5, 3.25, 1.5, 0.0)
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
        await engine.dispose()
