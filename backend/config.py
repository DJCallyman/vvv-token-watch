import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    VENICE_ADMIN_KEY: str
    VENICE_API_KEY: Optional[str] = None
    DATABASE_URL: str
    
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
    
    LOG_LEVEL: str = "INFO"
    LOG_FILE_PATH: str = "/data/logs/app.log"
    DATA_DIR: str = "/data"
    BENCHMARK_RESULTS_DIR: str = "scripts/results"
    
    CACHE_TTL_SECONDS: int = 300
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )
    
    @property
    def coingecko_currencies_list(self) -> list[str]:
        return [c.strip() for c in self.COINGECKO_CURRENCIES.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()