"""Shared SlowAPI limiter instance.

Kept in its own module so route files can decorate endpoints without
circular imports through backend.main.

SEC-09: proxy-aware key function. When the direct peer is a configured
trusted proxy, the first value of X-Forwarded-For is used as the client
identity for rate limiting. Never trust XFF from untrusted peers.
"""

from __future__ import annotations

import logging
from typing import Optional

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from backend.config import get_settings

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """Return a stable client identifier for rate limiting.

    - If the direct peer IP is in TRUSTED_PROXY_IPS, use the first
      (leftmost) value from the X-Forwarded-For header.
    - Otherwise fall back to the direct peer IP (get_remote_address).
    - Never trust X-Forwarded-For from an untrusted direct peer.
    """
    try:
        settings = get_settings()
        trusted = set(settings.trusted_proxy_ips_list)

        peer_ip: Optional[str] = None
        if request.client and request.client.host:
            peer_ip = request.client.host

        # Check X-Forwarded-For only when peer is trusted
        if peer_ip and peer_ip in trusted:
            xff = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
            if xff:
                # XFF format: "client, proxy1, proxy2"
                first = xff.split(",")[0].strip()
                if first:
                    return first

        # Fall back to direct peer or localhost
        if peer_ip:
            return peer_ip
        return get_remote_address(request)
    except Exception:
        # Defensive: never let rate-limit key derivation crash a request
        logger.exception("Failed to derive rate-limit client IP; falling back to remote address")
        try:
            return get_remote_address(request)
        except Exception:
            return "127.0.0.1"


limiter = Limiter(key_func=get_client_ip)
