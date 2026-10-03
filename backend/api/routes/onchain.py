"""On-chain VVV data via Venice crypto RPC (Base) and venicestats.com.

Supply and staking KPIs (total supply, staked ratio, APR, free float)
come from the free venicestats REST API (no auth) — one HTTP call replaces
several eth_call round-trips. Per-address balance and transfer history
still use Venice crypto RPC.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.config import Settings, get_settings
from backend.core import venicestats_client
from backend.core.cache import TtlCache
from backend.core.venice_api_client import VeniceAPIClient
from backend.core.venicestats_client import VeniceStatsError

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
_TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

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


def _topic_address(topic: str) -> str:
    return "0x" + topic[-40:]


@router.get("/onchain/transfers")
async def get_onchain_transfers(
    address: str = Query(...),
    blocks: int = Query(10000, ge=100, le=100000),
    client: VeniceAPIClient = Depends(get_venice_client),
):
    """Return recent VVV ERC-20 transfers involving a Base wallet."""
    if not _ADDR_RE.match(address):
        raise HTTPException(400, "Invalid EVM address")
    normalized = address.lower()
    cache_key = f"transfers:{normalized}:{blocks}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        latest = _decode_uint(await _rpc(client, "eth_blockNumber", []))
        from_block = max(0, latest - blocks)
        padded = _pad_address(normalized)
        logs = await _rpc(client, "eth_getLogs", [{
            "address": VVV_TOKEN,
            "fromBlock": hex(from_block),
            "toBlock": hex(latest),
            "topics": [_TRANSFER_TOPIC, None, None],
        }])
        if not isinstance(logs, list):
            raise HTTPException(502, "Unexpected transfer log response")
        meta = await _fetch_vvv_erc20_meta(client)
        scale = 10 ** meta["decimals"]
        transfers = []
        for log in logs:
            topics = log.get("topics") or []
            if len(topics) < 3 or (padded not in (topics[1][-64:].lower(), topics[2][-64:].lower())):
                continue
            raw = _decode_uint(log.get("data", "0x0"))
            sender = _topic_address(topics[1])
            recipient = _topic_address(topics[2])
            transfers.append({
                "from": sender, "to": recipient, "value": str(raw), "value_human": raw / scale,
                "tx_hash": log.get("transactionHash"), "block_number": log.get("blockNumber"),
                "log_index": log.get("logIndex"), "direction": "in" if recipient == normalized else "out",
            })
        result = {"network": NETWORK, "address": address, "token_address": VVV_TOKEN, "transfers": transfers, "count": len(transfers), "from_block": hex(from_block), "to_block": hex(latest)}
        _cache.set(cache_key, result, ttl=60)
        return result
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch on-chain transfers")
        raise HTTPException(500, "Failed to fetch on-chain transfers")


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
    settings: Settings = Depends(get_settings),
):
    """VVV supply decomposition via venicestats (one HTTP call, no RPC)."""
    cached = _cache.get("supply")
    if cached is not None:
        return cached

    try:
        m = await venicestats_client.get_metrics(settings)
        total = m.get("totalSupply")
        burned = m.get("burnedSupply") or 0.0
        staked = m.get("totalStaked") or 0.0
        if not isinstance(total, (int, float)):
            raise VeniceStatsError("Metrics payload missing totalSupply")
        circulating = m.get("circulatingSupply")
        if not isinstance(circulating, (int, float)):
            circulating = max(total - burned - staked, 0.0)

        result = {
            "network": NETWORK,
            "token_address": VVV_TOKEN,
            "staking_contract": STAKING_CONTRACT,
            "decimals": 18,
            "source": "venicestats",
            "total_supply": total,
            "staked_in_contract": staked,
            "circulating_estimate": circulating,
            "burned_supply": burned,
            "free_float": m.get("freeFloatVvv"),
            "free_float_pct_circulating": m.get("freeFloatVvvPctCirc"),
            "free_float_pct_total": m.get("freeFloatVvvPctTotal"),
        }
        _cache.set("supply", result)
        return result
    except HTTPException:
        raise
    except VeniceStatsError as e:
        raise HTTPException(502, f"VeniceStats error: {e}")
    except Exception:
        logger.exception("Failed to fetch on-chain supply")
        raise HTTPException(500, "Failed to fetch on-chain supply")


@router.get("/onchain/staking")
async def get_onchain_staking(
    client: VeniceAPIClient = Depends(get_venice_client),
    settings: Settings = Depends(get_settings),
):
    """Staking stats via venicestats — now includes APR (previously unavailable via RPC)."""
    cached = _cache.get("staking")
    if cached is not None:
        return cached

    try:
        m = await venicestats_client.get_metrics(settings)
        staked = m.get("totalStaked") or 0.0
        total = m.get("totalSupply")
        ratio = m.get("stakingRatio")
        apr = m.get("stakerApr")

        result = {
            "network": NETWORK,
            "token_address": VVV_TOKEN,
            "staking_contract": STAKING_CONTRACT,
            "staked_vvv": staked,
            "total_supply": total,
            "staked_percent": (ratio * 100.0) if isinstance(ratio, (int, float)) else None,
            "staking_ratio": ratio,
            "staking_ratio_change_24h": m.get("stakingRatioChange24h"),
            "apr": apr,
            "svvv_locked": m.get("svvvLocked"),
            "svvv_unlocked": m.get("svvvUnlocked"),
            "lock_ratio": m.get("lockRatio"),
            "staking_growth_7d": m.get("stakingGrowth7d"),
            "staking_growth_30d": m.get("stakingGrowth30d"),
            "cooldown_vvv": m.get("cooldownVvv"),
            "cooldown_wallets": m.get("cooldownWallets"),
            "source": "venicestats",
            "note": (
                "Staking ratio, APR, lock ratio and growth data from venicestats.com "
                "(free, no auth). Previously APY was not wired; it is now available."
            ),
        }
        _cache.set("staking", result)
        return result
    except HTTPException:
        raise
    except VeniceStatsError as e:
        raise HTTPException(502, f"VeniceStats error: {e}")
    except Exception:
        logger.exception("Failed to fetch on-chain staking")
        raise HTTPException(500, "Failed to fetch on-chain staking")


async def fetch_vvv_balance(address: str, client: VeniceAPIClient) -> Dict[str, Any]:
    """VVV balance for a wallet on Base (shared by route and prices route).

    Returns a dict with ``vvv_balance`` (human units) and metadata.
    """
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


@router.get("/onchain/balance/{address}")
async def get_onchain_balance(
    address: str,
    client: VeniceAPIClient = Depends(get_venice_client),
):
    """VVV balance for a wallet on Base."""
    return await fetch_vvv_balance(address, client)
