import os
from dotenv import load_dotenv
from typing import Dict, Any

# Load environment variables from .env file
load_dotenv()

class Config:
    """Centralized configuration class for the application."""
    
    # Venice AI API Configuration
    VENICE_API_KEY = os.getenv('VENICE_API_KEY')
    VENICE_ADMIN_KEY = os.getenv('VENICE_ADMIN_KEY')  # Must be explicitly set to a Venice Admin API key
    
    # API Pagination Settings
    API_PAGE_SIZE = int(os.getenv('API_PAGE_SIZE', '500'))
    API_MAX_PAGES = int(os.getenv('API_MAX_PAGES', '20'))
    
    # Default Limits (conservative daily spending limits)
    DEFAULT_DAILY_DIEM_LIMIT = float(os.getenv('DEFAULT_DAILY_DIEM_LIMIT', '100.0'))
    DEFAULT_DAILY_USD_LIMIT = float(os.getenv('DEFAULT_DAILY_USD_LIMIT', '25.0'))
    
    # Fallback Exchange Rate (DIEM to USD) when APIs are unavailable
    DEFAULT_EXCHANGE_RATE = float(os.getenv('DEFAULT_EXCHANGE_RATE', '0.72'))
    
    # IMPORTANT: For billing/usage endpoints, you MUST use a Venice Admin API key
    # Regular API keys will return 401 Unauthorized for /billing/usage endpoint
    
    # CoinGecko Configuration - Venice Token
    COINGECKO_TOKEN_ID = os.getenv('COINGECKO_TOKEN_ID', 'venice-token')
    COINGECKO_CURRENCIES = os.getenv('COINGECKO_CURRENCIES', 'usd,aud').split(',')
    COINGECKO_HOLDING_AMOUNT = float(os.getenv('COINGECKO_HOLDING_AMOUNT', '2750'))
    COINGECKO_REFRESH_INTERVAL_MS = int(os.getenv('COINGECKO_REFRESH_INTERVAL_MS', '60000'))
    COINGECKO_INITIAL_DELAY_MS = int(os.getenv('COINGECKO_INITIAL_DELAY_MS', '500'))
    
    # CoinGecko Configuration - DIEM Token
    DIEM_TOKEN_ID = os.getenv('DIEM_TOKEN_ID', 'diem')
    DIEM_HOLDING_AMOUNT = float(os.getenv('DIEM_HOLDING_AMOUNT', '0'))
    
    THEME_MODE = os.getenv('THEME_MODE', 'dark')
    
    # Usage tracking configuration
    USAGE_REFRESH_INTERVAL_MS = int(os.getenv('USAGE_REFRESH_INTERVAL_MS', '30000'))  # Default to 30 seconds
    
    # Validation
    @classmethod
    def validate(cls) -> tuple[bool, str]:
        """Validate configuration settings.
        
        Note: VENICE_ADMIN_KEY is required for the monitoring application.
        VENICE_API_KEY is optional and reserved for future inference features.
        """
        if not cls.VENICE_ADMIN_KEY:
            return False, "VENICE_ADMIN_KEY is required - must be a Venice Admin API key from https://venice.ai/settings/api (regular inference keys won't work for billing endpoints)"
        return True, "Configuration is valid"
        
    @classmethod
    def validate_usage_tracking(cls) -> tuple[bool, str]:
        """Validate configuration settings for usage tracking."""
        if not cls.VENICE_ADMIN_KEY:
            return False, "VENICE_ADMIN_KEY is required for usage tracking - must be a Venice Admin API key (regular API keys won't work for billing endpoints)"
        return True, "Usage tracking configuration is valid"
        
    @classmethod
    def get_all_settings(cls) -> Dict[str, Any]:
        """Get all configuration settings for debugging purposes.
        
        Note: API keys are masked for security - only first 8 characters shown.
        """
        def mask_key(key: str) -> str:
            """Mask API key showing only first 8 characters."""
            if not key:
                return None
            return f"{key[:8]}..." if len(key) > 8 else "***"
        
        return {
            'VENICE_API_KEY': mask_key(cls.VENICE_API_KEY),
            'VENICE_ADMIN_KEY': mask_key(cls.VENICE_ADMIN_KEY),
            'COINGECKO_TOKEN_ID': cls.COINGECKO_TOKEN_ID,
            'COINGECKO_CURRENCIES': cls.COINGECKO_CURRENCIES,
            'COINGECKO_HOLDING_AMOUNT': cls.COINGECKO_HOLDING_AMOUNT,
            'COINGECKO_REFRESH_INTERVAL_MS': cls.COINGECKO_REFRESH_INTERVAL_MS,
            'COINGECKO_INITIAL_DELAY_MS': cls.COINGECKO_INITIAL_DELAY_MS,
            'DIEM_TOKEN_ID': cls.DIEM_TOKEN_ID,
            'DIEM_HOLDING_AMOUNT': cls.DIEM_HOLDING_AMOUNT,
            'THEME_MODE': cls.THEME_MODE,
            'USAGE_REFRESH_INTERVAL_MS': cls.USAGE_REFRESH_INTERVAL_MS
        }
