from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from backend.config import get_settings

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


async def init_db():
    """Create tables if they do not exist.

    Best-effort: logs and continues if the database is unreachable so the
    rest of the API (Venice/CoinGecko proxies) can still serve traffic.
    """
    import logging

    # Import models so they register on Base.metadata before create_all.
    import backend.models.db  # noqa: F401

    logger = logging.getLogger(__name__)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables ready")
    except Exception:
        logger.exception(
            "Failed to initialize database (history/alerts features will be unavailable)"
        )
