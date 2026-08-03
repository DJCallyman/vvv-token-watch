"""
Small bounded TTL cache.

Used by in-process caches that must not grow unbounded (e.g. onchain
RPC responses keyed by wallet address). Eviction order is insertion-time
FIFO — simple and adequate for the small working set size we cap at.
Expired entries are dropped on read (lazy) and on insert when the cap is
exceeded.


This is a process-local cache; it does not survive restarts and is not
shared across replicas. For multi-replica deployments swap to Redis
behind the same get/set interface.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple


class TtlCache:
    """A simple TTL+bounded cache.

    Cap defaults to 256 entries; mostly arbitrary and protective —
    much more than the steady-state working set for onchain wallets.
    Drop oldest by insertion time when over cap.
    """

    DEFAULT_MAX_SIZE = 256

    def __init__(self, max_size: int = DEFAULT_MAX_SIZE):
        if max_size < 1:
            raise ValueError("max_size must be >= 1")
        self._data: Dict[str, Tuple[float, Any]] = {}
        self._order: List[str] = []
        self._max = max_size

    def get(self, key: str) -> Optional[Any]:
        item = self._data.get(key)
        if item is None:
            return None
        expires_at, value = item
        if time.time() > expires_at:
            self._evict(key)
            return None
        return value

    def set(self, key: str, value: Any, ttl: float = 60.0) -> None:
        if key in self._data:
            self._data[key] = (time.time() + ttl, value)
            return
        # New key: enforce capacity by dropping the oldest.
        if len(self._order) >= self._max:
            oldest = self._order.pop(0)
            self._data.pop(oldest, None)
        self._order.append(key)
        self._data[key] = (time.time() + ttl, value)

    def clear(self) -> None:
        self._data.clear()
        self._order.clear()

    def __len__(self) -> int:
        return len(self._data)

    def _evict(self, key: str) -> None:
        self._data.pop(key, None)
        try:
            self._order.remove(key)
        except ValueError:
            pass
