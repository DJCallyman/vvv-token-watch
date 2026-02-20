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
