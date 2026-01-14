"""
Price Worker for fetching cryptocurrency prices in a background thread.

This module provides a QThread worker for fetching CoinGecko price data
without blocking the main UI thread.
"""

from typing import List, Optional
import requests
import logging
import time
from PySide6.QtCore import QThread, Signal

from src.config.config import Config

logger = logging.getLogger(__name__)


class PriceWorker(QThread):
    """
    Worker thread for fetching cryptocurrency prices from CoinGecko.
    Prevents UI freezing during price lookups.
    """
    
    # Signals
    price_updated = Signal(dict)  # Emits {currency: price} dict
    error_occurred = Signal(str)
    
    def __init__(self, token_id: str, currencies: List[str], parent=None):
        """
        Initialize the price worker.
        
        Args:
            token_id: CoinGecko token ID (e.g., 'venice-token')
            currencies: List of currency codes (e.g., ['usd', 'aud'])
            parent: Parent QObject
        """
        super().__init__(parent)
        self.token_id = token_id
        self.currencies = currencies
        self.max_retries = 3
        self.api_key: Optional[str] = Config.COINGECKO_API_KEY
        
        # Log which API tier is being used
        if self.api_key:
            if self.api_key.startswith("CG-"):
                logger.info(f"CoinGecko Demo API key configured for {token_id} - higher rate limits available")
            else:
                logger.info(f"CoinGecko Pro API key configured for {token_id} - highest rate limits available")
        else:
            logger.info(f"CoinGecko free tier for {token_id} - limited to ~30 calls/minute")
    
    def run(self):
        """Fetch prices from CoinGecko with retry logic."""
        url = "https://api.coingecko.com/api/v3/simple/price"
        vs_currencies_str = ','.join(self.currencies)
        params = {
            'ids': self.token_id,
            'vs_currencies': vs_currencies_str
        }
        
        # Add API key to headers if available
        headers = {}
        use_pro_api = False
        use_demo_api = False
        
        if self.api_key:
            # Demo API keys (start with "CG-") use the regular API endpoint
            # Pro API keys use the Pro endpoint
            if self.api_key.startswith("CG-"):
                # Demo API key - use regular endpoint with API key
                headers['x-cg-demo-api-key'] = self.api_key
                use_demo_api = True
                logger.debug(f"Using CoinGecko Demo API key for {self.token_id}")
            else:
                # Pro API key - use Pro endpoint
                headers['x-cg-pro-api-key'] = self.api_key
                use_pro_api = True
                logger.debug(f"Using CoinGecko Pro API key for {self.token_id}")
        else:
            logger.debug(f"No CoinGecko API key, using free tier for {self.token_id}")
        
        # Use Pro API endpoint only for Pro API keys
        if use_pro_api:
            url = "https://pro-api.coingecko.com/api/v3/simple/price"
        
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, params=params, headers=headers, timeout=30)
                
                # Log response details for debugging
                if use_pro_api or use_demo_api:
                    logger.debug(f"API response status: {response.status_code}")
                    if response.status_code != 200:
                        logger.error(f"API error response: {response.text}")
                        # If Pro API fails with 400 or 401, fall back to free API
                        if use_pro_api and response.status_code in [400, 401] and attempt == 0:
                            logger.warning(f"Pro API failed with {response.status_code}, falling back to free API")
                            use_pro_api = False
                            use_demo_api = False
                            url = "https://api.coingecko.com/api/v3/simple/price"
                            headers = {}  # Remove API key header
                            continue  # Retry with free API
                
                response.raise_for_status()
                data = response.json()
                
                if self.token_id in data:
                    price_data = {}
                    for currency in self.currencies:
                        if currency in data[self.token_id]:
                            price_data[currency] = data[self.token_id][currency]
                    
                    if price_data:
                        self.price_updated.emit(price_data)
                        return
                    else:
                        self.error_occurred.emit(f"No price data found for currencies: {self.currencies}")
                        return
                else:
                    self.error_occurred.emit(f"Token '{self.token_id}' not found in CoinGecko response")
                    return
                    
            except requests.exceptions.RequestException as e:
                # Don't use logger in worker thread - can cause crashes on macOS
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    self.error_occurred.emit(f"Failed to fetch prices after {self.max_retries} attempts: {e}")
