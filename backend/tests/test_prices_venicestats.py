"""Tests for the venicestats-backed prices and onchain routes.

Covers:
  * /api/prices — venicestats metrics + frankfurter FX conversion,
    snapshot persistence (market_cap/change_24h), alert evaluation.
  * venicestats client — caching and FX parsing.
  * /api/onchain/supply + /api/onchain/staking — venicestats-backed values.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.config import get_settings
from backend.core import venicestats_client
from backend.core.venicestats_client import VeniceStatsError
from backend.database import Base
from backend.models.db import PriceSnapshot
from backend.services.price_history_service import get_price_history


METRICS = {
    "vvvPrice": 27.92,
    "priceChange24h": -0.48,
    "marketCap": 1_355_845_044.32,
    "fdv": 2_263_574_106.6,
    "diemPrice": 1967.67,
    "diemPriceChange24h": 0.078,
    "diemMarketCap": 71_574_446.14,
    "diemFdv": 78_706_915.3,
    "totalSupply": 114_951_328.59,
    "circulatingSupply": 48_559_016.66,
    "burnedSupply": 33_882_379.59,
    "totalStaked": 33_197_812.67,
    "stakingRatio": 0.665543,
    "stakingRatioChange24h": -0.2083,
    "stakerApr": 0.0834,
    "svvvLocked": 8_298_207.68,
    "svvvUnlocked": 24_899_604.99,
    "lockRatio": 0.249962,
    "freeFloatVvv": 15_361_203.99,
    "freeFloatVvvPctCirc": 31.63,
    "freeFloatVvvPctTotal": 13.36,
}


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        yield s
    await engine.dispose()


@pytest.fixture(autouse=True)
def _clear_client_caches():
    venicestats_client._metrics_cache.clear()
    venicestats_client._fx_cache.clear()
    venicestats_client._chart_cache.clear()
    yield
    venicestats_client._metrics_cache.clear()
    venicestats_client._fx_cache.clear()
    venicestats_client._chart_cache.clear()


@pytest.fixture
def metrics_only(monkeypatch):
    """Stub the metrics fetch; leave FX unstubbed (tests stub it per-case)."""
    async def fake_metrics(settings=None):
        return dict(METRICS)

    monkeypatch.setattr(venicestats_client, "get_metrics", fake_metrics)


@pytest.fixture
def fx_rate(monkeypatch):
    async def fake_fx(settings=None):
        return 1.4237

    monkeypatch.setattr(venicestats_client, "get_usd_aud_rate", fake_fx)


# ---------------------------------------------------------------------------
# Price snapshots with the new fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_snapshot_persists_market_cap_and_change(session):
    from backend.services.price_history_service import record_price_snapshot

    row = await record_price_snapshot(
        session,
        token_id="vvv",
        price_usd=27.92,
        price_aud=39.75,
        market_cap=1_355_845_044.32,
        change_24h=-0.48,
    )
    assert row is not None
    assert row.market_cap == pytest.approx(1_355_845_044.32)
    assert row.change_24h == pytest.approx(-0.48)

    history = await get_price_history(session, token_id="vvv", range_key="24h")
    assert history, "history should contain the new snapshot"
    point = history[-1]
    assert point["market_cap"] == pytest.approx(1_355_845_044.32)
    assert point["change_24h"] == pytest.approx(-0.48)


# ---------------------------------------------------------------------------
# venicestats client
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_metrics_caches(monkeypatch):
    calls = []

    async def fake_request(url, params=None):
        calls.append(url)
        return dict(METRICS)

    monkeypatch.setattr(venicestats_client, "_request_json", fake_request)
    first = await venicestats_client.get_metrics()
    second = await venicestats_client.get_metrics()
    assert first == second == METRICS
    assert len(calls) == 1, "second call must be served from cache"


@pytest.mark.asyncio
async def test_get_usd_aud_rate_parses_frankfurter(monkeypatch):
    async def fake_request(url, params=None):
        return {"amount": 1.0, "base": "USD", "date": "2026-09-28", "rates": {"AUD": 1.4237}}

    monkeypatch.setattr(venicestats_client, "_request_json", fake_request)
    rate = await venicestats_client.get_usd_aud_rate()
    assert rate == pytest.approx(1.4237)


@pytest.mark.asyncio
async def test_get_usd_aud_rate_rejects_bad_payload(monkeypatch):
    async def fake_request(url, params=None):
        return {"rates": {}}

    monkeypatch.setattr(venicestats_client, "_request_json", fake_request)
    with pytest.raises(VeniceStatsError):
        await venicestats_client.get_usd_aud_rate()


@pytest.mark.asyncio
async def test_upstream_http_error_maps_to_venicestats_error(monkeypatch):
    import httpx

    async def fake_request(url, params=None):
        raise venicestats_client.VeniceStatsError("Upstream HTTP 503")

    monkeypatch.setattr(venicestats_client, "_request_json", fake_request)
    with pytest.raises(VeniceStatsError):
        await venicestats_client.get_metrics()


# ---------------------------------------------------------------------------
# /api/prices route
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_prices_uses_venicestats(
    session, metrics_only, fx_rate, monkeypatch
):
    from backend.api.routes import prices as prices_routes
    from backend.services import app_settings

    class FakeResult:
        def scalar_one_or_none(self):
            return None

    async def fake_execute(*args, **kwargs):
        return FakeResult()

    async def fake_effective(db, settings):
        return {
            "coingecko_holding_amount": 100.0,
            "diem_holding_amount": 2.0,
            "vvv_holding_source": "manual",
            "vvv_wallet_address": "",
            "benchmark_max_cost_usd": 5.0,
            "benchmark_enable_billing_reconciliation": False,
            "benchmark_judge_model": "x",
        }

    monkeypatch.setattr(app_settings, "get_effective_settings", fake_effective)
    monkeypatch.setattr(prices_routes, "get_effective_settings", fake_effective)

    alerts_seen = {}

    async def fake_evaluate(db, metrics, history=None):
        alerts_seen.update(metrics)
        return []

    monkeypatch.setattr(prices_routes.alert_engine, "evaluate_alerts", fake_evaluate)

    result = await prices_routes.get_prices(settings=get_settings(), db=session)

    assert result["vvv"]["usd"] == pytest.approx(27.92)
    assert result["vvv"]["aud"] == pytest.approx(27.92 * 1.4237, rel=1e-4)
    assert result["diem"]["usd"] == pytest.approx(1967.67)
    assert result["vvv"]["market_cap"] == pytest.approx(METRICS["marketCap"])
    assert result["vvv"]["change_24h"] == pytest.approx(-0.48)
    assert result["diem"]["change_24h"] == pytest.approx(0.078)
    assert result["portfolio"]["vvv_value_usd"] == pytest.approx(2792.0)
    assert result["portfolio"]["total_usd"] == pytest.approx(2792.0 + 2.0 * 1967.67)
    assert alerts_seen["vvv_price_usd"] == pytest.approx(27.92)
    assert alerts_seen["diem_price_usd"] == pytest.approx(1967.67)


@pytest.mark.asyncio
async def test_get_prices_degrades_without_fx(session, metrics_only, monkeypatch):
    """FX outage omits aud but must not fail the price poll."""
    from backend.api.routes import prices as prices_routes
    from backend.services import app_settings

    async def fake_fx(settings=None):
        raise VeniceStatsError("Upstream unavailable")

    monkeypatch.setattr(venicestats_client, "get_usd_aud_rate", fake_fx)

    async def fake_effective(db, settings):
        return {
            "coingecko_holding_amount": 1.0,
            "diem_holding_amount": 0.0,
            "vvv_holding_source": "manual",
            "vvv_wallet_address": "",
            "benchmark_max_cost_usd": 5.0,
            "benchmark_enable_billing_reconciliation": False,
            "benchmark_judge_model": "x",
        }

    monkeypatch.setattr(app_settings, "get_effective_settings", fake_effective)
    monkeypatch.setattr(prices_routes, "get_effective_settings", fake_effective)

    async def fake_evaluate(db, metrics, history=None):
        return []

    monkeypatch.setattr(prices_routes.alert_engine, "evaluate_alerts", fake_evaluate)

    result = await prices_routes.get_prices(settings=get_settings(), db=session)
    assert result["vvv"]["usd"] == pytest.approx(27.92)
    assert result["vvv"]["aud"] is None
    assert result["diem"]["aud"] is None


@pytest.mark.asyncio
async def test_get_prices_wallet_source_uses_onchain_balance(
    session, metrics_only, fx_rate, monkeypatch
):
    """Wallet source: holdings come from venicestats wallet balances."""
    from backend.api.routes import prices as prices_routes
    from backend.services import app_settings

    async def fake_effective(db, settings):
        return {
            "coingecko_holding_amount": 100.0,
            "diem_holding_amount": 0.0,
            "vvv_holding_source": "wallet",
            "vvv_wallet_address": "0x" + "ab" * 20,
            "benchmark_max_cost_usd": 5.0,
            "benchmark_enable_billing_reconciliation": False,
            "benchmark_judge_model": "x",
        }

    monkeypatch.setattr(app_settings, "get_effective_settings", fake_effective)
    monkeypatch.setattr(prices_routes, "get_effective_settings", fake_effective)

    alerts_seen = {}

    async def fake_evaluate(db, metrics, history=None):
        alerts_seen.update(metrics)
        return []

    monkeypatch.setattr(prices_routes.alert_engine, "evaluate_alerts", fake_evaluate)

    fetch_calls = []

    async def fake_holdings(address, settings=None):
        fetch_calls.append(address)
        return {
            "vvv_wallet": 100.0,
            "svvv_total": 200.0,
            "svvv_locked": 150.0,
            "pending_rewards": 5.0,
            "diem_wallet": 1.5,
            "diem_staked": 2.5,
        }

    monkeypatch.setattr(venicestats_client, "get_wallet_holdings", fake_holdings)

    result = await prices_routes.get_prices(settings=get_settings(), db=session)

    assert fetch_calls == ["0x" + "ab" * 20]
    # VVV = wallet + staked (locked + unlocked) + unclaimed rewards
    assert result["holdings"]["vvv"] == pytest.approx(305.0)
    assert result["holdings"]["vvv_source"] == "wallet"
    # DIEM = unstaked + staked
    assert result["holdings"]["diem"] == pytest.approx(4.0)
    assert result["holdings"]["diem_source"] == "wallet"
    portfolio = result["portfolio"]
    assert portfolio["vvv_value_usd"] == pytest.approx(100.0 * 27.92)
    assert portfolio["svvv_value_usd"] == pytest.approx(200.0 * 27.92)
    assert portfolio["unclaimed_rewards_value_usd"] == pytest.approx(5.0 * 27.92)
    assert portfolio["diem_value_usd"] == pytest.approx(4.0 * 1967.67)
    assert portfolio["diem_unlock_offset_usd"] == pytest.approx(portfolio["diem_value_usd"])
    assert portfolio["gross_exposure_usd"] == pytest.approx(
        100.0 * 27.92 + 200.0 * 27.92 + 5.0 * 27.92 + 4.0 * 1967.67
    )
    assert portfolio["net_worth_usd"] == pytest.approx(
        100.0 * 27.92 + 200.0 * 27.92 + 5.0 * 27.92
    )


@pytest.mark.asyncio
async def test_get_prices_wallet_source_falls_back_on_failure(
    session, metrics_only, fx_rate, monkeypatch
):
    """Chain-read failure falls back to the manual amount, not an error."""
    from backend.api.routes import prices as prices_routes
    from backend.services import app_settings

    async def fake_effective(db, settings):
        return {
            "coingecko_holding_amount": 100.0,
            "diem_holding_amount": 0.0,
            "vvv_holding_source": "wallet",
            "vvv_wallet_address": "0x" + "ab" * 20,
            "benchmark_max_cost_usd": 5.0,
            "benchmark_enable_billing_reconciliation": False,
            "benchmark_judge_model": "x",
        }

    monkeypatch.setattr(app_settings, "get_effective_settings", fake_effective)
    monkeypatch.setattr(prices_routes, "get_effective_settings", fake_effective)

    async def fake_evaluate(db, metrics, history=None):
        return []

    monkeypatch.setattr(prices_routes.alert_engine, "evaluate_alerts", fake_evaluate)

    async def failing_holdings(address, settings=None):
        raise ValueError("venicestats down")

    monkeypatch.setattr(venicestats_client, "get_wallet_holdings", failing_holdings)

    result = await prices_routes.get_prices(settings=get_settings(), db=session)

    assert result["holdings"]["vvv"] == pytest.approx(100.0)
    assert result["holdings"]["vvv_source"] == "manual"


# ---------------------------------------------------------------------------
# /api/onchain/supply + /api/onchain/staking
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_onchain_supply_uses_venicestats(monkeypatch):
    from backend.api.routes import onchain as onchain_routes

    async def fake_metrics(settings=None):
        return dict(METRICS)

    monkeypatch.setattr(venicestats_client, "get_metrics", fake_metrics)
    onchain_routes._cache.clear()

    result = await onchain_routes.get_onchain_supply(
        client=None, settings=get_settings()
    )
    assert result["total_supply"] == pytest.approx(METRICS["totalSupply"])
    assert result["staked_in_contract"] == pytest.approx(METRICS["totalStaked"])
    assert result["burned_supply"] == pytest.approx(METRICS["burnedSupply"])
    assert result["free_float_pct_circulating"] == pytest.approx(31.63)
    assert result["source"] == "venicestats"
    onchain_routes._cache.clear()


@pytest.mark.asyncio
async def test_onchain_staking_includes_apr(monkeypatch):
    from backend.api.routes import onchain as onchain_routes

    async def fake_metrics(settings=None):
        return dict(METRICS)

    monkeypatch.setattr(venicestats_client, "get_metrics", fake_metrics)
    onchain_routes._cache.clear()

    result = await onchain_routes.get_onchain_staking(
        client=None, settings=get_settings()
    )
    assert result["apr"] == pytest.approx(0.0834)
    assert result["staked_percent"] == pytest.approx(66.5543)
    assert result["lock_ratio"] == pytest.approx(0.249962)
    assert result["source"] == "venicestats"
    onchain_routes._cache.clear()
