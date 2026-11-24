"""Notifications + /inbox: the right messages, in the right language, exactly once."""

import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.messaging import Notification

PASSWORD = "S3cure-pass!"


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def register(
    client: AsyncClient, name: str, n: int, *, language: str = "en"
) -> tuple[str, dict[str, Any]]:
    """Returns (access_token, primary account)."""
    response = await client.post(
        "/auth/register",
        json={
            "full_name": name,
            "email": f"user{n}@jaga.my",
            "phone_number": f"01{n:08d}",
            "password": PASSWORD,
            "preferred_language": language,
            "device_fingerprint": f"fp-phone-{n}",
        },
    )
    assert response.status_code == 201, response.text
    token: str = response.json()["tokens"]["access_token"]
    accounts = (await client.get("/accounts/me", headers=bearer(token))).json()
    return token, accounts[0]


async def inbox(client: AsyncClient, token: str, **params: Any) -> Any:
    response = await client.get("/inbox", headers=bearer(token), params=params)
    assert response.status_code == 200, response.text
    return response.json()


async def pay(client: AsyncClient, sender: str, recipient_number: str, amount: str) -> Any:
    payee = await client.post(
        "/payees", headers=bearer(sender), json={"account_number": recipient_number}
    )
    payee_id = payee.json()["id"] if payee.status_code == 201 else None
    if payee_id is None:  # already saved
        payee_id = (await client.get("/payees", headers=bearer(sender))).json()[0]["id"]
    return await client.post(
        "/transfers",
        headers={**bearer(sender), "Idempotency-Key": str(uuid.uuid4())},
        json={"payee_id": payee_id, "amount": amount},
    )


# ---------- Welcome ----------
async def test_new_customer_gets_a_welcome_message(client: AsyncClient) -> None:
    token, account = await register(client, "Aisyah Rahman", 1)
    box = await inbox(client, token)

    assert box["unread_count"] == 1
    [welcome] = box["items"]
    assert welcome["event"] == "welcome"
    assert welcome["subject"] == "Welcome to Jaga"
    assert "RM 10,000.00" in welcome["message"]
    assert "•••• " + account["account_number"][-4:] in welcome["message"]
    assert account["account_number"] not in welcome["message"]  # never the full number
    assert welcome["read"] is False
    assert welcome["language"] == "en"


async def test_messages_use_the_customers_language(client: AsyncClient) -> None:
    ms, _ = await register(client, "Siti Aminah", 1, language="ms")
    zh, _ = await register(client, "Tan Mei Ling", 2, language="zh")

    ms_msg = (await inbox(client, ms))["items"][0]
    zh_msg = (await inbox(client, zh))["items"][0]
    assert ms_msg["language"] == "ms" and "Selamat datang" in ms_msg["message"]
    assert zh_msg["language"] == "zh" and "欢迎" in zh_msg["message"]


# ---------- Transfers ----------
async def test_transfer_tells_both_sides(client: AsyncClient) -> None:
    aisyah, _ = await register(client, "Aisyah Rahman", 1)
    ali, ali_account = await register(client, "Ali bin Abu", 2)

    sent = await pay(client, aisyah, ali_account["account_number"], "1250.50")
    assert sent.status_code == 201
    receipt = sent.json()

    mine = (await inbox(client, aisyah))["items"][0]
    assert mine["event"] == "transfer_sent"
    assert mine["transaction_id"] == receipt["id"]
    assert "RM 1,250.50 sent to Ali b** A**" in mine["message"]
    assert receipt["reference"] in mine["message"]

    theirs = (await inbox(client, ali))["items"][0]
    assert theirs["event"] == "transfer_received"
    assert theirs["transaction_id"] == receipt["id"]
    assert "You received RM 1,250.50 from Aisyah R**" in theirs["message"]


async def test_failed_or_replayed_transfers_send_no_extra_messages(
    client: AsyncClient, db: AsyncSession
) -> None:
    aisyah, _ = await register(client, "Aisyah Rahman", 1)
    _, ali_account = await register(client, "Ali Abu", 2)

    # Insufficient funds: the transfer rolls back, and so do its messages.
    failed = await pay(client, aisyah, ali_account["account_number"], "99999.00")
    assert failed.status_code == 409
    count = await db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.template_key.in_(["transfer_sent", "transfer_received"]))
    )
    assert count == 0

    # Replay with the same key: no second pair of messages.
    payee_id = (await client.get("/payees", headers=bearer(aisyah))).json()[0]["id"]
    headers = {**bearer(aisyah), "Idempotency-Key": "replay-key-123"}
    body = {"payee_id": payee_id, "amount": "10.00"}
    assert (await client.post("/transfers", headers=headers, json=body)).status_code == 201
    assert (await client.post("/transfers", headers=headers, json=body)).status_code == 200
    count = await db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.template_key.in_(["transfer_sent", "transfer_received"]))
    )
    assert count == 2  # one for Aisyah, one for Ali


# ---------- Security alerts ----------
async def test_new_device_login_alert_only_for_new_devices(client: AsyncClient) -> None:
    token, _ = await register(client, "Aisyah Rahman", 1)

    async def login(fingerprint: str) -> None:
        response = await client.post(
            "/auth/login",
            json={
                "email": "user1@jaga.my",
                "password": PASSWORD,
                "device_fingerprint": fingerprint,
            },
        )
        assert response.status_code == 200

    await login("fp-phone-1")  # the phone she registered on: known
    await login("fp-laptop-9")  # new
    await login("fp-laptop-9")  # known now

    events = [m["event"] for m in (await inbox(client, token))["items"]]
    assert events == ["new_device_login", "welcome"]


async def test_password_change_alert(client: AsyncClient) -> None:
    token, _ = await register(client, "Aisyah Rahman", 1)
    response = await client.post(
        "/customers/me/password",
        headers=bearer(token),
        json={"current_password": PASSWORD, "new_password": "N3w-secure-pass!"},
    )
    assert response.status_code == 200
    latest = (await inbox(client, token))["items"][0]
    assert latest["event"] == "password_changed"
    assert "Your password was changed" in latest["message"]


# ---------- Reading ----------
async def test_mark_read_and_read_all(client: AsyncClient) -> None:
    aisyah, _ = await register(client, "Aisyah Rahman", 1)
    ali, ali_account = await register(client, "Ali Abu", 2)
    for amount in ("1.00", "2.00"):
        await pay(client, aisyah, ali_account["account_number"], amount)

    box = await inbox(client, aisyah)
    assert box["unread_count"] == 3  # welcome + 2 sent
    first = box["items"][0]["id"]

    assert (await client.post(f"/inbox/{first}/read", headers=bearer(aisyah))).status_code == 204
    # Again: still fine, nothing changes.
    assert (await client.post(f"/inbox/{first}/read", headers=bearer(aisyah))).status_code == 204
    box = await inbox(client, aisyah)
    assert box["unread_count"] == 2
    assert box["items"][0]["read"] is True

    # Someone else's message: 404, same as one that doesn't exist.
    ali_msg = (await inbox(client, ali))["items"][0]["id"]
    nosy = await client.post(f"/inbox/{ali_msg}/read", headers=bearer(aisyah))
    assert nosy.status_code == 404 and nosy.json()["code"] == "message_not_found"

    marked = await client.post("/inbox/read-all", headers=bearer(aisyah))
    assert marked.json() == {"marked": 2}
    assert (await inbox(client, aisyah))["unread_count"] == 0
    assert (await client.post("/inbox/read-all", headers=bearer(aisyah))).json() == {"marked": 0}
    # Ali's messages weren't touched.
    assert (await inbox(client, ali))["unread_count"] == 3


async def test_inbox_paging(client: AsyncClient) -> None:
    aisyah, _ = await register(client, "Aisyah Rahman", 1)
    _, ali_account = await register(client, "Ali Abu", 2)
    for n in range(4):
        await pay(client, aisyah, ali_account["account_number"], f"{n + 1}.00")
    # 5 messages: welcome + 4 sent.

    seen: list[int] = []
    cursor = None
    while True:
        params: dict[str, Any] = {"limit": 2}
        if cursor is not None:
            params["before"] = cursor
        page = await inbox(client, aisyah, **params)
        seen += [m["id"] for m in page["items"]]
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert len(seen) == 5 and seen == sorted(seen, reverse=True)


async def test_inbox_requires_login(client: AsyncClient) -> None:
    assert (await client.get("/inbox")).status_code == 401
    assert (await client.post("/inbox/read-all")).status_code == 401
    assert (await client.post("/inbox/1/read")).status_code == 401
