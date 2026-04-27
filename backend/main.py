import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import get_settings
from backend.database import init_db
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


app = FastAPI(
    title="VVV Token Watch API",
    description="API for monitoring Venice AI usage, balances, and token prices",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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