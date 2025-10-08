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
    
    # IMPORTANT: For billing/usage endpoints, you MUST use a Venice Admin API key
    # Regular API keys will return 401 Unauthorized for /billing/usage endpoint
    
    # CoinGecko Configuration
    COINGECKO_TOKEN_ID = os.getenv('COINGECKO_TOKEN_ID', 'venice-token')
    COINGECKO_CURRENCIES = os.getenv('COINGECKO_CURRENCIES', 'usd,aud').split(',')
    COINGECKO_HOLDING_AMOUNT = float(os.getenv('COINGECKO_HOLDING_AMOUNT', '2750'))
    COINGECKO_REFRESH_INTERVAL_MS = int(os.getenv('COINGECKO_REFRESH_INTERVAL_MS', '60000'))
    COINGECKO_INITIAL_DELAY_MS = int(os.getenv('COINGECKO_INITIAL_DELAY_MS', '500'))
    THEME_MODE = os.getenv('THEME_MODE', 'dark')
    
    # Usage tracking configuration
    USAGE_REFRESH_INTERVAL_MS = int(os.getenv('USAGE_REFRESH_INTERVAL_MS', '30000'))  # Default to 30 seconds
    
    # Validation
    @classmethod
    def validate(cls) -> tuple[bool, str]:
        """Validate configuration settings."""
        if not cls.VENICE_API_KEY:
            return False, "VENICE_API_KEY is required but not set in environment variables or .env file"
        return True, "Configuration is valid"
        
    @classmethod
    def validate_usage_tracking(cls) -> tuple[bool, str]:
        """Validate configuration settings for usage tracking."""
        if not cls.VENICE_ADMIN_KEY:
            return False, "VENICE_ADMIN_KEY is required for usage tracking - must be a Venice Admin API key (regular API keys won't work for billing endpoints)"
        return True, "Usage tracking configuration is valid"
        
    @classmethod
    def get_all_settings(cls) -> Dict[str, Any]:
        """Get all configuration settings for debugging purposes."""
        return {
            'VENICE_API_KEY': cls.VENICE_API_KEY,
            'VENICE_ADMIN_KEY': cls.VENICE_ADMIN_KEY,
            'COINGECKO_TOKEN_ID': cls.COINGECKO_TOKEN_ID,
            'COINGECKO_CURRENCIES': cls.COINGECKO_CURRENCIES,
            'COINGECKO_HOLDING_AMOUNT': cls.COINGECKO_HOLDING_AMOUNT,
            'COINGECKO_REFRESH_INTERVAL_MS': cls.COINGECKO_REFRESH_INTERVAL_MS,
            'COINGECKO_INITIAL_DELAY_MS': cls.COINGECKO_INITIAL_DELAY_MS,
            'THEME_MODE': cls.THEME_MODE,
            'USAGE_REFRESH_INTERVAL_MS': cls.USAGE_REFRESH_INTERVAL_MS
        }
