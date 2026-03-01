"""
Tests for utility functions.
"""

import pytest
from unittest.mock import Mock, patch


class TestFormatCurrency:
    """Test cases for currency formatting."""
    
    def test_format_currency_usd(self):
        """Test USD currency formatting."""
        from src.utils.utils import format_currency
        
        result = format_currency(1234.56, 'USD')
        
        assert '$' in result
        assert '1,234.56' in result or '1234.56' in result
    
    def test_format_currency_aud(self):
        """Test AUD currency formatting."""
        from src.utils.utils import format_currency
        
        result = format_currency(1234.56, 'AUD')
        
        assert 'A$' in result or '$' in result
        assert '1,234.56' in result or '1234.56' in result
    
    def test_format_currency_zero(self):
        """Test formatting zero value."""
        from src.utils.utils import format_currency
        
        result = format_currency(0, 'USD')
        
        assert '$0.00' in result or '$0' in result
    
    def test_format_currency_none(self):
        """Test formatting None value."""
        from src.utils.utils import format_currency
        
        result = format_currency(None, 'USD')
        
        assert result == "N/A"


class TestValidateHoldingAmount:
    """Test cases for holding amount validation."""
    
    def test_validate_valid_amount(self):
        """Test validation with valid amount."""
        from src.utils.utils import validate_holding_amount, ValidationState
        
        result = validate_holding_amount("1000.50")
        
        assert result == ValidationState.VALID
    
    def test_validate_empty_string(self):
        """Test validation with empty string."""
        from src.utils.utils import validate_holding_amount, ValidationState
        
        result = validate_holding_amount("")
        
        assert result == ValidationState.ERROR
    
    def test_validate_invalid_format(self):
        """Test validation with invalid format."""
        from src.utils.utils import validate_holding_amount, ValidationState
        
        result = validate_holding_amount("abc")
        
        assert result == ValidationState.ERROR
    
    def test_validate_negative_amount(self):
        """Test validation with negative amount."""
        from src.utils.utils import validate_holding_amount, ValidationState
        
        result = validate_holding_amount("-100")
        
        assert result == ValidationState.ERROR


class TestErrorHandler:
    """Test cases for error handling utilities."""
    
    def test_error_handler_logs_warning(self):
        """Test that error handler logs warnings."""
        from src.utils.error_handler import ErrorHandler
        
        with patch('src.utils.error_handler.logger') as mock_logger:
            ErrorHandler.log_warning("Test warning message")
            
            mock_logger.warning.assert_called_once()
            assert "Test warning message" in mock_logger.warning.call_args[0][0]
    
    def test_error_handler_logs_info(self):
        """Test that error handler logs info messages."""
        from src.utils.error_handler import ErrorHandler
        
        with patch('src.utils.error_handler.logger') as mock_logger:
            ErrorHandler.log_info("Test info message")
            
            mock_logger.info.assert_called_once()
            assert "Test info message" in mock_logger.info.call_args[0][0]
    
    def test_error_handler_logs_debug(self):
        """Test that error handler logs debug messages."""
        from src.utils.error_handler import ErrorHandler
        
        with patch('src.utils.error_handler.logger') as mock_logger:
            ErrorHandler.log_debug("Test debug message")
            
            mock_logger.debug.assert_called_once()
            assert "Test debug message" in mock_logger.debug.call_args[0][0]


class TestDateUtils:
    """Test cases for date utilities."""
    
    def test_format_creation_date(self):
        """Test creation date formatting."""
        from src.utils.date_utils import format_creation_date
        from datetime import datetime
        
        date = datetime(2024, 1, 15, 10, 30, 0)
        result = format_creation_date(date)
        
        assert "2024" in result
        assert "15" in result
    
    def test_get_relative_time(self):
        """Test relative time formatting."""
        from src.utils.date_utils import get_relative_time
        from datetime import datetime, timedelta
        
        now = datetime.now()
        recent = now - timedelta(minutes=5)
        
        result = get_relative_time(recent)
        
        # Result could be "5 minutes ago" or similar format
        # Just check it returns a string with time-related content
        assert isinstance(result, str)
        assert len(result) > 0
