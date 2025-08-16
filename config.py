import os
from dotenv import load_dotenv
from typing import Dict, Any

# Load environment variables from .env file
load_dotenv()

class Config:
    """Centralized configuration class for the application."""
    
    # Venice AI API Configuration
    VENICE_API_KEY = os.getenv('VENICE_API_KEY')
    
    # CoinGecko Configuration
    COINGECKO_TOKEN_ID = os.getenv('COINGECKO_TOKEN_ID', 'venice-token')
    COINGECKO_CURRENCIES = os.getenv('COINGECKO_CURRENCIES', 'usd,aud').split(',')
    COINGECKO_HOLDING_AMOUNT = float(os.getenv('COINGECKO_HOLDING_AMOUNT', '2500'))
    COINGECKO_REFRESH_INTERVAL_MS = int(os.getenv('COINGECKO_REFRESH_INTERVAL_MS', '60000'))
    COINGECKO_INITIAL_DELAY_MS = int(os.getenv('COINGECKO_INITIAL_DELAY_MS', '500'))
    
    # Validation
    @classmethod
    def validate(cls) -> tuple[bool, str]:
        """Validate configuration settings."""
        if not cls.VENICE_API_KEY:
            return False, "VENICE_API_KEY is required but not set in environment variables or .env file"
        return True, "Configuration is valid"
