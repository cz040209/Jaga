"""/payees: lookup, add, list, rename, remove, and the rules that protect each."""

from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.banking import BankAccount, Payee
from app.models.enums import AccountStatus
from app.services.accounts import luhn_check_digit

PASSWORD = "S3cure-pass!"


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def register(client: AsyncClient, name: str, n: int) -> tuple[str, str]:
    """Returns (access_token, account_number)."""
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
    return token, accounts[0]["account_number"]


async def add(client: AsyncClient, token: str, **body: Any) -> Any:
    return await client.post("/payees", headers=bearer(token), json=body)


def a_valid_unused_number() -> str:
    body = "88000000001"
    return body + luhn_check_digit(body)


# ---------- Lookup ----------
async def test_lookup_shows_masked_owner(client: AsyncClient) -> None:
    token, _ = await register(client, "Aisyah Rahman", 1)
    _, ali_number = await register(client, "Ali bin Abu Bakar", 2)

    # Spaces and dashes are fine: people paste numbers like that.
    spaced = f"{ali_number[:4]} {ali_number[4:8]}-{ali_number[8:]}"
    response = await client.get(
        "/payees/lookup", headers=bearer(token), params={"account_number": spaced}
    )
    assert response.status_code == 200
    assert response.json() == {
        "masked_name": "Ali b** A** B**",
        "masked_number": "•••• " + ali_number[-4:],
    }


async def test_lookup_errors(client: AsyncClient) -> None:
    token, own_number = await register(client, "Aisyah Rahman", 1)
    _, ali_number = await register(client, "Ali Abu", 2)

    async def lookup(number: str) -> Any:
        return await client.get(
            "/payees/lookup", headers=bearer(token), params={"account_number": number}
        )

    typo = ali_number[:-1] + str((int(ali_number[-1]) + 1) % 10)
    assert (await lookup(typo)).json()["code"] == "invalid_account_number"
    assert (await lookup("JAGA-TREASURY")).json()["code"] == "invalid_account_number"
    missing = await lookup(a_valid_unused_number())
    assert missing.status_code == 404 and missing.json()["code"] == "account_not_found"
    own = await lookup(own_number)
    assert own.status_code == 400 and own.json()["code"] == "own_account"
    no_login = await client.get("/payees/lookup", params={"account_number": ali_number})
    assert no_login.status_code == 401


# ---------- Add / list ----------
async def test_add_and_list_payees(client: AsyncClient) -> None:
    token, _ = await register(client, "Aisyah Rahman", 1)
    _, ali_number = await register(client, "Ali bin Abu", 2)
    _, mei_number = await register(client, "Tan Mei Ling", 3)

    ali = await add(client, token, account_number=ali_number, nickname="  Ali   (housemate) ")
    assert ali.status_code == 201, ali.text
    body = ali.json()
    assert body["nickname"] == "Ali (housemate)"
    assert body["recipient"]["masked_name"] == "Ali b** A**"
    assert body["check_status"] == "pending"

    # No nickname: the masked owner name is used.
    mei = await add(client, token, account_number=mei_number)
    assert mei.json()["nickname"] == "Tan M** L**"

    listed = (await client.get("/payees", headers=bearer(token))).json()
    assert [p["nickname"] for p in listed] == ["Ali (housemate)", "Tan M** L**"]
    # The full account number of someone else is never sent back.
    assert ali_number not in str(listed)


async def test_add_payee_rules(client: AsyncClient) -> None:
    token, own_number = await register(client, "Aisyah Rahman", 1)
    _, ali_number = await register(client, "Ali Abu", 2)

    assert (await add(client, token, account_number=own_number)).json()["code"] == "own_account"
    assert (await add(client, token, account_number="12345")).status_code == 400
    assert (await add(client, token, account_number=a_valid_unused_number())).status_code == 404

    assert (await add(client, token, account_number=ali_number)).status_code == 201
    again = await add(client, token, account_number=ali_number)
    assert again.status_code == 409 and again.json()["code"] == "payee_exists"

    for bad in ({}, {"account_number": ""}, {"account_number": ali_number, "nickname": "  "}):
        assert (await client.post("/payees", headers=bearer(token), json=bad)).status_code == 422


async def test_closed_account_cannot_be_added(client: AsyncClient, db: AsyncSession) -> None:
    token, _ = await register(client, "Aisyah Rahman", 1)
    _, ali_number = await register(client, "Ali Abu", 2)
    account = await db.scalar(select(BankAccount).where(BankAccount.account_number == ali_number))
    assert account is not None
    account.status = AccountStatus.CLOSED
    await db.commit()

    response = await add(client, token, account_number=ali_number)
    assert response.status_code == 404  # same answer as "doesn't exist"


async def test_payees_are_private(client: AsyncClient) -> None:
    aisyah, _ = await register(client, "Aisyah Rahman", 1)
    ali, ali_number = await register(client, "Ali Abu", 2)
    mei, mei_number = await register(client, "Mei Tan", 3)

    payee_id = (await add(client, aisyah, account_number=mei_number)).json()["id"]

    # Ali sees none of Aisyah's payees, and can't touch them.
    assert (await client.get("/payees", headers=bearer(ali))).json() == []
    renamed = await client.patch(
        f"/payees/{payee_id}", headers=bearer(ali), json={"nickname": "hacked"}
    )
    assert renamed.status_code == 404
    assert (await client.delete(f"/payees/{payee_id}", headers=bearer(ali))).status_code == 404

    # Two customers may both save the same person.
    assert (await add(client, mei, account_number=ali_number)).status_code == 201
    assert (await add(client, aisyah, account_number=ali_number)).status_code == 201


# ---------- Rename / remove ----------
async def test_rename_and_remove(client: AsyncClient, db: AsyncSession) -> None:
    token, _ = await register(client, "Aisyah Rahman", 1)
    _, ali_number = await register(client, "Ali Abu", 2)
    payee_id = (await add(client, token, account_number=ali_number)).json()["id"]

    renamed = await client.patch(
        f"/payees/{payee_id}", headers=bearer(token), json={"nickname": "Ali (gym)"}
    )
    assert renamed.status_code == 200 and renamed.json()["nickname"] == "Ali (gym)"

    removed = await client.delete(f"/payees/{payee_id}", headers=bearer(token))
    assert removed.status_code == 204

    # Soft delete: the row is kept (past transfers point at it), but hidden.
    row = await db.get(Payee, payee_id)
    assert row is not None and row.deleted_at is not None
    assert (await client.get("/payees", headers=bearer(token))).json() == []
    assert (await client.delete(f"/payees/{payee_id}", headers=bearer(token))).status_code == 404

    # Adding the same person again works: a NEW payee row.
    again = await add(client, token, account_number=ali_number)
    assert again.status_code == 201 and again.json()["id"] != payee_id
