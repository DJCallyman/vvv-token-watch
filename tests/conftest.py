"""
Test configuration and shared fixtures for VVV Token Watch test suite.
"""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def mock_config():
    """Create a mock configuration object."""
    config = Mock()
    config.VENICE_ADMIN_KEY = "test_admin_key"
    config.VENICE_API_KEY = "test_api_key"
    config.COINGECKO_TOKEN_ID = "venice-token"
    config.COINGECKO_HOLDING_AMOUNT = 1000.0
    config.DIEM_HOLDING_AMOUNT = 100.0
    config.THEME_MODE = "dark"
    config.LOG_LEVEL = 'INFO'
    config.USAGE_REFRESH_INTERVAL_MS = 30000
    config.COINGECKO_REFRESH_INTERVAL_MS = 60000
    config.MINIMIZE_TO_TRAY = True
    return config


@pytest.fixture
def sample_models_data():
    """Provide sample model data for testing."""
    return {
        "data": [
            {
                "id": "llama-3.3-70b",
                "type": "text",
                "model_spec": {
                    "availableContextTokens": 131072,
                    "capabilities": {
                        "vision": False,
                        "function_calling": True
                    },
                    "constraints": {
                        "max_tokens": 8192
                    },
                    "traits": ["reasoning", "fast"]
                }
            },
            {
                "id": "stable-diffusion-3.5",
                "type": "image",
                "model_spec": {
                    "constraints": {
                        "aspect_ratios": ["1:1", "16:9"]
                    },
                    "traits": ["photorealistic"]
                }
            },
            {
                "id": "tts-1",
                "type": "audio",
                "model_spec": {
                    "constraints": {
                        "voices": ["alloy", "echo"]
                    },
                    "traits": ["natural"]
                }
            }
        ]
    }


@pytest.fixture
def sample_usage_data():
    """Provide sample API usage data for testing."""
    return [
        {
            "key_id": "key_1",
            "name": "Test Key 1",
            "usage": {
                "usd": 10.50,
                "diem": 100.0
            },
            "limits": {
                "daily": 1000.0
            }
        },
        {
            "key_id": "key_2", 
            "name": "Test Key 2",
            "usage": {
                "usd": 5.25,
                "diem": 50.0
            },
            "limits": {
                "daily": 500.0
            }
        }
    ]


@pytest.fixture
def sample_price_data():
    """Provide sample price data for testing."""
    return {
        "venice-token": {
            "usd": 2.50,
            "aud": 3.75,
            "usd_24h_change": 5.5
        }
    }


@pytest.fixture
def mock_qt_app():
    """Create a mock QApplication for testing."""
    app = MagicMock()
    app.exec_ = Mock()
    app.quit = Mock()
    return app


@pytest.fixture
def mock_qt_widget():
    """Create a mock QWidget for testing."""
    widget = MagicMock()
    widget.show = Mock()
    widget.hide = Mock()
    widget.close = Mock()
    return widget


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def mock_venice_api_response():
    """Provide mock Venice API response structure."""
    return {
        "success": True,
        "data": {
            "models": [],
            "api_keys": [],
            "usage": {}
        }
    }


@pytest.fixture
def mock_requests_session():
    """Create a mock requests session."""
    session = Mock()
    session.get = Mock()
    session.post = Mock()
    return session


@pytest.fixture
def mock_api_client():
    """Create a mock VeniceAPIClient for testing."""
    from unittest.mock import MagicMock
    client = MagicMock()
    client.api_key = "test_api_key"
    client.base_url = "https://api.venice.ai/api/v1"
    client.get = MagicMock(return_value=MagicMock(status_code=200, json=lambda: {"data": []}))
    client.post = MagicMock(return_value=MagicMock(status_code=200, json=lambda: {"success": True}))
    return client


@pytest.fixture
def mock_balance_info():
    """Create a mock BalanceInfo for testing."""
    from src.core.usage_tracker import BalanceInfo
    return BalanceInfo(
        diem=1000.0,
        usd=50.0,
        updated_at="2024-01-01T00:00:00Z"
    )


@pytest.fixture
def mock_api_key_usage():
    """Create a mock APIKeyUsage for testing."""
    from src.core.usage_tracker import APIKeyUsage, UsageMetrics
    return APIKeyUsage(
        id="key_test123",
        name="Test API Key",
        is_active=True,
        created_at="2024-01-01T00:00:00Z",
        last_used_at="2024-01-15T12:00:00Z",
        usage=UsageMetrics(diem=10.0, usd=1.5)
    )


@pytest.fixture
def mock_cached_model():
    """Create a mock CachedModel for testing."""
    from src.core.model_cache import CachedModel
    return CachedModel(
        id="test-model",
        name="Test Model",
        model_type="text",
        input_price_usd=0.60,
        output_price_usd=6.00,
        cache_input_price_usd=0.06,
        cache_write_price_usd=0.75,
        supports_cache=True,
        capabilities=["vision", "function_calling"]
    )


@pytest.fixture
def mock_exchange_rate_data():
    """Create mock exchange rate data for testing."""
    from src.services.exchange_rate_service import ExchangeRateData
    from datetime import datetime
    return ExchangeRateData(
        rate=0.05,
        timestamp=datetime.now(),
        change_24h=2.5,
        volume_24h=100000.0,
        source="test",
        confidence=0.9
    )


@pytest.fixture
def qt_app():
    """Qt application fixture for widget tests."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def sample_billing_records():
    """Provide sample billing records for cache analytics testing."""
    return [
        {
            "sku": "llama-llm-input-mtoken",
            "amount": -0.0006,
            "currency": "USD",
            "pricePerUnitUsd": 0.60,
            "units": 0.001,
            "timestamp": "2024-01-15T10:00:00Z",
            "inferenceDetails": {
                "requestId": "req-1",
                "promptTokens": 500,
                "completionTokens": 100
            }
        },
        {
            "sku": "llama-llm-cache-input-mtoken",
            "amount": -0.00006,
            "currency": "USD",
            "pricePerUnitUsd": 0.06,
            "units": 0.001,
            "timestamp": "2024-01-15T10:00:00Z",
            "inferenceDetails": {
                "requestId": "req-1",
                "promptTokens": 500,
                "completionTokens": 100
            }
        },
        {
            "sku": "llama-llm-output-mtoken",
            "amount": -0.0006,
            "currency": "USD",
            "pricePerUnitUsd": 6.00,
            "units": 0.0001,
            "timestamp": "2024-01-15T10:00:00Z",
            "inferenceDetails": {
                "requestId": "req-1",
                "promptTokens": 500,
                "completionTokens": 100
            }
        },
        {
            "sku": "deepseek-llm-input-mtoken",
            "amount": -0.0003,
            "currency": "USD",
            "pricePerUnitUsd": 0.30,
            "units": 0.001,
            "timestamp": "2024-01-15T11:00:00Z",
            "inferenceDetails": {
                "requestId": "req-2",
                "promptTokens": 800,
                "completionTokens": 200
            }
        },
        {
            "sku": "deepseek-llm-output-mtoken",
            "amount": -0.0005,
            "currency": "USD",
            "pricePerUnitUsd": 0.50,
            "units": 0.001,
            "timestamp": "2024-01-15T11:00:00Z",
            "inferenceDetails": {
                "requestId": "req-2",
                "promptTokens": 800,
                "completionTokens": 200
            }
        }
    ]
