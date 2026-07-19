import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    VENICE_ADMIN_KEY: str
    VENICE_API_KEY: Optional[str] = None
    # Matches docker-compose.dev.yml (host port 5433, user/db/password: vvvwatch).
    DATABASE_URL: Optional[str] = "postgresql+asyncpg://vvvwatch:vvvwatch@localhost:5433/vvvwatch"
    
    COINGECKO_API_KEY: Optional[str] = None
    COINGECKO_TOKEN_ID: str = "venice-token"
    COINGECKO_CURRENCIES: str = "usd,aud"
    COINGECKO_HOLDING_AMOUNT: float = 2750.0
    DIEM_TOKEN_ID: str = "diem"
    DIEM_HOLDING_AMOUNT: float = 0.0
    
    API_PAGE_SIZE: int = 500
    API_MAX_PAGES: int = 20
    
    DEFAULT_DAILY_DIEM_LIMIT: float = 100.0
    DEFAULT_DAILY_USD_LIMIT: float = 25.0
    
    VENICE_API_BASE_URL: str = "https://api.venice.ai/api/v1"
    COINGECKO_API_BASE_URL: str = "https://api.coingecko.com/api/v3"
    
    LOG_LEVEL: str = "INFO"
    LOG_FILE_PATH: str = "./data/logs/app.log"
    DATA_DIR: str = "./data"
    BENCHMARK_RESULTS_DIR: str = "./data/benchmark_results"
    SQL_ECHO: bool = False
    
    CACHE_TTL_SECONDS: int = 300

    # Server-side cost ceiling for a single benchmark run. /benchmark/start
    # rejects requests whose pre-run estimate exceeds this (USD).
    BENCHMARK_MAX_COST_USD: float = 5.0
    # Billing reconciliation needs the admin key (billing scope); disabled by
    # default so benchmark runs only need an inference-scoped key.
    BENCHMARK_ENABLE_BILLING_RECONCILIATION: bool = False

    # When false (default), interactive API docs (/docs, /redoc, /openapi.json)
    # are disabled. Set true only for local development.
    DEBUG: bool = False

    # Shared app password for personal/self-hosted auth. Required unless
    # ALLOW_INSECURE_NO_AUTH is explicitly set to true.
    APP_PASSWORD: Optional[str] = None
    # Explicit opt-in to run without authentication (NOT recommended).
    ALLOW_INSECURE_NO_AUTH: bool = False
    # Comma-separated CORS origins. Defaults to the local Next.js dev/prod origin.
    CORS_ORIGINS: str = "http://localhost:3000"

    # Comma-separated list of trusted proxy IPs (for X-Forwarded-For handling in rate limiting).
    # When a request comes from one of these IPs, the first value in X-Forwarded-For is used
    # as the client IP for rate limiting. Never trust XFF from untrusted peers.
    TRUSTED_PROXY_IPS: str = "127.0.0.1"

    # Cooldown window (seconds) for alert events: do not create a new unacknowledged
    # event for the same alert_config_id if one exists within this window.
    # Prevents flooding the alert_events table on every poll while a threshold is breached.
    ALERT_COOLDOWN_SECONDS: int = 3600  # 1 hour default

    # Snapshot interval for usage and price history (seconds). Background poller
    # (if enabled) and/or request-path snapshots use this cadence.
    SNAPSHOT_INTERVAL_SECONDS: int = 300  # 5 minutes

    # Retention for snapshot tables (days). Rows older than this are purged on
    # each snapshot write and at startup.
    SNAPSHOT_RETENTION_DAYS: int = 90
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )
    
    @property
    def coingecko_currencies_list(self) -> list[str]:
        return [c.strip() for c in self.COINGECKO_CURRENCIES.split(",")]

    @property
    def cors_origins_list(self) -> list[str]:
        raw = [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        return raw or ["*"]

    @property
    def trusted_proxy_ips_list(self) -> list[str]:
        """List of IPs that are trusted to forward X-Forwarded-For headers for rate limiting."""
        raw = [ip.strip() for ip in self.TRUSTED_PROXY_IPS.split(",") if ip.strip()]
        return raw or ["127.0.0.1"]


@lru_cache()
def get_settings() -> Settings:
    return Settings()