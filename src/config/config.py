import os
from dotenv import load_dotenv
from typing import Dict, Any

# Load environment variables from .env file
load_dotenv()

class Config:
    """Centralized configuration class for the application."""
    
    # Venice AI API Configuration
    VENICE_API_KEY = os.getenv('VENICE_API_KEY')
    VENICE_ADMIN_KEY = os.getenv('VENICE_ADMIN_KEY')
    VENICE_API_BASE_URL = os.getenv('VENICE_API_BASE_URL', 'https://api.venice.ai/api/v1')
    VENICE_EXCHANGE_RATE_URL = f"{VENICE_API_BASE_URL}/exchange/rate"
    
    # API Pagination Settings
    API_PAGE_SIZE = int(os.getenv('API_PAGE_SIZE', '500'))
    API_MAX_PAGES = int(os.getenv('API_MAX_PAGES', '20'))
    
    # Default Limits
    DEFAULT_DAILY_DIEM_LIMIT = float(os.getenv('DEFAULT_DAILY_DIEM_LIMIT', '100.0'))
    DEFAULT_DAILY_USD_LIMIT = float(os.getenv('DEFAULT_DAILY_USD_LIMIT', '25.0'))
    DEFAULT_EXCHANGE_RATE = float(os.getenv('DEFAULT_EXCHANGE_RATE', '0.72'))
    
    # CoinGecko Configuration - Venice Token
    COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY')
    COINGECKO_TOKEN_ID = os.getenv('COINGECKO_TOKEN_ID', 'venice-token')
    COINGECKO_CURRENCIES = os.getenv('COINGECKO_CURRENCIES', 'usd,aud').split(',')
    COINGECKO_HOLDING_AMOUNT = float(os.getenv('COINGECKO_HOLDING_AMOUNT', '2750'))
    COINGECKO_REFRESH_INTERVAL_MS = int(os.getenv('COINGECKO_REFRESH_INTERVAL_MS', '60000'))
    COINGECKO_INITIAL_DELAY_MS = int(os.getenv('COINGECKO_INITIAL_DELAY_MS', '500'))
    COINGECKO_API_BASE_URL = os.getenv('COINGECKO_API_BASE_URL', 'https://api.coingecko.com/api/v3')
    COINGECKO_PRICE_URL = f"{COINGECKO_API_BASE_URL}/simple/price"
    
    # CoinGecko Configuration - DIEM Token
    DIEM_TOKEN_ID = os.getenv('DIEM_TOKEN_ID', 'diem')
    DIEM_HOLDING_AMOUNT = float(os.getenv('DIEM_HOLDING_AMOUNT', '0'))
    
    THEME_MODE = os.getenv('THEME_MODE', 'dark')
    USAGE_REFRESH_INTERVAL_MS = int(os.getenv('USAGE_REFRESH_INTERVAL_MS', '30000'))
    
    # Cache Configuration
    CACHE_TTL_SECONDS = int(os.getenv('CACHE_TTL_SECONDS', '300'))
    INCREMENTAL_THRESHOLD_SECONDS = int(os.getenv('INCREMENTAL_THRESHOLD_SECONDS', '3600'))
    CACHE_MAX_PAGES = int(os.getenv('CACHE_MAX_PAGES', str(API_MAX_PAGES)))
    CACHE_PAGE_SIZE = int(os.getenv('CACHE_PAGE_SIZE', str(API_PAGE_SIZE)))
    
    # UI Configuration
    DEFAULT_WINDOW_WIDTH = int(os.getenv('DEFAULT_WINDOW_WIDTH', '1280'))
    DEFAULT_WINDOW_HEIGHT = int(os.getenv('DEFAULT_WINDOW_HEIGHT', '920'))
    MIN_WINDOW_WIDTH = int(os.getenv('MIN_WINDOW_WIDTH', '1200'))
    MIN_WINDOW_HEIGHT = int(os.getenv('MIN_WINDOW_HEIGHT', '850'))
    UPDATE_STAGGER_DELAY_MS = int(os.getenv('UPDATE_STAGGER_DELAY_MS', '1000'))
    
    # Video/Audio Configuration
    DEFAULT_VIDEO_DURATION_SECONDS = float(os.getenv('DEFAULT_VIDEO_DURATION_SECONDS', '5.0'))
    DEFAULT_DURATION_VALUE = float(os.getenv('DEFAULT_DURATION_VALUE', '5.0'))
    INVALID_DURATION_SCORE = int(os.getenv('INVALID_DURATION_SCORE', '999'))
    DEFAULT_DURATION = os.getenv('DEFAULT_DURATION', '5s')
    
    # Validation Thresholds
    MIN_HOLDING_THRESHOLD = float(os.getenv('MIN_HOLDING_THRESHOLD', '0.01'))
    SECONDS_PER_DAY = 86400
    
    # Request Configuration
    DEFAULT_REQUEST_TIMEOUT_SECONDS = int(os.getenv('DEFAULT_REQUEST_TIMEOUT_SECONDS', '30'))
    
    # Debug Configuration
    DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() in ('true', '1', 'yes')
    
    # Validation
    @classmethod
    def validate(cls) -> tuple[bool, str]:
        if not cls.VENICE_ADMIN_KEY:
            return False, "VENICE_ADMIN_KEY is required"
        return True, "Configuration is valid"
    
    @classmethod
    def validate_usage_tracking(cls) -> tuple[bool, str]:
        if not cls.VENICE_ADMIN_KEY:
            return False, "VENICE_ADMIN_KEY is required for usage tracking"
        return True, "Usage tracking configuration is valid"
    
    @classmethod
    def get_all_settings(cls) -> Dict[str, Any]:
        def mask_key(key: str) -> str:
            if not key:
                return None
            return f"{key[:8]}..." if len(key) > 8 else "***"
        
        return {
            'VENICE_API_KEY': mask_key(cls.VENICE_API_KEY),
            'VENICE_ADMIN_KEY': mask_key(cls.VENICE_ADMIN_KEY),
            'COINGECKO_API_KEY': mask_key(cls.COINGECKO_API_KEY),
            'COINGECKO_TOKEN_ID': cls.COINGECKO_TOKEN_ID,
            'COINGECKO_CURRENCIES': cls.COINGECKO_CURRENCIES,
            'COINGECKO_HOLDING_AMOUNT': cls.COINGECKO_HOLDING_AMOUNT,
            'COINGECKO_REFRESH_INTERVAL_MS': cls.COINGECKO_REFRESH_INTERVAL_MS,
            'COINGECKO_INITIAL_DELAY_MS': cls.COINGECKO_INITIAL_DELAY_MS,
            'DIEM_TOKEN_ID': cls.DIEM_TOKEN_ID,
            'DIEM_HOLDING_AMOUNT': cls.DIEM_HOLDING_AMOUNT,
            'THEME_MODE': cls.THEME_MODE,
            'USAGE_REFRESH_INTERVAL_MS': cls.USAGE_REFRESH_INTERVAL_MS,
            'VENICE_API_BASE_URL': cls.VENICE_API_BASE_URL,
            'VENICE_EXCHANGE_RATE_URL': cls.VENICE_EXCHANGE_RATE_URL,
            'COINGECKO_PRICE_URL': cls.COINGECKO_PRICE_URL,
            'DEBUG_MODE': cls.DEBUG_MODE
        }
