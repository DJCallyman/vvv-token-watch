import logging
import os
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from backend.config import get_settings
from backend.database import init_db, engine
from backend.limiter import limiter
from backend.api.routes import usage, balance, prices, models, health, analytics, benchmark, onchain, alerts, api_keys, characters, news, insights, assistant, settings as settings_routes
from backend.api.deps import verify_auth

settings = get_settings()

# SEC-01: fail closed if no auth password is configured, unless the operator
# explicitly opts in to running without authentication.
if not settings.APP_PASSWORD and not settings.ALLOW_INSECURE_NO_AUTH:
    raise RuntimeError(
        "APP_PASSWORD is not set. Refusing to start without authentication. "
        "Set APP_PASSWORD to a strong secret (e.g. `openssl rand -hex 24`), "
        "or set ALLOW_INSECURE_NO_AUTH=true to explicitly run without auth "
        "(NOT recommended for anything but a fully isolated, trusted network)."
    )
if not settings.APP_PASSWORD and settings.ALLOW_INSECURE_NO_AUTH:
    logging.getLogger(__name__).warning(
        "SECURITY WARNING: running with ALLOW_INSECURE_NO_AUTH=true and no "
        "APP_PASSWORD. All API endpoints are unauthenticated."
    )

# Ensure log directory exists. dirname("") returns ""; makedirs("") raises,
# so coerce to a safe value when the operator gives a bare file name.
os.makedirs(os.path.dirname(settings.LOG_FILE_PATH) or ".", exist_ok=True)

log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
log_formatter = logging.Formatter(log_format)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

# File handler (persistent across restarts)
file_handler = logging.FileHandler(settings.LOG_FILE_PATH)
file_handler.setFormatter(log_formatter)

# Uvicorn configures logging before importing the application, so
# logging.basicConfig() may be a no-op. Configure the root and Uvicorn
# loggers explicitly to ensure application and access logs reach the file.
root_logger = logging.getLogger()
root_logger.setLevel(log_level)
file_path = os.path.abspath(settings.LOG_FILE_PATH)

if not any(
    isinstance(handler, logging.FileHandler)
    and os.path.abspath(handler.baseFilename) == file_path
    for handler in root_logger.handlers
):
    root_logger.addHandler(file_handler)

if not any(
    isinstance(handler, logging.StreamHandler)
    and not isinstance(handler, logging.FileHandler)
    for handler in root_logger.handlers
):
    root_logger.addHandler(console_handler)

logging.basicConfig(
    level=log_level,
    handlers=[console_handler, file_handler]
)
logger = logging.getLogger(__name__)

# Apply LOG_LEVEL to uvicorn loggers for consistent verbosity
for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
    uvicorn_logger = logging.getLogger(logger_name)
    uvicorn_logger.setLevel(log_level)
    uvicorn_logger.propagate = False
    if not any(
        isinstance(handler, logging.FileHandler)
        and os.path.abspath(handler.baseFilename) == file_path
        for handler in uvicorn_logger.handlers
    ):
        uvicorn_logger.addHandler(file_handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting VVV Token Watch API...")
    if not await init_db():
        raise RuntimeError(
            "Database schema initialization failed. Verify DATABASE_URL and grant "
            "the configured PostgreSQL role USAGE and CREATE on schema public."
        )
    logger.info("Database initialized")

    # Build the model cache lazily, once per process, so /api/models does
    # not read or parse the JSON file on every request.
    from backend.core.model_cache import ModelCacheManager
    cache = ModelCacheManager()
    await cache.initialize()
    app.state.model_cache = cache
    logger.info("Model cache initialized")

    yield

    logger.info("Shutting down VVV Token Watch API...")
    try:
        await engine.dispose()
        logger.info("Database engine disposed")
    except Exception as e:
        logger.error(f"Error disposing database engine: {e}")
    try:
        from backend.api.routes.benchmark import terminate_all_jobs
        await terminate_all_jobs()
    except Exception as e:
        logger.error(f"Error terminating benchmark jobs: {e}")


app = FastAPI(
    title="VVV Token Watch API",
    description="API for monitoring Venice AI usage, balances, and token prices",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_cors_origins = settings.cors_origins_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception in request %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(usage.router, prefix="/api/usage", tags=["usage"], dependencies=[Depends(verify_auth)])
app.include_router(balance.router, prefix="/api", tags=["balance"], dependencies=[Depends(verify_auth)])
app.include_router(prices.router, prefix="/api", tags=["prices"], dependencies=[Depends(verify_auth)])
app.include_router(models.router, prefix="/api", tags=["models"], dependencies=[Depends(verify_auth)])
app.include_router(api_keys.router, prefix="/api", tags=["api-keys"], dependencies=[Depends(verify_auth)])
app.include_router(characters.router, prefix="/api", tags=["characters"], dependencies=[Depends(verify_auth)])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"], dependencies=[Depends(verify_auth)])
app.include_router(benchmark.router, prefix="/api", tags=["benchmark"], dependencies=[Depends(verify_auth)])
app.include_router(onchain.router, prefix="/api", tags=["onchain"], dependencies=[Depends(verify_auth)])
app.include_router(alerts.router, prefix="/api", tags=["alerts"], dependencies=[Depends(verify_auth)])
app.include_router(news.router, prefix="/api", tags=["news"], dependencies=[Depends(verify_auth)])
app.include_router(insights.router, prefix="/api", tags=["insights"], dependencies=[Depends(verify_auth)])
app.include_router(assistant.router, prefix="/api", tags=["assistant"], dependencies=[Depends(verify_auth)])
app.include_router(settings_routes.router, prefix="/api", tags=["settings"], dependencies=[Depends(verify_auth)])


@app.get("/")
async def root():
    return {
        "name": "VVV Token Watch API",
        "version": "1.0.0",
        "docs": "/docs" if settings.DEBUG else None
    }
