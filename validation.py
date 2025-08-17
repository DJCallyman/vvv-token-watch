from enum import Enum

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
        elif amount < 0.01:
            return ValidationState.WARNING
        return ValidationState.VALID
    except ValueError:
        return ValidationState.ERROR
