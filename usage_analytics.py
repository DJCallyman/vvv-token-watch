"""
Usage analytics module for Venice API dashboard.

This module provides usage trend analysis, spending estimates, and usage forecasting
based on historical API usage data.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import statistics
import json
import os

from usage_tracker import APIKeyUsage, UsageMetrics, BalanceInfo


@dataclass
class UsageSnapshot:
    """Represents a usage snapshot at a specific point in time"""
    timestamp: datetime
    total_diem: float
    total_usd: float
    api_key_count: int


@dataclass
class UsageTrend:
    """Represents usage trend analysis results"""
    trend_direction: str  # 'increasing', 'decreasing', 'stable'
    daily_average_diem: float
    daily_average_usd: float
    days_remaining_estimate: Optional[int]
    confidence_level: float  # 0.0 to 1.0
    trend_percentage: float  # % change over analysis period


class UsageAnalytics:
    """
    Analytics engine for API usage tracking and trend analysis.
    
    Features:
    - Historical usage data collection and storage
    - Trend analysis and forecasting
    - Spending pattern recognition
    - Balance depletion estimates
    - Usage anomaly detection
    """
    
    def __init__(self, storage_path: str = None):
        """
        Initialize the usage analytics engine.
        
        Args:
            storage_path: Path to store historical usage data (defaults to current directory)
        """
        self.storage_path = storage_path or os.path.join(os.getcwd(), "usage_history.json")
        self.usage_history: List[UsageSnapshot] = []
        self.load_historical_data()
    
    def record_usage_snapshot(self, api_keys: List[APIKeyUsage], balance_info: BalanceInfo) -> None:
        """
        Record a new usage snapshot for trend analysis.
        
        Args:
            api_keys: Current API key usage data
            balance_info: Current balance information
        """
        total_diem = sum(key.usage.diem for key in api_keys)
        total_usd = sum(key.usage.usd for key in api_keys)
        
        snapshot = UsageSnapshot(
            timestamp=datetime.now(),
            total_diem=total_diem,
            total_usd=total_usd,
            api_key_count=len(api_keys)
        )
        
        self.usage_history.append(snapshot)
        
        # Keep only last 30 days of data
        cutoff_date = datetime.now() - timedelta(days=30)
        self.usage_history = [
            s for s in self.usage_history 
            if s.timestamp >= cutoff_date
        ]
        
        self.save_historical_data()
    
    def calculate_daily_average(self, days: int = 7, currency: str = "usd") -> float:
        """
        Calculate average daily spending over the specified period.
        
        Args:
            days: Number of days to analyze (default: 7)
            currency: Currency to analyze ('usd' or 'diem')
            
        Returns:
            Average daily spending amount
        """
        if len(self.usage_history) < 2:
            return 0.0
        
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_snapshots = [
            s for s in self.usage_history 
            if s.timestamp >= cutoff_date
        ]
        
        if len(recent_snapshots) < 2:
            return 0.0
        
        # Sort by timestamp
        recent_snapshots.sort(key=lambda x: x.timestamp)
        
        if currency.lower() == "diem":
            values = [s.total_diem for s in recent_snapshots]
        else:
            values = [s.total_usd for s in recent_snapshots]
        
        # Calculate daily differences
        daily_changes = []
        for i in range(1, len(recent_snapshots)):
            prev_value = values[i-1]
            curr_value = values[i]
            time_diff = (recent_snapshots[i].timestamp - recent_snapshots[i-1].timestamp).total_seconds() / 86400  # Convert to days
            
            if time_diff > 0:
                daily_change = (curr_value - prev_value) / time_diff
                daily_changes.append(abs(daily_change))  # Use absolute value for spending
        
        return statistics.mean(daily_changes) if daily_changes else 0.0
    
    def estimate_days_remaining(self, current_balance: float, currency: str = "usd") -> Optional[int]:
        """
        Estimate days until balance depletion based on usage trends.
        
        Args:
            current_balance: Current balance amount
            currency: Currency for calculation ('usd' or 'diem')
            
        Returns:
            Estimated days remaining, or None if calculation not possible
        """
        daily_average = self.calculate_daily_average(days=7, currency=currency)
        
        if daily_average <= 0 or current_balance <= 0:
            return None
        
        days_remaining = int(current_balance / daily_average)
        return max(0, days_remaining)  # Don't return negative days
    
    def get_usage_trend(self, days: int = 7, currency: str = "usd") -> UsageTrend:
        """
        Analyze usage trend over the specified period.
        
        Args:
            days: Number of days to analyze
            currency: Currency to analyze ('usd' or 'diem')
            
        Returns:
            UsageTrend object with analysis results
        """
        if len(self.usage_history) < 2:
            return UsageTrend(
                trend_direction="stable",
                daily_average_diem=0.0,
                daily_average_usd=0.0,
                days_remaining_estimate=None,
                confidence_level=0.0,
                trend_percentage=0.0
            )
        
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_snapshots = [
            s for s in self.usage_history 
            if s.timestamp >= cutoff_date
        ]
        
        if len(recent_snapshots) < 2:
            return UsageTrend(
                trend_direction="stable",
                daily_average_diem=0.0,
                daily_average_usd=0.0,
                days_remaining_estimate=None,
                confidence_level=0.0,
                trend_percentage=0.0
            )
        
        # Sort by timestamp
        recent_snapshots.sort(key=lambda x: x.timestamp)
        
        # Calculate trend direction and percentage
        if currency.lower() == "diem":
            start_value = recent_snapshots[0].total_diem
            end_value = recent_snapshots[-1].total_diem
        else:
            start_value = recent_snapshots[0].total_usd
            end_value = recent_snapshots[-1].total_usd
        
        if start_value == 0:
            trend_percentage = 0.0
            trend_direction = "stable"
        else:
            trend_percentage = ((end_value - start_value) / start_value) * 100
            
            if abs(trend_percentage) < 5:  # Less than 5% change
                trend_direction = "stable"
            elif trend_percentage > 0:
                trend_direction = "increasing"
            else:
                trend_direction = "decreasing"
        
        # Calculate confidence based on data points and consistency
        confidence_level = min(len(recent_snapshots) / 10.0, 1.0)  # More data points = higher confidence
        
        daily_avg_diem = self.calculate_daily_average(days, "diem")
        daily_avg_usd = self.calculate_daily_average(days, "usd")
        
        return UsageTrend(
            trend_direction=trend_direction,
            daily_average_diem=daily_avg_diem,
            daily_average_usd=daily_avg_usd,
            days_remaining_estimate=None,  # Will be calculated separately with current balance
            confidence_level=confidence_level,
            trend_percentage=trend_percentage
        )
    
    def detect_usage_anomalies(self, threshold_multiplier: float = 2.5) -> List[Dict[str, any]]:
        """
        Detect unusual usage patterns that might indicate issues.
        
        Args:
            threshold_multiplier: How many standard deviations constitute an anomaly
            
        Returns:
            List of detected anomalies with details
        """
        if len(self.usage_history) < 7:  # Need at least a week of data
            return []
        
        anomalies = []
        recent_snapshots = self.usage_history[-14:]  # Last 2 weeks
        
        if len(recent_snapshots) < 7:
            return anomalies
        
        # Calculate baseline statistics
        usd_values = [s.total_usd for s in recent_snapshots[:-3]]  # Exclude last 3 days from baseline
        if len(usd_values) < 4:
            return anomalies
        
        mean_usage = statistics.mean(usd_values)
        std_usage = statistics.stdev(usd_values) if len(usd_values) > 1 else 0
        
        # Check recent days for anomalies
        for snapshot in recent_snapshots[-3:]:
            if std_usage > 0:
                z_score = abs(snapshot.total_usd - mean_usage) / std_usage
                
                if z_score > threshold_multiplier:
                    anomaly_type = "high" if snapshot.total_usd > mean_usage else "low"
                    anomalies.append({
                        "timestamp": snapshot.timestamp.isoformat(),
                        "type": f"{anomaly_type}_usage",
                        "value": snapshot.total_usd,
                        "baseline": mean_usage,
                        "severity": min(z_score / threshold_multiplier, 3.0)  # Cap at 3.0
                    })
        
        return anomalies
    
    def get_usage_summary(self, days: int = 7) -> Dict[str, any]:
        """
        Get a comprehensive usage summary for the dashboard.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with usage summary data
        """
        trend = self.get_usage_trend(days)
        anomalies = self.detect_usage_anomalies()
        
        # Calculate total usage over period
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_snapshots = [
            s for s in self.usage_history 
            if s.timestamp >= cutoff_date
        ]
        
        total_usd = sum(s.total_usd for s in recent_snapshots)
        total_diem = sum(s.total_diem for s in recent_snapshots)
        
        return {
            "period_days": days,
            "total_usage_usd": total_usd,
            "total_usage_diem": total_diem,
            "daily_average_usd": trend.daily_average_usd,
            "daily_average_diem": trend.daily_average_diem,
            "trend_direction": trend.trend_direction,
            "trend_percentage": trend.trend_percentage,
            "confidence_level": trend.confidence_level,
            "anomalies_count": len(anomalies),
            "data_points": len(recent_snapshots),
            "last_updated": datetime.now().isoformat()
        }
    
    def save_historical_data(self) -> None:
        """Save historical usage data to storage file."""
        try:
            data = {
                "snapshots": [
                    {
                        "timestamp": s.timestamp.isoformat(),
                        "total_diem": s.total_diem,
                        "total_usd": s.total_usd,
                        "api_key_count": s.api_key_count
                    }
                    for s in self.usage_history
                ],
                "last_saved": datetime.now().isoformat()
            }
            
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Warning: Failed to save usage history: {e}")
    
    def load_historical_data(self) -> None:
        """Load historical usage data from storage file."""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                
                self.usage_history = []
                for snapshot_data in data.get("snapshots", []):
                    snapshot = UsageSnapshot(
                        timestamp=datetime.fromisoformat(snapshot_data["timestamp"]),
                        total_diem=float(snapshot_data["total_diem"]),
                        total_usd=float(snapshot_data["total_usd"]),
                        api_key_count=int(snapshot_data["api_key_count"])
                    )
                    self.usage_history.append(snapshot)
                
                print(f"Loaded {len(self.usage_history)} historical usage snapshots")
                
        except Exception as e:
            print(f"Warning: Failed to load usage history: {e}")
            self.usage_history = []


def format_trend_display(trend: UsageTrend) -> str:
    """
    Format a usage trend for display in the UI.
    
    Args:
        trend: UsageTrend object to format
        
    Returns:
        Formatted string for display
    """
    direction_emoji = {
        "increasing": "↗️",
        "decreasing": "↘️", 
        "stable": "➡️"
    }
    
    emoji = direction_emoji.get(trend.trend_direction, "➡️")
    direction = trend.trend_direction.capitalize()
    
    if abs(trend.trend_percentage) < 1:
        return f"{emoji} {direction} usage"
    else:
        sign = "+" if trend.trend_percentage > 0 else ""
        return f"{emoji} {direction} ({sign}{trend.trend_percentage:.1f}%)"


def format_days_remaining(days: Optional[int]) -> str:
    """
    Format days remaining estimate for display.
    
    Args:
        days: Number of days remaining or None
        
    Returns:
        Formatted string for display
    """
    if days is None:
        return "Unable to estimate"
    elif days == 0:
        return "⚠️ Running low"
    elif days == 1:
        return "⚠️ ~1 day remaining"
    elif days < 7:
        return f"⚠️ ~{days} days remaining"
    elif days < 30:
        return f"~{days} days remaining"
    else:
        return f"~{days//7} weeks remaining"