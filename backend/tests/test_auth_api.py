"""End-to-end tests for /auth: real HTTP requests, real (test) database."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from httpx import AsyncClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.models.enums import CustomerStatus, SessionStatus
from app.models.identity import Customer, CustomerSession, LoginEvent

PASSWORD = "S3cure-pass!"


def register_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "full_name": "Aisyah Rahman",
        "email": "aisyah@jaga.my",
        "phone_number": "012-345 6789",
        "password": PASSWORD,
        "preferred_language": "en",
        "device_fingerprint": "fp-iphone-0001",
    }
    body.update(overrides)
    return body


async def register(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    response = await client.post("/auth/register", json=register_body(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


async def login(client: AsyncClient, **overrides: Any) -> Any:
    body = {"email": "aisyah@jaga.my", "password": PASSWORD, "device_fingerprint": "fp-iphone-0001"}
    body.update(overrides)
    return await client.post("/auth/login", json=body)


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------- Register ----------
async def test_register_creates_customer_and_returns_tokens(client: AsyncClient) -> None:
    data = await register(client, full_name="  Aisyah   Rahman ", email="Aisyah@JAGA.my")

    customer = data["customer"]
    assert customer["full_name"] == "Aisyah Rahman"  # whitespace cleaned
    assert customer["email"] == "aisyah@jaga.my"  # lower-cased
    assert customer["phone_number"] == "+60123456789"  # normalised
    assert customer["status"] == "active"
    assert "password" not in str(data) and "password_hash" not in customer
    assert data["tokens"]["token_type"] == "bearer"
    assert data["tokens"]["expires_in"] == settings.jwt_access_ttl_minutes * 60
    assert data["is_new_device"] is True


async def test_register_stores_hashed_password(client: AsyncClient, db: AsyncSession) -> None:
    await register(client)
    stored = await db.scalar(select(Customer.password_hash))
    assert stored is not None and stored != PASSWORD and stored.startswith("$2")


async def test_register_duplicate_email_is_case_insensitive(client: AsyncClient) -> None:
    await register(client)
    response = await client.post(
        "/auth/register",
        json=register_body(email="AISYAH@jaga.my", phone_number="0198887777"),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "email_taken"


async def test_register_duplicate_phone(client: AsyncClient) -> None:
    await register(client)
    response = await client.post(
        "/auth/register",
        json=register_body(email="other@jaga.my", phone_number="+60 12 345 6789"),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "phone_taken"


async def test_register_rejects_bad_input(client: AsyncClient) -> None:
    for bad in (
        {"password": "short"},
        {"password": "x" * 73},
        {"email": "not-an-email"},
        {"phone_number": "12345"},
        {"preferred_language": "fr"},
        {"full_name": " "},
    ):
        response = await client.post("/auth/register", json=register_body(**bad))
        assert response.status_code == 422, bad


# ---------- Login ----------
async def test_login_success(client: AsyncClient, db: AsyncSession) -> None:
    await register(client)
    response = await login(client, email="AISYAH@jaga.my")
    assert response.status_code == 200
    body = response.json()
    assert body["customer"]["email"] == "aisyah@jaga.my"
    assert body["is_new_device"] is False  # same fingerprint as at registration

    events = (await db.scalars(select(LoginEvent).order_by(LoginEvent.id))).all()
    assert [e.succeeded for e in events] == [True, True]  # register + login


async def test_login_flags_new_device(client: AsyncClient) -> None:
    await register(client)
    response = await login(client, device_fingerprint="fp-laptop-9999")
    assert response.json()["is_new_device"] is True


async def test_login_wrong_password_and_unknown_email_look_identical(
    client: AsyncClient, db: AsyncSession
) -> None:
    await register(client)
    wrong_password = await login(client, password="wrong-password")
    unknown_email = await login(client, email="nobody@jaga.my")

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()

    reasons = (
        await db.scalars(
            select(LoginEvent.failure_reason).where(LoginEvent.succeeded.is_(False))
        )
    ).all()
    assert sorted(reasons) == ["unknown_email", "wrong_password"]


async def test_failed_login_counter_increments_then_resets(
    client: AsyncClient, db: AsyncSession
) -> None:
    await register(client)
    await login(client, password="wrong-1")
    await login(client, password="wrong-2")
    assert await db.scalar(select(Customer.failed_login_count)) == 2

    assert (await login(client)).status_code == 200
    db.expire_all()
    assert await db.scalar(select(Customer.failed_login_count)) == 0


# ---------- Access token / me ----------
async def test_me_with_valid_token(client: AsyncClient) -> None:
    data = await register(client)
    response = await client.get("/auth/me", headers=bearer(data["tokens"]["access_token"]))
    assert response.status_code == 200
    assert response.json()["email"] == "aisyah@jaga.my"


async def test_me_rejects_missing_bad_expired_and_staff_tokens(client: AsyncClient) -> None:
    data = await register(client)
    customer_id = data["customer"]["id"]
    expired = jwt.encode(
        {
            "sub": str(customer_id),
            "type": "customer",
            "exp": datetime.now(UTC) - timedelta(minutes=1),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    staff_token = create_access_token(customer_id, "staff")

    assert (await client.get("/auth/me")).status_code == 401
    for token in ("garbage", expired, staff_token):
        response = await client.get("/auth/me", headers=bearer(token))
        assert response.status_code == 401, token


# ---------- Refresh ----------
async def test_refresh_rotates_tokens(client: AsyncClient) -> None:
    data = await register(client)
    old_refresh = data["tokens"]["refresh_token"]

    response = await client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert response.status_code == 200
    new_tokens = response.json()
    assert new_tokens["refresh_token"] != old_refresh
    assert (
        await client.get("/auth/me", headers=bearer(new_tokens["access_token"]))
    ).status_code == 200

    # The old refresh token is single-use: it no longer works.
    reused = await client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert reused.status_code == 401
    assert reused.json()["code"] == "invalid_refresh_token"


async def test_refresh_fails_after_session_expires(client: AsyncClient, db: AsyncSession) -> None:
    data = await register(client)
    await db.execute(
        update(CustomerSession).values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
    )
    await db.commit()

    response = await client.post(
        "/auth/refresh", json={"refresh_token": data["tokens"]["refresh_token"]}
    )
    assert response.status_code == 401
    assert await db.scalar(select(CustomerSession.status)) == SessionStatus.EXPIRED


# ---------- Logout ----------
async def test_logout_revokes_session_and_is_idempotent(
    client: AsyncClient, db: AsyncSession
) -> None:
    data = await register(client)
    refresh_token = data["tokens"]["refresh_token"]
    access_token = data["tokens"]["access_token"]

    assert (
        await client.post("/auth/logout", json={"refresh_token": refresh_token})
    ).status_code == 204
    # The access token dies with its session, not 15 minutes later.
    assert (await client.get("/auth/me", headers=bearer(access_token))).status_code == 401
    assert (
        await client.post("/auth/logout", json={"refresh_token": refresh_token})
    ).status_code == 204
    assert (
        await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    ).status_code == 401
    assert await db.scalar(select(CustomerSession.revoke_reason)) == "logout"


# ---------- Kill switch / frozen account ----------
async def test_frozen_account_is_locked_out_everywhere(
    client: AsyncClient, db: AsyncSession
) -> None:
    data = await register(client)
    await db.execute(update(Customer).values(status=CustomerStatus.FROZEN))
    await db.commit()

    # Existing access token stops working immediately (not after 15 minutes).
    me = await client.get("/auth/me", headers=bearer(data["tokens"]["access_token"]))
    assert me.status_code == 403

    # Refresh is refused and the session is revoked.
    refreshed = await client.post(
        "/auth/refresh", json={"refresh_token": data["tokens"]["refresh_token"]}
    )
    assert refreshed.status_code == 401
    assert await db.scalar(select(CustomerSession.revoke_reason)) == "account_not_active"

    # Correct password still can't log in, and the attempt is recorded.
    logged_in = await login(client)
    assert logged_in.status_code == 403
    assert logged_in.json()["code"] == "account_not_active"
    assert (
        await db.scalar(
            select(func.count()).select_from(LoginEvent).where(
                LoginEvent.failure_reason == "account_frozen"
            )
        )
        == 1
    )
