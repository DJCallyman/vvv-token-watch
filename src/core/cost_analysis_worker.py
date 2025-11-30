"""
Cost Analysis Worker for fetching billing data in a background thread.

This module provides a QThread worker for fetching billing data from the Venice API
without blocking the main UI thread.

NOTE: Logging is intentionally avoided in worker threads on macOS to prevent crashes.
Use status_update and error_occurred signals to communicate with main thread.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import requests
from PySide6.QtCore import QThread, Signal

from src.core.venice_api_client import VeniceAPIClient


class CostAnalysisWorker(QThread):
    """
    Worker thread for fetching billing data from Venice API.
    Implements intelligent caching to minimize API calls.
    """
    
    # Signals
    billing_data_ready = Signal(list, list, int)  # billing_records, api_keys_data, analysis_days
    error_occurred = Signal(str)
    status_update = Signal(str)  # Progress updates for UI
    
    # Cache configuration
    CACHE_FILE = Path("data/billing_cache.json")
    CACHE_TTL_SECONDS = 300  # 5 minutes
    INCREMENTAL_THRESHOLD_SECONDS = 3600  # 1 hour
    MAX_PAGES = 20
    PAGE_SIZE = 500
    
    def __init__(self, admin_key: str, analysis_days: int = 7, parent=None):
        """
        Initialize the cost analysis worker.
        
        Args:
            admin_key: Venice Admin API key (required for billing endpoints)
            analysis_days: Number of days to analyze (default 7)
            parent: Parent QObject
        """
        super().__init__(parent)
        self.admin_key = admin_key
        self.analysis_days = analysis_days
        self.api_client = VeniceAPIClient(admin_key)
    
    def run(self):
        """Fetch billing data with intelligent caching."""
        try:
            # Calculate date range
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=self.analysis_days)
            
            # Setup cache
            self.CACHE_FILE.parent.mkdir(exist_ok=True)
            
            # Load cached data
            cached_data, last_fetch_time = self._load_cache()
            
            # Determine fetch strategy
            if last_fetch_time and (end_date - last_fetch_time).total_seconds() < self.CACHE_TTL_SECONDS:
                # Cache is fresh - use it
                cache_age = int((end_date - last_fetch_time).total_seconds())
                self.status_update.emit(f"Using cached data ({len(cached_data)} records, {cache_age}s old)")
                
                if cached_data:
                    api_keys_data = self._fetch_api_keys()
                    self.billing_data_ready.emit(cached_data, api_keys_data, self.analysis_days)
                    return
            
            # Determine if incremental or full refresh
            if last_fetch_time and (end_date - last_fetch_time).total_seconds() < self.INCREMENTAL_THRESHOLD_SECONDS:
                fetch_start = last_fetch_time - timedelta(minutes=5)  # Small overlap
                self.status_update.emit("Incremental refresh...")
            else:
                fetch_start = start_date
                cached_data = []  # Clear cache for full refresh
                self.status_update.emit("Full refresh...")
            
            # Fetch billing data
            new_records = self._fetch_billing_data(fetch_start, end_date)
            
            # Merge with cache
            all_records = self._merge_records(cached_data, new_records, start_date)
            
            # Save to cache
            self._save_cache(all_records, end_date)
            
            # Fetch API keys data
            api_keys_data = self._fetch_api_keys()
            
            # Emit results
            if all_records:
                self.status_update.emit(f"Analysis ready ({len(all_records)} records)")
                self.billing_data_ready.emit(all_records, api_keys_data, self.analysis_days)
            else:
                self.status_update.emit("No billing data available")
                self.billing_data_ready.emit([], api_keys_data, self.analysis_days)
                
        except requests.exceptions.HTTPError as e:
            self._handle_http_error(e)
        except Exception as e:
            error_msg = f"Cost analysis failed: {type(e).__name__}: {e}"
            self.error_occurred.emit(error_msg)
    
    def _load_cache(self) -> tuple[List[Dict], Optional[datetime]]:
        """Load cached billing data."""
        cached_data = []
        last_fetch_time = None
        
        if self.CACHE_FILE.exists():
            try:
                with open(self.CACHE_FILE, 'r') as f:
                    cache = json.load(f)
                    cached_data = cache.get('records', [])
                    last_fetch_str = cache.get('last_fetch')
                    if last_fetch_str:
                        last_fetch_time = datetime.fromisoformat(last_fetch_str.replace('Z', '+00:00'))
            except Exception:
                pass  # Ignore cache load errors
        
        return cached_data, last_fetch_time
    
    def _save_cache(self, records: List[Dict], fetch_time: datetime) -> None:
        """Save billing data to cache."""
        try:
            cache = {
                'last_fetch': fetch_time.isoformat(),
                'records': records
            }
            with open(self.CACHE_FILE, 'w') as f:
                json.dump(cache, f)
        except Exception:
            pass  # Ignore cache save errors
    
    def _fetch_billing_data(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Fetch billing data from Venice API with pagination."""
        all_records = []
        page = 1
        
        while page <= self.MAX_PAGES:
            params = {
                'startDate': start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                'endDate': end_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                'limit': self.PAGE_SIZE,
                'page': page,
                'sortOrder': 'desc'
            }
            
            self.status_update.emit(f"Fetching page {page}...")
            response = self.api_client.get("/billing/usage", params=params, timeout=60)
            data = response.json()
            
            billing_data = data.get('data', [])
            pagination = data.get('pagination', {})
            
            all_records.extend(billing_data)
            
            total_pages = pagination.get('totalPages', 1)
            
            if page >= total_pages:
                break
            
            page += 1
        
        return all_records
    
    def _merge_records(self, cached: List[Dict], new_records: List[Dict], cutoff_date: datetime) -> List[Dict]:
        """Merge new records with cached data, removing duplicates."""
        if cached and new_records:
            existing_ids = {r.get('timestamp', '') for r in cached}
            unique_new = [r for r in new_records if r.get('timestamp', '') not in existing_ids]
            all_records = cached + unique_new
        else:
            all_records = new_records or cached
        
        # Filter to analysis period
        cutoff_str = cutoff_date.isoformat()
        all_records = [r for r in all_records if r.get('timestamp', '') >= cutoff_str]
        
        return all_records
    
    def _fetch_api_keys(self) -> List[Dict]:
        """Fetch API keys data for attribution."""
        try:
            response = self.api_client.get("/api_keys")
            api_keys_data = response.json().get('data', [])
            return api_keys_data
        except Exception:
            return []
    
    def _handle_http_error(self, e: requests.exceptions.HTTPError) -> None:
        """Handle HTTP errors."""
        if e.response is not None:
            status = e.response.status_code
            
            if status == 400:
                try:
                    error_body = e.response.json()
                    self.error_occurred.emit(f"API Error: {error_body.get('message', str(error_body))}")
                except:
                    self.error_occurred.emit(f"API Error (400): {e.response.text[:200]}")
            elif status == 401:
                self.error_occurred.emit("Authentication failed - check VENICE_ADMIN_KEY")
            elif status == 403:
                self.error_occurred.emit("Access denied - admin key required for billing endpoint")
            else:
                self.error_occurred.emit(f"HTTP {status} error")
        else:
            self.error_occurred.emit(f"Request failed: {e}")
