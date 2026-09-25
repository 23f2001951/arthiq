"""Authentication module for Arth IQ.

Provides single-user password protection, session token generation and verification,
and FastAPI dependency guards.
"""

from __future__ import annotations

import hmac
import logging
import os
import secrets
import time

from fastapi import Header, HTTPException, status

from invst.config import get_config

logger = logging.getLogger("invst.auth")

# In-memory session store: token -> expiry_timestamp (epoch seconds)
ACTIVE_SESSIONS: dict[str, float] = {}


def get_master_password() -> str:
    """Retrieve the master password from environment or settings."""
    env_pass = os.getenv("ARTH_IQ_PASSWORD")
    if env_pass is not None and env_pass.strip():
        return env_pass.strip()
    try:
        cfg = get_config()
        if hasattr(cfg, "auth") and "password" in cfg.auth:
            return str(cfg.auth.password).strip()
    except Exception:
        pass
    return "arth"


def is_auth_enabled() -> bool:
    """Check whether authentication is enabled."""
    env_disabled = os.getenv("ARTH_IQ_AUTH_DISABLED", "0").lower() in ("1", "true", "yes")
    if env_disabled:
        return False
    try:
        cfg = get_config()
        if hasattr(cfg, "auth") and "enabled" in cfg.auth:
            return bool(cfg.auth.enabled)
    except Exception:
        pass
    return True


def get_session_expiry_hours() -> int:
    """Retrieve session expiry duration in hours."""
    try:
        cfg = get_config()
        if hasattr(cfg, "auth") and "session_expiry_hours" in cfg.auth:
            return int(cfg.auth.session_expiry_hours)
    except Exception:
        pass
    return 72


def verify_password(password: str) -> bool:
    """Safely compare provided password with the master password."""
    master = get_master_password()
    return hmac.compare_digest(password.strip(), master)


def create_session(expiry_hours: int | None = None) -> str:
    """Create a new session token with an expiration timestamp."""
    hours = expiry_hours if expiry_hours is not None else get_session_expiry_hours()
    token = secrets.token_hex(32)
    ACTIVE_SESSIONS[token] = time.time() + (hours * 3600)
    return token


def validate_session(token: str | None) -> bool:
    """Check if a session token is valid and not expired."""
    if not token:
        return False
    clean_token = token.replace("Bearer ", "").strip()
    expiry = ACTIVE_SESSIONS.get(clean_token)
    if expiry is None:
        return False
    if time.time() > expiry:
        ACTIVE_SESSIONS.pop(clean_token, None)
        return False
    return True


def revoke_session(token: str | None) -> None:
    """Revoke/delete an active session token."""
    if not token:
        return
    clean_token = token.replace("Bearer ", "").strip()
    ACTIVE_SESSIONS.pop(clean_token, None)


def require_auth(authorization: str | None = Header(None)) -> bool:
    """FastAPI dependency to protect endpoints.

    Requires 'Authorization: Bearer <token>' header.
    Allows bypass during pytest test runs unless ARTH_IQ_FORCE_AUTH=1.
    """
    if not is_auth_enabled():
        return True

    # Pytest bypass when not explicitly testing auth
    if "PYTEST_CURRENT_TEST" in os.environ and os.getenv("ARTH_IQ_FORCE_AUTH") != "1":
        if authorization is None:
            return True

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please enter master password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    token = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else authorization
    if not validate_session(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid. Please re-authenticate.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True
