"""
Tests for /api/models and /api/models/{model_id} endpoints.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


def _make_mock_response(payload: dict) -> MagicMock:
    mock = MagicMock()
    mock.json.return_value = payload
    mock.status_code = 200
    return mock


@pytest.fixture
def client(sample_models_response):
    """TestClient with settings and Venice client overridden."""
    with patch("backend.main.init_db", new_callable=AsyncMock):
        from backend.main import app
        from backend.config import get_settings, Settings
        from backend.api.routes import models as models_module

        def override_settings():
            return Settings(
                VENICE_ADMIN_KEY="test_admin_key_12345",
                DATABASE_URL="postgresql://test:test@localhost:5432/test_db",
            )

        mock_client = MagicMock()
        mock_client.api_key = "test_admin_key_12345"
        mock_client.get.return_value = _make_mock_response(sample_models_response)

        def override_venice_client(settings=None):
            return mock_client

        app.dependency_overrides[get_settings] = override_settings
        app.dependency_overrides[models_module.get_venice_client] = override_venice_client

        yield TestClient(app), mock_client, sample_models_response

        app.dependency_overrides.clear()


class TestModelsListEndpoint:
    """Tests for GET /api/models"""

    def test_models_returns_200(self, client):
        tc, mock_client, models_data = client
        response = tc.get("/api/models")
        assert response.status_code == 200

    def test_models_returns_model_list(self, client):
        tc, mock_client, models_data = client
        response = tc.get("/api/models")
        body = response.json()
        assert "models" in body
        assert isinstance(body["models"], list)

    def test_models_returns_correct_count(self, client):
        tc, mock_client, models_data = client
        response = tc.get("/api/models")
        body = response.json()
        assert body["count"] == len(models_data["data"])

    def test_models_returns_types_set(self, client):
        tc, mock_client, models_data = client
        response = tc.get("/api/models")
        body = response.json()
        assert "types" in body
        assert isinstance(body["types"], list)
        # Both "text" and "image" types should be present
        assert "text" in body["types"]
        assert "image" in body["types"]

    def test_models_data_matches_api_response(self, client):
        tc, mock_client, models_data = client
        response = tc.get("/api/models")
        body = response.json()
        model_ids = [m["id"] for m in body["models"]]
        assert "llama-3.3-70b" in model_ids
        assert "stable-diffusion-3.5" in model_ids

    def test_models_propagates_exception_as_500(self):
        with patch("backend.main.init_db", new_callable=AsyncMock):
            from backend.main import app
            from backend.config import get_settings, Settings
            from backend.api.routes import models as models_module

            def override_settings():
                return Settings(
                    VENICE_ADMIN_KEY="test_admin_key_12345",
                    DATABASE_URL="postgresql://test:test@localhost:5432/test_db",
                )

            failing_client = MagicMock()
            failing_client.api_key = "test_admin_key_12345"
            failing_client.get.side_effect = Exception("Venice unreachable")

            def override_venice_client(settings=None):
                return failing_client

            app.dependency_overrides[get_settings] = override_settings
            app.dependency_overrides[models_module.get_venice_client] = override_venice_client

            tc = TestClient(app, raise_server_exceptions=False)
            response = tc.get("/api/models")
            app.dependency_overrides.clear()

        assert response.status_code == 500
        assert "Venice unreachable" in response.json()["detail"]


class TestModelDetailEndpoint:
    """Tests for GET /api/models/{model_id}"""

    def test_model_detail_returns_200_for_known_id(self, client):
        tc, mock_client, _ = client
        response = tc.get("/api/models/llama-3.3-70b")
        assert response.status_code == 200

    def test_model_detail_returns_correct_model(self, client):
        tc, mock_client, _ = client
        response = tc.get("/api/models/llama-3.3-70b")
        data = response.json()
        assert data["id"] == "llama-3.3-70b"
        assert data["type"] == "text"

    def test_model_detail_returns_404_for_unknown_id(self, client):
        tc, mock_client, _ = client
        response = tc.get("/api/models/nonexistent-model-xyz")
        assert response.status_code == 404

    def test_model_detail_404_message(self, client):
        tc, mock_client, _ = client
        response = tc.get("/api/models/nonexistent-model-xyz")
        detail = response.json()["detail"]
        assert "nonexistent-model-xyz" in detail

    def test_model_detail_image_model(self, client):
        tc, mock_client, _ = client
        response = tc.get("/api/models/stable-diffusion-3.5")
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "image"
