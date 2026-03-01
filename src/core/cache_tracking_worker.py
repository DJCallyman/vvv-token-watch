"""
Cache Tracking Worker for fetching billing data and generating cache analytics.

This module provides a QThread worker that fetches billing usage data,
analyzes cache metrics, and emits cache performance reports.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
from pathlib import Path
import json
from PySide6.QtCore import QThread, Signal

from src.core.venice_api_client import VeniceAPIClient
from src.core.model_cache import ModelCacheManager
from src.core.cache_analytics import CacheAnalytics
from src.core.cache_models import CachePerformanceReport, ModelCacheStats
from src.config.config import Config

logger = logging.getLogger(__name__)


class CacheTrackingWorker(QThread):
    """
    Worker thread for fetching billing data and analyzing prompt cache performance.

    Fetches data from /billing/usage endpoint, uses CacheAnalytics to calculate
    cache metrics, and emits results for UI display.
    """

    class CacheDataBundle:
        """Bundle for passing cache data from worker to UI"""
        def __init__(self, report: CachePerformanceReport, model_stats: dict):
            self.report = report
            self.model_stats = model_stats

    cache_data_ready = Signal(object)
    error_occurred = Signal(str)
    status_update = Signal(str)

    CACHE_FILE = Path("data/cache_tracking_cache.json")
    CACHE_TTL_SECONDS = Config.CACHE_TTL_SECONDS
    MAX_PAGES = Config.CACHE_MAX_PAGES
    PAGE_SIZE = Config.CACHE_PAGE_SIZE

    def __init__(self, admin_key: str, analysis_days: int = 7, parent=None):
        """
        Initialize the cache tracking worker.

        Args:
            admin_key: Venice Admin API key for billing endpoint access
            analysis_days: Number of days to analyze (default 7)
            parent: Parent QObject
        """
        super().__init__(parent)
        self.admin_key = admin_key
        self.analysis_days = analysis_days
        self.api_client = VeniceAPIClient(admin_key)
        self.model_cache = ModelCacheManager()
        self.analytics = CacheAnalytics(model_cache_manager=self.model_cache)

    def run(self):
        """Execute cache tracking analysis in background thread."""
        try:
            self.status_update.emit(f"Analyzing cache performance for {self.analysis_days} days...")

            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=self.analysis_days)

            self.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

            cached_data, last_fetch_time = self._load_cache()

            if last_fetch_time and (end_date - last_fetch_time).total_seconds() < self.CACHE_TTL_SECONDS:
                cache_age = int((end_date - last_fetch_time).total_seconds())
                self.status_update.emit(f"Using cached data ({len(cached_data)} records, {cache_age}s old)")
                if cached_data:
                    report, model_stats = self.analytics.analyze_billing_records(cached_data, self.analysis_days)
                    self.cache_data_ready.emit(self.CacheDataBundle(report, model_stats))
                    return

            if last_fetch_time and (end_date - last_fetch_time).total_seconds() < Config.INCREMENTAL_THRESHOLD_SECONDS:
                fetch_start = last_fetch_time - timedelta(minutes=5)
                self.status_update.emit("Incremental refresh...")
            else:
                fetch_start = start_date
                cached_data = []
                self.status_update.emit("Full refresh...")

            new_records = self._fetch_billing_data(fetch_start, end_date)

            all_records = self._merge_records(cached_data, new_records, start_date)

            self._save_cache(all_records, end_date)

            if all_records:
                report, model_stats = self.analytics.analyze_billing_records(all_records, self.analysis_days)
                self.status_update.emit(
                    f"Analysis complete: {report.total_requests} requests, "
                    f"${report.total_savings_usd:.4f} savings, "
                    f"{report.overall_cache_hit_rate:.1f}% cache hit rate"
                )
                self.cache_data_ready.emit(self.CacheDataBundle(report, model_stats))
            else:
                self.status_update.emit("No billing data available for analysis")
                self.cache_data_ready.emit(
                    self.CacheDataBundle(
                        CachePerformanceReport(
                            start_date=start_date.strftime('%Y-%m-%d'),
                            end_date=end_date.strftime('%Y-%m-%d'),
                            period_days=self.analysis_days
                        ),
                        {}
                    )
                )

        except Exception as e:
            error_msg = f"Cache tracking failed: {type(e).__name__}: {e}"
            logger.exception(error_msg)
            self.error_occurred.emit(error_msg)

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

            self.status_update.emit(f"Fetching billing data page {page}...")
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
            except Exception as e:
                logger.warning(f"Failed to load cache tracking cache: {e}")

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
            logger.debug(f"Saved cache tracking data: {len(records)} records")
        except Exception as e:
            logger.warning(f"Failed to save cache tracking cache: {e}")

    def _merge_records(self, cached: List[Dict], new_records: List[Dict], cutoff_date: datetime) -> List[Dict]:
        """Merge new records with cached data, removing duplicates."""
        if cached and new_records:
            existing_ids = {r.get('timestamp', '') for r in cached}
            unique_new = [r for r in new_records if r.get('timestamp', '') not in existing_ids]
            all_records = cached + unique_new
        else:
            all_records = new_records or cached

        cutoff_str = cutoff_date.isoformat()
        all_records = [r for r in all_records if r.get('timestamp', '') >= cutoff_str]

        return all_records
