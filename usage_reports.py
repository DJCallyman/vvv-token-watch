"""
Usage Reports Module for Phase 3 API Key Management.
Provides detailed usage analytics and reporting functionality.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import os
from dataclasses import dataclass

try:
    from .usage_tracker import APIKeyUsage, UsageMetrics
except ImportError:
    # Fallback for direct execution
    from usage_tracker import APIKeyUsage, UsageMetrics


@dataclass
class UsageReport:
    """Comprehensive usage report for an API key"""
    key_id: str
    key_name: str
    total_diem: float
    total_usd: float
    daily_average_usd: float
    monthly_projection_usd: float
    usage_trend: str  # "increasing", "decreasing", "stable"
    risk_level: str   # "low", "medium", "high"
    recommendations: List[str]
    created_at: str
    last_used_at: Optional[str]


class UsageReportGenerator:
    """Generates detailed usage reports for API keys"""
    
    def __init__(self):
        self.historical_data = {}
        self.load_historical_data()
    
    def load_historical_data(self):
        """Load historical usage data from storage"""
        try:
            data_file = "usage_reports_history.json"
            if os.path.exists(data_file):
                with open(data_file, 'r') as f:
                    self.historical_data = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load historical usage data: {e}")
            self.historical_data = {}
    
    def save_historical_data(self):
        """Save historical usage data to storage"""
        try:
            data_file = "usage_reports_history.json"
            with open(data_file, 'w') as f:
                json.dump(self.historical_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save historical usage data: {e}")
    
    def record_usage_snapshot(self, api_key_usage: APIKeyUsage):
        """Record a usage snapshot for historical tracking"""
        key_id = api_key_usage.id
        timestamp = datetime.now().isoformat()
        
        if key_id not in self.historical_data:
            self.historical_data[key_id] = []
        
        # Add current snapshot
        snapshot = {
            "timestamp": timestamp,
            "diem": api_key_usage.usage.diem,
            "usd": api_key_usage.usage.usd,
            "key_name": api_key_usage.name,
            "is_active": api_key_usage.is_active
        }
        
        self.historical_data[key_id].append(snapshot)
        
        # Keep only last 30 days of data
        cutoff_date = datetime.now() - timedelta(days=30)
        self.historical_data[key_id] = [
            s for s in self.historical_data[key_id]
            if datetime.fromisoformat(s["timestamp"]) > cutoff_date
        ]
        
        self.save_historical_data()
    
    def generate_report(self, api_key_usage: APIKeyUsage) -> UsageReport:
        """Generate a comprehensive usage report for an API key"""
        key_id = api_key_usage.id
        
        # Record current usage
        self.record_usage_snapshot(api_key_usage)
        
        # Calculate metrics
        daily_average = self._calculate_daily_average(key_id)
        monthly_projection = daily_average * 30.44  # Average days per month
        usage_trend = self._analyze_usage_trend(key_id)
        risk_level = self._assess_risk_level(api_key_usage.usage.usd, daily_average)
        recommendations = self._generate_recommendations(api_key_usage, risk_level, usage_trend)
        
        return UsageReport(
            key_id=key_id,
            key_name=api_key_usage.name,
            total_diem=api_key_usage.usage.diem,
            total_usd=api_key_usage.usage.usd,
            daily_average_usd=daily_average,
            monthly_projection_usd=monthly_projection,
            usage_trend=usage_trend,
            risk_level=risk_level,
            recommendations=recommendations,
            created_at=api_key_usage.created_at,
            last_used_at=api_key_usage.last_used_at
        )
    
    def _calculate_daily_average(self, key_id: str) -> float:
        """Calculate daily average usage for a key"""
        if key_id not in self.historical_data or len(self.historical_data[key_id]) < 2:
            # Use 7-day data as estimate
            recent_snapshots = self.historical_data.get(key_id, [])
            if recent_snapshots:
                return recent_snapshots[-1].get("usd", 0) / 7
            return 0.0
        
        # Calculate based on historical data
        snapshots = self.historical_data[key_id]
        if len(snapshots) < 2:
            return 0.0
        
        # Get daily differences
        daily_usage = []
        for i in range(1, len(snapshots)):
            prev_usage = snapshots[i-1]["usd"]
            current_usage = snapshots[i]["usd"]
            
            # Calculate time difference
            prev_time = datetime.fromisoformat(snapshots[i-1]["timestamp"])
            current_time = datetime.fromisoformat(snapshots[i]["timestamp"])
            days_diff = (current_time - prev_time).total_seconds() / 86400  # seconds to days
            
            if days_diff > 0:
                usage_diff = current_usage - prev_usage
                if usage_diff >= 0:  # Only count positive changes (actual usage)
                    daily_usage.append(usage_diff / days_diff)
        
        return sum(daily_usage) / len(daily_usage) if daily_usage else 0.0
    
    def _analyze_usage_trend(self, key_id: str) -> str:
        """Analyze usage trend over time"""
        if key_id not in self.historical_data or len(self.historical_data[key_id]) < 3:
            return "stable"
        
        snapshots = self.historical_data[key_id][-7:]  # Last 7 snapshots
        if len(snapshots) < 3:
            return "stable"
        
        # Calculate trend over recent snapshots
        usage_values = [s["usd"] for s in snapshots]
        
        # Simple linear trend analysis
        n = len(usage_values)
        x_mean = (n - 1) / 2
        y_mean = sum(usage_values) / n
        
        numerator = sum((i - x_mean) * (usage_values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return "stable"
        
        slope = numerator / denominator
        
        # Classify trend
        if slope > 0.1:
            return "increasing"
        elif slope < -0.1:
            return "decreasing"
        else:
            return "stable"
    
    def _assess_risk_level(self, current_usage: float, daily_average: float) -> str:
        """Assess risk level based on usage patterns"""
        monthly_projection = daily_average * 30.44
        
        if monthly_projection == 0:
            return "low"
        elif monthly_projection < 5:
            return "low"
        elif monthly_projection < 25:
            return "medium"
        else:
            return "high"
    
    def _generate_recommendations(self, api_key_usage: APIKeyUsage, risk_level: str, 
                                usage_trend: str) -> List[str]:
        """Generate recommendations based on usage patterns"""
        recommendations = []
        
        # Usage-based recommendations
        if api_key_usage.usage.usd == 0:
            recommendations.append("No recent usage detected - consider removing if no longer needed")
            recommendations.append("Verify key is correctly implemented in your applications")
        elif api_key_usage.usage.usd < 1:
            recommendations.append("Low usage pattern - suitable for testing and development")
        elif api_key_usage.usage.usd < 10:
            recommendations.append("Moderate usage - typical for active development")
        else:
            recommendations.append("High usage detected - monitor closely")
        
        # Trend-based recommendations
        if usage_trend == "increasing":
            recommendations.append("Usage is trending upward - review your application's API call patterns")
            recommendations.append("Consider implementing request caching to reduce costs")
        elif usage_trend == "decreasing":
            recommendations.append("Usage is trending downward - good cost optimization")
        
        # Security recommendations
        if api_key_usage.last_used_at:
            try:
                last_used = datetime.fromisoformat(api_key_usage.last_used_at.replace('Z', '+00:00'))
                days_since_use = (datetime.now(last_used.tzinfo) - last_used).days
                
                if days_since_use > 30:
                    recommendations.append("Key hasn't been used in over 30 days - consider revoking")
                elif days_since_use > 7:
                    recommendations.append("Key usage has been inactive recently - verify applications")
            except:
                pass
        else:
            recommendations.append("No usage history available - verify key is active")
        
        # Risk-based recommendations
        if risk_level == "high":
            recommendations.append("High-risk usage pattern - implement strict monitoring")
            recommendations.append("Consider splitting workload across multiple keys")
        
        return recommendations
    
    def get_key_history(self, key_id: str) -> List[Dict[str, Any]]:
        """Get historical usage data for a specific key"""
        return self.historical_data.get(key_id, [])
    
    def export_report(self, report: UsageReport) -> str:
        """Export report as formatted text"""
        trend_emoji = {"increasing": "↗️", "decreasing": "↘️", "stable": "➡️"}
        risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}
        
        export_text = f"""
VENICE AI API KEY USAGE REPORT
===============================

Key Information:
  Name: {report.key_name}
  ID: {report.key_id}
  Created: {report.created_at}
  Last Used: {report.last_used_at or "Never"}

Current Usage (7-day trailing):
  DIEM: {report.total_diem:.4f}
  USD: ${report.total_usd:.2f}

Usage Analytics:
  Daily Average: ${report.daily_average_usd:.2f}
  Monthly Projection: ${report.monthly_projection_usd:.2f}
  Usage Trend: {trend_emoji.get(report.usage_trend, '')} {report.usage_trend.title()}
  Risk Level: {risk_emoji.get(report.risk_level, '')} {report.risk_level.title()}

Recommendations:
"""
        
        for i, rec in enumerate(report.recommendations, 1):
            export_text += f"  {i}. {rec}\n"
        
        export_text += f"\nReport generated: {datetime.now().isoformat()}\n"
        
        return export_text


# Global instance for use across the application
usage_report_generator = UsageReportGenerator()