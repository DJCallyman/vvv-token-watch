"""Wallet proof-of-ownership helpers for the x402 wallet session (Slice 2.8).

Only Base mainnet is supported. Challenges are one-time, expiring, and
chain-bound; signatures are verified with EIP-191 ``personal_sign``.
"""

from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from eth_account import Account
from eth_account.messages import encode_defunct

DOMAIN = "VVV Token Watch"
SUPPORTED_CHAIN_ID = 8453  # Base mainnet only
CHALLENGE_TTL_SECONDS = 300
SESSION_TTL_SECONDS = 24 * 3600

_ADDR_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")


def is_valid_evm_address(address: str) -> bool:
    return bool(_ADDR_RE.match(address or ""))


def generate_nonce() -> str:
    return secrets.token_hex(16)


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalize_address(address: str) -> str:
    return (address or "").lower()


def build_challenge_message(
    *,
    address: str,
    chain_id: int,
    nonce: str,
    issued_at: datetime,
    expires_at: datetime,
) -> str:
    """Build the deterministic human-readable message the wallet signs."""
    return (
        f"{DOMAIN} wants you to sign in with your wallet:\n"
        f"{address}\n\n"
        f"Chain ID: {chain_id}\n"
        f"Nonce: {nonce}\n"
        f"Issued At: {issued_at.astimezone(timezone.utc).isoformat()}\n"
        f"Expiration Time: {expires_at.astimezone(timezone.utc).isoformat()}\n"
        f"Statement: Authenticate read-only wallet access. This request does not "
        f"authorize transactions."
    )


def challenge_expiry(now: Optional[datetime] = None) -> datetime:
    base = now or datetime.now(timezone.utc)
    return base + timedelta(seconds=CHALLENGE_TTL_SECONDS)


def session_expiry(now: Optional[datetime] = None) -> datetime:
    base = now or datetime.now(timezone.utc)
    return base + timedelta(seconds=SESSION_TTL_SECONDS)


def verify_personal_signature(message: str, signature: str, expected_address: str) -> bool:
    """Return True when the signature recovers to ``expected_address``."""
    if not signature or not expected_address:
        return False
    try:
        recovered = Account.recover_message(
            encode_defunct(text=message), signature=signature
        )
    except Exception:
        return False
    return recovered.lower() == expected_address.lower()
