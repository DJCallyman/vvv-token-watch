"""Tests for Slice 2.5 staking events, holder lookup, and watchlists."""

from __future__ import annotations

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.api.routes import onchain
from backend.api.routes import watchlists as watchlist_routes
from backend.api.routes.watchlists import WatchlistCreate
from backend.database import Base
from backend.core import venicestats_client
from backend.core.venicestats_client import VeniceStatsError
from tests.conftest import FakeResponse

ADDRESS = "0x" + "ab" * 20
STAKING = onchain.STAKING_CONTRACT


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        yield s
    await engine.dispose()


def _rpc_result(result):
    return FakeResponse(json_data={"jsonrpc": "2.0", "id": 1, "result": result})


def _transfer_log(sender: str, recipient: str, value: int, index: int = 0):
    padded = lambda a: "0x" + a.lower().replace("0x", "").zfill(64)  # noqa: E731
    return {
        "topics": [onchain._TRANSFER_TOPIC, padded(sender), padded(recipient)],
        "data": hex(value),
        "transactionHash": "0x" + "cd" * 32,
        "blockNumber": "0x64",
        "logIndex": hex(index),
    }


def _queue_meta_calls(fake):
    fake.queue("crypto/rpc", [
        _rpc_result("0x12"),  # decimals
        _rpc_result(hex(1000 * 10**18)),  # totalSupply
        _rpc_result(hex(100 * 10**18)),  # balanceOf(staking)
    ])


@pytest.mark.asyncio
async def test_staking_events_classifies_direction_and_bounds_range():
    from tests.conftest import FakeVeniceAPIClient

    fake = FakeVeniceAPIClient()
    fake.queue("crypto/rpc", [
        _rpc_result(hex(100000)),  # eth_blockNumber
        _rpc_result([
            _transfer_log(ADDRESS, STAKING, 10**18, index=0),
            _transfer_log(STAKING, ADDRESS, 2 * 10**18, index=1),
            _transfer_log(ADDRESS, "0x" + "ef" * 20, 5 * 10**18, index=2),
        ]),
    ])
    _queue_meta_calls(fake)
    onchain._cache.clear()

    result = await onchain.get_staking_events(
        blocks=1000, address=None, chain="base-mainnet", token="vvv", client=fake
    )
    assert result["count"] == 2
    directions = {event["direction"] for event in result["events"]}
    assert directions == {"stake", "unstake"}
    assert result["from_block"] == hex(100000 - 1000)
    assert result["to_block"] == hex(100000)
    assert result["chain"] == "base-mainnet"
    assert "partial upstream history" in result["note"]


@pytest.mark.asyncio
async def test_staking_events_empty_result():
    from tests.conftest import FakeVeniceAPIClient

    fake = FakeVeniceAPIClient()
    fake.queue("crypto/rpc", [_rpc_result(hex(5000)), _rpc_result([]), _rpc_result([])])
    _queue_meta_calls(fake)
    onchain._cache.clear()

    result = await onchain.get_staking_events(
        blocks=1000, address=ADDRESS, chain="base-mainnet", token="vvv", client=fake
    )
    assert result["count"] == 0
    assert result["events"] == []


@pytest.mark.asyncio
async def test_staking_events_upstream_failure_reports_error():
    from tests.conftest import FakeVeniceAPIClient

    fake = FakeVeniceAPIClient()
    fake.queue("crypto/rpc", [FakeResponse(status_code=502, json_data={})])
    onchain._cache.clear()

    with pytest.raises(HTTPException) as exc:
        await onchain.get_staking_events(
            blocks=1000, address=None, chain="base-mainnet", token="vvv", client=fake
        )
    assert exc.value.status_code in (500, 502)


@pytest.mark.asyncio
async def test_staking_events_reject_unapproved_chain():
    from tests.conftest import FakeVeniceAPIClient

    with pytest.raises(HTTPException) as exc:
        await onchain.get_staking_events(
            blocks=1000,
            address=None,
            chain="ethereum-mainnet",
            token="vvv",
            client=FakeVeniceAPIClient(),
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_holder_lookup_documents_address_only_limitation(monkeypatch):
    async def fake_holdings(address, settings=None):
        return {
            "vvv_wallet": 1.0,
            "svvv_total": 2.0,
            "svvv_locked": 1.5,
            "pending_rewards": 0.5,
            "diem_wallet": 3.0,
            "diem_staked": 4.0,
        }

    monkeypatch.setattr(venicestats_client, "get_wallet_holdings", fake_holdings)
    onchain._cache.clear()
    result = await onchain.get_holder_lookup(address=ADDRESS, chain="base-mainnet")
    assert result["all_holders_available"] is False
    assert "single address" in result["note"]
    assert result["holdings"]["diem_staked"] == 4.0


@pytest.mark.asyncio
async def test_holder_lookup_upstream_failure_is_502(monkeypatch):
    async def failing(address, settings=None):
        raise VeniceStatsError("down")

    monkeypatch.setattr(venicestats_client, "get_wallet_holdings", failing)
    onchain._cache.clear()
    with pytest.raises(HTTPException) as exc:
        await onchain.get_holder_lookup(address=ADDRESS, chain="base-mainnet")
    assert exc.value.status_code == 502


# ---------------------------------------------------------------------------
# Watchlists
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_watchlist_crud_and_duplicates(session):
    created = await watchlist_routes.create_watchlist_item(
        WatchlistCreate(address=ADDRESS, label="ops"), session
    )
    assert created["address"] == ADDRESS
    listed = await watchlist_routes.list_watchlist(session)
    assert listed["count"] == 1

    with pytest.raises(HTTPException) as exc:
        await watchlist_routes.create_watchlist_item(WatchlistCreate(address=ADDRESS), session)
    assert exc.value.status_code == 409

    deleted = await watchlist_routes.delete_watchlist_item(created["id"], session)
    assert deleted["deleted"] is True
    assert (await watchlist_routes.list_watchlist(session))["count"] == 0


@pytest.mark.asyncio
async def test_watchlist_rejects_invalid_address_and_chain(session):
    with pytest.raises(HTTPException) as exc:
        await watchlist_routes.create_watchlist_item(
            WatchlistCreate(address="0x" + "zz" * 20), session
        )
    assert exc.value.status_code == 400

    with pytest.raises(HTTPException) as exc:
        await watchlist_routes.create_watchlist_item(
            WatchlistCreate(address=ADDRESS, chain="ethereum-mainnet"), session
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_watchlist_delete_missing_is_404(session):
    with pytest.raises(HTTPException) as exc:
        await watchlist_routes.delete_watchlist_item(999, session)
    assert exc.value.status_code == 404
