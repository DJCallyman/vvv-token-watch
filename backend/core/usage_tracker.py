"""
Module for tracking Venice API usage metrics including overall balance and per-key usage.
Web-optimized version without Qt dependencies.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import requests
import json
import logging
from datetime import datetime, timezone

from backend.core.venice_api_client import VeniceAPIClient

logger = logging.getLogger(__name__)


@dataclass
class UsageMetrics:
    """Tracks usage metrics for a specific time period"""
    diem: float
    usd: float


@dataclass
class APIKeyUsage:
    """Represents usage data for a single API key"""
    id: str
    name: str
    usage: UsageMetrics
    created_at: str
    is_active: bool
    last_used_at: Optional[str] = None


@dataclass
class BalanceInfo:
    """Tracks current balance information and daily limits"""
    diem: float
    usd: float
    daily_diem_limit: float = 100.0
    daily_usd_limit: float = 25.0
    next_epoch_begins: Optional[str] = None


class UsageTracker:
    """
    Service class for fetching Venice API usage data.
    Optimized for web backend without Qt dependencies.
    """
    
    def __init__(self, admin_key: str):
        self.admin_key = admin_key
        self.api_client = VeniceAPIClient(admin_key)
    
    def fetch_rate_limits(self) -> BalanceInfo:
        try:
            response = self.api_client.get("/api_keys/rate_limits")
            data = response.json().get("data", {})
            balances = data.get("balances", {})
            next_epoch = data.get("nextEpochBegins", "")
            
            current_diem = float(balances.get("DIEM", 0))
            current_usd = float(balances.get("USD", 0))
            
            daily_diem_limit = 100.0
            daily_usd_limit = 25.0
            
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
    
    def get_daily_usage(self, target_date: Optional[str] = None) -> Dict[str, float]:
        try:
            if target_date is None:
                today = datetime.now(timezone.utc).date()
                target_date = today.isoformat()
            
            start_datetime = f"{target_date}T00:00:00Z"
            end_datetime = f"{target_date}T23:59:59Z"
            
            params = {
                'startDate': start_datetime,
                'endDate': end_datetime,
                'limit': 500,
                'sortOrder': 'desc'
            }
            
            response = self.api_client.get("/billing/usage", params=params)
            data = response.json().get("data", [])
            
            daily_totals = {'diem': 0.0, 'usd': 0.0}
            
            for entry in data:
                currency = entry.get('currency', '').upper()
                amount = abs(float(entry.get('amount', 0)))
                
                if currency == 'DIEM':
                    daily_totals['diem'] += amount
                elif currency == 'USD':
                    daily_totals['usd'] += amount
            
            return daily_totals
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch daily usage: {str(e)}")
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            raise Exception(f"Failed to parse daily usage response: {str(e)}")
    
    def fetch_api_keys_with_daily_usage(self) -> List[APIKeyUsage]:
        try:
            keys_response = self.api_client.get("/api_keys")
            keys_data = keys_response.json()
            
            api_keys = []
            for key_data in keys_data.get("data", []):
                key_id = key_data.get("id", "unknown")
                
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
            
        except Exception as e:
            raise Exception(f"Failed to fetch keys with daily usage: {str(e)}")


class UsageWorker:
    """
    Compatibility class that wraps UsageTracker.
    Provides the same interface as the Qt-based UsageWorker.
    """
    
    def __init__(self, admin_key: str, parent=None):
        self.admin_key = admin_key
        self.api_client = VeniceAPIClient(admin_key)
        self._tracker = UsageTracker(admin_key)
    
    def fetch_rate_limits(self) -> BalanceInfo:
        return self._tracker.fetch_rate_limits()
    
    def get_daily_usage(self, target_date: Optional[str] = None) -> Dict[str, float]:
        return self._tracker.get_daily_usage(target_date)
    
    def fetch_api_keys_with_daily_usage(self) -> List[APIKeyUsage]:
        return self._tracker.fetch_api_keys_with_daily_usage()