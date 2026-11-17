import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("correct horse")
    assert hashed != "correct horse"
    assert verify_password("correct horse", hashed)
    assert not verify_password("wrong", hashed)


def test_same_password_gives_different_hashes():
    # The random salt means two users with the same password get different hashes.
    assert hash_password("same-password") != hash_password("same-password")


def test_access_token_roundtrip():
    token = create_access_token(42, "customer")
    assert decode_access_token(token, "customer") == 42


def test_customer_token_rejected_for_staff():
    token = create_access_token(42, "customer")
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token, "staff")


def test_tampered_token_rejected():
    token = create_access_token(42, "customer")
    tampered = token[:-2] + ("AA" if not token.endswith("AA") else "BB")
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(tampered, "customer")


def test_refresh_token_hash_matches():
    token, token_hash = new_refresh_token()
    assert hash_refresh_token(token) == token_hash
    assert token != token_hash  # the database never stores the real token
