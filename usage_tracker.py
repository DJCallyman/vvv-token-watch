"""
Module for tracking Venice API usage metrics including overall balance and per-key usage.
Implements worker threads for non-blocking API calls to retrieve usage data.
"""

from dataclasses import dataclass
from typing import List, Dict, Any
import requests
import json
from PySide6.QtCore import QThread, Signal

@dataclass
class UsageMetrics:
    """Tracks usage metrics for a specific time period"""
    diem: float
    usd: float

@dataclass
class APIKeyUsage:
    """Represents usage data for a single API key"""
    id: str           # Unique API key identifier
    name: str         # User-assigned name for the key
    usage: UsageMetrics
    created_at: str   # ISO 8601 timestamp
    is_active: bool   # Whether the key is currently enabled

@dataclass
class BalanceInfo:
    """Tracks current balance information"""
    diem: float       # Current DIEM balance (replaces VCU)
    usd: float        # Current USD equivalent balance

class UsageWorker(QThread):
    """
    Worker thread for fetching Venice API usage data.
    Operates in the background to prevent UI freezing during API calls.
    """
    
    # Signals for communicating with the main thread
    usage_data_updated = Signal(object)
    balance_data_updated = Signal(object)
    error_occurred = Signal(str)

    def __init__(self, admin_key: str, parent=None):
        """
        Initialize the UsageWorker with admin key for authentication.
        
        Args:
            admin_key: Admin API key with permission to access all keys' data
            parent: Parent QObject (typically the main window)
        """
        super().__init__(parent)
        self.admin_key = admin_key
        self.base_url = "https://api.venice.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.admin_key}",
            "Content-Type": "application/json"
        }

    def run(self):
        """
        Main execution method called when the thread starts.
        Fetches both API key usage and rate limit data.
        Emits signals with results or error messages.
        """
        try:
            # Fetch usage data for all API keys
            usage_data = self.fetch_api_keys_usage()
            if usage_data:
                self.usage_data_updated.emit(usage_data)
            
            # Fetch current balance/limit information
            balance_data = self.fetch_rate_limits()
            if balance_data:
                self.balance_data_updated.emit(balance_data)
                
        except Exception as e:
            self.error_occurred.emit(f"Usage tracking error: {str(e)}")

    def fetch_api_keys_usage(self) -> List[APIKeyUsage]:
        """
        Fetch API keys and their usage data from the Venice API using individual key endpoints.

        Returns:
            List of APIKeyUsage objects containing usage information for each key
        """
        try:
            # Get list of API keys
            keys_url = f"{self.base_url}/api_keys"
            keys_response = requests.get(keys_url, headers=self.headers, timeout=30)
            keys_response.raise_for_status()
            keys_data = keys_response.json()

            api_keys = []
            for key_data in keys_data.get("data", []):
                key_id = key_data.get("id", "unknown")
                
                # Fetch key-specific usage
                key_url = f"{self.base_url}/api_keys/{key_id}"
                key_response = requests.get(key_url, headers=self.headers, timeout=30)
                key_response.raise_for_status()
                key_info = key_response.json().get("data", {})
                
                # Extract usage data
                usage_data = key_info.get("usage", {}).get("trailingSevenDays", {})
                diem_usage = float(usage_data.get("diem", 0))
                usd_usage = float(usage_data.get("usd", 0))

                metrics = UsageMetrics(
                    diem=diem_usage,
                    usd=usd_usage
                )

                api_key_usage = APIKeyUsage(
                    id=key_id,
                    name=key_data.get("description", f"Key {key_id[-8:]}"),
                    usage=metrics,
                    created_at=key_data.get("createdAt", "2025-01-01T00:00:00Z"),
                    is_active=True
                )
                api_keys.append(api_key_usage)

            return api_keys

        except Exception as e:
            raise Exception(f"Failed to fetch key-specific usage: {str(e)}")

    def fetch_rate_limits(self) -> BalanceInfo:
        """
        Fetch current balance information from the Venice API.

        Returns:
            BalanceInfo object containing current DIEM/USD balance
        """
        try:
            # Use the rate_limits endpoint to get current balances
            url = f"{self.base_url}/api_keys/rate_limits"
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()

            data = response.json().get("data", {})
            balances = data.get("balances", {})

            # Extract current balances
            current_diem = float(balances.get("DIEM", 0))
            current_usd = float(balances.get("USD", 0))

            return BalanceInfo(
                diem=current_diem,
                usd=current_usd
            )

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch rate limits: {str(e)}")
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            raise Exception(f"Failed to parse rate limits response: {str(e)}")
