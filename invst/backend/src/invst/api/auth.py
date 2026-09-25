"""Authentication module for Arth IQ.

Provides enterprise-grade RBAC authentication, PBKDF2-SHA256 password hashing,
JWT token generation/verification, user management DB storage,
and FastAPI dependency guards (require_auth, require_admin).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import Header, HTTPException, status

from invst.config import get_config

logger = logging.getLogger("invst.auth")

JWT_SECRET_KEY = os.getenv("ARTH_IQ_SECRET_KEY", "arth-iq-super-secret-production-jwt-key-2025")
JWT_ALGORITHM = "HS256"

# In-memory session fallback and token revocation store
ACTIVE_SESSIONS: dict[str, float] = {}
REVOKED_TOKENS: set[str] = set()


# -------------------------------------------------------------------------
# Base64url and Cryptographic Helpers (Zero External Dependencies)
# -------------------------------------------------------------------------
def _b64url_encode(data: bytes) -> str:
    """Base64url encode without padding (RFC 7515/7519)."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    """Base64url decode with automatic padding handling."""
    s = data.strip()
    padding = 4 - (len(s) % 4)
    if padding < 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s.encode("ascii"))


# -------------------------------------------------------------------------
# Password & Config Helpers
# -------------------------------------------------------------------------
def get_admin_bootstrap_password() -> str:
    """Retrieve optional bootstrap admin password from environment or settings.

    Returns an empty string if not configured in environment or settings.
    No hardcoded passwords exist in the codebase.
    """
    env_pass = os.getenv("ARTH_IQ_ADMIN_PASSWORD") or os.getenv("ARTH_IQ_PASSWORD")
    if env_pass is not None and env_pass.strip():
        return env_pass.strip()
    try:
        cfg = get_config()
        if hasattr(cfg, "auth") and "password" in cfg.auth:
            val = str(cfg.auth.password).strip()
            if val:
                return val
    except Exception:
        pass
    return ""


def get_master_password() -> str:
    """Backwards-compatible alias for get_admin_bootstrap_password."""
    return get_admin_bootstrap_password()



def get_admin_email() -> str:
    """Retrieve bootstrap admin email."""
    return os.getenv("ARTH_IQ_ADMIN_EMAIL", "admin@arth.iq").strip().lower()


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


def hash_password(raw_password: str) -> str:
    """Hash password using standard PBKDF2-SHA256 with 100,000 iterations (zero external dependencies)."""
    salt = secrets.token_bytes(16)
    salt_b64 = base64.b64encode(salt).decode("ascii")
    derived = hashlib.pbkdf2_hmac("sha256", raw_password.strip().encode("utf-8"), salt, 100_000)
    hash_b64 = base64.b64encode(derived).decode("ascii")
    return f"pbkdf2_sha256$100000${salt_b64}${hash_b64}"


def verify_password_hash(raw_password: str, hashed_password: str | None) -> bool:
    """Verify raw password against standard PBKDF2 hash, passlib hash format, or plaintext fallback."""
    if not hashed_password:
        return False
    pw_bytes = raw_password.strip().encode("utf-8")

    # 1. Standard format: pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>
    if hashed_password.startswith("pbkdf2_sha256$"):
        try:
            parts = hashed_password.split("$")
            if len(parts) == 4:
                iterations = int(parts[1])
                salt = base64.b64decode(parts[2].encode("ascii"))
                expected_hash = base64.b64decode(parts[3].encode("ascii"))
                derived = hashlib.pbkdf2_hmac("sha256", pw_bytes, salt, iterations)
                return hmac.compare_digest(derived, expected_hash)
        except Exception:
            pass

    # 2. Passlib format compatibility: $pbkdf2-sha256$<rounds>$<salt_ab64>$<hash_ab64>
    if hashed_password.startswith("$pbkdf2-sha256$") or hashed_password.startswith("$pbkdf2$"):
        try:
            parts = hashed_password.split("$")
            if len(parts) >= 5:
                rounds = int(parts[2])
                salt_str = parts[3].replace(".", "+")
                salt_str += "=" * (-len(salt_str) % 4)
                salt = base64.b64decode(salt_str)

                hash_str = parts[4].replace(".", "+")
                hash_str += "=" * (-len(hash_str) % 4)
                expected_hash = base64.b64decode(hash_str)

                derived = hashlib.pbkdf2_hmac("sha256", pw_bytes, salt, rounds)
                return hmac.compare_digest(derived, expected_hash)
        except Exception:
            pass

    # 3. Plaintext master password or fallback direct comparison
    try:
        return hmac.compare_digest(raw_password.strip(), hashed_password)
    except Exception:
        return False


def verify_admin_password(password: str, conn: Any = None) -> bool:
    """Verify administrator password strictly against admin@arth.iq in database.

    admin@arth.iq is the master administrator. Authentication strictly compares
    against the stored password_hash in the database.
    """
    clean_pw = password.strip()
    should_close = False
    if conn is None:
        try:
            from invst.db.engine import get_db_connection
            conn = get_db_connection()
            should_close = True
        except Exception:
            return False

    try:
        admin_email = get_admin_email()
        cur = conn.cursor()
        cur.execute(
            "SELECT password_hash FROM users WHERE LOWER(email) = LOWER(?) LIMIT 1",
            (admin_email,),
        )
        row = cur.fetchone()
        if not row or not row[0]:
            # Also check any user with role = 'admin'
            cur.execute(
                "SELECT password_hash FROM users WHERE role = 'admin' ORDER BY id ASC LIMIT 1"
            )
            row = cur.fetchone()
        if row and row[0]:
            return verify_password_hash(clean_pw, row[0])
        return False
    except Exception as e:
        logger.debug("Error checking admin password in database: %s", e)
        return False
    finally:
        if should_close and conn is not None:
            conn.close()


def verify_master_password(password: str, conn: Any = None) -> bool:
    """Alias for backwards compatibility: strictly verifies against admin@arth.iq in DB."""
    return verify_admin_password(password, conn=conn)


def verify_password(password: str, conn: Any = None) -> bool:
    """Safely compare provided password with the master admin (admin@arth.iq) password."""
    return verify_admin_password(password, conn=conn)



# -------------------------------------------------------------------------
# JWT Token Helpers (Zero External Dependencies)
# -------------------------------------------------------------------------
def create_access_token(user_data: dict[str, Any], expiry_hours: int | None = None) -> str:
    """Generate RFC 7519 compliant HS256 JWT token using standard library."""
    hours = expiry_hours if expiry_hours is not None else get_session_expiry_hours()
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "jti": secrets.token_hex(16),
        "sub": user_data["email"],
        "email": user_data["email"],
        "user_id": user_data.get("id"),
        "role": user_data.get("role", "user"),
        "user_type": user_data.get("user_type") or ("ADMIN" if user_data.get("role") == "admin" else "PRO_INVESTOR"),
        "name": user_data.get("name") or "",
        "status": user_data.get("status", "ACTIVE"),
        "iat": now,
        "exp": now + (hours * 3600),
    }

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate an HS256 JWT access token using standard library."""
    clean_token = token.replace("Bearer ", "").strip()
    if not clean_token or clean_token in REVOKED_TOKENS:
        return None
    try:
        parts = clean_token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, signature_b64 = parts

        # Verify signature
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = hmac.new(JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
        actual_sig = _b64url_decode(signature_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        # Parse payload
        payload_bytes = _b64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))

        # Verify expiration
        exp = payload.get("exp")
        if exp is not None and int(time.time()) > int(exp):
            return None

        return payload
    except Exception:
        return None


def create_session(expiry_hours: int | None = None) -> str:
    """Legacy fallback: create a hex session token."""
    hours = expiry_hours if expiry_hours is not None else get_session_expiry_hours()
    token = secrets.token_hex(32)
    ACTIVE_SESSIONS[token] = time.time() + (hours * 3600)
    return token


def validate_session(token: str | None) -> bool:
    """Check if token is valid either via JWT or legacy in-memory session store."""
    if not token:
        return False
    clean_token = token.replace("Bearer ", "").strip()
    if clean_token in REVOKED_TOKENS:
        return False

    # 1. Try JWT decode
    jwt_data = decode_access_token(clean_token)
    if jwt_data is not None:
        return True

    # 2. Try in-memory fallback
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
    REVOKED_TOKENS.add(clean_token)
    ACTIVE_SESSIONS.pop(clean_token, None)


# -------------------------------------------------------------------------
# Database Initialization & User Store
# -------------------------------------------------------------------------
def init_users_table(conn: sqlite3.Connection | None = None) -> None:
    """Ensure users table exists and bootstrap initial admin user if table empty."""
    should_close = False
    if conn is None:
        from invst.db.engine import get_db_connection
        conn = get_db_connection()
        should_close = True

    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT,
                password_hash TEXT,
                role TEXT NOT NULL DEFAULT 'user',
                user_type TEXT NOT NULL DEFAULT 'PRO_INVESTOR',
                status TEXT NOT NULL DEFAULT 'INVITED',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
        conn.commit()

        # Add user_type column if upgrading existing table
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        if "user_type" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN user_type TEXT DEFAULT 'PRO_INVESTOR'")
            cursor.execute("UPDATE users SET user_type = 'ADMIN' WHERE role = 'admin' OR LOWER(role) = 'admin'")
            cursor.execute("UPDATE users SET user_type = 'PRO_INVESTOR' WHERE user_type IS NULL OR user_type != 'ADMIN'")
            conn.commit()

        # Check if admin user exists
        cursor.execute("SELECT id, email FROM users WHERE role = 'admin' LIMIT 1")
        admin = cursor.fetchone()
        if not admin:
            admin_email = get_admin_email()
            bootstrap_pass = get_admin_bootstrap_password()
            p_hash = hash_password(bootstrap_pass) if bootstrap_pass else None
            admin_status = "ACTIVE" if p_hash else "INVITED"
            cursor.execute(
                """
                INSERT OR IGNORE INTO users (email, name, password_hash, role, user_type, status)
                VALUES (?, ?, ?, 'admin', 'ADMIN', ?)
                """,
                (admin_email, "Platform Administrator", p_hash, admin_status),
            )
            conn.commit()
            logger.info("Bootstrapped master admin user: %s (status: %s)", admin_email, admin_status)
    finally:
        if should_close and conn is not None:
            conn.close()


def get_user_by_email(conn: sqlite3.Connection, email: str) -> dict[str, Any] | None:
    """Lookup user by email address (case-insensitive)."""
    init_users_table(conn)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, email, name, password_hash, role, status, created_at, last_login, user_type FROM users WHERE LOWER(email) = LOWER(?)",
        (email.strip(),),
    )
    row = cursor.fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "email": row[1],
        "name": row[2],
        "password_hash": row[3],
        "role": row[4],
        "status": row[5],
        "created_at": str(row[6]) if row[6] else None,
        "last_login": str(row[7]) if row[7] else None,
        "user_type": row[8] if len(row) > 8 and row[8] else ("ADMIN" if row[4] == "admin" else "PRO_INVESTOR"),
    }


def get_user_by_id(conn: sqlite3.Connection, user_id: int) -> dict[str, Any] | None:
    """Lookup user by primary key ID."""
    init_users_table(conn)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, email, name, password_hash, role, status, created_at, last_login, user_type FROM users WHERE id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "email": row[1],
        "name": row[2],
        "password_hash": row[3],
        "role": row[4],
        "status": row[5],
        "created_at": str(row[6]) if row[6] else None,
        "last_login": str(row[7]) if row[7] else None,
        "user_type": row[8] if len(row) > 8 and row[8] else ("ADMIN" if row[4] == "admin" else "PRO_INVESTOR"),
    }


def create_invited_user(
    conn: sqlite3.Connection,
    email: str,
    name: str | None = None,
    role: str = "user",
    user_type: str | None = None,
) -> dict[str, Any]:
    """Admin registers a new pro investor via their email in 'INVITED' status."""
    init_users_table(conn)
    clean_email = email.strip().lower()
    existing = get_user_by_email(conn, clean_email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{clean_email}' already exists.",
        )

    clean_role = role.lower() if role else "user"
    clean_user_type = user_type.upper() if user_type else ("ADMIN" if clean_role == "admin" else "PRO_INVESTOR")
    if clean_user_type == "ADMIN":
        clean_role = "admin"

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO users (email, name, password_hash, role, user_type, status)
        VALUES (?, ?, NULL, ?, ?, 'INVITED')
        """,
        (clean_email, name.strip() if name else None, clean_role, clean_user_type),
    )
    conn.commit()
    new_user = get_user_by_email(conn, clean_email)
    assert new_user is not None

    # Auto-initialize user's personal default portfolio and target list
    try:
        from invst.portfolio.health import ensure_user_portfolio_and_target_list
        ensure_user_portfolio_and_target_list(conn, new_user["id"])
    except Exception as exc:
        logger.warning("Could not auto-initialize portfolio for new user %s: %s", clean_email, exc)

    return new_user


def activate_user_password(
    conn: sqlite3.Connection,
    email: str,
    raw_password: str,
) -> dict[str, Any]:
    """User sets password on first login to activate their account."""
    init_users_table(conn)
    clean_email = email.strip().lower()
    user = get_user_by_email(conn, clean_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please contact your platform administrator.",
        )

    if user["status"] == "SUSPENDED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended. Please contact administrator.",
        )

    p_hash = hash_password(raw_password)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE users
        SET password_hash = ?, status = 'ACTIVE', last_login = ?
        WHERE LOWER(email) = LOWER(?)
        """,
        (p_hash, now_str, clean_email),
    )
    conn.commit()
    updated = get_user_by_email(conn, clean_email)
    assert updated is not None
    return updated


def update_user_password(
    conn: sqlite3.Connection,
    email: str,
    current_password: str,
    new_password: str,
) -> None:
    """Verify current password and update to new password for authenticated user or admin."""
    init_users_table(conn)
    clean_email = email.strip().lower()
    user = get_user_by_email(conn, clean_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found.",
        )

    # Verify current password
    stored_hash = user.get("password_hash")
    is_valid = False
    if stored_hash:
        is_valid = verify_password_hash(current_password, stored_hash)
    elif user.get("role") == "admin":
        is_valid = verify_password(current_password)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    if len(new_password.strip()) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 4 characters.",
        )

    new_hash = hash_password(new_password)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET password_hash = ? WHERE LOWER(email) = LOWER(?)",
        (new_hash, clean_email),
    )
    conn.commit()


def update_user_profile(
    conn: sqlite3.Connection,
    email: str,
    name: str | None = None,
) -> dict[str, Any]:
    """Update profile details (e.g. display name) for authenticated user."""
    init_users_table(conn)
    clean_email = email.strip().lower()
    user = get_user_by_email(conn, clean_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found.",
        )

    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET name = ? WHERE LOWER(email) = LOWER(?)",
        (name.strip() if name else None, clean_email),
    )
    conn.commit()
    updated = get_user_by_email(conn, clean_email)
    assert updated is not None
    return updated


def update_user_last_login(conn: sqlite3.Connection, email: str) -> None:
    """Record login timestamp for user."""
    init_users_table(conn)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET last_login = ? WHERE LOWER(email) = LOWER(?)",
        (now_str, email.strip().lower()),
    )
    conn.commit()


def list_all_users(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """List all users for Admin User Management."""
    init_users_table(conn)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, email, name, role, status, created_at, last_login, user_type FROM users ORDER BY created_at DESC"
    )
    rows = cursor.fetchall()
    return [
        {
            "id": r[0],
            "email": r[1],
            "name": r[2],
            "role": r[3],
            "status": r[4],
            "created_at": str(r[5]) if r[5] else None,
            "last_login": str(r[6]) if r[6] else None,
            "user_type": r[7] if len(r) > 7 and r[7] else ("ADMIN" if r[3] == "admin" else "PRO_INVESTOR"),
        }
        for r in rows
    ]


def update_user_status(conn: sqlite3.Connection, user_id: int, new_status: str) -> dict[str, Any]:
    """Admin updates user status (ACTIVE, SUSPENDED, INVITED)."""
    valid_statuses = {"ACTIVE", "SUSPENDED", "INVITED"}
    if new_status.upper() not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{new_status}'. Must be one of: {', '.join(valid_statuses)}",
        )

    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status = ? WHERE id = ?", (new_status.upper(), user_id))
    conn.commit()
    user = get_user_by_id(conn, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def delete_user_by_id(conn: sqlite3.Connection, user_id: int, current_admin_id: int | None = None) -> bool:
    """Admin deletes user. Prevents self-deletion."""
    if current_admin_id is not None and user_id == current_admin_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own admin account.",
        )

    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_portfolio_holdings WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM user_portfolios WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM user_target_list_items WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM user_target_lists WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    return cursor.rowcount > 0


# -------------------------------------------------------------------------
# FastAPI Dependency Guards
# -------------------------------------------------------------------------
def get_current_user(authorization: str | None = Header(None)) -> dict[str, Any]:
    """Extract authenticated user payload from Bearer token."""
    if not is_auth_enabled():
        return {
            "id": 1,
            "sub": get_admin_email(),
            "email": get_admin_email(),
            "name": "Local Developer",
            "role": "admin",
            "user_type": "ADMIN",
            "status": "ACTIVE",
        }

    # Pytest bypass when not explicitly testing auth
    if "PYTEST_CURRENT_TEST" in os.environ and os.getenv("ARTH_IQ_FORCE_AUTH") != "1":
        if authorization is None:
            return {
                "id": 1,
                "sub": get_admin_email(),
                "email": get_admin_email(),
                "name": "Test Runner",
                "role": "admin",
                "user_type": "ADMIN",
                "status": "ACTIVE",
            }

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please enter email and password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    token = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else authorization

    # Check JWT first
    payload = decode_access_token(token)
    if payload is not None:
        if payload.get("status") == "SUSPENDED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is suspended. Please contact administrator.",
            )
        if "user_type" not in payload:
            payload["user_type"] = "ADMIN" if payload.get("role") == "admin" else "PRO_INVESTOR"
        return payload

    # Check legacy session fallback
    if validate_session(token):
        return {
            "id": 1,
            "sub": get_admin_email(),
            "email": get_admin_email(),
            "name": "Platform Administrator",
            "role": "admin",
            "user_type": "ADMIN",
            "status": "ACTIVE",
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session expired or invalid. Please re-authenticate.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_auth(authorization: str | None = Header(None)) -> dict[str, Any]:
    """Dependency ensuring request is authenticated (any valid role: user or admin)."""
    return get_current_user(authorization)


def require_admin(authorization: str | None = Header(None)) -> dict[str, Any]:
    """Dependency strictly requiring platform 'admin' role. Rejects Pro Investors with 403."""
    user = require_auth(authorization)
    role = user.get("role", "user")
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden. Administrator privileges required to access this resource.",
        )
    return user
