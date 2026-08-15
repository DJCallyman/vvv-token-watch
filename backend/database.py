import asyncio
import logging

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
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
    """Create missing tables and report whether schema setup succeeded."""
    # Import models so they register on Base.metadata before create_all.
    import backend.models.db  # noqa: F401

    logger = logging.getLogger(__name__)
    attempts = max(1, attempts)
    retry_delay = max(0.0, retry_delay)

    for attempt in range(1, attempts + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables ready")
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
