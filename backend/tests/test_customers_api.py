"""End-to-end tests for /customers/me: profile, password, sessions, devices, close."""

from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import CustomerStatus, SessionStatus
from app.models.identity import Customer, CustomerSession, Device

PASSWORD = "S3cure-pass!"
NEW_PASSWORD = "N3w-secure-pass!"


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def register(
    client: AsyncClient, *, email: str = "aisyah@jaga.my", phone: str = "0123456789"
) -> dict[str, Any]:
    response = await client.post(
        "/auth/register",
        json={
            "full_name": "Aisyah Rahman",
            "email": email,
            "phone_number": phone,
            "password": PASSWORD,
            "device_fingerprint": "fp-phone-0001",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def login(
    client: AsyncClient,
    *,
    fingerprint: str,
    email: str = "aisyah@jaga.my",
    password: str = PASSWORD,
) -> Any:
    return await client.post(
        "/auth/login",
        json={"email": email, "password": password, "device_fingerprint": fingerprint},
    )


async def two_devices(client: AsyncClient) -> tuple[dict[str, Any], dict[str, Any]]:
    """Registered on a phone, then logged in on a laptop. Returns (phone, laptop) tokens."""
    phone = (await register(client))["tokens"]
    laptop_response = await login(client, fingerprint="fp-laptop-0002")
    assert laptop_response.status_code == 200
    return phone, laptop_response.json()["tokens"]


# ---------- Profile ----------
async def test_get_and_update_profile(client: AsyncClient) -> None:
    token = (await register(client))["tokens"]["access_token"]

    profile = await client.get("/customers/me", headers=bearer(token))
    assert profile.status_code == 200
    assert profile.json()["full_name"] == "Aisyah Rahman"

    updated = await client.patch(
        "/customers/me",
        headers=bearer(token),
        json={"full_name": "  Aisyah  Binti Rahman ", "preferred_language": "ms"},
    )
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Aisyah Binti Rahman"
    assert updated.json()["preferred_language"] == "ms"

    # Partial update: only the language changes.
    partial = await client.patch(
        "/customers/me", headers=bearer(token), json={"preferred_language": "zh"}
    )
    assert partial.json()["full_name"] == "Aisyah Binti Rahman"
    assert partial.json()["preferred_language"] == "zh"


async def test_update_profile_validation(client: AsyncClient) -> None:
    token = (await register(client))["tokens"]["access_token"]
    for bad in ({}, {"preferred_language": "fr"}, {"full_name": "A"}, {"full_name": None}):
        response = await client.patch("/customers/me", headers=bearer(token), json=bad)
        assert response.status_code == 422, bad


async def test_profile_requires_login(client: AsyncClient) -> None:
    assert (await client.get("/customers/me")).status_code == 401
    assert (await client.patch("/customers/me", json={"full_name": "X Y"})).status_code == 401


# ---------- Password ----------
async def test_change_password_signs_out_other_devices(client: AsyncClient) -> None:
    phone, laptop = await two_devices(client)

    response = await client.post(
        "/customers/me/password",
        headers=bearer(phone["access_token"]),
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert response.status_code == 200
    assert response.json() == {"revoked_sessions": 1}

    # Phone (the device that changed it) stays logged in; the laptop is out.
    assert (
        await client.get("/customers/me", headers=bearer(phone["access_token"]))
    ).status_code == 200
    assert (
        await client.get("/customers/me", headers=bearer(laptop["access_token"]))
    ).status_code == 401

    # Old password no longer works; the new one does.
    assert (await login(client, fingerprint="fp-x-0003")).status_code == 401
    assert (
        await login(client, fingerprint="fp-x-0003", password=NEW_PASSWORD)
    ).status_code == 200


async def test_change_password_rejects_wrong_or_same_password(client: AsyncClient) -> None:
    token = (await register(client))["tokens"]["access_token"]

    wrong = await client.post(
        "/customers/me/password",
        headers=bearer(token),
        json={"current_password": "not-it", "new_password": NEW_PASSWORD},
    )
    assert wrong.status_code == 400 and wrong.json()["code"] == "invalid_password"

    same = await client.post(
        "/customers/me/password",
        headers=bearer(token),
        json={"current_password": PASSWORD, "new_password": PASSWORD},
    )
    assert same.status_code == 400 and same.json()["code"] == "password_unchanged"

    weak = await client.post(
        "/customers/me/password",
        headers=bearer(token),
        json={"current_password": PASSWORD, "new_password": "short"},
    )
    assert weak.status_code == 422


# ---------- Sessions ----------
async def test_list_sessions_marks_current(client: AsyncClient) -> None:
    phone, _laptop = await two_devices(client)
    response = await client.get("/customers/me/sessions", headers=bearer(phone["access_token"]))
    assert response.status_code == 200
    sessions = response.json()
    assert len(sessions) == 2
    assert sum(s["is_current"] for s in sessions) == 1


async def test_revoke_one_session_kills_its_access_token_immediately(
    client: AsyncClient,
) -> None:
    phone, laptop = await two_devices(client)
    sessions = (
        await client.get("/customers/me/sessions", headers=bearer(phone["access_token"]))
    ).json()
    laptop_session = next(s for s in sessions if not s["is_current"])

    response = await client.delete(
        f"/customers/me/sessions/{laptop_session['id']}", headers=bearer(phone["access_token"])
    )
    assert response.status_code == 204
    assert (
        await client.get("/customers/me", headers=bearer(laptop["access_token"]))
    ).status_code == 401
    assert (
        await client.post("/auth/refresh", json={"refresh_token": laptop["refresh_token"]})
    ).status_code == 401
    # Revoking it again: it is no longer an active session.
    again = await client.delete(
        f"/customers/me/sessions/{laptop_session['id']}", headers=bearer(phone["access_token"])
    )
    assert again.status_code == 404


async def test_cannot_touch_another_customers_session(client: AsyncClient) -> None:
    aisyah = (await register(client))["tokens"]
    other = (await register(client, email="mei@jaga.my", phone="0198765432"))["tokens"]
    other_sessions = (
        await client.get("/customers/me/sessions", headers=bearer(other["access_token"]))
    ).json()

    response = await client.delete(
        f"/customers/me/sessions/{other_sessions[0]['id']}",
        headers=bearer(aisyah["access_token"]),
    )
    assert response.status_code == 404  # same as "doesn't exist": reveals nothing
    assert (
        await client.get("/customers/me", headers=bearer(other["access_token"]))
    ).status_code == 200


async def test_sign_out_everywhere_else(client: AsyncClient) -> None:
    phone, laptop = await two_devices(client)
    response = await client.delete("/customers/me/sessions", headers=bearer(phone["access_token"]))
    assert response.json() == {"revoked_sessions": 1}
    assert (
        await client.get("/customers/me", headers=bearer(phone["access_token"]))
    ).status_code == 200
    assert (
        await client.get("/customers/me", headers=bearer(laptop["access_token"]))
    ).status_code == 401


# ---------- Devices ----------
async def test_list_and_rename_devices(client: AsyncClient) -> None:
    phone, _laptop = await two_devices(client)
    devices = (
        await client.get("/customers/me/devices", headers=bearer(phone["access_token"]))
    ).json()
    assert len(devices) == 2
    current = next(d for d in devices if d["is_current"])
    assert current["trust_status"] == "unknown"

    renamed = await client.patch(
        f"/customers/me/devices/{current['id']}",
        headers=bearer(phone["access_token"]),
        json={"display_name": "  Aisyah's   iPhone "},
    )
    assert renamed.status_code == 200
    assert renamed.json()["display_name"] == "Aisyah's iPhone"
    assert renamed.json()["is_current"] is True

    missing = await client.patch(
        "/customers/me/devices/999999",
        headers=bearer(phone["access_token"]),
        json={"display_name": "x"},
    )
    assert missing.status_code == 404


async def test_forget_device_is_a_soft_delete(client: AsyncClient, db: AsyncSession) -> None:
    phone, laptop = await two_devices(client)
    devices = (
        await client.get("/customers/me/devices", headers=bearer(phone["access_token"]))
    ).json()
    laptop_device = next(d for d in devices if not d["is_current"])

    response = await client.delete(
        f"/customers/me/devices/{laptop_device['id']}", headers=bearer(phone["access_token"])
    )
    assert response.status_code == 204

    # The row is kept for history, only marked as deleted.
    forgotten = await db.get(Device, laptop_device["id"])
    assert forgotten is not None and forgotten.deleted_at is not None

    # Hidden from the API: not listed, can't be renamed or forgotten twice.
    listed = (
        await client.get("/customers/me/devices", headers=bearer(phone["access_token"]))
    ).json()
    assert laptop_device["id"] not in [d["id"] for d in listed]
    renamed = await client.patch(
        f"/customers/me/devices/{laptop_device['id']}",
        headers=bearer(phone["access_token"]),
        json={"display_name": "x"},
    )
    assert renamed.status_code == 404

    # Its session is signed out.
    assert (
        await client.get("/customers/me", headers=bearer(laptop["access_token"]))
    ).status_code == 401

    # Same laptop logs in again: a NEW device row (partial unique index allows it).
    relogin = await login(client, fingerprint="fp-laptop-0002")
    assert relogin.json()["is_new_device"] is True
    relisted = (
        await client.get("/customers/me/devices", headers=bearer(phone["access_token"]))
    ).json()
    assert len(relisted) == 2
    assert laptop_device["id"] not in [d["id"] for d in relisted]


# ---------- Close account ----------
async def test_close_account(client: AsyncClient, db: AsyncSession) -> None:
    phone, laptop = await two_devices(client)

    wrong = await client.request(
        "DELETE", "/customers/me", headers=bearer(phone["access_token"]), json={"password": "no"}
    )
    assert wrong.status_code == 400

    closed = await client.request(
        "DELETE",
        "/customers/me",
        headers=bearer(phone["access_token"]),
        json={"password": PASSWORD},
    )
    assert closed.status_code == 204

    customer = await db.scalar(select(Customer))
    assert customer is not None and customer.status == CustomerStatus.CLOSED
    assert customer.closed_at is not None  # soft delete: row kept for audit
    statuses = set((await db.scalars(select(CustomerSession.status))).all())
    assert statuses == {SessionStatus.REVOKED}

    for token in (phone["access_token"], laptop["access_token"]):
        assert (await client.get("/customers/me", headers=bearer(token))).status_code == 401
    assert (await login(client, fingerprint="fp-phone-0001")).status_code == 403
