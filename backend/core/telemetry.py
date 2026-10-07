"""In-process Venice telemetry captured from authoritative response headers.

Slice 2.7: upstream rate-limit and Crypto RPC cost data is read from the
response headers Venice returns (``X-Venice-RPC-Credits``,
``X-Venice-RPC-Cost-USD``, and rate-limit headers). Nothing is estimated from
call counts. This store is bounded and process-local; missing data is reported
as unavailable — never as zero.
"""

from __future__ import annotations

import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, Mapping, Optional

_MAX_SAMPLES = 200

_lock = threading.Lock()
_rpc_samples: Deque[Dict[str, Any]] = deque(maxlen=_MAX_SAMPLES)
_rpc_totals = {"cost_usd": 0.0, "credits": 0.0, "count": 0}
_header_state: Dict[str, Dict[str, Any]] = {}
_last_seen_at: Optional[str] = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_float(value: str) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def record_response(endpoint: str, headers: Mapping[str, str]) -> None:
    """Capture rate-limit and RPC cost headers from a Venice response."""
    global _last_seen_at
    lowered = {str(key).lower(): str(value) for key, value in headers.items()}
    if not lowered:
        return
    with _lock:
        timestamp = _now_iso()
        for key, value in lowered.items():
            if key.startswith("x-ratelimit") or key.startswith("x-venice"):
                _header_state[key] = {"value": value, "endpoint": endpoint, "timestamp": timestamp}
        _last_seen_at = timestamp

        cost = _parse_float(lowered.get("x-venice-rpc-cost-usd", ""))
        credits = _parse_float(lowered.get("x-venice-rpc-credits", ""))
        if cost is not None or credits is not None:
            sample = {
                "endpoint": endpoint,
                "cost_usd": cost,
                "credits": credits,
                "timestamp": timestamp,
            }
            _rpc_samples.append(sample)
            _rpc_totals["count"] += 1
            if cost is not None:
                _rpc_totals["cost_usd"] += cost
            if credits is not None:
                _rpc_totals["credits"] += credits


def rate_limit_snapshot() -> Dict[str, Any]:
    """Latest observed rate-limit header values with freshness."""
    with _lock:
        fields = {
            key: value
            for key, value in _header_state.items()
            if key.startswith("x-ratelimit")
        }
        last_seen = _last_seen_at
    if not fields:
        return {
            "status": "unavailable",
            "reason": "no_rate_limit_headers_observed",
            "note": "No Venice response has reported rate-limit headers yet.",
        }
    return {"status": "ok", "fields": fields, "last_seen_at": last_seen}


def rpc_cost_snapshot() -> Dict[str, Any]:
    """Per-call RPC cost data read from response headers only."""
    with _lock:
        samples = list(_rpc_samples)
        totals = dict(_rpc_totals)
    if not samples:
        return {
            "status": "unavailable",
            "reason": "no_rpc_cost_headers_observed",
            "note": (
                "No Venice Crypto RPC response has reported cost headers yet. "
                "Costs are never estimated from call counts."
            ),
        }
    latest_cost = next(
        (sample["cost_usd"] for sample in reversed(samples) if sample.get("cost_usd") is not None),
        None,
    )
    latest_credits = next(
        (sample["credits"] for sample in reversed(samples) if sample.get("credits") is not None),
        None,
    )
    return {
        "status": "ok",
        "totals": totals,
        "latest": {"cost_usd": latest_cost, "credits": latest_credits},
        "sample_count": len(samples),
        "samples": samples[-20:],
        "source": "X-Venice-RPC-Credits / X-Venice-RPC-Cost-USD response headers",
    }


def venice_header_snapshot() -> Dict[str, Any]:
    with _lock:
        fields = {key: dict(value) for key, value in _header_state.items()}
        last_seen = _last_seen_at
    if not fields:
        return {"status": "unavailable", "reason": "no_venice_headers_observed"}
    return {"status": "ok", "fields": fields, "last_seen_at": last_seen}


def reset_for_tests() -> None:
    global _last_seen_at
    with _lock:
        _rpc_samples.clear()
        _rpc_totals.update({"cost_usd": 0.0, "credits": 0.0, "count": 0})
        _header_state.clear()
        _last_seen_at = None
