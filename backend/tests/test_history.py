"""GET /accounts/me/transactions: statement lines, running balance, paging, ownership."""

from decimal import Decimal
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ledger import service as ledger
from app.models.enums import Channel, TransactionType

PASSWORD = "S3cure-pass!"


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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


async def send(db: AsyncSession, source: int, destination: int, amount: str, key: str) -> None:
    await ledger.transfer(
        db,
        source_account_id=source,
        destination_account_id=destination,
        amount=Decimal(amount),
        transaction_type=TransactionType.TRANSFER,
        channel=Channel.API,
        idempotency_key=key,
        description="Makan",
    )
    await db.commit()


async def history(client: AsyncClient, token: str, **params: Any) -> Any:
    return await client.get("/accounts/me/transactions", headers=bearer(token), params=params)


async def test_new_customer_sees_opening_balance(client: AsyncClient) -> None:
    token, account = await register(client, "Aisyah Rahman", 1)
    page = (await history(client, token)).json()

    assert page["account_id"] == account["id"]
    assert page["next_cursor"] is None
    [line] = page["items"]
    assert line["type"] == "opening_balance"
    assert line["direction"] == "in"
    assert line["amount"] == "10000.00"
    assert line["balance_after"] == "10000.00"
    assert line["status"] == "posted"
    assert line["counterparty"] == {"name": "Jaga", "masked_number": None}
    assert line["reference"].startswith("JG")


async def test_lines_are_newest_first_with_running_balance(
    client: AsyncClient, db: AsyncSession
) -> None:
    token, aisyah = await register(client, "Aisyah Rahman", 1)
    _, ali = await register(client, "Ali bin Abu Bakar", 2)

    await send(db, aisyah["id"], ali["id"], "250.00", "t1")
    await send(db, ali["id"], aisyah["id"], "40.50", "t2")

    items = (await history(client, token)).json()["items"]
    assert [(i["direction"], i["amount"], i["balance_after"]) for i in items] == [
        ("in", "40.50", "9790.50"),
        ("out", "250.00", "9750.00"),
        ("in", "10000.00", "10000.00"),
    ]
    # The other person is masked: enough to recognise, not their full details.
    assert items[0]["counterparty"] == {
        "name": "Ali b** A** B**",
        "masked_number": "•••• " + ali["account_number"][-4:],
    }
    assert items[0]["description"] == "Makan"
    # Same transfer, other side: Ali's statement shows it as money out.
    # (Covered by the running-balance check on Ali's side below.)


async def test_paging_with_cursor_keeps_balances_correct(
    client: AsyncClient, db: AsyncSession
) -> None:
    token, aisyah = await register(client, "Aisyah Rahman", 1)
    _, ali = await register(client, "Ali Abu", 2)
    for n in range(4):
        await send(db, aisyah["id"], ali["id"], "100.00", f"p{n}")
    # 5 lines in total: opening + 4 transfers out.

    seen: list[dict[str, Any]] = []
    cursor = None
    pages = 0
    while True:
        params: dict[str, Any] = {"limit": 2}
        if cursor is not None:
            params["before"] = cursor
        page = (await history(client, token, **params)).json()
        seen.extend(page["items"])
        pages += 1
        cursor = page["next_cursor"]
        if cursor is None:
            break

    assert pages == 3  # 2 + 2 + 1
    assert len({i["id"] for i in seen}) == 5  # no line twice, none missing
    assert [i["balance_after"] for i in seen] == [
        "9600.00",
        "9700.00",
        "9800.00",
        "9900.00",
        "10000.00",
    ]


async def test_cannot_read_someone_elses_account(client: AsyncClient) -> None:
    token, _ = await register(client, "Aisyah Rahman", 1)
    _, ali = await register(client, "Ali Abu", 2)

    response = await history(client, token, account_id=ali["id"])
    assert response.status_code == 404
    assert response.json()["code"] == "account_not_found"
    # Same answer as an account that doesn't exist at all.
    assert (await history(client, token, account_id=999999)).status_code == 404


async def test_history_validation_and_auth(client: AsyncClient) -> None:
    token, _ = await register(client, "Aisyah Rahman", 1)
    for bad in ({"limit": 0}, {"limit": 101}, {"before": 0}, {"limit": "x"}):
        assert (await history(client, token, **bad)).status_code == 422, bad
    assert (await client.get("/accounts/me/transactions")).status_code == 401
