"""Explicit chain and token registry (Slice 2.6).

A network or token is only usable when it appears in ``APPROVED_CHAIN_KEYS``.
Every cache key and API response identifies the chain and token so adding a
network cannot silently change existing VVV/DIEM (Base) behavior.

Only Base mainnet is approved today. Slice 2.0 verified Base as the network
for the existing Venice deployments; additional chains require their own
verified token addresses and data sources.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Optional, Tuple


class UnsupportedPairError(ValueError):
    """Raised when a chain/token pair is not approved or not registered."""

    def __init__(self, message: str, *, allowed: Tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.allowed = allowed


@dataclass(frozen=True)
class TokenInfo:
    symbol: str
    decimals: int
    address: Optional[str]
    data_sources: Tuple[str, ...]


@dataclass(frozen=True)
class ChainInfo:
    key: str
    chain_id: int
    display_name: str
    rpc_network: str
    explorer_base_url: str
    tokens: Mapping[str, TokenInfo]


BASE_MAINNET = ChainInfo(
    key="base-mainnet",
    chain_id=8453,
    display_name="Base",
    rpc_network="base-mainnet",
    explorer_base_url="https://basescan.org",
    tokens=MappingProxyType(
        {
            # Canonical Base contracts (from Venice docs).
            "vvv": TokenInfo(
                symbol="VVV",
                decimals=18,
                address="0xacfE6019Ed1A7Dc6f7B508C02d1b04ec88cC21bf",
                data_sources=("venicestats", "venice-rpc"),
            ),
            # DIEM balances are only reported by the VeniceStats wallet
            # lookup; no verified Base contract address is registered yet.
            "diem": TokenInfo(
                symbol="DIEM",
                decimals=18,
                address=None,
                data_sources=("venicestats",),
            ),
        }
    ),
)

_CHAINS: Mapping[str, ChainInfo] = MappingProxyType({BASE_MAINNET.key: BASE_MAINNET})

# A network is not approved until it appears here.
APPROVED_CHAIN_KEYS: Tuple[str, ...] = (BASE_MAINNET.key,)

STAKING_CONTRACT = "0x321b7ff75154472B18EDb199033fF4D116F340Ff"


def list_chains() -> Tuple[ChainInfo, ...]:
    return tuple(_CHAINS.values())


def get_chain(key: str) -> ChainInfo:
    chain = _CHAINS.get(key)
    if chain is None:
        raise UnsupportedPairError(
            f"Unsupported chain '{key}'. Approved chains: {', '.join(APPROVED_CHAIN_KEYS)}",
            allowed=APPROVED_CHAIN_KEYS,
        )
    return chain


def get_token(chain_key: str, token: str) -> TokenInfo:
    chain = get_chain(chain_key)
    symbol = (token or "").lower()
    info = chain.tokens.get(symbol)
    if info is None:
        raise UnsupportedPairError(
            f"Token '{token}' is not registered on {chain_key}. "
            f"Registered tokens: {', '.join(sorted(chain.tokens))}",
            allowed=tuple(sorted(chain.tokens)),
        )
    return info


def resolve_pair(chain_key: str, token: str) -> Tuple[ChainInfo, TokenInfo]:
    chain = get_chain(chain_key)
    return chain, get_token(chain_key, token)


def cache_key(*parts: str) -> str:
    """Build a namespaced cache key that always identifies chain and token."""
    return ":".join(part for part in parts if part)
