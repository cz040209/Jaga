"""Password hashing, access tokens (JWT) and refresh tokens.

Access token  = short-lived JWT, checked by signature only (no DB lookup).
Refresh token = long-lived random string, stored only as a SHA-256 hash in
                customer_sessions / staff_sessions so it can be revoked.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal

import bcrypt
import jwt

from app.core.config import settings

TokenType = Literal["customer", "staff"]


# ---------- Passwords ----------
def hash_password(password: str) -> str:
    """bcrypt is deliberately slow, and gensalt() makes every hash unique."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


# ---------- Access tokens (JWT) ----------
def create_access_token(subject_id: int, token_type: TokenType) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(subject_id),
        "type": token_type,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_ttl_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, expected_type: TokenType) -> int:
    """Return the user id, or raise jwt.InvalidTokenError (expired, tampered, wrong type)."""
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],  # never let the token choose its own algorithm
        options={"require": ["exp", "sub", "type"]},
    )
    if payload["type"] != expected_type:
        raise jwt.InvalidTokenError("wrong token type")
    return int(payload["sub"])


# ---------- Refresh tokens (opaque, stored hashed) ----------
def new_refresh_token() -> tuple[str, str]:
    """Return (token for the client, hash for the database)."""
    token = secrets.token_urlsafe(48)
    return token, hash_refresh_token(token)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
