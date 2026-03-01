"""
Tests for the /api/health endpoint.
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client with mocked database init."""
    with patch("backend.main.init_db", new_callable=AsyncMock):
        from backend.main import app
        from backend.config import get_settings, Settings

        def override_settings():
            return Settings(
                VENICE_ADMIN_KEY="test_admin_key_12345",
                DATABASE_URL="postgresql://test:test@localhost:5432/test_db",
            )

        app.dependency_overrides[get_settings] = override_settings
        yield TestClient(app, raise_server_exceptions=True)
        app.dependency_overrides.clear()


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_returns_200(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_returns_healthy_status(self, client):
        response = client.get("/api/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_returns_service_name(self, client):
        response = client.get("/api/health")
        data = response.json()
        assert data["service"] == "vvv-token-watch-api"

    def test_health_returns_timestamp(self, client):
        response = client.get("/api/health")
        data = response.json()
        assert "timestamp" in data
        assert data["timestamp"]  # non-empty

    def test_root_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_returns_api_info(self, client):
        response = client.get("/")
        data = response.json()
        assert data["name"] == "VVV Token Watch API"
        assert data["version"] == "1.0.0"
        assert "docs" in data
