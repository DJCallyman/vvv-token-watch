import asyncio
import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import inspect
from backend.config import get_settings


DATABASE_INIT_ATTEMPTS = 5
DATABASE_INIT_RETRY_DELAY_SECONDS = 2.0

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.SQL_ECHO,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()


# Tables created by baseline revision 0001_initial. Later migrations add more
# tables/columns; an existing pre-Alembic database only needs the baseline
# shape to be safely stamped at 0001 and then upgraded.
_BASELINE_TABLES = {
    "usage_snapshots",
    "price_snapshots",
    "alert_configs",
    "alert_events",
    "billing_entries",
    "app_settings",
}

# Columns added by post-baseline migrations. They may be absent from an
# existing pre-Alembic database; the migrations add them.
_POST_BASELINE_COLUMNS = {
    "usage_snapshots": {"earned_credits"},        # 0002_earned_credits
    "alert_configs": {"window_seconds", "min_samples"},  # 0003_phase2_monitoring
}


def _validate_existing_schema(connection) -> None:
    """Reject unsafe Alembic baselines for partially initialized databases.

    Only the baseline (0001) shape is required. Tables and columns introduced
    by later migrations are allowed to be missing; ``upgrade`` adds them.
    """
    inspector = inspect(connection)
    existing_tables = set(inspector.get_table_names())
    baseline_present = existing_tables & _BASELINE_TABLES

    if not baseline_present:
        # Nothing recognizable: treat as a fresh database instead of refusing.
        return

    missing_tables = _BASELINE_TABLES - existing_tables
    missing_columns = []
    for table_name, table in Base.metadata.tables.items():
        if table_name not in _BASELINE_TABLES or table_name not in existing_tables:
            continue
        existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
        allowed_missing = _POST_BASELINE_COLUMNS.get(table_name, set())
        for column in table.columns:
            if column.name in allowed_missing:
                continue
            if column.name not in existing_columns:
                missing_columns.append(f"{table_name}.{column.name}")

    if missing_tables or missing_columns:
        details = []
        if missing_tables:
            details.append(f"missing tables: {', '.join(sorted(missing_tables))}")
        if missing_columns:
            details.append(f"missing columns: {', '.join(sorted(missing_columns))}")
        raise RuntimeError(
            "Cannot safely baseline the existing database (" + "; ".join(details) +
            "). Back up the database and reconcile its schema before restarting."
        )


def _run_schema_migrations(connection) -> None:
    from alembic import command
    from alembic.config import Config

    from backend.models import db  # noqa: F401

    config = Config(str(Path(__file__).with_name("alembic.ini")))
    config.attributes["connection"] = connection

    if not inspect(connection).has_table("alembic_version"):
        existing_tables = set(inspect(connection).get_table_names())
        if existing_tables.intersection(Base.metadata.tables):
            _validate_existing_schema(connection)
            command.stamp(config, "0001_initial")

    command.upgrade(config, "head")


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db(
    *,
    attempts: int = DATABASE_INIT_ATTEMPTS,
    retry_delay: float = DATABASE_INIT_RETRY_DELAY_SECONDS,
) -> bool:
    """Apply schema migrations and report whether setup succeeded."""
    import backend.models.db  # noqa: F401

    logger = logging.getLogger(__name__)
    attempts = max(1, attempts)
    retry_delay = max(0.0, retry_delay)

    for attempt in range(1, attempts + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(_run_schema_migrations)
            logger.info("Database migrations applied")
            return True
        except Exception as exc:
            if attempt == attempts:
                if "permission denied for schema" in str(exc):
                    logger.error(
                        "The DATABASE_URL role cannot create tables in schema public. "
                        "Grant it USAGE and CREATE on schema public as a PostgreSQL administrator."
                    )
                logger.exception("Failed to initialize database schema")
                return False
            logger.warning(
                "Database initialization attempt %s/%s failed; retrying in %.1fs: %s",
                attempt,
                attempts,
                retry_delay,
                exc,
            )
            await asyncio.sleep(retry_delay)

    return False
