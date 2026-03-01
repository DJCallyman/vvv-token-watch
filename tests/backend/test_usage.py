"""
Tests for /api/usage/* endpoints.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


def _make_mock_response(payload: dict) -> MagicMock:
    """Create a mock requests.Response returning the given payload."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = payload
    mock_resp.status_code = 200
    return mock_resp


@pytest.fixture
def client(sample_billing_response, sample_rate_limits_response, sample_api_keys_response):
    """TestClient with settings and Venice API overridden."""
    with patch("backend.main.init_db", new_callable=AsyncMock):
        from backend.main import app
        from backend.config import get_settings, Settings
        from backend.api.routes import usage as usage_module

        def override_settings():
            return Settings(
                VENICE_ADMIN_KEY="test_admin_key_12345",
                DATABASE_URL="postgresql://test:test@localhost:5432/test_db",
            )

        mock_client = MagicMock()
        mock_client.api_key = "test_admin_key_12345"
        mock_client.get.return_value = _make_mock_response(sample_billing_response)

        def override_venice_client(settings=None):
            return mock_client

        app.dependency_overrides[get_settings] = override_settings
        app.dependency_overrides[usage_module.get_venice_client] = override_venice_client

        yield TestClient(app), mock_client, sample_billing_response, sample_api_keys_response

        app.dependency_overrides.clear()


class TestDailyUsageEndpoint:
    """Tests for GET /api/usage/daily"""

    def test_daily_usage_returns_200_with_mocked_tracker(self):
        """Daily usage returns HTTP 200 when Venice API is mocked."""
        with patch("backend.main.init_db", new_callable=AsyncMock):
            from backend.main import app
            from backend.config import get_settings, Settings
            from backend.api.routes import usage as usage_module
            from backend.core.usage_tracker import UsageTracker

            def override_settings():
                return Settings(
                    VENICE_ADMIN_KEY="test_admin_key_12345",
                    DATABASE_URL="postgresql://test:test@localhost:5432/test_db",
                )

            mock_tracker = MagicMock(spec=UsageTracker)
            mock_tracker.get_daily_usage.return_value = {"diem": 12.5, "usd": 3.1}

            mock_client = MagicMock()
            mock_client.api_key = "test_admin_key_12345"

            def override_venice_client(settings=None):
                return mock_client

            app.dependency_overrides[get_settings] = override_settings
            app.dependency_overrides[usage_module.get_venice_client] = override_venice_client

            with patch("backend.api.routes.usage.UsageTracker", return_value=mock_tracker):
                tc = TestClient(app)
                response = tc.get("/api/usage/daily")

            app.dependency_overrides.clear()

        assert response.status_code == 200

    def test_daily_usage_response_shape(self):
        """Daily usage response contains expected keys."""
        with patch("backend.main.init_db", new_callable=AsyncMock):
            from backend.main import app
            from backend.config import get_settings, Settings
            from backend.api.routes import usage as usage_module
            from backend.core.usage_tracker import UsageTracker

            def override_settings():
                return Settings(
                    VENICE_ADMIN_KEY="test_admin_key_12345",
                    DATABASE_URL="postgresql://test:test@localhost:5432/test_db",
                )

            mock_tracker = MagicMock(spec=UsageTracker)
            mock_tracker.get_daily_usage.return_value = {"diem": 5.0, "usd": 1.25}

            mock_client = MagicMock()
            mock_client.api_key = "test_admin_key_12345"

            def override_venice_client(settings=None):
                return mock_client

            app.dependency_overrides[get_settings] = override_settings
            app.dependency_overrides[usage_module.get_venice_client] = override_venice_client

            with patch("backend.api.routes.usage.UsageTracker", return_value=mock_tracker):
                tc = TestClient(app)
                response = tc.get("/api/usage/daily")

            app.dependency_overrides.clear()

        data = response.json()
        assert "date" in data
        assert "diem" in data
        assert "usd" in data

    def test_daily_usage_accepts_target_date_param(self):
        """Daily usage accepts an optional target_date query parameter."""
        with patch("backend.main.init_db", new_callable=AsyncMock):
            from backend.main import app
            from backend.config import get_settings, Settings
            from backend.api.routes import usage as usage_module
            from backend.core.usage_tracker import UsageTracker

            def override_settings():
                return Settings(
                    VENICE_ADMIN_KEY="test_admin_key_12345",
                    DATABASE_URL="postgresql://test:test@localhost:5432/test_db",
                )

            mock_tracker = MagicMock(spec=UsageTracker)
            mock_tracker.get_daily_usage.return_value = {"diem": 0.0, "usd": 0.0}

            mock_client = MagicMock()
            mock_client.api_key = "test_admin_key_12345"

            def override_venice_client(settings=None):
                return mock_client

            app.dependency_overrides[get_settings] = override_settings
            app.dependency_overrides[usage_module.get_venice_client] = override_venice_client

            with patch("backend.api.routes.usage.UsageTracker", return_value=mock_tracker):
                tc = TestClient(app)
                response = tc.get("/api/usage/daily?target_date=2026-02-28")

            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["date"] == "2026-02-28"


class TestUsageHistoryEndpoint:
    """Tests for GET /api/usage/history"""

    def test_history_returns_200(self, client):
        """History endpoint returns HTTP 200."""
        tc, mock_client, billing_data, _ = client
        mock_client.get.return_value = _make_mock_response(billing_data)
        response = tc.get("/api/usage/history")
        assert response.status_code == 200

    def test_history_returns_data_and_pagination(self, client):
        """History response contains data and pagination keys."""
        tc, mock_client, billing_data, _ = client
        mock_client.get.return_value = _make_mock_response(billing_data)
        response = tc.get("/api/usage/history")
        body = response.json()
        assert "data" in body
        assert "pagination" in body

    def test_history_data_matches_api_response(self, client):
        """History data list matches what the Venice API returned."""
        tc, mock_client, billing_data, _ = client
        mock_client.get.return_value = _make_mock_response(billing_data)
        response = tc.get("/api/usage/history")
        body = response.json()
        assert len(body["data"]) == len(billing_data["data"])

    def test_history_respects_limit_param(self, client):
        """History passes limit parameter through to Venice API."""
        tc, mock_client, billing_data, _ = client
        mock_client.get.return_value = _make_mock_response(billing_data)
        tc.get("/api/usage/history?limit=50")
        call_kwargs = mock_client.get.call_args
        assert call_kwargs is not None

    def test_history_respects_start_date_param(self, client):
        """History passes start_date through."""
        tc, mock_client, billing_data, _ = client
        mock_client.get.return_value = _make_mock_response(billing_data)
        response = tc.get("/api/usage/history?start_date=2026-02-01")
        body = response.json()
        assert body.get("start_date") == "2026-02-01"

    def test_history_caps_limit_at_500(self, client):
        """History endpoint caps limit at 500 regardless of input."""
        tc, mock_client, billing_data, _ = client
        mock_client.get.return_value = _make_mock_response(billing_data)
        tc.get("/api/usage/history?limit=9999")
        call_kwargs = mock_client.get.call_args
        params = call_kwargs[1].get("params") or call_kwargs[0][1]
        assert params["limit"] <= 500


class TestApiKeysUsageEndpoint:
    """Tests for GET /api/usage/keys"""

    def test_keys_returns_200(self):
        """Keys endpoint returns HTTP 200."""
        with patch("backend.main.init_db", new_callable=AsyncMock):
            from backend.main import app
            from backend.config import get_settings, Settings
            from backend.api.routes import usage as usage_module
            from backend.core.usage_tracker import UsageTracker, APIKeyUsage, UsageMetrics

            def override_settings():
                return Settings(
                    VENICE_ADMIN_KEY="test_admin_key_12345",
                    DATABASE_URL="postgresql://test:test@localhost:5432/test_db",
                )

            mock_keys = [
                APIKeyUsage(
                    id="key_abc",
                    name="Main Key",
                    usage=UsageMetrics(diem=10.5, usd=2.6),
                    created_at="2026-01-01T00:00:00Z",
                    is_active=True,
                ),
                APIKeyUsage(
                    id="key_def",
                    name="Dev Key",
                    usage=UsageMetrics(diem=0.0, usd=0.0),
                    created_at="2026-01-15T00:00:00Z",
                    is_active=False,
                ),
            ]

            mock_tracker = MagicMock(spec=UsageTracker)
            mock_tracker.fetch_api_keys_with_daily_usage.return_value = mock_keys

            mock_client = MagicMock()
            mock_client.api_key = "test_admin_key_12345"

            def override_venice_client(settings=None):
                return mock_client

            app.dependency_overrides[get_settings] = override_settings
            app.dependency_overrides[usage_module.get_venice_client] = override_venice_client

            with patch("backend.api.routes.usage.UsageTracker", return_value=mock_tracker):
                tc = TestClient(app)
                response = tc.get("/api/usage/keys")

            app.dependency_overrides.clear()

        assert response.status_code == 200

    def test_keys_response_shape(self):
        """Keys endpoint returns a list under the 'keys' key."""
        with patch("backend.main.init_db", new_callable=AsyncMock):
            from backend.main import app
            from backend.config import get_settings, Settings
            from backend.api.routes import usage as usage_module
            from backend.core.usage_tracker import UsageTracker, APIKeyUsage, UsageMetrics

            def override_settings():
                return Settings(
                    VENICE_ADMIN_KEY="test_admin_key_12345",
                    DATABASE_URL="postgresql://test:test@localhost:5432/test_db",
                )

            mock_keys = [
                APIKeyUsage(
                    id="key_abc",
                    name="Main Key",
                    usage=UsageMetrics(diem=10.5, usd=2.6),
                    created_at="2026-01-01T00:00:00Z",
                    is_active=True,
                )
            ]
            mock_tracker = MagicMock(spec=UsageTracker)
            mock_tracker.fetch_api_keys_with_daily_usage.return_value = mock_keys

            mock_client = MagicMock()
            mock_client.api_key = "test_admin_key_12345"

            def override_venice_client(settings=None):
                return mock_client

            app.dependency_overrides[get_settings] = override_settings
            app.dependency_overrides[usage_module.get_venice_client] = override_venice_client

            with patch("backend.api.routes.usage.UsageTracker", return_value=mock_tracker):
                tc = TestClient(app)
                response = tc.get("/api/usage/keys")

            app.dependency_overrides.clear()

        body = response.json()
        assert "keys" in body
        assert isinstance(body["keys"], list)
        assert len(body["keys"]) == 1
        key = body["keys"][0]
        assert key["id"] == "key_abc"
        assert key["name"] == "Main Key"
        assert "diem_usage" in key
        assert "usd_usage" in key
        assert "is_active" in key
