"""Thin async client for the free venicestats.com REST API.

No auth required. Primary surfaces used by this app:

- ``GET /api/metrics``  — 60+ protocol KPIs in one payload (VVV/DIEM prices,
  24h change, market cap, FDV, supply decomposition, staking ratio, APR,
  free float). See https://venicestats.com/developers.
- ``GET /api/charts?metric=`` — historical time-series (LTTB-sampled,
  up to 200 points) for ``vvvPrice``, ``diemPrice``, ``stakingRatio`` etc.

Also hosts the USD→AUD conversion helper backed by frankfurter.dev (free
ECB daily FX rates, no key). ECB rates update once daily, so the AUD rate
is cached for an hour without loss of fidelity.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, TypedDict

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from backend.config import Settings, get_settings
from backend.core.cache import TtlCache

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://venicestats.com/api"
_FRANKFURTER_BASE_URL = "https://api.frankfurter.dev/v1"

# Module-level caches: prices are volatile (short TTL); FX rates change
# daily (long TTL). Bounded per TtlCache semantics.
_metrics_cache = TtlCache(max_size=8)
_chart_cache = TtlCache(max_size=64)
_fx_cache = TtlCache(max_size=8)

_METRICS_TTL_SECONDS = 30.0
_CHART_TTL_SECONDS = 300.0
_FX_TTL_SECONDS = 3600.0


class VeniceStatsError(Exception):
    """Raised when venicestats or the FX service cannot be reached."""


class _SharedClient:
    """Lazily-created pooled httpx client shared across calls."""

    _client: Optional[httpx.AsyncClient] = None

    @classmethod
    def get(cls) -> httpx.AsyncClient:
        if cls._client is None or cls._client.is_closed:
            cls._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                headers={"User-Agent": "vvv-token-watch/1.0"},
                follow_redirects=True,
            )
        return cls._client


async def aclose() -> None:
    """Close the pooled HTTP client (call on app shutdown if needed)."""
    if _SharedClient._client is not None and not _SharedClient._client.is_closed:
        await _SharedClient._client.aclose()
    _SharedClient._client = None


async def _request_json(url: str, params: Optional[dict] = None) -> Any:
    """GET a JSON document with bounded retry on transient network errors."""
    client = _SharedClient.get()
    attempt = AsyncRetrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
        reraise=True,
    )
    try:
        async for state in attempt:
            with state:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
    except httpx.HTTPStatusError as exc:
        raise VeniceStatsError(f"Upstream HTTP {exc.response.status_code}") from exc
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise VeniceStatsError("Upstream unavailable") from exc


async def get_metrics(settings: Optional[Settings] = None) -> dict:
    """Return the full venicestats KPI payload (cached ~30s)."""
    settings = settings or get_settings()
    cached = _metrics_cache.get("metrics")
    if cached is not None:
        return cached
    payload = await _request_json(f"{settings.VENICESTATS_BASE_URL}/metrics")
    if not isinstance(payload, dict):
        raise VeniceStatsError("Unexpected /api/metrics payload")
    _metrics_cache.set("metrics", payload, ttl=_METRICS_TTL_SECONDS)
    return payload


async def get_chart(metric: str, settings: Optional[Settings] = None) -> list:
    """Return a single LTTB-sampled time-series from /api/charts."""
    settings = settings or get_settings()
    key = f"chart:{metric}"
    cached = _chart_cache.get(key)
    if cached is not None:
        return cached
    payload = await _request_json(
        f"{settings.VENICESTATS_BASE_URL}/charts", params={"metric": metric}
    )
    points = payload.get(metric) if isinstance(payload, dict) else payload
    if not isinstance(points, list):
        raise VeniceStatsError(f"Unexpected /api/charts payload for {metric}")
    _chart_cache.set(key, points, ttl=_CHART_TTL_SECONDS)
    return points


async def get_usd_aud_rate(settings: Optional[Settings] = None) -> float:
    """Return the USD→AUD conversion rate (cached ~1h; ECB daily rates)."""
    cached = _fx_cache.get("usd_aud")
    if cached is not None:
        return cached
    payload = await _request_json(
        f"{settings.FRANKFURTER_BASE_URL}/latest" if settings else f"{_FRANKFURTER_BASE_URL}/latest",
        params={"base": "USD", "symbols": "AUD"},
    )
    rate = payload.get("rates", {}).get("AUD") if isinstance(payload, dict) else None
    if not isinstance(rate, (int, float)) or rate <= 0:
        raise VeniceStatsError("Unexpected frankfurter payload")
    _fx_cache.set("usd_aud", float(rate), ttl=_FX_TTL_SECONDS)
    return float(rate)


# ---------------------------------------------------------------------------
# Wallet holdings (venicestats /api/venetians)
# ---------------------------------------------------------------------------

# Cache for wallet identity/balance payloads keyed by lowercase address.
_wallet_cache = TtlCache(max_size=64)
_WALLET_TTL_SECONDS = 60.0


class WalletHoldings(TypedDict):
    """Wallet balances as reported by venicestats.

    ``vvv_wallet``  — unstaked VVV at the address
    ``svvv_total``  — total staked position (sVVV)
    ``svvv_locked`` — portion locked (in cooldown commitment)
    ``pending_rewards`` — unclaimed staking earnings
    ``diem_wallet`` — unstaked DIEM at the address
    ``diem_staked`` — DIEM locked in staking
    """

    vvv_wallet: float
    svvv_total: float
    svvv_locked: float
    pending_rewards: float
    diem_wallet: float
    diem_staked: float


async def get_wallet_holdings(
    address: str, settings: Optional[Settings] = None
) -> WalletHoldings:
    """Fetch wallet balances from venicestats /api/venetians (60s TTL).

    Raises ``VeniceStatsError`` on upstream failure or if the address is
    not recognised.
    """
    key = address.lower()
    cached = _wallet_cache.get(key)
    if cached is not None:
        return cached
    settings = settings or get_settings()
    payload = await _request_json(
        f"{settings.VENICESTATS_BASE_URL}/venetians", params={"address": address}
    )
    if not isinstance(payload, dict) or not payload.get("address"):
        raise VeniceStatsError(f"Wallet {address} not found on venicestats")

    def _num(value: Any) -> float:
        return float(value) if isinstance(value, (int, float)) else 0.0

    holdings: WalletHoldings = {
        "vvv_wallet": _num(payload.get("vvvBalance")),
        "svvv_total": _num(payload.get("svvvBalance")),
        "svvv_locked": _num(payload.get("svvvLocked")),
        "pending_rewards": _num(payload.get("pendingRewards")),
        "diem_wallet": _num(payload.get("diemBalance")),
        "diem_staked": _num(payload.get("diemStaked")),
    }
    _wallet_cache.set(key, holdings, ttl=_WALLET_TTL_SECONDS)
    return holdings
