"""Password hashing, access tokens (JWT) and refresh tokens.

Access token  = short-lived JWT. Carries the user id and (for customers) the
                session id, so a revoked session can be refused immediately.
Refresh token = long-lived random string, stored only as a SHA-256 hash in
                customer_sessions / staff_sessions so it can be revoked.
"""

import asyncio
import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

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


async def hash_password_async(password: str) -> str:
    # bcrypt takes ~0.2 s of CPU. A worker thread keeps the event loop free
    # to serve other requests meanwhile.
    return await asyncio.to_thread(hash_password, password)


async def verify_password_async(password: str, password_hash: str) -> bool:
    return await asyncio.to_thread(verify_password, password, password_hash)


# ---------- Access tokens (JWT) ----------
@dataclass(frozen=True)
class AccessTokenClaims:
    subject_id: int
    session_id: int | None


def create_access_token(
    subject_id: int,
    token_type: TokenType,
    session_id: int | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(subject_id),
        "type": token_type,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_ttl_minutes),
    }
    if session_id is not None:
        payload["sid"] = str(session_id)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token_claims(token: str, expected_type: TokenType) -> AccessTokenClaims:
    """Verify the token and return its claims, or raise jwt.InvalidTokenError."""
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],  # never let the token choose its own algorithm
        options={"require": ["exp", "sub", "type"]},
    )
    if payload["type"] != expected_type:
        raise jwt.InvalidTokenError("wrong token type")
    sid = payload.get("sid")
    return AccessTokenClaims(
        subject_id=int(payload["sub"]),
        session_id=int(sid) if sid is not None else None,
    )


def decode_access_token(token: str, expected_type: TokenType) -> int:
    """Return just the user id, or raise jwt.InvalidTokenError."""
    return decode_access_token_claims(token, expected_type).subject_id


# ---------- Refresh tokens (opaque, stored hashed) ----------
def new_refresh_token() -> tuple[str, str]:
    """Return (token for the client, hash for the database)."""
    token = secrets.token_urlsafe(48)
    return token, hash_refresh_token(token)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
