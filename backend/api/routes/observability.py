"""Rate-limit and RPC cost observability (Slice 2.7).

Three data sources, kept explicitly separate:

* ``app_limiter`` — this application's own SlowAPI request limits.
* ``upstream_rate_limits`` — Venice response headers observed in-process, and
  the experimental ``/api_keys/rate_limits/log`` events when an ADMIN key is
  available. Missing/forbidden/failed telemetry is reported as ``unavailable``,
  never as zero.
* ``rpc_costs`` — per-call Crypto RPC cost headers (authoritative), plus a
  coverage probe of ``/billing/usage-history``. Account-level reconciliation
  stays unverified unless RPC charges are actually found in the ledger.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from backend.config import Settings, get_settings
from backend.core import telemetry
from backend.core.cache import TtlCache
from backend.core.venice_api_client import VeniceAPIClient
from backend.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter()

_RPC_SKU_MARKERS = ("rpc", "crypto", "blockchain")

# Upstream probes are cached briefly so a dashboard refresh or several open
# tabs cannot hammer Venice's experimental/admin endpoints.
_probe_cache = TtlCache(max_size=8)
_RATE_LOG_TTL_SECONDS = 60.0
_BILLING_COVERAGE_TTL_SECONDS = 300.0


def get_admin_client(settings: Settings = Depends(get_settings)) -> VeniceAPIClient:
    return VeniceAPIClient(settings.VENICE_ADMIN_KEY)


async def _cached_probe(key: str, ttl: float, producer) -> Dict[str, Any]:
    cached = _probe_cache.get(key)
    if cached is not None:
        return cached
    result = await producer()
    _probe_cache.set(key, result, ttl=ttl)
    return result


async def _fetch_rate_limit_log(client: VeniceAPIClient) -> Dict[str, Any]:
    """Fetch the experimental Venice rate-limit event log.

    Treat missing, forbidden, and failed upstream telemetry as unavailable.
    Cached briefly so repeated dashboard refreshes do not repeat the probe.
    """
    return await _cached_probe(
        "rate-log", _RATE_LOG_TTL_SECONDS, lambda: _fetch_rate_limit_log_uncached(client)
    )


async def _fetch_rate_limit_log_uncached(client: VeniceAPIClient) -> Dict[str, Any]:
    try:
        response = await client.get("/api_keys/rate_limits/log", timeout=15.0)
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        return {
            "status": "unavailable",
            "reason": "upstream_unreachable",
            "detail": type(exc).__name__,
        }
    if response.status_code == 401:
        return {"status": "unavailable", "reason": "unauthorized"}
    if response.status_code == 403:
        return {"status": "unavailable", "reason": "forbidden_admin_key_required"}
    if response.status_code == 404:
        return {"status": "unavailable", "reason": "endpoint_unavailable"}
    if response.status_code >= 400:
        return {
            "status": "unavailable",
            "reason": "upstream_error",
            "detail": f"HTTP {response.status_code}",
        }
    try:
        payload = response.json()
    except Exception:
        return {"status": "unavailable", "reason": "invalid_payload"}
    events = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(events, list):
        return {"status": "unavailable", "reason": "invalid_payload"}
    return {
        "status": "ok",
        "events": events[:50],
        "count": len(events),
        "source": "GET /api_keys/rate_limits/log (experimental; last 50 exceeded-limit events)",
        "note": "No retention window is documented upstream; treat as best-effort.",
    }


@router.get("/observability/rate-limits")
@limiter.limit("30/minute")
async def get_rate_limits(
    request: Request,
    client: VeniceAPIClient = Depends(get_admin_client),
):
    upstream_events = await _fetch_rate_limit_log(client)
    return {
        "app_limiter": {
            "status": "ok",
            "note": (
                "This application's SlowAPI request limits are active and distinct "
                "from upstream Venice limits."
            ),
        },
        "upstream_headers": telemetry.rate_limit_snapshot(),
        "upstream_events": upstream_events,
    }


async def _check_billing_coverage(client: VeniceAPIClient) -> Dict[str, Any]:
    """Probe one page of /billing/usage-history for RPC charges.

    Returns ``confirmed`` only when RPC-like ledger entries are actually seen;
    absent coverage is reported as ``unverified`` rather than assumed.
    Cached briefly to bound upstream calls.
    """
    return await _cached_probe(
        "billing-coverage",
        _BILLING_COVERAGE_TTL_SECONDS,
        lambda: _check_billing_coverage_uncached(client),
    )


async def _check_billing_coverage_uncached(client: VeniceAPIClient) -> Dict[str, Any]:
    try:
        response = await client.get(
            "/billing/usage-history", params={"pageSize": 100}, timeout=30.0
        )
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        return {
            "status": "unavailable",
            "reason": "upstream_unreachable",
            "detail": type(exc).__name__,
        }
    if response.status_code in (401, 403):
        return {"status": "unavailable", "reason": "forbidden_admin_key_required"}
    if response.status_code >= 400:
        return {
            "status": "unavailable",
            "reason": "upstream_error",
            "detail": f"HTTP {response.status_code}",
        }
    try:
        payload = response.json()
    except Exception:
        return {"status": "unavailable", "reason": "invalid_payload"}
    entries = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        return {"status": "unavailable", "reason": "invalid_payload"}
    rpc_entries = 0
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        sku = str(entry.get("sku") or "").lower()
        if any(marker in sku for marker in _RPC_SKU_MARKERS):
            rpc_entries += 1
    if rpc_entries:
        return {
            "status": "confirmed",
            "scanned": len(entries),
            "rpc_entries": rpc_entries,
            "note": "RPC charges appear in the billing ledger sample.",
        }
    return {
        "status": "unverified",
        "scanned": len(entries),
        "rpc_entries": 0,
        "note": (
            "No RPC charges were found in the sampled billing page. Ledger coverage "
            "for RPC costs is not confirmed; account-level reconciliation is not used."
        ),
    }


@router.get("/observability/rpc-costs")
@limiter.limit("30/minute")
async def get_rpc_costs(
    request: Request,
    client: VeniceAPIClient = Depends(get_admin_client),
):
    coverage = await _check_billing_coverage(client)
    per_call = telemetry.rpc_cost_snapshot()
    return {
        "per_call": per_call,
        "billing_coverage": coverage,
        "account_reconciliation": {
            "status": "unverified" if coverage.get("status") != "confirmed" else "available",
            "note": (
                "USD, DIEM, bundled credits, earned credits, and refunds must be kept "
                "separate when reconciling; per-call headers remain the authoritative "
                "source until ledger coverage is confirmed."
            ),
        },
    }


@router.get("/observability/summary")
@limiter.limit("60/minute")
async def get_observability_summary(
    request: Request,
    client: VeniceAPIClient = Depends(get_admin_client),
):
    """Combined freshness/availability view for the dashboard card."""
    return {
        "headers": telemetry.venice_header_snapshot(),
        "rate_limits": telemetry.rate_limit_snapshot(),
        "rpc_costs": telemetry.rpc_cost_snapshot(),
        "upstream_events": await _fetch_rate_limit_log(client),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/observability/headers")
@limiter.limit("60/minute")
async def get_header_snapshot(request: Request):
    return telemetry.venice_header_snapshot()
