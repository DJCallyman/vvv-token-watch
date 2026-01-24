"""
Utility functions for the vvv_token_watch application.

This module contains small helper functions for currency formatting,
input validation, and other common utilities.
"""

from enum import Enum

from src.config.config import Config


# Currency formatting utilities
def format_currency(value, currency):
    """Format a numeric value as a currency string with appropriate symbol and decimal places."""
    if value is None:
        return "N/A"
    
    if currency.lower() == 'usd':
        return f"${value:,.2f}"
    elif currency.lower() == 'aud':
        return f"A${value:,.2f}"
    else:
        # Fallback for other currencies
        return f"{currency.upper()} {value:,.2f}"


# Validation utilities
class ValidationState(Enum):
    VALID = "valid"
    WARNING = "warning"
    ERROR = "error"


def validate_holding_amount(value: str) -> ValidationState:
    """
    Validates holding amount input with real-time feedback.
    
    Returns:
    - VALID: Valid positive number
    - WARNING: Value is positive but below minimum threshold (0.01)
    - ERROR: Empty, non-numeric, or negative value
    """
    if not value.strip():
        return ValidationState.ERROR
    
    try:
        amount = float(value)
        if amount <= 0:
            return ValidationState.ERROR
        elif amount < Config.MIN_HOLDING_THRESHOLD:
            return ValidationState.WARNING
        return ValidationState.VALID
    except ValueError:
        return ValidationState.ERROR
