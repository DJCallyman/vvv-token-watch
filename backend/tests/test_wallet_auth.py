"""Tests for Slice 2.8 x402 wallet authentication."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.requests import Request

from backend.api.routes import wallet as wallet_routes
from backend.api.routes.wallet import ChallengeRequest, VerifyRequest
from backend.core import wallet_auth
from backend.database import Base


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        yield s
    await engine.dispose()


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/wallet/challenge",
            "headers": [],
            "client": ("127.0.0.1", 1234),
        }
    )


def _sign(message: str, account: Account) -> str:
    signed = Account.sign_message(encode_defunct(text=message), private_key=account.key)
    return signed.signature.hex()


# ---------------------------------------------------------------------------
# Pure verification
# ---------------------------------------------------------------------------


def test_signature_verification_round_trip():
    account = Account.create()
    now = datetime.now(timezone.utc)
    message = wallet_auth.build_challenge_message(
        address=account.address,
        chain_id=wallet_auth.SUPPORTED_CHAIN_ID,
        nonce="abc123",
        issued_at=now,
        expires_at=now + timedelta(minutes=5),
    )
    signature = _sign(message, account)
    assert wallet_auth.verify_personal_signature(message, signature, account.address)
    assert not wallet_auth.verify_personal_signature(message + "x", signature, account.address)
    assert not wallet_auth.verify_personal_signature(
        message, signature, "0x" + "11" * 20
    )
    assert not wallet_auth.verify_personal_signature(message, "0xdeadbeef", account.address)


def test_challenge_message_is_deterministic_and_chain_bound():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    message = wallet_auth.build_challenge_message(
        address="0x" + "ab" * 20,
        chain_id=8453,
        nonce="nonce",
        issued_at=now,
        expires_at=now + timedelta(minutes=5),
    )
    assert "Chain ID: 8453" in message
    assert "Nonce: nonce" in message
    assert "does not authorize transactions" in message


# ---------------------------------------------------------------------------
# Route flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_challenge_verify_and_replay_rejection(session):
    account = Account.create()
    challenge = await wallet_routes.create_wallet_challenge(
        _request(), ChallengeRequest(address=account.address), session
    )
    signature = _sign(challenge["message"], account)
    verified = await wallet_routes.verify_wallet_challenge(
        _request(), VerifyRequest(challenge_id=challenge["challenge_id"], signature=signature), session
    )
    assert verified["address"] == account.address.lower()
    assert verified["chain_id"] == wallet_auth.SUPPORTED_CHAIN_ID
    assert verified["token"]

    with pytest.raises(HTTPException) as exc:
        await wallet_routes.verify_wallet_challenge(
            _request(),
            VerifyRequest(challenge_id=challenge["challenge_id"], signature=signature),
            session,
        )
    assert exc.value.status_code == 401
    assert "already been used" in exc.value.detail


@pytest.mark.asyncio
async def test_wrong_signature_is_rejected(session):
    account = Account.create()
    other = Account.create()
    challenge = await wallet_routes.create_wallet_challenge(
        _request(), ChallengeRequest(address=account.address), session
    )
    signature = _sign(challenge["message"], other)
    with pytest.raises(HTTPException) as exc:
        await wallet_routes.verify_wallet_challenge(
            _request(), VerifyRequest(challenge_id=challenge["challenge_id"], signature=signature), session
        )
    assert exc.value.status_code == 401
    assert "Signature verification failed" in exc.value.detail


@pytest.mark.asyncio
async def test_wrong_network_challenge_is_rejected(session):
    account = Account.create()
    with pytest.raises(HTTPException) as exc:
        await wallet_routes.create_wallet_challenge(
            _request(), ChallengeRequest(address=account.address, chain_id=1), session
        )
    assert exc.value.status_code == 400
    assert "Base mainnet" in exc.value.detail


@pytest.mark.asyncio
async def test_expired_challenge_is_rejected(session):
    account = Account.create()
    challenge = await wallet_routes.create_wallet_challenge(
        _request(), ChallengeRequest(address=account.address), session
    )
    row = await session.get(wallet_routes.WalletChallenge, challenge["challenge_id"])
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await session.commit()
    signature = _sign(challenge["message"], account)
    with pytest.raises(HTTPException) as exc:
        await wallet_routes.verify_wallet_challenge(
            _request(), VerifyRequest(challenge_id=challenge["challenge_id"], signature=signature), session
        )
    assert exc.value.status_code == 401
    assert "expired" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_session_dependency_requires_and_accepts_token(session):
    account = Account.create()
    challenge = await wallet_routes.create_wallet_challenge(
        _request(), ChallengeRequest(address=account.address), session
    )
    signature = _sign(challenge["message"], account)
    verified = await wallet_routes.verify_wallet_challenge(
        _request(), VerifyRequest(challenge_id=challenge["challenge_id"], signature=signature), session
    )

    with pytest.raises(HTTPException) as exc:
        await wallet_routes.require_wallet_session(x_wallet_token=None, db=session)
    assert exc.value.status_code == 401

    with pytest.raises(HTTPException) as exc:
        await wallet_routes.require_wallet_session(x_wallet_token="not-a-token", db=session)
    assert exc.value.status_code == 401

    session_row = await wallet_routes.require_wallet_session(
        x_wallet_token=verified["token"], db=session
    )
    assert session_row.address == account.address.lower()


@pytest.mark.asyncio
async def test_expired_session_is_rejected_and_deleted(session):
    account = Account.create()
    challenge = await wallet_routes.create_wallet_challenge(
        _request(), ChallengeRequest(address=account.address), session
    )
    signature = _sign(challenge["message"], account)
    verified = await wallet_routes.verify_wallet_challenge(
        _request(), VerifyRequest(challenge_id=challenge["challenge_id"], signature=signature), session
    )
    row = await wallet_routes._get_session(session, verified["token"])
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await session.commit()

    with pytest.raises(HTTPException) as exc:
        await wallet_routes.require_wallet_session(
            x_wallet_token=verified["token"], db=session
        )
    assert exc.value.status_code == 401
    assert await wallet_routes._get_session(session, verified["token"]) is None
