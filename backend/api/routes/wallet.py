"""Read-only x402 wallet session endpoints (Slice 2.8).

Wallet authentication is separate from the shared-password app session and is
scoped to Base mainnet. Endpoints only ever return the authenticated wallet's
own data. Proofs are one-time, expiring, and chain-bound; replayed, expired,
and wrong-network proofs are rejected.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import Settings, get_settings
from backend.core import chains, venicestats_client, wallet_auth
from backend.core.wallet_auth import SUPPORTED_CHAIN_ID
from backend.core.venicestats_client import VeniceStatsError
from backend.database import get_db
from backend.limiter import limiter
from backend.models.db import WalletChallenge, WalletSession
from backend.api.routes.onchain import fetch_transfers, fetch_vvv_balance, get_venice_client

logger = logging.getLogger(__name__)
router = APIRouter()


class ChallengeRequest(BaseModel):
    address: str = Field(..., min_length=42, max_length=42)
    chain_id: int = Field(SUPPORTED_CHAIN_ID)


class VerifyRequest(BaseModel):
    challenge_id: int
    signature: str = Field(..., min_length=1, max_length=512)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def _get_session(db: AsyncSession, token: str) -> Optional[WalletSession]:
    token_hash = wallet_auth.hash_token(token)
    result = await db.execute(
        select(WalletSession).where(WalletSession.token_hash == token_hash)
    )
    return result.scalars().first()


async def require_wallet_session(
    x_wallet_token: Optional[str] = Header(default=None, alias="X-Wallet-Token"),
    db: AsyncSession = Depends(get_db),
) -> WalletSession:
    """Authenticate a read-only wallet session from the ``X-Wallet-Token`` header."""
    if not x_wallet_token:
        raise HTTPException(
            401,
            "Missing wallet session. Complete the wallet challenge first.",
            headers={"WWW-Authenticate": "Wallet"},
        )
    session = await _get_session(db, x_wallet_token)
    if session is None:
        raise HTTPException(401, "Invalid wallet session")
    if _as_utc(session.expires_at) <= datetime.now(timezone.utc):
        await db.delete(session)
        await db.commit()
        raise HTTPException(401, "Wallet session expired")
    session.last_used_at = datetime.now(timezone.utc)
    await db.commit()
    return session


@router.post("/wallet/challenge")
@limiter.limit("20/hour")
async def create_wallet_challenge(
    request: Request,
    body: ChallengeRequest,
    db: AsyncSession = Depends(get_db),
):
    if body.chain_id != SUPPORTED_CHAIN_ID:
        raise HTTPException(
            400,
            f"Unsupported network. Base mainnet (chain id {SUPPORTED_CHAIN_ID}) only.",
        )
    if not wallet_auth.is_valid_evm_address(body.address):
        raise HTTPException(400, "Invalid EVM address")

    now = datetime.now(timezone.utc)
    issued_at = now
    expires_at = wallet_auth.challenge_expiry(now)
    nonce = wallet_auth.generate_nonce()
    message = wallet_auth.build_challenge_message(
        address=body.address,
        chain_id=body.chain_id,
        nonce=nonce,
        issued_at=issued_at,
        expires_at=expires_at,
    )
    row = WalletChallenge(
        address=wallet_auth.normalize_address(body.address),
        chain_id=body.chain_id,
        nonce=nonce,
        message=message,
        expires_at=expires_at,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {
        "challenge_id": row.id,
        "address": row.address,
        "chain_id": row.chain_id,
        "message": row.message,
        "expires_at": row.expires_at.isoformat(),
    }


@router.post("/wallet/verify")
@limiter.limit("30/hour")
async def verify_wallet_challenge(
    request: Request,
    body: VerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    challenge = await db.get(WalletChallenge, body.challenge_id)
    if challenge is None:
        raise HTTPException(404, "Challenge not found")
    if challenge.used_at is not None:
        raise HTTPException(401, "Challenge has already been used")
    if _as_utc(challenge.expires_at) <= datetime.now(timezone.utc):
        raise HTTPException(401, "Challenge expired")
    if challenge.chain_id != SUPPORTED_CHAIN_ID:
        raise HTTPException(401, "Challenge is bound to an unsupported network")
    if not wallet_auth.verify_personal_signature(
        challenge.message, body.signature, challenge.address
    ):
        raise HTTPException(401, "Signature verification failed")

    challenge.used_at = datetime.now(timezone.utc)
    token = wallet_auth.generate_session_token()
    expires_at = wallet_auth.session_expiry()
    session = WalletSession(
        token_hash=wallet_auth.hash_token(token),
        address=challenge.address,
        chain_id=challenge.chain_id,
        expires_at=expires_at,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return {
        "token": token,
        "address": session.address,
        "chain_id": session.chain_id,
        "expires_at": session.expires_at.isoformat(),
    }


@router.get("/wallet/session")
async def read_wallet_session(
    session: WalletSession = Depends(require_wallet_session),
):
    return {
        "address": session.address,
        "chain_id": session.chain_id,
        "expires_at": session.expires_at.isoformat() if session.expires_at else None,
    }


@router.post("/wallet/logout")
async def logout_wallet_session(
    session: WalletSession = Depends(require_wallet_session),
    db: AsyncSession = Depends(get_db),
):
    await db.delete(session)
    await db.commit()
    return {"logged_out": True}


@router.get("/wallet/balance")
async def get_wallet_balance(
    session: WalletSession = Depends(require_wallet_session),
    settings: Settings = Depends(get_settings),
    client=Depends(get_venice_client),
):
    """Read-only balance for the authenticated wallet only."""
    if session.chain_id != SUPPORTED_CHAIN_ID:
        raise HTTPException(400, "Wallet session is bound to an unsupported network")
    holdings = None
    holdings_error = None
    try:
        holdings = await venicestats_client.get_wallet_holdings(session.address, settings)
    except VeniceStatsError as exc:
        holdings_error = str(exc)
    onchain = None
    onchain_error = None
    try:
        onchain = await fetch_vvv_balance(session.address, client)
    except HTTPException as exc:
        onchain_error = str(exc.detail)
    if holdings is None and onchain is None:
        raise HTTPException(502, "Wallet balance sources are unavailable")
    return {
        "address": session.address,
        "chain": chains.BASE_MAINNET.key,
        "chain_id": session.chain_id,
        "holdings": dict(holdings) if holdings is not None else None,
        "holdings_error": holdings_error,
        "onchain": onchain,
        "onchain_error": onchain_error,
        "sources": ["venicestats", "venice-rpc"],
        "read_only": True,
    }


@router.get("/wallet/transactions")
async def get_wallet_transactions(
    blocks: int = Query(10000, ge=100, le=100000),
    session: WalletSession = Depends(require_wallet_session),
    client=Depends(get_venice_client),
):
    """Read-only VVV transfer history for the authenticated wallet only."""
    if session.chain_id != SUPPORTED_CHAIN_ID:
        raise HTTPException(400, "Wallet session is bound to an unsupported network")
    try:
        return await fetch_transfers(session.address, blocks, chains.BASE_MAINNET.key, "vvv", client)
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"Upstream RPC error: {type(exc).__name__}") from exc
    except Exception:
        logger.exception("Failed to fetch wallet transactions")
        raise HTTPException(500, "Failed to fetch wallet transactions")
