from __future__ import annotations

import os

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from backend.database import Base, _run_schema_migrations
from backend.models import db  # noqa: F401


MIGRATION_TEST_DATABASE_URL = os.getenv("MIGRATION_TEST_DATABASE_URL")


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
            await connection.execute(text("DROP TABLE alembic_version"))
            await connection.execute(
                text("ALTER TABLE usage_snapshots DROP COLUMN earned_credits")
            )

            await connection.run_sync(_run_schema_migrations)

            table_names = await connection.run_sync(
                lambda sync_connection: set(inspect(sync_connection).get_table_names())
            )
            assert "alembic_version" in table_names
            assert "billing_entries" in table_names
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
