"""On-chain VVV data via Venice crypto RPC (Base)."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException

from backend.config import Settings, get_settings
from backend.core.cache import TtlCache
from backend.core.venice_api_client import VeniceAPIClient

logger = logging.getLogger(__name__)
router = APIRouter()

# Canonical Base contracts (from Venice docs).
VVV_TOKEN = "0xacfE6019Ed1A7Dc6f7B508C02d1b04ec88cC21bf"
STAKING_CONTRACT = "0x321b7ff75154472B18EDb199033fF4D116F340Ff"
NETWORK = "base-mainnet"

# ERC-20 selectors
_SEL_TOTAL_SUPPLY = "0x18160ddd"
_SEL_DECIMALS = "0x313ce567"
_SEL_BALANCE_OF = "0x70a08231"
_SEL_SYMBOL = "0x95d89b41"

_ADDR_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")

# Bounded in-process TTL cache. Capped at 256 entries (caps history growth
# from per-address balance queries) — for a single-instance deployment this
# is generous. Replace with Redis if scaling out.
_cache = TtlCache(max_size=256)
_META_TTL_SECONDS = 60.0
_BALANCE_TTL_SECONDS = 30.0

# One cached entry holds (decimals, total_raw, staked_raw) so /onchain/supply
# and /onchain/staking don't triple-fetch on a cold cache.
_META_CACHE_KEY = "vvv-erc20-meta"


def get_venice_client(settings: Settings = Depends(get_settings)) -> VeniceAPIClient:
    api_key = settings.VENICE_API_KEY or settings.VENICE_ADMIN_KEY
    return VeniceAPIClient(api_key)


def _pad_address(address: str) -> str:
    return address.lower().replace("0x", "").zfill(64)


def _decode_uint(hex_value: str) -> int:
    if not hex_value or hex_value == "0x":
        return 0
    return int(hex_value, 16)


async def _rpc(
    client: VeniceAPIClient,
    method: str,
    params: list,
) -> Any:
    # Venice crypto RPC path is /crypto/rpc/{network} with a JSON-RPC body.
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }
    data = await client.post_json(f"/crypto/rpc/{NETWORK}", data=payload, timeout=30.0)
    if isinstance(data, dict) and "error" in data and data["error"]:
        raise HTTPException(502, f"RPC error: {data['error']}")
    # Some gateways wrap result under data
    if isinstance(data, dict) and "result" in data:
        return data["result"]
    if isinstance(data, dict) and "data" in data:
        inner = data["data"]
        if isinstance(inner, dict) and "result" in inner:
            return inner["result"]
        return inner
    return data


async def _eth_call(client: VeniceAPIClient, to: str, data: str) -> str:
    result = await _rpc(
        client,
        "eth_call",
        [{"to": to, "data": data}, "latest"],
    )
    if not isinstance(result, str):
        raise HTTPException(502, f"Unexpected eth_call result: {result!r}")
    return result


async def _fetch_vvv_erc20_meta(client: VeniceAPIClient) -> Dict[str, int]:
    """Cached read of (decimals, totalSupply, stakedRaw). One entry per TTL
    so /onchain/supply and /onchain/staking share the bound check."""
    cached = _cache.get(_META_CACHE_KEY)
    if cached is not None:
        return cached
    decimals = _decode_uint(await _eth_call(client, VVV_TOKEN, _SEL_DECIMALS))
    total_raw = _decode_uint(await _eth_call(client, VVV_TOKEN, _SEL_TOTAL_SUPPLY))
    staked_raw = _decode_uint(
        await _eth_call(
            client, VVV_TOKEN, _SEL_BALANCE_OF + _pad_address(STAKING_CONTRACT)
        )
    )
    meta = {"decimals": decimals, "total_raw": total_raw, "staked_raw": staked_raw}
    _cache.set(_META_CACHE_KEY, meta, ttl=_META_TTL_SECONDS)
    return meta


@router.get("/onchain/supply")
async def get_onchain_supply(
    client: VeniceAPIClient = Depends(get_venice_client),
):
    """VVV total supply on Base via Venice crypto RPC."""
    cached = _cache.get("supply")
    if cached is not None:
        return cached

    try:
        meta = await _fetch_vvv_erc20_meta(client)
        scale = 10 ** meta["decimals"]
        total = meta["total_raw"] / scale
        staked = meta["staked_raw"] / scale
        circulating_est = max(total - staked, 0.0)

        result = {
            "network": NETWORK,
            "token_address": VVV_TOKEN,
            "staking_contract": STAKING_CONTRACT,
            "decimals": meta["decimals"],
            "total_supply": total,
            "staked_in_contract": staked,
            "circulating_estimate": circulating_est,
            "total_supply_raw": str(meta["total_raw"]),
            "staked_raw": str(meta["staked_raw"]),
        }
        _cache.set("supply", result)
        return result
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch on-chain supply")
        raise HTTPException(500, "Failed to fetch on-chain supply")


@router.get("/onchain/staking")
async def get_onchain_staking(
    client: VeniceAPIClient = Depends(get_venice_client),
):
    """Staking pool stats derived from VVV balance of the staking contract."""
    cached = _cache.get("staking")
    if cached is not None:
        return cached

    try:
        meta = await _fetch_vvv_erc20_meta(client)
        scale = 10 ** meta["decimals"]
        total = meta["total_raw"] / scale
        staked = meta["staked_raw"] / scale
        pct = (staked / total * 100.0) if total else 0.0

        result = {
            "network": NETWORK,
            "token_address": VVV_TOKEN,
            "staking_contract": STAKING_CONTRACT,
            "staked_vvv": staked,
            "total_supply": total,
            "staked_percent": pct,
            "note": (
                "staked_vvv is the VVV ERC-20 balance of the Venice staking contract. "
                "APY and staker count require additional contract reads not yet wired."
            ),
        }
        _cache.set("staking", result)
        return result
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch on-chain staking")
        raise HTTPException(500, "Failed to fetch on-chain staking")


@router.get("/onchain/balance/{address}")
async def get_onchain_balance(
    address: str,
    client: VeniceAPIClient = Depends(get_venice_client),
):
    """VVV balance for a wallet on Base."""
    if not _ADDR_RE.match(address):
        raise HTTPException(400, "Invalid EVM address")

    cache_key = f"bal:{address.lower()}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        meta = await _fetch_vvv_erc20_meta(client)
        bal_raw = _decode_uint(
            await _eth_call(
                client, VVV_TOKEN, _SEL_BALANCE_OF + _pad_address(address)
            )
        )
        scale = 10 ** meta["decimals"]
        result = {
            "network": NETWORK,
            "address": address,
            "token_address": VVV_TOKEN,
            "vvv_balance": bal_raw / scale,
            "vvv_balance_raw": str(bal_raw),
            "decimals": meta["decimals"],
        }
        _cache.set(cache_key, result, ttl=_BALANCE_TTL_SECONDS)
        return result
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch on-chain balance")
        raise HTTPException(500, "Failed to fetch on-chain balance")
