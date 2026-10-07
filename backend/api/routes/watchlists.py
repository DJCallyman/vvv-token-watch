"""Wallet and token watchlists (Slice 2.5).

Watchlist entries persist across reloads and identify the approved chain and
token. Addresses are validated; unapproved chains fail explicitly.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core import chains
from backend.core.chains import UnsupportedPairError
from backend.database import get_db
from backend.models.db import WatchlistItem

logger = logging.getLogger(__name__)
router = APIRouter()

_ADDR_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
DEFAULT_CHAIN = chains.BASE_MAINNET.key


class WatchlistCreate(BaseModel):
    address: str = Field(..., min_length=42, max_length=42)
    chain: str = Field(DEFAULT_CHAIN, min_length=1, max_length=64)
    token: str = Field("vvv", min_length=1, max_length=32)
    label: Optional[str] = Field(None, max_length=128)


def _item_dict(row: WatchlistItem) -> dict:
    return {
        "id": row.id,
        "chain": row.chain,
        "token": row.token,
        "address": row.address,
        "label": row.label,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/watchlists")
async def list_watchlist(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(WatchlistItem).order_by(WatchlistItem.id.asc()))
        rows = list(result.scalars().all())
        return {"items": [_item_dict(row) for row in rows], "count": len(rows)}
    except Exception:
        logger.exception("Failed to list watchlist")
        raise HTTPException(500, "Failed to list watchlist")


@router.post("/watchlists", status_code=201)
async def create_watchlist_item(
    body: WatchlistCreate,
    db: AsyncSession = Depends(get_db),
):
    if not _ADDR_RE.match(body.address):
        raise HTTPException(400, "Invalid EVM address")
    try:
        chains.resolve_pair(body.chain, body.token)
    except UnsupportedPairError as exc:
        raise HTTPException(400, str(exc)) from exc

    normalized = body.address.lower()
    existing = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.chain == body.chain,
            WatchlistItem.address == normalized,
        )
    )
    if existing.scalars().first() is not None:
        raise HTTPException(409, "Address is already on the watchlist")
    row = WatchlistItem(
        chain=body.chain,
        token=body.token.lower(),
        address=normalized,
        label=body.label.strip() if body.label else None,
    )
    try:
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return _item_dict(row)
    except Exception:
        logger.exception("Failed to create watchlist item")
        raise HTTPException(500, "Failed to create watchlist item")


@router.delete("/watchlists/{item_id}")
async def delete_watchlist_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        row = await db.get(WatchlistItem, item_id)
        if row is None:
            raise HTTPException(404, f"Watchlist item {item_id} not found")
        await db.delete(row)
        await db.commit()
        return {"deleted": True, "id": item_id}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete watchlist item")
        raise HTTPException(500, "Failed to delete watchlist item")
