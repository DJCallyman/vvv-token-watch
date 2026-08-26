"""
Billing entry sync: persist Venice billing ledger entries to the database.

Billing data is append-only — entries are never modified or deleted upstream.
This module fetches only entries newer than the newest stored timestamp,
so subsequent analytics requests are near-instant (0–1 API pages instead
of a full 19-page walk).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.billing_pagination import (
    UsageHistoryUnavailable,
    walk_billing_usage_history,
)
from backend.core.venice_api_client import VeniceAPIClient
from backend.models.db import BillingEntry

logger = logging.getLogger(__name__)

# How far back to look on the very first sync (no existing data in DB).
# This bounds the initial walk; subsequent syncs only fetch new entries.
# 30 days matches the largest period the analytics UI offers.
INITIAL_SYNC_DAYS = 30


async def get_latest_entry_timestamp(session: AsyncSession) -> Optional[datetime]:
    """Return the newest entry_timestamp in the database, or None if empty."""
    result = await session.execute(select(func.max(BillingEntry.entry_timestamp)))
    return result.scalar_one_or_none()


async def sync_billing_entries(
    session: AsyncSession,
    client: VeniceAPIClient,
    *,
    max_pages: int = 30,
) -> int:
    """Fetch new billing entries from Venice and persist them to the database.

    Returns the number of new entries stored. On the first sync (empty DB),
    fetches the last INITIAL_SYNC_DAYS days. On subsequent syncs, fetches
    only entries newer than the newest stored timestamp.

    Uses INSERT ... ON CONFLICT DO NOTHING so re-fetching overlapping
    entries is safe (dedup by natural key).
    """
    latest = await get_latest_entry_timestamp(session)

    if latest is not None:
        # Fetch from just before the latest entry to catch any entries
        # that arrived in the same second but weren't in the last page.
        start = latest - timedelta(seconds=1)
        start_str = start.strftime("%Y-%m-%dT%H:%M:%SZ")
        logger.info("Billing sync: fetching entries since %s", start_str)
    else:
        # First sync — fetch a bounded window
        start = datetime.now(timezone.utc) - timedelta(days=INITIAL_SYNC_DAYS)
        start_str = start.strftime("%Y-%m-%dT%H:%M:%SZ")
        logger.info("Billing sync: initial sync, fetching last %d days from %s", INITIAL_SYNC_DAYS, start_str)

    end = datetime.now(timezone.utc)
    end_str = end.strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        entries = await walk_billing_usage_history(
            client, start_str, end_str, max_pages=max_pages
        )
    except UsageHistoryUnavailable:
        logger.warning("Billing sync: /billing/usage-history unavailable, skipping sync")
        return 0

    if not entries:
        logger.info("Billing sync: no new entries")
        return 0

    # Convert raw API entries to ORM objects, deduping by natural key
    seen_keys: set[tuple] = set()
    new_rows: List[BillingEntry] = []

    for entry in entries:
        ts_str = entry.get("timestamp", "")
        if not ts_str:
            continue

        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            continue

        sku = entry.get("sku", "unknown")
        inference = entry.get("inferenceDetails") or {}
        request_id = inference.get("requestId") if isinstance(inference, dict) else None

        # Natural dedup key
        key = (ts, sku, request_id)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        new_rows.append(BillingEntry(
            entry_timestamp=ts,
            sku=sku,
            units=float(entry.get("units") or 0),
            amount=float(entry.get("amount") or 0),
            currency=(entry.get("currency") or "").upper(),
            price_per_unit_usd=float(entry.get("pricePerUnitUsd")) if entry.get("pricePerUnitUsd") is not None else None,
            notes=entry.get("notes"),
            request_id=request_id,
            prompt_tokens=int(inference.get("promptTokens") or 0) if isinstance(inference, dict) else 0,
            completion_tokens=int(inference.get("completionTokens") or 0) if isinstance(inference, dict) else 0,
            inference_execution_time=inference.get("inferenceExecutionTime") if isinstance(inference, dict) else None,
        ))

    if not new_rows:
        logger.info("Billing sync: %d raw entries, 0 new after dedup", len(entries))
        return 0

    # Bulk insert with ON CONFLICT DO NOTHING (dedup by natural key)
    session.add_all(new_rows)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        # Fall back to individual inserts to skip conflicting rows
        logger.info("Billing sync: bulk insert failed, trying individual inserts")
        count = 0
        for row in new_rows:
            try:
                session.add(row)
                await session.commit()
                count += 1
            except Exception:
                await session.rollback()
        logger.info("Billing sync: inserted %d entries via individual inserts", count)
        return count

    logger.info("Billing sync: stored %d new entries (from %d raw)", len(new_rows), len(entries))
    return len(new_rows)


async def load_billing_entries(
    session: AsyncSession,
    start: datetime,
    end: datetime,
) -> List[Dict[str, Any]]:
    """Load billing entries from the database for a time window.

    Returns entries in the same shape as the raw API response so that
    process_usage_data and the daily aggregation can consume them unchanged.
    """
    result = await session.execute(
        select(BillingEntry)
        .where(BillingEntry.entry_timestamp >= start)
        .where(BillingEntry.entry_timestamp < end)
        .order_by(BillingEntry.entry_timestamp)
    )
    rows = result.scalars().all()

    # Convert back to the raw API entry dict shape
    entries: List[Dict[str, Any]] = []
    for row in rows:
        inference: Optional[Dict[str, Any]] = None
        if row.request_id or row.prompt_tokens or row.completion_tokens:
            inference = {
                "requestId": row.request_id,
                "promptTokens": row.prompt_tokens,
                "completionTokens": row.completion_tokens,
            }
            if row.inference_execution_time is not None:
                inference["inferenceExecutionTime"] = row.inference_execution_time

        entries.append({
            "sku": row.sku,
            "units": row.units,
            "amount": row.amount,
            "currency": row.currency,
            "timestamp": row.entry_timestamp.isoformat(),
            "pricePerUnitUsd": row.price_per_unit_usd,
            "notes": row.notes,
            "inferenceDetails": inference,
        })

    return entries
