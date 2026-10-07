"""Tests for the Slice 2.6 chain/token registry."""

from __future__ import annotations

from types import MappingProxyType

import pytest
from fastapi import HTTPException

from backend.core import chains
from backend.core.chains import ChainInfo, TokenInfo, UnsupportedPairError
from backend.api.routes import onchain


def test_base_mainnet_is_the_only_approved_chain():
    assert chains.APPROVED_CHAIN_KEYS == ("base-mainnet",)
    chain = chains.get_chain("base-mainnet")
    assert chain.chain_id == 8453
    assert chain.tokens["vvv"].address.lower().startswith("0x")
    assert chain.tokens["vvv"].decimals == 18
    assert chain.tokens["diem"].address is None
    assert chain.tokens["diem"].data_sources == ("venicestats",)


def test_unsupported_chain_and_token_fail_explicitly():
    with pytest.raises(UnsupportedPairError) as exc:
        chains.resolve_pair("ethereum-mainnet", "vvv")
    assert "Unsupported chain" in str(exc.value)

    with pytest.raises(UnsupportedPairError) as exc:
        chains.resolve_pair("base-mainnet", "usdc")
    assert "not registered" in str(exc.value)
    assert "vvv" in exc.value.allowed


def test_cache_key_namespaces_chain_and_token():
    key = chains.cache_key("transfers", "base-mainnet", "vvv", "0xabc")
    assert key == "transfers:base-mainnet:vvv:0xabc"


def test_two_chains_have_distinct_token_metadata(monkeypatch):
    """The registry resolves two chains with different metadata independently."""
    testnet = ChainInfo(
        key="test-network",
        chain_id=99999,
        display_name="Test Network",
        rpc_network="test-network",
        explorer_base_url="https://example.invalid",
        tokens=MappingProxyType(
            {
                "vvv": TokenInfo(
                    symbol="VVV",
                    decimals=6,
                    address="0x" + "11" * 20,
                    data_sources=("test",),
                )
            }
        ),
    )
    monkeypatch.setattr(
        chains,
        "_CHAINS",
        MappingProxyType({chains.BASE_MAINNET.key: chains.BASE_MAINNET, testnet.key: testnet}),
    )
    base_chain, base_token = chains.resolve_pair("base-mainnet", "vvv")
    test_chain, test_token = chains.resolve_pair("test-network", "vvv")
    assert base_chain.chain_id != test_chain.chain_id
    assert base_token.decimals != test_token.decimals
    assert base_token.address != test_token.address
    # Approved list is unchanged: the extra chain is registered, not approved.
    assert chains.APPROVED_CHAIN_KEYS == ("base-mainnet",)


def test_onchain_resolver_returns_http_400_for_unapproved_pair():
    with pytest.raises(HTTPException) as exc:
        onchain._resolve("ethereum-mainnet", "vvv")
    assert exc.value.status_code == 400
    assert "Unsupported chain" in exc.value.detail


def test_onchain_resolver_returns_http_400_for_unregistered_token():
    with pytest.raises(HTTPException) as exc:
        onchain._resolve("base-mainnet", "usdc")
    assert exc.value.status_code == 400
    assert "not registered" in exc.value.detail
