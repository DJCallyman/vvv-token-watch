"""
Module for tracking Venice API usage metrics including overall balance and per-key usage.
Implements worker threads for non-blocking API calls to retrieve usage data.
"""

from dataclasses import dataclass
from typing import List, Dict, Any
import requests
import json
from datetime import datetime, timezone
from PySide6.QtCore import QThread, Signal

from src.core.venice_api_client import VeniceAPIClient
from src.utils.date_utils import DateFormatter


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
    last_used_at: str = None  # Last usage timestamp for security monitoring (Phase 3)

@dataclass
class BalanceInfo:
    """Tracks current balance information and daily limits"""
    diem: float       # Current DIEM balance
    usd: float        # Current USD equivalent balance
    daily_diem_limit: float = 100.0  # Daily DIEM consumption limit (default)
    daily_usd_limit: float = 25.0    # Daily USD consumption limit (default)
    next_epoch_begins: str = None     # When limits reset (UTC timestamp)

class UsageWorker(QThread):
    """
    Worker thread for fetching Venice API usage data.
    Operates in the background to prevent UI freezing during API calls.
    """
    
    # Signals for communicating with the main thread
    usage_data_updated = Signal(object)
    balance_data_updated = Signal(object)
    daily_usage_updated = Signal(object)  # New signal for daily usage totals
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
        self.api_client = VeniceAPIClient(admin_key)

    def run(self):
        """
        Main execution method called when the thread starts.
        Fetches both API key usage (daily) and rate limit data.
        Emits signals with results or error messages.
        """
        try:
            # Fetch daily usage totals first
            daily_usage = self.get_daily_usage()
            if daily_usage:
                self.daily_usage_updated.emit(daily_usage)
            
            # Fetch daily usage data for all API keys
            usage_data = self.fetch_api_keys_with_daily_usage()
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
        DEPRECATED: This method fetches trailing 7-day usage data.
        Use fetch_api_keys_with_daily_usage() instead for accurate daily limits.
        
        Fetch API keys and their usage data from the Venice API using individual key endpoints.

        Returns:
            List of APIKeyUsage objects containing usage information for each key
        """
        print("WARNING: Using deprecated fetch_api_keys_usage method. Use fetch_api_keys_with_daily_usage instead.")
        try:
            # Get list of API keys
            keys_response = self.api_client.get("/api_keys")
            keys_data = keys_response.json()

            api_keys = []
            for key_data in keys_data.get("data", []):
                key_id = key_data.get("id", "unknown")
                
                # Fetch key-specific usage
                key_response = self.api_client.get(f"/api_keys/{key_id}")
                key_info = key_response.json().get("data", {})
                
                # Extract usage data (DEPRECATED - 7-day trailing data)
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
                    is_active=True,
                    last_used_at=key_data.get("lastUsedAt")  # Phase 3 security monitoring
                )
                api_keys.append(api_key_usage)

            return api_keys

        except Exception as e:
            raise Exception(f"Failed to fetch key-specific usage: {str(e)}")

    def fetch_rate_limits(self) -> BalanceInfo:
        """
        Fetch current balance information and daily limits from the Venice API.

        Returns:
            BalanceInfo object containing current DIEM/USD balance and daily limits
        """
        try:
            # Use the rate_limits endpoint to get current balances and limits
            response = self.api_client.get("/api_keys/rate_limits")

            data = response.json().get("data", {})
            balances = data.get("balances", {})
            next_epoch = data.get("nextEpochBegins", "")

            # Extract current balances
            current_diem = float(balances.get("DIEM", 0))
            current_usd = float(balances.get("USD", 0))

            # For now, use default daily limits as Venice API doesn't explicitly provide daily spending limits
            # These can be made configurable in the future
            daily_diem_limit = 100.0  # Conservative daily DIEM limit
            daily_usd_limit = 25.0    # Conservative daily USD limit

            return BalanceInfo(
                diem=current_diem,
                usd=current_usd,
                daily_diem_limit=daily_diem_limit,
                daily_usd_limit=daily_usd_limit,
                next_epoch_begins=next_epoch
            )

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch rate limits: {str(e)}")
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            raise Exception(f"Failed to parse rate limits response: {str(e)}")

    def get_daily_usage(self, target_date: str = None) -> Dict[str, float]:
        """
        Fetch daily usage data from the Venice /billing/usage endpoint.
        
        Args:
            target_date: Date in 'YYYY-MM-DD' format. If None, uses today's date in UTC.
            
        Returns:
            Dict containing daily usage totals: {'diem': float, 'usd': float}
        """
        try:
            # Use target date or today's date in UTC
            if target_date is None:
                today = datetime.now(timezone.utc).date()
                target_date = today.isoformat()
            
            # Use DateFormatter for consistent date range creation
            date_params = DateFormatter.create_daily_date_range(target_date)
            
            # Prepare the request parameters
            params = {
                **date_params,
                'limit': 500,  # Get all entries for the day
                'sortOrder': 'desc'
            }
            
            response = self.api_client.get("/billing/usage", params=params)
            
            data = response.json().get("data", [])
            
            # Aggregate usage by currency
            daily_totals = {'diem': 0.0, 'usd': 0.0}
            
            for entry in data:
                currency = entry.get('currency', '').upper()
                amount = abs(float(entry.get('amount', 0)))  # Use absolute value for consumption
                
                if currency == 'DIEM':
                    daily_totals['diem'] += amount
                elif currency == 'USD':
                    daily_totals['usd'] += amount
            
            return daily_totals
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch daily usage: {str(e)}")
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            raise Exception(f"Failed to parse daily usage response: {str(e)}")

    def fetch_api_keys_with_daily_usage(self, target_date: str = None) -> List[APIKeyUsage]:
        """
        Fetch API keys with their trailing 7-day usage data from Venice API.
        
        Note: This now uses the per-key 7-day trailing usage data from /api_keys endpoint.
        The daily usage distribution logic is preserved below for potential future use.
        
        Args:
            target_date: Date in 'YYYY-MM-DD' format. If None, uses today's date in UTC.
            
        Returns:
            List of APIKeyUsage objects containing 7-day trailing usage information for each key
        """
        try:
            # Get list of API keys with their usage data
            keys_response = self.api_client.get("/api_keys")
            keys_data = keys_response.json()

            api_keys = []
            for key_data in keys_data.get("data", []):
                key_id = key_data.get("id", "unknown")
                
                # Extract 7-day trailing usage data from the API response
                usage_data = key_data.get("usage", {}).get("trailingSevenDays", {})
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
                    is_active=key_data.get("isActive", True),
                    last_used_at=key_data.get("lastUsedAt")
                )
                api_keys.append(api_key_usage)

            return api_keys
            
            # PRESERVED FOR FUTURE USE: Daily usage distribution logic
            # Uncomment and modify the above code if daily per-key distribution is needed
            # 
            # # Get daily usage totals for the target date
            # daily_usage = self.get_daily_usage(target_date)
            # 
            # api_keys = []
            # for key_data in keys_data.get("data", []):
            #     key_id = key_data.get("id", "unknown")
            #     
            #     # Distribute the total daily usage across all active keys
            #     num_active_keys = len([k for k in keys_data.get("data", []) if k.get("isActive", True)])
            #     
            #     # Distribute daily usage evenly across active keys (approximation)
            #     key_diem_usage = daily_usage['diem'] / max(1, num_active_keys)
            #     key_usd_usage = daily_usage['usd'] / max(1, num_active_keys)
            #     
            #     metrics = UsageMetrics(
            #         diem=key_diem_usage,
            #         usd=key_usd_usage
            #     )
            #
            #     api_key_usage = APIKeyUsage(
            #         id=key_id,
            #         name=key_data.get("description", f"Key {key_id[-8:]}"),
            #         usage=metrics,
            #         created_at=key_data.get("createdAt", "2025-01-01T00:00:00Z"),
            #         is_active=key_data.get("isActive", True),
            #         last_used_at=key_data.get("lastUsedAt")
            #     )
            #     api_keys.append(api_key_usage)
            #
            # return api_keys

        except Exception as e:
            raise Exception(f"Failed to fetch keys with daily usage: {str(e)}")
