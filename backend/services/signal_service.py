"""Structured AI signal history and deterministic outcome tracking (Phase 3).

Signals record the model's direction, confidence, and rationale at creation.
Outcomes are evaluated deterministically against a supplied current price:

* ``bullish`` — hit when the current price is above the entry price.
* ``bearish`` — hit when the current price is below the entry price.
* ``neutral`` — hit when the absolute move is under 1%.

Missing prices leave the signal ``pending`` (never guessed).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.db import SignalRecord

logger = logging.getLogger(__name__)

NEUTRAL_HIT_BAND_PCT = 1.0
VALID_DIRECTIONS = ("bullish", "bearish", "neutral")
VALID_KINDS = ("sentiment", "x_sentiment", "manual", "analysis")


def evaluate_outcome(
    direction: str,
    entry_price_usd: Optional[float],
    current_price_usd: Optional[float],
) -> Dict[str, Any]:
    """Return ``{status, value_usd, note}`` for a signal outcome."""
    if entry_price_usd is None or current_price_usd is None or entry_price_usd == 0:
        return {
            "status": "pending",
            "value_usd": current_price_usd,
            "note": "Outcome requires both entry and current prices.",
        }
    change_pct = ((current_price_usd - entry_price_usd) / entry_price_usd) * 100.0
    normalized = (direction or "").lower()
    if normalized == "bullish":
        hit = change_pct > 0
    elif normalized == "bearish":
        hit = change_pct < 0
    else:
        hit = abs(change_pct) < NEUTRAL_HIT_BAND_PCT
    return {
        "status": "hit" if hit else "miss",
        "value_usd": current_price_usd,
        "note": (
            f"Move {change_pct:+.2f}% from entry {entry_price_usd:.6f} to "
            f"{current_price_usd:.6f}; neutral band is ±{NEUTRAL_HIT_BAND_PCT}%."
        ),
    }


def signal_dict(row: SignalRecord) -> Dict[str, Any]:
    def _loads(value: str, fallback: Any) -> Any:
        try:
            parsed = json.loads(value)
            return parsed
        except (TypeError, json.JSONDecodeError):
            return fallback

    return {
        "id": row.id,
        "kind": row.kind,
        "subject": row.subject,
        "direction": row.direction,
        "confidence": row.confidence,
        "rationale": row.rationale,
        "sources": _loads(row.sources, []),
        "metrics": _loads(row.metrics, {}),
        "entry_price_usd": row.entry_price_usd,
        "outcome_status": row.outcome_status,
        "outcome_value_usd": row.outcome_value_usd,
        "outcome_note": row.outcome_note,
        "evaluated_at": row.evaluated_at.isoformat() if row.evaluated_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


async def record_signal(
    db: AsyncSession,
    *,
    kind: str,
    subject: str = "vvv",
    direction: str,
    confidence: float,
    rationale: str = "",
    sources: Optional[List[str]] = None,
    metrics: Optional[Dict[str, Any]] = None,
    entry_price_usd: Optional[float] = None,
) -> SignalRecord:
    normalized_direction = (direction or "neutral").lower()
    if normalized_direction not in VALID_DIRECTIONS:
        normalized_direction = "neutral"
    row = SignalRecord(
        kind=kind if kind in VALID_KINDS else "manual",
        subject=(subject or "vvv").lower(),
        direction=normalized_direction,
        confidence=max(0.0, min(100.0, float(confidence or 0.0))),
        rationale=rationale or "",
        sources=json.dumps(sources or []),
        metrics=json.dumps(metrics or {}),
        entry_price_usd=entry_price_usd,
        outcome_status="pending",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def list_signals(
    db: AsyncSession,
    *,
    limit: int = 50,
    subject: Optional[str] = None,
    kind: Optional[str] = None,
) -> List[SignalRecord]:
    stmt = select(SignalRecord).order_by(SignalRecord.created_at.desc()).limit(limit)
    if subject:
        stmt = stmt.where(SignalRecord.subject == subject.lower())
    if kind:
        stmt = stmt.where(SignalRecord.kind == kind)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def evaluate_signal(
    db: AsyncSession,
    signal_id: int,
    current_price_usd: Optional[float],
) -> Optional[SignalRecord]:
    row = await db.get(SignalRecord, signal_id)
    if row is None:
        return None
    outcome = evaluate_outcome(row.direction, row.entry_price_usd, current_price_usd)
    row.outcome_status = outcome["status"]
    row.outcome_value_usd = outcome["value_usd"]
    row.outcome_note = outcome["note"]
    if outcome["status"] != "pending":
        row.evaluated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(row)
    return row


def extract_entry_price(prices: Dict[str, Any]) -> Optional[float]:
    """Best-effort extraction of a VVV entry price from insight request data."""
    if not isinstance(prices, dict):
        return None
    direct = prices.get("vvv_price_usd")
    if isinstance(direct, (int, float)):
        return float(direct)
    vvv = prices.get("vvv")
    if isinstance(vvv, dict):
        usd = vvv.get("usd")
        if isinstance(usd, (int, float)):
            return float(usd)
    return None
