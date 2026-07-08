import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from backend.config import get_settings
from backend.database import init_db, engine
from backend.api.routes import usage, balance, prices, models, health, analytics, benchmark

settings = get_settings()

# Ensure log directory exists
os.makedirs(os.path.dirname(settings.LOG_FILE_PATH), exist_ok=True)

log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(log_format))

# File handler (persistent across restarts)
file_handler = logging.FileHandler(settings.LOG_FILE_PATH)
file_handler.setFormatter(logging.Formatter(log_format))

logging.basicConfig(
    level=log_level,
    handlers=[console_handler, file_handler]
)
logger = logging.getLogger(__name__)

# Apply LOG_LEVEL to uvicorn loggers for consistent verbosity
logging.getLogger("uvicorn").setLevel(log_level)
logging.getLogger("uvicorn.access").setLevel(log_level)
logging.getLogger("uvicorn.error").setLevel(log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting VVV Token Watch API...")
    await init_db()
    logger.info("Database initialized")
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


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="VVV Token Watch API",
    description="API for monitoring Venice AI usage, balances, and token prices",
    version="1.0.0",
    lifespan=lifespan
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
app.include_router(usage.router, prefix="/api/usage", tags=["usage"])
app.include_router(balance.router, prefix="/api", tags=["balance"])
app.include_router(prices.router, prefix="/api", tags=["prices"])
app.include_router(models.router, prefix="/api", tags=["models"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(benchmark.router, prefix="/api", tags=["benchmark"])


@app.get("/")
async def root():
    return {
        "name": "VVV Token Watch API",
        "version": "1.0.0",
        "docs": "/docs"
    }