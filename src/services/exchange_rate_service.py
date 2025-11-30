"""
Exchange rate service for DIEM/USD conversion and monitoring.

This module provides real-time exchange rate fetching, caching, and display formatting
for the Venice AI Dashboard.
"""

import asyncio
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass
from PySide6.QtCore import QThread, Signal, QTimer, QObject, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
import json
import os
import logging

from src.config.config import Config

logger = logging.getLogger(__name__)


@dataclass
class ExchangeRateData:
    """Exchange rate information with metadata"""
    rate: float                    # Current DIEM to USD rate
    timestamp: datetime           # When the rate was fetched
    change_24h: Optional[float]   # 24-hour change percentage
    volume_24h: Optional[float]   # 24-hour trading volume
    source: str                   # Data source (venice_api, coingecko, cached)
    confidence: float             # Confidence in the rate (0.0 to 1.0)


class ExchangeRateService(QObject):
    """
    Service for fetching and managing DIEM/USD exchange rates.
    
    Features:
    - Multiple data sources (Venice API, CoinGecko)
    - Rate caching with TTL
    - Automatic rate updates
    - Fallback mechanisms
    - Rate change monitoring
    """
    
    rate_updated = Signal(object)  # ExchangeRateData
    rate_error = Signal(str)       # Error message
    
    def __init__(self, cache_ttl_minutes: int = 5, parent=None):
        """
        Initialize the exchange rate service.
        
        Args:
            cache_ttl_minutes: Cache time-to-live in minutes
            parent: Parent QObject
        """
        super().__init__(parent)
        
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        self.cache_file = os.path.join(os.getcwd(), "exchange_rate_cache.json")
        
        self.current_rate: Optional[ExchangeRateData] = None
        self.rate_history: List[ExchangeRateData] = []
        
        # Rate update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.fetch_current_rate)
        
        # Load cached data
        self.load_cached_rate()
    
    def start_automatic_updates(self, interval_minutes: int = 5) -> None:
        """
        Start automatic rate updates.
        
        Args:
            interval_minutes: Update interval in minutes
        """
        self.update_timer.start(interval_minutes * 60 * 1000)  # Convert to milliseconds
        
        # Fetch immediately if no current rate or rate is stale
        if (not self.current_rate or 
            datetime.now() - self.current_rate.timestamp > self.cache_ttl):
            self.fetch_current_rate()
    
    def stop_automatic_updates(self) -> None:
        """Stop automatic rate updates."""
        self.update_timer.stop()
    
    def fetch_current_rate(self) -> None:
        """Fetch current exchange rate using available sources."""
        # Try Venice API first, then fallback to CoinGecko
        worker = ExchangeRateWorker()
        worker.rate_fetched.connect(self._handle_rate_update)
        worker.error_occurred.connect(self._handle_rate_error)
        worker.start()
    
    def _handle_rate_update(self, rate_data: ExchangeRateData) -> None:
        """Handle successful rate update."""
        self.current_rate = rate_data
        self.rate_history.append(rate_data)
        
        # Keep only last 24 hours of history
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.rate_history = [
            rate for rate in self.rate_history 
            if rate.timestamp >= cutoff_time
        ]
        
        self.save_cached_rate()
        self.rate_updated.emit(rate_data)
    
    def _handle_rate_error(self, error_msg: str) -> None:
        """Handle rate fetch error."""
        self.rate_error.emit(error_msg)
        
        # If we have a cached rate, use it but mark as stale
        if self.current_rate:
            stale_rate = ExchangeRateData(
                rate=self.current_rate.rate,
                timestamp=self.current_rate.timestamp,
                change_24h=self.current_rate.change_24h,
                volume_24h=self.current_rate.volume_24h,
                source="cached_stale",
                confidence=0.5  # Lower confidence for stale data
            )
            self.rate_updated.emit(stale_rate)
    
    def get_current_rate(self) -> Optional[ExchangeRateData]:
        """Get the current exchange rate."""
        return self.current_rate
    
    def get_rate_age_minutes(self) -> Optional[int]:
        """Get age of current rate in minutes."""
        if not self.current_rate:
            return None
        
        age = datetime.now() - self.current_rate.timestamp
        return int(age.total_seconds() / 60)
    
    def calculate_24h_change(self) -> Optional[float]:
        """Calculate 24-hour rate change percentage."""
        if len(self.rate_history) < 2:
            return None
        
        # Find rate from ~24 hours ago
        target_time = datetime.now() - timedelta(hours=24)
        
        # Find closest historical rate
        closest_rate = min(
            self.rate_history[:-1],  # Exclude current rate
            key=lambda r: abs((r.timestamp - target_time).total_seconds())
        )
        
        if not self.current_rate:
            return None
        
        change = ((self.current_rate.rate - closest_rate.rate) / closest_rate.rate) * 100
        return change
    
    def save_cached_rate(self) -> None:
        """Save current rate to cache file."""
        try:
            if self.current_rate:
                cache_data = {
                    "rate": self.current_rate.rate,
                    "timestamp": self.current_rate.timestamp.isoformat(),
                    "change_24h": self.current_rate.change_24h,
                    "volume_24h": self.current_rate.volume_24h,
                    "source": self.current_rate.source,
                    "confidence": self.current_rate.confidence,
                    "cached_at": datetime.now().isoformat()
                }
                
                with open(self.cache_file, 'w') as f:
                    json.dump(cache_data, f, indent=2)
                    
        except Exception as e:
            logger.warning(f"Failed to save rate cache: {e}")
    
    def load_cached_rate(self) -> None:
        """Load cached rate from file."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                cached_time = datetime.fromisoformat(cache_data["timestamp"])
                
                # Check if cache is still valid
                if datetime.now() - cached_time <= self.cache_ttl:
                    self.current_rate = ExchangeRateData(
                        rate=float(cache_data["rate"]),
                        timestamp=cached_time,
                        change_24h=cache_data.get("change_24h"),
                        volume_24h=cache_data.get("volume_24h"),
                        source=cache_data.get("source", "cached"),
                        confidence=float(cache_data.get("confidence", 0.8))
                    )
                    logger.debug(f"Loaded cached exchange rate: {self.current_rate.rate}")
                
        except Exception as e:
            logger.warning(f"Failed to load rate cache: {e}")


class ExchangeRateWorker(QThread):
    """Worker thread for fetching exchange rates from various sources."""
    
    rate_fetched = Signal(object)  # ExchangeRateData
    error_occurred = Signal(str)   # Error message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Data source URLs and configurations
        self.venice_api_url = "https://api.venice.ai/api/v1/exchange/rate"
        self.coingecko_url = "https://api.coingecko.com/api/v3/simple/price"
        
        self.timeout = 10  # Request timeout in seconds
    
    def run(self):
        """Fetch exchange rate from available sources."""
        rate_data = None
        
        # Try Venice API first (most accurate for DIEM)
        try:
            rate_data = self.fetch_from_venice_api()
            if rate_data:
                self.rate_fetched.emit(rate_data)
                return
        except Exception:
            pass  # Try next source
        
        # Fallback to CoinGecko
        try:
            rate_data = self.fetch_from_coingecko()
            if rate_data:
                self.rate_fetched.emit(rate_data)
                return
        except Exception:
            pass  # Try next source
        
        # Fallback to fixed rate (last resort)
        try:
            rate_data = self.get_fallback_rate()
            if rate_data:
                self.rate_fetched.emit(rate_data)
                return
        except Exception:
            pass  # All sources failed
        
        # If all sources fail
        self.error_occurred.emit("Failed to fetch exchange rate from all sources")
    
    def fetch_from_venice_api(self) -> Optional[ExchangeRateData]:
        """
        Fetch DIEM/USD rate from Venice API.
        
        Returns:
            ExchangeRateData or None if fetch fails
        """
        try:
            # Note: This endpoint may not exist yet - using placeholder
            headers = {"Accept": "application/json"}
            response = requests.get(
                self.venice_api_url,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                
                rate = float(data.get("rate", 0))
                change_24h = data.get("change_24h")
                volume_24h = data.get("volume_24h")
                
                if rate > 0:
                    return ExchangeRateData(
                        rate=rate,
                        timestamp=datetime.now(),
                        change_24h=change_24h,
                        volume_24h=volume_24h,
                        source="venice_api",
                        confidence=1.0  # Highest confidence for official API
                    )
            
        except Exception as e:
            logger.error(f"Venice API request failed: {e}")
        
        return None
    
    def fetch_from_coingecko(self) -> Optional[ExchangeRateData]:
        """
        Fetch DIEM/USD rate from CoinGecko API.
        
        Returns:
            ExchangeRateData or None if fetch fails
        """
        try:
            # CoinGecko API call for DIEM price
            params = {
                "ids": "diem",  # May need to adjust based on actual CoinGecko ID
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_24hr_vol": "true"
            }
            
            response = requests.get(
                self.coingecko_url,
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if "diem" in data:
                    diem_data = data["diem"]
                    rate = float(diem_data.get("usd", 0))
                    change_24h = diem_data.get("usd_24h_change")
                    volume_24h = diem_data.get("usd_24h_vol")
                    
                    if rate > 0:
                        return ExchangeRateData(
                            rate=rate,
                            timestamp=datetime.now(),
                            change_24h=change_24h,
                            volume_24h=volume_24h,
                            source="coingecko",
                            confidence=0.8  # High confidence for established API
                        )
            
        except Exception as e:
            logger.debug(f"CoinGecko request failed: {e}")
        
        return None
    
    def get_fallback_rate(self) -> Optional[ExchangeRateData]:
        """
        Get fallback rate when all APIs fail.
        
        Returns:
            ExchangeRateData with estimated rate
        """
        # Use configurable fallback rate
        fallback_rate = Config.DEFAULT_EXCHANGE_RATE
        
        return ExchangeRateData(
            rate=fallback_rate,
            timestamp=datetime.now(),
            change_24h=None,
            volume_24h=None,
            source="fallback",
            confidence=0.3  # Low confidence for fallback
        )


class ExchangeRateWidget(QWidget):
    """
    Widget for displaying current DIEM/USD exchange rate with updates.
    
    Features:
    - Current rate display
    - 24-hour change indicator
    - Last update timestamp
    - Visual rate change indicators
    - Click-to-refresh functionality
    """
    
    refresh_requested = Signal()
    
    def __init__(self, theme_colors: Dict[str, str], parent=None):
        """
        Initialize the exchange rate widget.
        
        Args:
            theme_colors: Theme color dictionary
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.theme_colors = theme_colors
        self.current_rate_data: Optional[ExchangeRateData] = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        
        # Main rate display
        self.rate_label = QLabel("Loading rate...")
        self.rate_label.setStyleSheet(f"""
            QLabel {{
                color: {self.theme_colors.get('text', '#ffffff')};
                font-size: 14px;
                font-weight: bold;
            }}
        """)
        layout.addWidget(self.rate_label)
        
        # Change indicator
        self.change_label = QLabel("")
        self.change_label.setStyleSheet(f"""
            QLabel {{
                color: {self.theme_colors.get('text_secondary', '#cccccc')};
                font-size: 12px;
            }}
        """)
        layout.addWidget(self.change_label)
        
        # Last updated
        self.updated_label = QLabel("")
        self.updated_label.setStyleSheet(f"""
            QLabel {{
                color: {self.theme_colors.get('text_secondary', '#cccccc')};
                font-size: 10px;
            }}
        """)
        layout.addWidget(self.updated_label)
        
        # Make widget clickable for refresh
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {self.theme_colors.get('card_background', '#2a2a2a')};
                border: 1px solid {self.theme_colors.get('border', '#444444')};
                border-radius: 6px;
                padding: 8px;
            }}
            QWidget:hover {{
                background-color: {self.theme_colors.get('card_background_hover', '#333333')};
                border-color: {self.theme_colors.get('accent', '#0066cc')};
            }}
        """)
    
    def update_rate_display(self, rate_data: ExchangeRateData):
        """
        Update the rate display with new data.
        
        Args:
            rate_data: New exchange rate data
        """
        self.current_rate_data = rate_data
        
        # Format rate display
        rate_text = f"1 DIEM = ${rate_data.rate:.4f} USD"
        self.rate_label.setText(rate_text)
        
        # Format change display
        change_text = ""
        change_color = self.theme_colors.get('text_secondary', '#cccccc')
        
        if rate_data.change_24h is not None:
            change_value = rate_data.change_24h
            if change_value > 0:
                change_text = f"↗️ +{change_value:.2f}% (24h)"
                change_color = self.theme_colors.get('positive', '#00aa00')
            elif change_value < 0:
                change_text = f"↘️ {change_value:.2f}% (24h)"
                change_color = self.theme_colors.get('negative', '#aa0000')
            else:
                change_text = "➡️ 0.00% (24h)"
        
        self.change_label.setText(change_text)
        self.change_label.setStyleSheet(f"""
            QLabel {{
                color: {change_color};
                font-size: 12px;
            }}
        """)
        
        # Format update time
        time_diff = datetime.now() - rate_data.timestamp
        if time_diff.total_seconds() < 60:
            updated_text = "Updated just now"
        elif time_diff.total_seconds() < 3600:
            minutes = int(time_diff.total_seconds() / 60)
            updated_text = f"Updated {minutes}m ago"
        else:
            hours = int(time_diff.total_seconds() / 3600)
            updated_text = f"Updated {hours}h ago"
        
        # Add source indicator
        source_indicator = {
            "venice_api": "🏛️",
            "coingecko": "🦎", 
            "cached": "💾",
            "cached_stale": "⚠️💾",
            "fallback": "⚠️"
        }.get(rate_data.source, "")
        
        self.updated_label.setText(f"{source_indicator} {updated_text}")
    
    def mousePressEvent(self, event):
        """Handle mouse clicks for refresh."""
        if event.button() == Qt.LeftButton:
            self.refresh_requested.emit()
        super().mousePressEvent(event)
    
    def set_theme_colors(self, theme_colors: Dict[str, str]):
        """Update theme colors."""
        self.theme_colors = theme_colors
        self.init_ui()
        
        # Refresh display if we have data
        if self.current_rate_data:
            self.update_rate_display(self.current_rate_data)


def format_rate_display(rate: float) -> str:
    """
    Format exchange rate for display.
    
    Args:
        rate: Exchange rate value
        
    Returns:
        Formatted rate string
    """
    return f"1 DIEM = ${rate:.4f} USD"


def format_rate_change(change_percentage: Optional[float]) -> Tuple[str, str]:
    """
    Format rate change for display.
    
    Args:
        change_percentage: 24-hour change percentage
        
    Returns:
        Tuple of (formatted_text, css_color)
    """
    if change_percentage is None:
        return ("No change data", "#cccccc")
    
    if change_percentage > 0:
        return (f"↗️ +{change_percentage:.2f}%", "#00aa00")
    elif change_percentage < 0:
        return (f"↘️ {change_percentage:.2f}%", "#aa0000")
    else:
        return ("➡️ 0.00%", "#cccccc")