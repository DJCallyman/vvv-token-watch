"""
Price Worker for fetching cryptocurrency prices in a background thread.

This module provides a QThread worker for fetching CoinGecko price data
without blocking the main UI thread.
"""

from typing import Dict, Optional, List
import requests
import logging
import time
from PySide6.QtCore import QThread, Signal

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
    
    def run(self):
        """Fetch prices from CoinGecko with retry logic."""
        url = "https://api.coingecko.com/api/v3/simple/price"
        vs_currencies_str = ','.join(self.currencies)
        params = {
            'ids': self.token_id,
            'vs_currencies': vs_currencies_str
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, params=params, timeout=30)
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
