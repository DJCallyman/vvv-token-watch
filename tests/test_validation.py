import pytest
from vvv_token_watch.validation import validate_holding_amount, ValidationState

def test_validate_holding_amount_valid():
    """Test valid holding amounts"""
    assert validate_holding_amount("100") == ValidationState.VALID
    assert validate_holding_amount("0.01") == ValidationState.VALID
    assert validate_holding_amount("1.5") == ValidationState.VALID

def test_validate_holding_amount_warning():
    """Test holding amounts that trigger warning state"""
    assert validate_holding_amount("0.009") == ValidationState.WARNING
    assert validate_holding_amount("0.005") == ValidationState.WARNING

def test_validate_holding_amount_error():
    """Test invalid holding amounts"""
    assert validate_holding_amount("") == ValidationState.ERROR
    assert validate_holding_amount("-1") == ValidationState.ERROR
    assert validate_holding_amount("abc") == ValidationState.ERROR
    assert validate_holding_amount("0") == ValidationState.ERROR
