"""On-chain VVV data via Venice crypto RPC (Base) and venicestats.com.

Supply and staking KPIs (total supply, staked ratio, APR, free float)
come from the free venicestats REST API (no auth) — one HTTP call replaces
several eth_call round-trips. Per-address balance and transfer history
still use Venice crypto RPC.

Slice 2.6 routes every request through ``backend.core.chains``: cache keys
and responses identify chain and token, and unapproved pairs fail explicitly.
Slice 2.5 adds bounded staking-event history and an address-specific holder
lookup (all-holder enumeration is not available from the verified sources).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.config import Settings, get_settings
from backend.core import chains, venicestats_client
from backend.core.cache import TtlCache
from backend.core.chains import UnsupportedPairError
from backend.core.venice_api_client import VeniceAPIClient
from backend.core.venicestats_client import VeniceStatsError

logger = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_CHAIN = chains.BASE_MAINNET.key

# Backwards-compatible aliases for existing importers (assistant route).
VVV_TOKEN = chains.BASE_MAINNET.tokens["vvv"].address
STAKING_CONTRACT = chains.STAKING_CONTRACT
NETWORK = chains.BASE_MAINNET.rpc_network

# ERC-20 selectors
_SEL_TOTAL_SUPPLY = "0x18160ddd"
_SEL_DECIMALS = "0x313ce567"
_SEL_BALANCE_OF = "0x70a08231"
_SEL_SYMBOL = "0x95d89b41"
_TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

_ADDR_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")

_MAX_STAKING_EVENTS = 500

# Bounded in-process TTL cache. Capped at 256 entries (caps history growth
# from per-address balance queries) — for a single-instance deployment this
# is generous. Replace with Redis if scaling out.
_cache = TtlCache(max_size=256)
_META_TTL_SECONDS = 60.0
_BALANCE_TTL_SECONDS = 30.0
_HOLDINGS_TTL_SECONDS = 60.0


def get_venice_client(settings: Settings = Depends(get_settings)) -> VeniceAPIClient:
    api_key = settings.VENICE_API_KEY or settings.VENICE_ADMIN_KEY
    return VeniceAPIClient(api_key)


def _resolve(chain_key: str, token: str):
    try:
        return chains.resolve_pair(chain_key, token)
    except UnsupportedPairError as exc:
        raise HTTPException(400, str(exc)) from exc


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
    *,
    network: str,
) -> Any:
    # Venice crypto RPC path is /crypto/rpc/{network} with a JSON-RPC body.
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }
    data = await client.post_json(f"/crypto/rpc/{network}", data=payload, timeout=30.0)
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


async def _eth_call(
    client: VeniceAPIClient,
    to: str,
    data: str,
    *,
    network: str,
) -> str:
    result = await _rpc(
        client,
        "eth_call",
        [{"to": to, "data": data}, "latest"],
        network=network,
    )
    if not isinstance(result, str):
        raise HTTPException(502, f"Unexpected eth_call result: {result!r}")
    return result


def _topic_address(topic: str) -> str:
    return "0x" + topic[-40:]


def _require_token_address(token) -> str:
    if not token.address:
        raise HTTPException(
            400,
            f"Token {token.symbol} has no registered on-chain contract address; "
            "use the holder lookup (VeniceStats) instead",
        )
    return token.address


@router.get("/onchain/chains")
async def list_chains():
    """Return the approved chain and token registry."""
    return {
        "approved_chains": list(chains.APPROVED_CHAIN_KEYS),
        "chains": [
            {
                "key": chain.key,
                "chain_id": chain.chain_id,
                "display_name": chain.display_name,
                "rpc_network": chain.rpc_network,
                "explorer_base_url": chain.explorer_base_url,
                "tokens": [
                    {
                        "symbol": token.symbol,
                        "key": token_key,
                        "address": token.address,
                        "decimals": token.decimals,
                        "data_sources": list(token.data_sources),
                    }
                    for token_key, token in sorted(chain.tokens.items())
                ],
            }
            for chain in chains.list_chains()
        ],
    }


@router.get("/onchain/transfers")
async def get_onchain_transfers(
    address: str = Query(...),
    blocks: int = Query(10000, ge=100, le=100000),
    chain: str = DEFAULT_CHAIN,
    token: str = "vvv",
    client: VeniceAPIClient = Depends(get_venice_client),
):
    """Return recent VVV ERC-20 transfers involving a Base wallet."""
    return await fetch_transfers(address, blocks, chain, token, client)


async def fetch_transfers(
    address: str,
    blocks: int,
    chain_key: str,
    token_key: str,
    client: VeniceAPIClient,
) -> Dict[str, Any]:
    """Shared transfer lookup used by the route and the wallet session."""
    if not _ADDR_RE.match(address):
        raise HTTPException(400, "Invalid EVM address")
    chain_info, token_info = _resolve(chain_key, token_key)
    contract = _require_token_address(token_info)
    normalized = address.lower()
    cache_key = chains.cache_key("transfers", chain_info.key, token_info.symbol.lower(), normalized, str(blocks))
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        latest = _decode_uint(await _rpc(client, "eth_blockNumber", [], network=chain_info.rpc_network))
        from_block = max(0, latest - blocks)
        padded = _pad_address(normalized)
        logs = await _rpc(client, "eth_getLogs", [{
            "address": contract,
            "fromBlock": hex(from_block),
            "toBlock": hex(latest),
            "topics": [_TRANSFER_TOPIC, None, None],
        }], network=chain_info.rpc_network)
        if not isinstance(logs, list):
            raise HTTPException(502, "Unexpected transfer log response")
        meta = await _fetch_vvv_erc20_meta(client, chain_info, token_info)
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
        result = {
            "chain": chain_info.key,
            "network": chain_info.rpc_network,
            "token_symbol": token_info.symbol,
            "address": address,
            "token_address": contract,
            "transfers": transfers,
            "count": len(transfers),
            "from_block": hex(from_block),
            "to_block": hex(latest),
        }
        _cache.set(cache_key, result, ttl=60)
        return result
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch on-chain transfers")
        raise HTTPException(500, "Failed to fetch on-chain transfers")


async def _fetch_vvv_erc20_meta(client, chain_info, token_info) -> Dict[str, int]:
    """Cached read of (decimals, totalSupply, stakedRaw) per chain/token."""
    cache_key = chains.cache_key("erc20-meta", chain_info.key, token_info.symbol.lower())
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached
    contract = _require_token_address(token_info)
    decimals = _decode_uint(await _eth_call(client, contract, _SEL_DECIMALS, network=chain_info.rpc_network))
    total_raw = _decode_uint(await _eth_call(client, contract, _SEL_TOTAL_SUPPLY, network=chain_info.rpc_network))
    staked_raw = _decode_uint(
        await _eth_call(
            client,
            contract,
            _SEL_BALANCE_OF + _pad_address(chains.STAKING_CONTRACT),
            network=chain_info.rpc_network,
        )
    )
    meta = {"decimals": decimals, "total_raw": total_raw, "staked_raw": staked_raw}
    _cache.set(cache_key, meta, ttl=_META_TTL_SECONDS)
    return meta


@router.get("/onchain/supply")
async def get_onchain_supply(
    chain: str = DEFAULT_CHAIN,
    token: str = "vvv",
    client: VeniceAPIClient = Depends(get_venice_client),
    settings: Settings = Depends(get_settings),
):
    """VVV supply decomposition via venicestats (one HTTP call, no RPC)."""
    chain_info, token_info = _resolve(chain, token)
    if chain_info.key != chains.BASE_MAINNET.key or token_info.symbol != "VVV":
        raise HTTPException(
            400,
            "Supply decomposition is only available for VVV on base-mainnet",
        )
    cache_key = chains.cache_key("supply", chain_info.key, token_info.symbol.lower())
    cached = _cache.get(cache_key)
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
            "chain": chain_info.key,
            "network": chain_info.rpc_network,
            "token_symbol": token_info.symbol,
            "token_address": token_info.address,
            "staking_contract": chains.STAKING_CONTRACT,
            "decimals": token_info.decimals,
            "source": "venicestats",
            "total_supply": total,
            "staked_in_contract": staked,
            "circulating_estimate": circulating,
            "burned_supply": burned,
            "free_float": m.get("freeFloatVvv"),
            "free_float_pct_circulating": m.get("freeFloatVvvPctCirc"),
            "free_float_pct_total": m.get("freeFloatVvvPctTotal"),
        }
        _cache.set(cache_key, result)
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
    chain: str = DEFAULT_CHAIN,
    token: str = "vvv",
    client: VeniceAPIClient = Depends(get_venice_client),
    settings: Settings = Depends(get_settings),
):
    """Staking stats via venicestats — includes APR and lock metrics."""
    chain_info, token_info = _resolve(chain, token)
    if chain_info.key != chains.BASE_MAINNET.key or token_info.symbol != "VVV":
        raise HTTPException(
            400,
            "Staking stats are only available for VVV on base-mainnet",
        )
    cache_key = chains.cache_key("staking", chain_info.key, token_info.symbol.lower())
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        m = await venicestats_client.get_metrics(settings)
        staked = m.get("totalStaked") or 0.0
        total = m.get("totalSupply")
        ratio = m.get("stakingRatio")
        apr = m.get("stakerApr")

        result = {
            "chain": chain_info.key,
            "network": chain_info.rpc_network,
            "token_symbol": token_info.symbol,
            "token_address": token_info.address,
            "staking_contract": chains.STAKING_CONTRACT,
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
                "(free, no auth)."
            ),
        }
        _cache.set(cache_key, result)
        return result
    except HTTPException:
        raise
    except VeniceStatsError as e:
        raise HTTPException(502, f"VeniceStats error: {e}")
    except Exception:
        logger.exception("Failed to fetch on-chain staking")
        raise HTTPException(500, "Failed to fetch on-chain staking")


async def fetch_vvv_balance(address: str, client: VeniceAPIClient, chain_key: str = DEFAULT_CHAIN) -> Dict[str, Any]:
    """VVV balance for a wallet (shared by route and prices route)."""
    if not _ADDR_RE.match(address):
        raise HTTPException(400, "Invalid EVM address")
    chain_info, token_info = _resolve(chain_key, "vvv")
    contract = _require_token_address(token_info)

    cache_key = chains.cache_key("bal", chain_info.key, token_info.symbol.lower(), address.lower())
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        meta = await _fetch_vvv_erc20_meta(client, chain_info, token_info)
        bal_raw = _decode_uint(
            await _eth_call(
                client,
                contract,
                _SEL_BALANCE_OF + _pad_address(address),
                network=chain_info.rpc_network,
            )
        )
        scale = 10 ** meta["decimals"]
        result = {
            "chain": chain_info.key,
            "network": chain_info.rpc_network,
            "token_symbol": token_info.symbol,
            "address": address,
            "token_address": contract,
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
    chain: str = DEFAULT_CHAIN,
    token: str = "vvv",
    client: VeniceAPIClient = Depends(get_venice_client),
):
    """VVV balance for a wallet on the selected approved chain."""
    chain_info, token_info = _resolve(chain, token)
    if token_info.symbol != "VVV":
        raise HTTPException(400, f"{token_info.symbol} balance is not available via RPC")
    return await fetch_vvv_balance(address, client, chain_info.key)


@router.get("/onchain/staking/events")
async def get_staking_events(
    blocks: int = Query(10000, ge=100, le=100000),
    address: Optional[str] = Query(None),
    chain: str = DEFAULT_CHAIN,
    token: str = "vvv",
    client: VeniceAPIClient = Depends(get_venice_client),
):
    """Bounded staking event history derived from VVV transfers involving
    the staking contract.

    Stake = transfer into the staking contract; unstake = transfer out of it.
    Partial upstream history is never implied to be complete: the queried
    block range is reported in the response.
    """
    chain_info, token_info = _resolve(chain, token)
    if chain_info.key != chains.BASE_MAINNET.key or token_info.symbol != "VVV":
        raise HTTPException(400, "Staking events are only available for VVV on base-mainnet")
    if address is not None and not _ADDR_RE.match(address):
        raise HTTPException(400, "Invalid EVM address")
    contract = _require_token_address(token_info)
    normalized_address = address.lower() if address else None
    cache_key = chains.cache_key(
        "staking-events",
        chain_info.key,
        token_info.symbol.lower(),
        normalized_address or "all",
        str(blocks),
    )
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        latest = _decode_uint(await _rpc(client, "eth_blockNumber", [], network=chain_info.rpc_network))
        from_block = max(0, latest - blocks)

        query_topics: List[list] = [[_TRANSFER_TOPIC, None, None]]
        if normalized_address:
            padded = _pad_address(normalized_address)
            query_topics = [
                [_TRANSFER_TOPIC, padded, None],
                [_TRANSFER_TOPIC, None, padded],
            ]

        logs: List[dict] = []
        for topics in query_topics:
            batch = await _rpc(client, "eth_getLogs", [{
                "address": contract,
                "fromBlock": hex(from_block),
                "toBlock": hex(latest),
                "topics": topics,
            }], network=chain_info.rpc_network)
            if not isinstance(batch, list):
                raise HTTPException(502, "Unexpected staking log response")
            logs.extend(batch)

        meta = await _fetch_vvv_erc20_meta(client, chain_info, token_info)
        scale = 10 ** meta["decimals"]
        staking_address = chains.STAKING_CONTRACT.lower()
        events = []
        for log in logs:
            topics = log.get("topics") or []
            if len(topics) < 3:
                continue
            sender = _topic_address(topics[1]).lower()
            recipient = _topic_address(topics[2]).lower()
            if sender == staking_address or recipient == staking_address:
                if sender == staking_address:
                    direction = "unstake"
                    counterparty = recipient
                else:
                    direction = "stake"
                    counterparty = sender
                if normalized_address and counterparty != normalized_address:
                    continue
                raw = _decode_uint(log.get("data", "0x0"))
                events.append({
                    "direction": direction,
                    "counterparty": counterparty,
                    "value": str(raw),
                    "value_human": raw / scale,
                    "tx_hash": log.get("transactionHash"),
                    "block_number": log.get("blockNumber"),
                    "log_index": log.get("logIndex"),
                })
        truncated = len(events) > _MAX_STAKING_EVENTS
        events = events[:_MAX_STAKING_EVENTS]
        result = {
            "chain": chain_info.key,
            "network": chain_info.rpc_network,
            "token_symbol": token_info.symbol,
            "staking_contract": chains.STAKING_CONTRACT,
            "address": address,
            "events": events,
            "count": len(events),
            "truncated": truncated,
            "from_block": hex(from_block),
            "to_block": hex(latest),
            "source": "venice-rpc eth_getLogs (VVV Transfer logs involving the staking contract)",
            "note": (
                "Only the reported block range is queried; partial upstream history "
                "is not implied to be complete."
            ),
        }
        _cache.set(cache_key, result, ttl=60)
        return result
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch staking events")
        raise HTTPException(500, "Failed to fetch staking events")


@router.get("/onchain/holders/{address}")
async def get_holder_lookup(
    address: str,
    chain: str = DEFAULT_CHAIN,
    settings: Settings = Depends(get_settings),
):
    """Address-specific holder lookup via venicestats.

    Slice 2.0 verified only an address-specific lookup; no all-holder
    endpoint, freshness interval, or retention period is documented. Holder
    views are therefore restricted to this lookup.
    """
    if not _ADDR_RE.match(address):
        raise HTTPException(400, "Invalid EVM address")
    chain_info, _ = _resolve(chain, "vvv")
    if chain_info.key != chains.BASE_MAINNET.key:
        raise HTTPException(400, "Holder lookup is only available on base-mainnet")
    cache_key = chains.cache_key("holders", chain_info.key, address.lower())
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        holdings = await venicestats_client.get_wallet_holdings(address, settings)
        result = {
            "chain": chain_info.key,
            "address": address,
            "source": "venicestats",
            "holdings": dict(holdings),
            "all_holders_available": False,
            "note": (
                "All-holder enumeration is not available from the verified sources; "
                "this view supports a single address only."
            ),
        }
        _cache.set(cache_key, result, ttl=_HOLDINGS_TTL_SECONDS)
        return result
    except VeniceStatsError as e:
        raise HTTPException(502, f"VeniceStats error: {e}")
    except Exception:
        logger.exception("Failed to fetch holder lookup")
        raise HTTPException(500, "Failed to fetch holder lookup")
