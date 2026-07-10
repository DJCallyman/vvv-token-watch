"""Shared FastAPI dependencies (auth, etc.)."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)


async def verify_auth(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
    settings: Settings = Depends(get_settings),
) -> None:
    """Optional single-password auth.

    When APP_PASSWORD is unset, all requests are allowed (local/VPN use).
    When set, require Authorization: Bearer <APP_PASSWORD>.
    """
    expected = settings.APP_PASSWORD
    if not expected:
        return

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials.credentials != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
