"""Tests for Slice 2.7 rate-limit and RPC cost observability."""

from __future__ import annotations

import pytest

from backend.api.routes import observability
from backend.core import telemetry
from backend.tests.conftest import FakeResponse, FakeVeniceAPIClient


@pytest.fixture(autouse=True)
def _reset_telemetry():
    telemetry.reset_for_tests()
    observability._probe_cache.clear()
    yield
    telemetry.reset_for_tests()
    observability._probe_cache.clear()


def test_missing_telemetry_is_unavailable_not_zero():
    rate = telemetry.rate_limit_snapshot()
    assert rate["status"] == "unavailable"
    assert "fields" not in rate

    rpc = telemetry.rpc_cost_snapshot()
    assert rpc["status"] == "unavailable"
    assert rpc.get("totals") is None


def test_record_response_captures_headers_and_rpc_costs():
    telemetry.record_response(
        "/crypto/rpc/base-mainnet",
        {
            "X-RateLimit-Limit": "60",
            "X-RateLimit-Remaining": "59",
            "X-Venice-RPC-Credits": "5",
            "X-Venice-RPC-Cost-USD": "0.0025",
        },
    )
    rate = telemetry.rate_limit_snapshot()
    assert rate["status"] == "ok"
    assert rate["fields"]["x-ratelimit-limit"]["value"] == "60"

    rpc = telemetry.rpc_cost_snapshot()
    assert rpc["status"] == "ok"
    assert rpc["totals"]["credits"] == pytest.approx(5.0)
    assert rpc["totals"]["cost_usd"] == pytest.approx(0.0025)
    assert rpc["latest"]["cost_usd"] == pytest.approx(0.0025)


def test_rpc_totals_accumulate_and_are_bounded():
    for index in range(5):
        telemetry.record_response(
            "/crypto/rpc/base-mainnet",
            {"X-Venice-RPC-Credits": "1", "X-Venice-RPC-Cost-USD": "0.001"},
        )
    rpc = telemetry.rpc_cost_snapshot()
    assert rpc["totals"]["count"] == 5
    assert rpc["totals"]["credits"] == pytest.approx(5.0)


@pytest.mark.asyncio
async def test_rate_limit_log_403_is_unavailable():
    fake = FakeVeniceAPIClient()
    fake.queue("rate_limits/log", [FakeResponse(status_code=403, json_data={})])
    result = await observability._fetch_rate_limit_log(fake)
    assert result["status"] == "unavailable"
    assert result["reason"] == "forbidden_admin_key_required"


@pytest.mark.asyncio
async def test_rate_limit_log_ok_returns_events():
    fake = FakeVeniceAPIClient()
    fake.queue(
        "rate_limits/log",
        [FakeResponse(json_data={"data": [{"timestamp": "t", "limit": 60}]})],
    )
    result = await observability._fetch_rate_limit_log(fake)
    assert result["status"] == "ok"
    assert result["count"] == 1


@pytest.mark.asyncio
async def test_rate_limit_log_404_is_unavailable():
    fake = FakeVeniceAPIClient()
    fake.queue("rate_limits/log", [FakeResponse(status_code=404, json_data={})])
    result = await observability._fetch_rate_limit_log(fake)
    assert result["status"] == "unavailable"
    assert result["reason"] == "endpoint_unavailable"


@pytest.mark.asyncio
async def test_billing_coverage_confirmed_when_rpc_entries_seen():
    fake = FakeVeniceAPIClient()
    fake.queue("usage-history", [FakeResponse(json_data={"data": [
        {"sku": "crypto-rpc-base", "amount": 0.01},
        {"sku": "chat-completion", "amount": 1.0},
    ]})])
    result = await observability._check_billing_coverage(fake)
    assert result["status"] == "confirmed"
    assert result["rpc_entries"] == 1
    assert result["scanned"] == 2


@pytest.mark.asyncio
async def test_billing_coverage_unverified_when_no_rpc_entries():
    fake = FakeVeniceAPIClient()
    fake.queue("usage-history", [FakeResponse(json_data={"data": [
        {"sku": "chat-completion", "amount": 1.0},
    ]})])
    result = await observability._check_billing_coverage(fake)
    assert result["status"] == "unverified"
    assert result["rpc_entries"] == 0
    assert "not confirmed" in result["note"]


@pytest.mark.asyncio
async def test_billing_coverage_forbidden_is_unavailable():
    fake = FakeVeniceAPIClient()
    fake.queue("usage-history", [FakeResponse(status_code=403, json_data={})])
    result = await observability._check_billing_coverage(fake)
    assert result["status"] == "unavailable"
    assert result["reason"] == "forbidden_admin_key_required"
