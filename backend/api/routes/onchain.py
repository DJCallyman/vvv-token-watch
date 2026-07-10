"""On-chain VVV data via Venice crypto RPC (Base)."""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.config import Settings, get_settings
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

# Simple in-process TTL cache: key -> (expires_at, value)
_cache: Dict[str, Tuple[float, Any]] = {}
_CACHE_TTL = 60.0


def get_venice_client(settings: Settings = Depends(get_settings)) -> VeniceAPIClient:
    api_key = settings.VENICE_API_KEY or settings.VENICE_ADMIN_KEY
    return VeniceAPIClient(api_key)


def _cache_get(key: str) -> Optional[Any]:
    item = _cache.get(key)
    if not item:
        return None
    expires, value = item
    if time.time() > expires:
        _cache.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: Any, ttl: float = _CACHE_TTL) -> None:
    _cache[key] = (time.time() + ttl, value)


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


async def _erc20_total_supply(client: VeniceAPIClient, token: str) -> int:
    return _decode_uint(await _eth_call(client, token, _SEL_TOTAL_SUPPLY))


async def _erc20_decimals(client: VeniceAPIClient, token: str) -> int:
    return _decode_uint(await _eth_call(client, token, _SEL_DECIMALS))


async def _erc20_balance(client: VeniceAPIClient, token: str, holder: str) -> int:
    data = _SEL_BALANCE_OF + _pad_address(holder)
    return _decode_uint(await _eth_call(client, token, data))


@router.get("/onchain/supply")
async def get_onchain_supply(
    client: VeniceAPIClient = Depends(get_venice_client),
):
    """VVV total supply on Base via Venice crypto RPC."""
    cached = _cache_get("supply")
    if cached is not None:
        return cached

    try:
        decimals = await _erc20_decimals(client, VVV_TOKEN)
        total_raw = await _erc20_total_supply(client, VVV_TOKEN)
        # Staking contract VVV balance ≈ staked amount (tokens locked in contract).
        staked_raw = await _erc20_balance(client, VVV_TOKEN, STAKING_CONTRACT)

        scale = 10 ** decimals
        total = total_raw / scale
        staked = staked_raw / scale
        circulating_est = max(total - staked, 0.0)

        result = {
            "network": NETWORK,
            "token_address": VVV_TOKEN,
            "staking_contract": STAKING_CONTRACT,
            "decimals": decimals,
            "total_supply": total,
            "staked_in_contract": staked,
            "circulating_estimate": circulating_est,
            "total_supply_raw": str(total_raw),
            "staked_raw": str(staked_raw),
        }
        _cache_set("supply", result)
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
    cached = _cache_get("staking")
    if cached is not None:
        return cached

    try:
        decimals = await _erc20_decimals(client, VVV_TOKEN)
        total_raw = await _erc20_total_supply(client, VVV_TOKEN)
        staked_raw = await _erc20_balance(client, VVV_TOKEN, STAKING_CONTRACT)
        scale = 10 ** decimals
        total = total_raw / scale
        staked = staked_raw / scale
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
        _cache_set("staking", result)
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
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        decimals = await _erc20_decimals(client, VVV_TOKEN)
        bal_raw = await _erc20_balance(client, VVV_TOKEN, address)
        # Staking contract may hold sVVV; for now report VVV ERC-20 balance only.
        scale = 10 ** decimals
        result = {
            "network": NETWORK,
            "address": address,
            "token_address": VVV_TOKEN,
            "vvv_balance": bal_raw / scale,
            "vvv_balance_raw": str(bal_raw),
            "decimals": decimals,
        }
        _cache_set(cache_key, result, ttl=30.0)
        return result
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch on-chain balance")
        raise HTTPException(500, "Failed to fetch on-chain balance")
