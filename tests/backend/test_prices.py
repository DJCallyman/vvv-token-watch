"""
Tests for /api/prices endpoint.
Uses unittest.mock to patch httpx.AsyncClient so no real CoinGecko requests are made.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


VVV_COINGECKO_RESPONSE = {"venice-token": {"usd": 2.50, "aud": 3.85}}
DIEM_COINGECKO_RESPONSE = {"diem": {"usd": 0.01, "aud": 0.015}}


def _mock_httpx_get(token_data: dict):
    """Return an async mock that behaves like httpx.AsyncClient.get()."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = token_data
    mock_get = AsyncMock(return_value=mock_response)
    return mock_get


@pytest.fixture
def client():
    """TestClient with mocked settings. Each test patches httpx separately."""
    with patch("backend.main.init_db", new_callable=AsyncMock):
        from backend.main import app
        from backend.config import get_settings, Settings

        def override_settings():
            return Settings(
                VENICE_ADMIN_KEY="test_admin_key_12345",
                DATABASE_URL="postgresql://test:test@localhost:5432/test_db",
                COINGECKO_TOKEN_ID="venice-token",
                COINGECKO_CURRENCIES="usd,aud",
                COINGECKO_HOLDING_AMOUNT=2750.0,
                DIEM_TOKEN_ID="diem",
                DIEM_HOLDING_AMOUNT=500.0,
            )

        app.dependency_overrides[get_settings] = override_settings
        yield TestClient(app)
        app.dependency_overrides.clear()


def _patch_coingecko(vvv_data=None, diem_data=None):
    """Return a context manager that patches fetch_coin_gecko_price."""
    vvv_data = vvv_data or VVV_COINGECKO_RESPONSE
    diem_data = diem_data or DIEM_COINGECKO_RESPONSE

    async def fake_fetch(token_id, currencies, api_key=None):
        if token_id == "venice-token":
            return vvv_data
        return diem_data

    return patch("backend.api.routes.prices.fetch_coin_gecko_price", side_effect=fake_fetch)


class TestPricesEndpoint:
    """Tests for GET /api/prices"""

    def test_prices_returns_200(self, client):
        with _patch_coingecko():
            response = client.get("/api/prices")
        assert response.status_code == 200

    def test_prices_contains_vvv_and_diem_keys(self, client):
        with _patch_coingecko():
            response = client.get("/api/prices")
        data = response.json()
        assert "vvv" in data
        assert "diem" in data

    def test_prices_returns_usd_values(self, client):
        with _patch_coingecko():
            response = client.get("/api/prices")
        data = response.json()
        assert data["vvv"].get("usd") == pytest.approx(2.50)
        assert data["diem"].get("usd") == pytest.approx(0.01)

    def test_prices_returns_aud_values(self, client):
        with _patch_coingecko():
            response = client.get("/api/prices")
        data = response.json()
        assert data["vvv"].get("aud") == pytest.approx(3.85)

    def test_prices_contains_holdings(self, client):
        with _patch_coingecko():
            response = client.get("/api/prices")
        data = response.json()
        assert "holdings" in data
        assert data["holdings"]["vvv"] == pytest.approx(2750.0)
        assert data["holdings"]["diem"] == pytest.approx(500.0)

    def test_prices_calculates_portfolio(self, client):
        with _patch_coingecko():
            response = client.get("/api/prices")
        data = response.json()
        # vvv_value_usd = 2750.0 * 2.50 = 6875.0
        # diem_value_usd = 500.0 * 0.01 = 5.0
        # total = 6880.0
        assert "portfolio" in data
        assert data["portfolio"]["vvv_value_usd"] == pytest.approx(6875.0)
        assert data["portfolio"]["diem_value_usd"] == pytest.approx(5.0)
        assert data["portfolio"]["total_usd"] == pytest.approx(6880.0)

    def test_prices_handles_missing_diem_gracefully(self, client):
        """When DIEM price is missing from response, portfolio still returns."""
        with _patch_coingecko(diem_data={}):
            response = client.get("/api/prices")
        assert response.status_code == 200
        data = response.json()
        assert "vvv" in data

    def test_prices_zero_holdings_gives_zero_portfolio(self, client):
        """Zero holdings produce a zero portfolio value."""
        with patch("backend.main.init_db", new_callable=AsyncMock):
            from backend.main import app
            from backend.config import get_settings, Settings

            def override_settings_zero():
                return Settings(
                    VENICE_ADMIN_KEY="test_admin_key_12345",
                    DATABASE_URL="postgresql://test:test@localhost:5432/test_db",
                    COINGECKO_TOKEN_ID="venice-token",
                    COINGECKO_HOLDING_AMOUNT=0.0,
                    DIEM_HOLDING_AMOUNT=0.0,
                )

            app.dependency_overrides[get_settings] = override_settings_zero
            with _patch_coingecko():
                tc = TestClient(app)
                response = tc.get("/api/prices")
            app.dependency_overrides.clear()

        data = response.json()
        assert data["portfolio"]["total_usd"] == pytest.approx(0.0)
