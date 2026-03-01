import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import get_settings
from backend.database import init_db
from backend.api.routes import usage, balance, prices, models, health

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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


@app.get("/")
async def root():
    return {
        "name": "VVV Token Watch API",
        "version": "1.0.0",
        "docs": "/docs"
    }