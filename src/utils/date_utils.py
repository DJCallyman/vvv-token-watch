"""
Date formatting utilities for human-friendly date display.

This module provides functions to convert ISO timestamps and datetime objects
into more readable, human-friendly formats using relative time descriptions.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Union, Dict
import re
import logging

logger = logging.getLogger(__name__)


class DateFormatter:
    """Utility class for formatting dates in human-friendly formats."""
    
    @staticmethod
    def _get_now() -> datetime:
        """
        Get current UTC time as timezone-aware datetime.
        
        Returns:
            Timezone-aware datetime in UTC
        """
        return datetime.now(timezone.utc)
    
    @staticmethod
    def _make_aware(dt: datetime) -> datetime:
        """
        Ensure datetime is timezone-aware.
        
        Args:
            dt: Datetime object (may be naive or aware)
            
        Returns:
            Timezone-aware datetime in UTC
        """
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    
    @staticmethod
    def create_date_range(days: int = 7, end_date: Optional[datetime] = None) -> Dict[str, str]:
        """
        Create API-compatible date range parameters for Venice API.
        
        Args:
            days: Number of days to include in the range (default 7)
            end_date: Optional end date (defaults to current UTC time)
            
        Returns:
            Dictionary with 'startDate' and 'endDate' in ISO 8601 format
            Example: {"startDate": "2025-10-26T00:00:00Z", "endDate": "2025-11-02T23:59:59Z"}
        """
        if end_date is None:
            end_date = DateFormatter._get_now()
        else:
            end_date = DateFormatter._make_aware(end_date)
        
        start_date = end_date - timedelta(days=days)
        
        return {
            "startDate": start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "endDate": end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
    
    @staticmethod
    def create_daily_date_range(target_date: Optional[str] = None) -> Dict[str, str]:
        """
        Create API-compatible date range for a single day.
        
        Args:
            target_date: Date in 'YYYY-MM-DD' format. If None, uses today's date in UTC.
            
        Returns:
            Dictionary with 'startDate' and 'endDate' covering the full day
            Example: {"startDate": "2025-11-02T00:00:00Z", "endDate": "2025-11-02T23:59:59Z"}
        """
        if target_date is None:
            today = DateFormatter._get_now().date()
            target_date = today.isoformat()
        
        return {
            "startDate": f"{target_date}T00:00:00Z",
            "endDate": f"{target_date}T23:59:59Z"
        }
    
    @staticmethod
    def format_iso_timestamp(dt: Optional[datetime] = None) -> str:
        """
        Format datetime as ISO 8601 timestamp for API requests.
        
        Args:
            dt: Datetime object (defaults to current UTC time)
            
        Returns:
            ISO 8601 formatted timestamp string
        """
        if dt is None:
            dt = DateFormatter._get_now()
        else:
            dt = DateFormatter._make_aware(dt)
        
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    @staticmethod
    def human_friendly(iso_timestamp: Union[str, datetime], context: str = "Created") -> str:
        """
        Convert ISO timestamp or datetime to human-friendly format.
        
        Args:
            iso_timestamp: ISO timestamp string or datetime object
            context: Context prefix for the message (e.g., "Created", "Last used")
            
        Returns:
            Human-friendly date string like "Created 18 days ago" or "Sept 20, 2025"
            
        Examples:
            - "Created 18 days ago"
            - "Last used 2 hours ago" 
            - "Sept 20, 2025"
        """
        try:
            if isinstance(iso_timestamp, str):
                timestamp = DateFormatter._parse_iso_timestamp(iso_timestamp)
            elif isinstance(iso_timestamp, datetime):
                timestamp = DateFormatter._make_aware(iso_timestamp)
            else:
                return f"{context} at unknown time"
            
            now = DateFormatter._get_now()
            diff = now - timestamp
            
            if diff.total_seconds() < 60:
                return f"{context} just now"
            
            if diff.days == 0:
                return f"{context} {DateFormatter.relative_time(iso_timestamp)}"
            
            if diff.days < 7:
                if diff.days == 1:
                    return f"{context} yesterday"
                else:
                    return f"{context} {diff.days} days ago"
            
            if timestamp.year == now.year:
                return f"{context} on {timestamp.strftime('%b %d')}"
            
            return f"{context} on {timestamp.strftime('%b %d, %Y')}"
            
        except Exception as e:
            logger.warning(f"Error formatting date: {e}")
            return f"{context} at unknown time"
    
    @staticmethod
    def relative_time(iso_timestamp: Union[str, datetime]) -> str:
        """
        Get relative time description from timestamp.
        
        Args:
            iso_timestamp: ISO timestamp string or datetime object
            
        Returns:
            Relative time string like "2 minutes ago", "yesterday", "last week"
        """
        try:
            if isinstance(iso_timestamp, str):
                timestamp = DateFormatter._parse_iso_timestamp(iso_timestamp)
            elif isinstance(iso_timestamp, datetime):
                timestamp = DateFormatter._make_aware(iso_timestamp)
            else:
                return "unknown time ago"
            
            now = DateFormatter._get_now()
            diff = now - timestamp
            
            if diff.total_seconds() < 0:
                return "in the future"
            
            seconds = int(diff.total_seconds())
            
            if seconds < 60:
                return "just now"
            
            minutes = seconds // 60
            if minutes < 60:
                if minutes == 1:
                    return "1 minute ago"
                return f"{minutes} minutes ago"
            
            hours = minutes // 60
            if hours < 24:
                if hours == 1:
                    return "1 hour ago"
                return f"{hours} hours ago"
            
            days = diff.days
            if days < 7:
                if days == 1:
                    return "yesterday"
                return f"{days} days ago"
            
            weeks = days // 7
            if weeks < 4:
                if weeks == 1:
                    return "last week"
                return f"{weeks} weeks ago"
            
            months = days // 30
            if months < 12:
                if months == 1:
                    return "last month"
                return f"{months} months ago"
            
            years = days // 365
            if years == 1:
                return "last year"
            return f"{years} years ago"
            
        except Exception as e:
            logger.warning(f"Error calculating relative time: {e}")
            return "unknown time ago"
    
    @staticmethod
    def _parse_iso_timestamp(iso_string: str) -> datetime:
        """
        Parse various ISO timestamp formats into timezone-aware datetime object.
        
        Args:
            iso_string: ISO timestamp string
            
        Returns:
            Timezone-aware datetime object
            
        Raises:
            ValueError: If timestamp format is not recognized
        """
        iso_string = iso_string.strip()
        
        formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(iso_string, fmt)
                return DateFormatter._make_aware(dt)
            except ValueError:
                continue
        
        if '+' in iso_string or iso_string.endswith(('Z',)):
            clean_string = re.sub(r'[+-]\d{2}:?\d{2}$|Z$', '', iso_string)
            for fmt in formats:
                try:
                    dt = datetime.strptime(clean_string, fmt)
                    return DateFormatter._make_aware(dt)
                except ValueError:
                    continue
        
        raise ValueError(f"Unrecognized timestamp format: {iso_string}")
    
    @staticmethod
    def format_for_display(timestamp: Union[str, datetime], 
                          context: str = "", 
                          show_time: bool = False) -> str:
        """
        Format timestamp for display in UI components.
        
        Args:
            timestamp: ISO timestamp string or datetime object
            context: Optional context prefix
            show_time: Whether to include time in the display
            
        Returns:
            Formatted string suitable for UI display
        """
        try:
            if isinstance(timestamp, str):
                dt = DateFormatter._parse_iso_timestamp(timestamp)
            elif isinstance(timestamp, datetime):
                dt = DateFormatter._make_aware(timestamp)
            else:
                return "Unknown date"
            
            now = DateFormatter._get_now()
            diff = now - dt
            
            if diff.total_seconds() < 3600:
                relative = DateFormatter.relative_time(timestamp)
                return f"{context} {relative}" if context else relative
            
            if diff.days == 0 and show_time:
                time_str = dt.strftime('%I:%M %p').lstrip('0')
                return f"{context} today at {time_str}" if context else f"Today at {time_str}"
            
            if diff.days < 7:
                day_name = dt.strftime('%A')
                if show_time:
                    time_str = dt.strftime('%I:%M %p').lstrip('0')
                    result = f"{day_name} at {time_str}"
                else:
                    result = day_name
                return f"{context} {result}" if context else result
            
            if dt.year == now.year:
                date_str = dt.strftime('%b %d')
                if show_time:
                    time_str = dt.strftime('%I:%M %p').lstrip('0')
                    result = f"{date_str} at {time_str}"
                else:
                    result = date_str
                return f"{context} {result}" if context else result
            
            date_str = dt.strftime('%b %d, %Y')
            if show_time:
                time_str = dt.strftime('%I:%M %p').lstrip('0')
                result = f"{date_str} at {time_str}"
            else:
                result = date_str
            return f"{context} {result}" if context else result
            
        except Exception as e:
            logger.warning(f"Error formatting timestamp for display: {e}")
            return f"{context} Unknown date" if context else "Unknown date"


# Convenience functions for common use cases
def format_creation_date(iso_timestamp: Union[str, datetime]) -> str:
    """Format creation date with 'Created' context."""
    return DateFormatter.human_friendly(iso_timestamp, "Created")

def format_last_used(iso_timestamp: Union[str, datetime]) -> str:
    """Format last used date with 'Last used' context."""
    return DateFormatter.human_friendly(iso_timestamp, "Last used")

def format_updated_date(iso_timestamp: Union[str, datetime]) -> str:
    """Format update date with 'Updated' context."""
    return DateFormatter.human_friendly(iso_timestamp, "Updated")

def get_relative_time(iso_timestamp: Union[str, datetime]) -> str:
    """Get relative time description."""
    return DateFormatter.relative_time(iso_timestamp)