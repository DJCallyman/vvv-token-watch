"""
Web app usage tracking for Venice AI.
Fetches usage data from /billing/usage endpoint and filters for web app consumption.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from PySide6.QtCore import QThread, Signal

from src.core.venice_api_client import VeniceAPIClient
from src.utils.date_utils import DateFormatter


@dataclass
class WebUsageItem:
    """Represents a single web app usage item (e.g., a video generation)"""
    sku: str                    # Model/service identifier
    amount: float               # Cost in currency
    currency: str               # USD, DIEM, or VCU
    units: float                # Quantity consumed
    price_per_unit_usd: float   # Unit pricing
    timestamp: str              # ISO 8601 timestamp
    notes: str                  # Usage type description
    
    def __post_init__(self):
        """Ensure amount is always positive for display"""
        self.amount = abs(self.amount)


@dataclass
class WebUsageMetrics:
    """Aggregated web app usage metrics"""
    diem: float
    usd: float
    vcu: float
    total_requests: int
    items: List[WebUsageItem]
    by_sku: Dict[str, Dict[str, Any]]  # Breakdown by model/service


class WebUsageWorker(QThread):
    """
    Worker thread for fetching web app usage from /billing/usage endpoint.
    Filters out API Inference to show only web app consumption.
    """
    
    # Signals
    web_usage_updated = Signal(object)  # WebUsageMetrics
    error_occurred = Signal(str)
    progress_updated = Signal(str)  # For status updates during fetch
    
    def __init__(self, admin_key: str, days: int = 7, parent=None):
        """
        Initialize the WebUsageWorker.
        
        Args:
            admin_key: Admin API key for authentication
            days: Number of days to fetch (default 7 to match API key data)
            parent: Parent QObject
        """
        super().__init__(parent)
        self.admin_key = admin_key
        self.days = days
        self.api_client = VeniceAPIClient(admin_key)
    
    def run(self):
        """Fetch and process web app usage data"""
        try:
            self.progress_updated.emit("Fetching web app usage...")
            
            metrics = self.fetch_web_usage()
            if metrics:
                self.web_usage_updated.emit(metrics)
                self.progress_updated.emit(f"Web usage: {metrics.total_requests} requests")
            else:
                self.progress_updated.emit("No web usage found")
                
        except Exception as e:
            self.error_occurred.emit(f"Web usage tracking error: {str(e)}")
    
    def fetch_web_usage(self) -> WebUsageMetrics:
        """
        Fetch web app usage from /billing/usage endpoint.
        Filters out 'API Inference' records to show only web app consumption.
        
        Returns:
            WebUsageMetrics with aggregated data
        """
        # Calculate date range using utility
        date_params = DateFormatter.create_date_range(days=self.days)
        
        params = {
            **date_params,
            "sortOrder": "desc",
            "limit": 500,
            "page": 1
        }
        
        all_web_records = []
        total_diem = 0.0
        total_usd = 0.0
        total_vcu = 0.0
        sku_breakdown = {}
        
        page = 1
        api_inference_count = 0
        
        # Fetch all pages (unfortunately we can't filter server-side)
        while True:
            params["page"] = page
            
            try:
                response = self.api_client.get("/billing/usage", params=params)
                
                data = response.json()
                records = data.get("data", [])
                pagination = data.get("pagination", {})
                
                if not records:
                    break
                
                # Filter records client-side
                for record in records:
                    notes = record.get("notes", "")
                    
                    if notes == "API Inference":
                        api_inference_count += 1
                        continue
                    
                    # This is web app usage
                    amount = abs(float(record.get("amount", 0)))
                    currency = record.get("currency", "")
                    sku = record.get("sku", "unknown")
                    
                    # Track totals
                    if currency == "USD":
                        total_usd += amount
                    elif currency == "DIEM":
                        total_diem += amount
                    elif currency == "VCU":
                        total_vcu += amount
                    
                    # Create usage item
                    item = WebUsageItem(
                        sku=sku,
                        amount=amount,
                        currency=currency,
                        units=float(record.get("units", 0)),
                        price_per_unit_usd=float(record.get("pricePerUnitUsd", 0)),
                        timestamp=record.get("timestamp", ""),
                        notes=notes
                    )
                    all_web_records.append(item)
                    
                    # Track by SKU
                    if sku not in sku_breakdown:
                        sku_breakdown[sku] = {
                            "count": 0,
                            "amount": 0.0,
                            "currency": currency,
                            "units": 0.0,
                            "notes": notes  # Store usage type (Video Inference, Image Inference, etc.)
                        }
                    sku_breakdown[sku]["count"] += 1
                    sku_breakdown[sku]["amount"] += amount
                    sku_breakdown[sku]["units"] += item.units
                
                # Update progress
                web_count = len(all_web_records)
                self.progress_updated.emit(
                    f"Page {page}/{pagination.get('totalPages', '?')}: "
                    f"{web_count} web app, {api_inference_count} API filtered"
                )
                
                # Check if more pages
                if page >= pagination.get("totalPages", 0):
                    break
                
                page += 1
                
            except Exception as e:
                raise Exception(f"Failed to fetch billing usage: {str(e)}")
        
        return WebUsageMetrics(
            diem=total_diem,
            usd=total_usd,
            vcu=total_vcu,
            total_requests=len(all_web_records),
            items=all_web_records,
            by_sku=sku_breakdown
        )
    
    def get_daily_average(self, metrics: WebUsageMetrics) -> Dict[str, float]:
        """
        Calculate daily average consumption.
        
        Args:
            metrics: WebUsageMetrics object
            
        Returns:
            Dict with daily averages for each currency
        """
        if self.days == 0:
            return {"diem": 0.0, "usd": 0.0, "vcu": 0.0}
        
        return {
            "diem": metrics.diem / self.days,
            "usd": metrics.usd / self.days,
            "vcu": metrics.vcu / self.days
        }
