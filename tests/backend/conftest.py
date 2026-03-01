"""
Shared fixtures for backend API tests.
Sets environment variables and mocks before any backend modules are imported.
"""

import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

# Ensure project root is on path for `backend.*` imports
ROOT = str(Path(__file__).parent.parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Set required environment variables BEFORE any backend module is imported.
# pydantic-settings reads these at Settings() construction time.
os.environ.setdefault("VENICE_ADMIN_KEY", "test_admin_key_12345")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test_db")
os.environ.setdefault("COINGECKO_TOKEN_ID", "venice-token")
os.environ.setdefault("LOG_LEVEL", "WARNING")


def make_settings():
    """Return a minimal Settings instance without needing a real .env file."""
    from backend.config import Settings
    from pydantic_settings import BaseSettings

    class TestSettings(Settings):
        class Config:
            env_file = None  # Don't read .env during tests

    return TestSettings(
        VENICE_ADMIN_KEY="test_admin_key_12345",
        DATABASE_URL="postgresql://test:test@localhost:5432/test_db",
    )


@pytest.fixture(scope="session")
def test_settings():
    """Provide test settings instance."""
    return make_settings()


@pytest.fixture
def mock_venice_client():
    """Return a mock VeniceAPIClient."""
    client = MagicMock()
    client.api_key = "test_admin_key_12345"
    return client


@pytest.fixture
def sample_billing_response():
    """Typical /billing/usage API response."""
    return {
        "data": [
            {
                "id": "record_001",
                "apiKeyId": "key_abc",
                "model": "llama-3.3-70b",
                "inputTokens": 1000,
                "outputTokens": 500,
                "totalCost": 0.0015,
                "timestamp": "2026-03-01T10:00:00Z",
            }
        ],
        "pagination": {"total": 1, "page": 1, "pageSize": 100},
    }


@pytest.fixture
def sample_rate_limits_response():
    """Typical /api_keys/rate_limits API response."""
    return {
        "data": {
            "balances": {"DIEM": "45.5", "USD": "11.25"},
            "nextEpochBegins": "2026-03-02T00:00:00Z",
        }
    }


@pytest.fixture
def sample_api_keys_response():
    """Typical /api_keys API response."""
    return {
        "data": [
            {
                "id": "key_abc",
                "name": "Main Key",
                "createdAt": "2026-01-01T00:00:00Z",
                "isActive": True,
            },
            {
                "id": "key_def",
                "name": "Dev Key",
                "createdAt": "2026-01-15T00:00:00Z",
                "isActive": False,
            },
        ]
    }


@pytest.fixture
def sample_models_response():
    """Typical /models API response."""
    return {
        "data": [
            {
                "id": "llama-3.3-70b",
                "type": "text",
                "model_spec": {
                    "availableContextTokens": 131072,
                    "capabilities": {"vision": False, "function_calling": True},
                    "traits": ["reasoning", "fast"],
                },
            },
            {
                "id": "stable-diffusion-3.5",
                "type": "image",
                "model_spec": {
                    "capabilities": {},
                    "traits": ["photorealistic"],
                },
            },
        ]
    }
