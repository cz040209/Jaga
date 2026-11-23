"""POST /transfers and GET /transfers/{id}: money moves, safely, exactly once."""

import asyncio
import uuid
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import ledger as ledger_crud
from app.models.banking import BankAccount, Transaction
from app.models.enums import AccountStatus, TransactionType

PASSWORD = "S3cure-pass!"


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def new_key() -> str:
    return str(uuid.uuid4())


async def register(client: AsyncClient, name: str, n: int) -> tuple[str, dict[str, Any]]:
    """Returns (access_token, primary account)."""
    response = await client.post(
        "/auth/register",
        json={
            "full_name": name,
            "email": f"user{n}@jaga.my",
            "phone_number": f"01{n:08d}",
            "password": PASSWORD,
        },
    )
    assert response.status_code == 201, response.text
    token: str = response.json()["tokens"]["access_token"]
    accounts = (await client.get("/accounts/me", headers=bearer(token))).json()
    return token, accounts[0]


async def balance(client: AsyncClient, token: str) -> str:
    balance_value: str = (await client.get("/accounts/me", headers=bearer(token))).json()[0][
        "balance"
    ]
    return balance_value


async def add_payee(client: AsyncClient, token: str, account_number: str) -> int:
    response = await client.post(
        "/payees",
        headers=bearer(token),
        json={"account_number": account_number, "nickname": "Ali (housemate)"},
    )
    assert response.status_code == 201, response.text
    payee_id: int = response.json()["id"]
    return payee_id


async def send(
    client: AsyncClient,
    token: str,
    *,
    payee_id: int,
    amount: Any,
    key: str | None = None,
    note: str | None = None,
) -> Any:
    headers = bearer(token)
    if key is not None:
        headers["Idempotency-Key"] = key
    body: dict[str, Any] = {"payee_id": payee_id, "amount": amount}
    if note is not None:
        body["note"] = note
    return await client.post("/transfers", headers=headers, json=body)


@pytest.fixture
async def setup(client: AsyncClient) -> dict[str, Any]:
    """Aisyah (sender) with Ali saved as a payee."""
    aisyah, aisyah_account = await register(client, "Aisyah Rahman", 1)
    ali, ali_account = await register(client, "Ali bin Abu", 2)
    payee_id = await add_payee(client, aisyah, ali_account["account_number"])
    return {
        "aisyah": aisyah,
        "ali": ali,
        "payee_id": payee_id,
        "aisyah_account": aisyah_account,
        "ali_account": ali_account,
    }


# ---------- Happy path ----------
async def test_send_money(client: AsyncClient, db: AsyncSession, setup: dict[str, Any]) -> None:
    response = await send(
        client,
        setup["aisyah"],
        payee_id=setup["payee_id"],
        amount="250.50",
        key=new_key(),
        note="  Rent   share ",
    )
    assert response.status_code == 201, response.text
    receipt = response.json()

    assert receipt["status"] == "posted"
    assert receipt["direction"] == "out"
    assert receipt["amount"] == "250.50"
    assert receipt["note"] == "Rent share"
    assert receipt["balance_after"] == "9749.50"
    assert receipt["reference"].startswith("JG")
    assert receipt["payee"] == {"id": setup["payee_id"], "nickname": "Ali (housemate)"}
    assert receipt["counterparty"]["name"] == "Ali b** A**"
    assert receipt["from_account"] == "•••• " + setup["aisyah_account"]["account_number"][-4:]
    assert "Idempotent-Replayed" not in response.headers

    # Money really moved, and the books still balance.
    assert await balance(client, setup["aisyah"]) == "9749.50"
    assert await balance(client, setup["ali"]) == "10250.50"
    assert await ledger_crud.system_total(db) == 0

    # Both statements show it, each from their own side.
    mine = (await client.get("/accounts/me/transactions", headers=bearer(setup["aisyah"]))).json()
    theirs = (await client.get("/accounts/me/transactions", headers=bearer(setup["ali"]))).json()
    assert (mine["items"][0]["direction"], mine["items"][0]["amount"]) == ("out", "250.50")
    assert (theirs["items"][0]["direction"], theirs["items"][0]["amount"]) == ("in", "250.50")
    assert theirs["items"][0]["counterparty"]["name"] == "Aisyah R**"
    assert theirs["items"][0]["description"] == "Rent share"


async def test_amount_as_json_number_and_default_description(
    client: AsyncClient, setup: dict[str, Any]
) -> None:
    response = await send(
        client, setup["aisyah"], payee_id=setup["payee_id"], amount=20, key=new_key()
    )
    assert response.status_code == 201
    assert response.json()["amount"] == "20.00"
    assert response.json()["note"] is None
    history = (await client.get("/accounts/me/transactions", headers=bearer(setup["ali"]))).json()
    assert history["items"][0]["description"] == "Fund transfer"


# ---------- Receipts ----------
async def test_receipt_for_sender_and_recipient_only(
    client: AsyncClient, setup: dict[str, Any]
) -> None:
    sent = await send(
        client, setup["aisyah"], payee_id=setup["payee_id"], amount="10.00", key=new_key()
    )
    transfer_id = sent.json()["id"]

    as_sender = await client.get(f"/transfers/{transfer_id}", headers=bearer(setup["aisyah"]))
    assert as_sender.status_code == 200
    assert as_sender.json() == sent.json()

    as_recipient = await client.get(f"/transfers/{transfer_id}", headers=bearer(setup["ali"]))
    assert as_recipient.status_code == 200
    body = as_recipient.json()
    assert body["direction"] == "in"
    assert body["payee"] is None  # Aisyah's nickname for Ali is her business
    assert body["balance_after"] == "10010.00"
    assert body["counterparty"]["name"] == "Aisyah R**"

    stranger, _ = await register(client, "Mei Tan", 3)
    nosy = await client.get(f"/transfers/{transfer_id}", headers=bearer(stranger))
    assert nosy.status_code == 404 and nosy.json()["code"] == "transfer_not_found"
    assert (await client.get("/transfers/999999", headers=bearer(stranger))).status_code == 404


async def test_opening_balance_is_not_a_transfer(client: AsyncClient, db: AsyncSession) -> None:
    token, _ = await register(client, "Aisyah Rahman", 1)
    opening = await db.scalar(select(Transaction.id))
    assert (await client.get(f"/transfers/{opening}", headers=bearer(token))).status_code == 404


# ---------- Idempotency (double-tap safety) ----------
async def test_same_key_twice_sends_once(
    client: AsyncClient, db: AsyncSession, setup: dict[str, Any]
) -> None:
    key = new_key()
    first = await send(
        client, setup["aisyah"], payee_id=setup["payee_id"], amount="100.00", key=key
    )
    again = await send(
        client, setup["aisyah"], payee_id=setup["payee_id"], amount="100.00", key=key
    )

    assert first.status_code == 201
    assert again.status_code == 200
    assert again.headers["Idempotent-Replayed"] == "true"
    assert again.json() == first.json()  # the same transfer, same balance_after
    assert await balance(client, setup["aisyah"]) == "9900.00"  # paid ONCE
    transfers = await db.scalar(
        select(func.count())
        .select_from(Transaction)
        .where(Transaction.transaction_type == TransactionType.TRANSFER)
    )
    assert transfers == 1


async def test_same_key_for_a_different_transfer_is_refused(
    client: AsyncClient, setup: dict[str, Any]
) -> None:
    key = new_key()
    await send(client, setup["aisyah"], payee_id=setup["payee_id"], amount="100.00", key=key)
    other = await send(
        client, setup["aisyah"], payee_id=setup["payee_id"], amount="999.00", key=key
    )
    assert other.status_code == 409
    assert other.json()["code"] == "idempotency_key_reused"
    assert await balance(client, setup["aisyah"]) == "9900.00"


async def test_keys_are_per_customer_and_dont_clash_with_internal_ones(
    client: AsyncClient, setup: dict[str, Any]
) -> None:
    # "opening-balance" is the key of every customer's opening transaction.
    response = await send(
        client, setup["aisyah"], payee_id=setup["payee_id"], amount="1.00", key="opening-balance"
    )
    assert response.status_code == 201
    # Ali may use the same key for his own transfer: keys are per customer.
    ali_payee = await add_payee(client, setup["ali"], setup["aisyah_account"]["account_number"])
    response = await send(
        client, setup["ali"], payee_id=ali_payee, amount="1.00", key="opening-balance"
    )
    assert response.status_code == 201


async def test_double_tap_at_the_same_moment_sends_once(
    client: AsyncClient, setup: dict[str, Any]
) -> None:
    """Two identical requests in flight together: one pays, the other replays it."""
    key = new_key()
    a, b = await asyncio.gather(
        send(client, setup["aisyah"], payee_id=setup["payee_id"], amount="300.00", key=key),
        send(client, setup["aisyah"], payee_id=setup["payee_id"], amount="300.00", key=key),
    )
    assert sorted([a.status_code, b.status_code]) == [200, 201]
    assert a.json()["id"] == b.json()["id"]
    assert await balance(client, setup["aisyah"]) == "9700.00"


async def test_idempotency_key_header_rules(client: AsyncClient, setup: dict[str, Any]) -> None:
    for key in (None, "short", "has spaces in it", "x" * 101, "semi;colon-key"):
        response = await send(
            client, setup["aisyah"], payee_id=setup["payee_id"], amount="1.00", key=key
        )
        assert response.status_code == 422, key


# ---------- Rules ----------
async def test_cannot_overspend(
    client: AsyncClient, db: AsyncSession, setup: dict[str, Any]
) -> None:
    response = await send(
        client, setup["aisyah"], payee_id=setup["payee_id"], amount="10000.01", key=new_key()
    )
    assert response.status_code == 409
    assert response.json()["code"] == "insufficient_funds"
    assert await balance(client, setup["aisyah"]) == "10000.00"

    # Exactly everything is fine.
    response = await send(
        client, setup["aisyah"], payee_id=setup["payee_id"], amount="10000.00", key=new_key()
    )
    assert response.status_code == 201
    assert response.json()["balance_after"] == "0.00"
    assert await ledger_crud.system_total(db) == 0


async def test_concurrent_transfers_cannot_double_spend(
    client: AsyncClient, setup: dict[str, Any]
) -> None:
    """Two different RM 6,000 transfers at once from RM 10,000: one must fail."""
    a, b = await asyncio.gather(
        send(client, setup["aisyah"], payee_id=setup["payee_id"], amount="6000.00", key=new_key()),
        send(client, setup["aisyah"], payee_id=setup["payee_id"], amount="6000.00", key=new_key()),
    )
    assert sorted([a.status_code, b.status_code]) == [201, 409]
    assert await balance(client, setup["aisyah"]) == "4000.00"


@pytest.mark.parametrize("amount", ["0", "-5", "10.001", "NaN", "abc", None])
async def test_bad_amounts(client: AsyncClient, setup: dict[str, Any], amount: Any) -> None:
    response = await send(
        client, setup["aisyah"], payee_id=setup["payee_id"], amount=amount, key=new_key()
    )
    assert response.status_code == 422


async def test_note_too_long(client: AsyncClient, setup: dict[str, Any]) -> None:
    response = await send(
        client,
        setup["aisyah"],
        payee_id=setup["payee_id"],
        amount="1.00",
        key=new_key(),
        note="x" * 141,
    )
    assert response.status_code == 422


async def test_payee_must_be_yours_and_live(client: AsyncClient, setup: dict[str, Any]) -> None:
    # Ali can't use Aisyah's payee.
    response = await send(
        client, setup["ali"], payee_id=setup["payee_id"], amount="1.00", key=new_key()
    )
    assert response.status_code == 404 and response.json()["code"] == "payee_not_found"

    # A removed payee can't be paid.
    await client.delete(f"/payees/{setup['payee_id']}", headers=bearer(setup["aisyah"]))
    response = await send(
        client, setup["aisyah"], payee_id=setup["payee_id"], amount="1.00", key=new_key()
    )
    assert response.status_code == 404


async def test_frozen_or_closed_accounts(
    client: AsyncClient, db: AsyncSession, setup: dict[str, Any]
) -> None:
    async def set_status(account_id: int, status: AccountStatus) -> None:
        account = await db.get(BankAccount, account_id)
        assert account is not None
        account.status = status
        await db.commit()

    # Recipient closed: refused.
    await set_status(setup["ali_account"]["id"], AccountStatus.CLOSED)
    response = await send(
        client, setup["aisyah"], payee_id=setup["payee_id"], amount="1.00", key=new_key()
    )
    assert response.status_code == 409 and response.json()["code"] == "account_unavailable"

    # Recipient frozen: can still receive.
    await set_status(setup["ali_account"]["id"], AccountStatus.FROZEN)
    response = await send(
        client, setup["aisyah"], payee_id=setup["payee_id"], amount="1.00", key=new_key()
    )
    assert response.status_code == 201

    # Sender's account frozen: can't send.
    await set_status(setup["aisyah_account"]["id"], AccountStatus.FROZEN)
    response = await send(
        client, setup["aisyah"], payee_id=setup["payee_id"], amount="1.00", key=new_key()
    )
    assert response.status_code == 409
    assert Decimal(await balance(client, setup["ali"])) == Decimal("10001.00")


async def test_requires_login(client: AsyncClient) -> None:
    response = await client.post(
        "/transfers", headers={"Idempotency-Key": new_key()}, json={"payee_id": 1, "amount": "1"}
    )
    assert response.status_code == 401
    assert (await client.get("/transfers/1")).status_code == 401
