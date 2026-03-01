"""
Tests for /api/balance and /api/rate-limits endpoints.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


def _app_with_mocks(balance_payload=None, rate_limits_payload=None):
    """Context manager: returns (TestClient, mock_tracker)."""
    from backend.main import app
    from backend.config import get_settings, Settings
    from backend.api.routes import balance as balance_module
    from backend.core.usage_tracker import UsageTracker, BalanceInfo

    def override_settings():
        return Settings(
            VENICE_ADMIN_KEY="test_admin_key_12345",
            DATABASE_URL="postgresql://test:test@localhost:5432/test_db",
        )

    mock_balance = BalanceInfo(
        diem=45.5,
        usd=11.25,
        daily_diem_limit=100.0,
        daily_usd_limit=25.0,
        next_epoch_begins="2026-03-02T00:00:00Z",
    )

    mock_tracker = MagicMock(spec=UsageTracker)
    mock_tracker.fetch_rate_limits.return_value = mock_balance

    mock_rl_response = MagicMock()
    mock_rl_response.json.return_value = rate_limits_payload or {"data": []}

    mock_client = MagicMock()
    mock_client.api_key = "test_admin_key_12345"
    mock_client.get.return_value = mock_rl_response

    def override_venice_client(settings=None):
        return mock_client

    app.dependency_overrides[get_settings] = override_settings
    app.dependency_overrides[balance_module.get_venice_client] = override_venice_client

    return app, mock_tracker, mock_client, override_settings, balance_module


class TestBalanceEndpoint:
    """Tests for GET /api/balance"""

    def test_balance_returns_200(self):
        with patch("backend.main.init_db", new_callable=AsyncMock):
            app, mock_tracker, mock_client, override_settings, balance_module = _app_with_mocks()
            with patch("backend.api.routes.balance.UsageTracker", return_value=mock_tracker):
                tc = TestClient(app)
                response = tc.get("/api/balance")
            app.dependency_overrides.clear()
        assert response.status_code == 200

    def test_balance_returns_expected_fields(self):
        with patch("backend.main.init_db", new_callable=AsyncMock):
            app, mock_tracker, mock_client, override_settings, balance_module = _app_with_mocks()
            with patch("backend.api.routes.balance.UsageTracker", return_value=mock_tracker):
                tc = TestClient(app)
                response = tc.get("/api/balance")
            app.dependency_overrides.clear()

        data = response.json()
        for field in ["diem", "usd", "daily_diem_limit", "daily_usd_limit",
                      "diem_usage_percent", "usd_usage_percent"]:
            assert field in data, f"Missing field: {field}"

    def test_balance_values_are_correct(self):
        with patch("backend.main.init_db", new_callable=AsyncMock):
            app, mock_tracker, mock_client, override_settings, balance_module = _app_with_mocks()
            with patch("backend.api.routes.balance.UsageTracker", return_value=mock_tracker):
                tc = TestClient(app)
                response = tc.get("/api/balance")
            app.dependency_overrides.clear()

        data = response.json()
        assert data["diem"] == pytest.approx(45.5)
        assert data["usd"] == pytest.approx(11.25)
        assert data["daily_diem_limit"] == pytest.approx(100.0)
        assert data["daily_usd_limit"] == pytest.approx(25.0)

    def test_balance_usage_percent_calculated_correctly(self):
        """diem_usage_percent should be diem/daily_diem_limit * 100."""
        with patch("backend.main.init_db", new_callable=AsyncMock):
            app, mock_tracker, mock_client, override_settings, balance_module = _app_with_mocks()
            with patch("backend.api.routes.balance.UsageTracker", return_value=mock_tracker):
                tc = TestClient(app)
                response = tc.get("/api/balance")
            app.dependency_overrides.clear()

        data = response.json()
        expected_pct = round((45.5 / 100.0) * 100, 2)
        assert data["diem_usage_percent"] == pytest.approx(expected_pct)

    def test_balance_returns_next_epoch(self):
        with patch("backend.main.init_db", new_callable=AsyncMock):
            app, mock_tracker, mock_client, override_settings, balance_module = _app_with_mocks()
            with patch("backend.api.routes.balance.UsageTracker", return_value=mock_tracker):
                tc = TestClient(app)
                response = tc.get("/api/balance")
            app.dependency_overrides.clear()

        data = response.json()
        assert data.get("next_epoch_begins") == "2026-03-02T00:00:00Z"

    def test_balance_zero_limit_returns_zero_percent(self):
        """When daily limit is 0, usage_percent should be 0 (no division by zero)."""
        from backend.core.usage_tracker import BalanceInfo

        with patch("backend.main.init_db", new_callable=AsyncMock):
            from backend.main import app
            from backend.config import get_settings, Settings
            from backend.api.routes import balance as balance_module
            from backend.core.usage_tracker import UsageTracker

            def override_settings():
                return Settings(
                    VENICE_ADMIN_KEY="test_admin_key_12345",
                    DATABASE_URL="postgresql://test:test@localhost:5432/test_db",
                )

            zero_balance = BalanceInfo(diem=0.0, usd=0.0, daily_diem_limit=0.0, daily_usd_limit=0.0)
            mock_tracker = MagicMock(spec=UsageTracker)
            mock_tracker.fetch_rate_limits.return_value = zero_balance

            mock_client = MagicMock()
            mock_client.api_key = "test_admin_key_12345"

            def override_venice_client(settings=None):
                return mock_client

            app.dependency_overrides[get_settings] = override_settings
            app.dependency_overrides[balance_module.get_venice_client] = override_venice_client

            with patch("backend.api.routes.balance.UsageTracker", return_value=mock_tracker):
                tc = TestClient(app)
                response = tc.get("/api/balance")

            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["diem_usage_percent"] == 0
        assert data["usd_usage_percent"] == 0

    def test_balance_propagates_tracker_exception(self):
        """A tracker exception should return HTTP 500."""
        with patch("backend.main.init_db", new_callable=AsyncMock):
            from backend.main import app
            from backend.config import get_settings, Settings
            from backend.api.routes import balance as balance_module
            from backend.core.usage_tracker import UsageTracker

            def override_settings():
                return Settings(
                    VENICE_ADMIN_KEY="test_admin_key_12345",
                    DATABASE_URL="postgresql://test:test@localhost:5432/test_db",
                )

            failing_tracker = MagicMock(spec=UsageTracker)
            failing_tracker.fetch_rate_limits.side_effect = Exception("API unreachable")

            mock_client = MagicMock()
            mock_client.api_key = "test_admin_key_12345"

            def override_venice_client(settings=None):
                return mock_client

            app.dependency_overrides[get_settings] = override_settings
            app.dependency_overrides[balance_module.get_venice_client] = override_venice_client

            with patch("backend.api.routes.balance.UsageTracker", return_value=failing_tracker):
                tc = TestClient(app, raise_server_exceptions=False)
                response = tc.get("/api/balance")

            app.dependency_overrides.clear()

        assert response.status_code == 500
        assert "API unreachable" in response.json()["detail"]


class TestRateLimitsEndpoint:
    """Tests for GET /api/rate-limits"""

    def test_rate_limits_returns_200(self):
        rl_payload = {"data": {"limits": {"rpm": 60, "tpm": 100000}}}
        with patch("backend.main.init_db", new_callable=AsyncMock):
            app, mock_tracker, mock_client, override_settings, balance_module = _app_with_mocks(
                rate_limits_payload=rl_payload
            )
            mock_client.get.return_value = MagicMock(
                json=MagicMock(return_value=rl_payload), status_code=200
            )
            tc = TestClient(app)
            response = tc.get("/api/rate-limits")
            app.dependency_overrides.clear()
        assert response.status_code == 200

    def test_rate_limits_forwards_venice_response(self):
        rl_payload = {"data": {"limits": {"rpm": 60}}}
        with patch("backend.main.init_db", new_callable=AsyncMock):
            app, mock_tracker, mock_client, override_settings, balance_module = _app_with_mocks(
                rate_limits_payload=rl_payload
            )
            mock_client.get.return_value = MagicMock(
                json=MagicMock(return_value=rl_payload), status_code=200
            )
            tc = TestClient(app)
            response = tc.get("/api/rate-limits")
            app.dependency_overrides.clear()
        assert response.json() == rl_payload
