"""Test setup: a separate database, rebuilt from the migrations on every run.

Tests NEVER touch jaga_db. They use jaga_test, which is dropped and recreated
at the start of each pytest run, then emptied before each API test.
"""

import asyncio
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_DB_NAME = "jaga_test"

_main_url = make_url(settings.database_url)
MAIN_DB_NAME = _main_url.database
assert MAIN_DB_NAME != TEST_DB_NAME, "DATABASE_URL already points at the test database"

# Point the whole app at the test database BEFORE app.core.db creates its engine.
settings.database_url = _main_url.set(database=TEST_DB_NAME).render_as_string(
    hide_password=False
)


def _asyncpg_dsn(database: str | None) -> str:
    return _main_url.set(drivername="postgresql", database=database).render_as_string(
        hide_password=False
    )


async def _recreate_test_database() -> None:
    conn = await asyncpg.connect(_asyncpg_dsn(MAIN_DB_NAME))
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}" WITH (FORCE)')
        await conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    finally:
        await conn.close()


@pytest.fixture(scope="session")
def test_database() -> Iterator[None]:
    """Create jaga_test and run every Alembic migration on it, once per test run."""
    from alembic import command
    from alembic.config import Config

    asyncio.run(_recreate_test_database())
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(config, "head")
    yield


async def _truncate_all_tables() -> None:
    from app.core.db import engine

    async with engine.begin() as conn:
        tables = (
            await conn.execute(
                text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
                )
            )
        ).scalars().all()
        quoted = ", ".join(f'"{table}"' for table in tables)
        await conn.execute(text(f"TRUNCATE {quoted} RESTART IDENTITY CASCADE"))


@pytest.fixture
async def client(test_database: None) -> AsyncIterator[AsyncClient]:
    """An HTTP client that talks to the app in-process, with an empty database."""
    from app.main import app

    await _truncate_all_tables()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


@pytest.fixture
async def db(test_database: None) -> AsyncIterator[AsyncSession]:
    """A database session for checking what the API wrote."""
    from app.core.db import SessionLocal

    async with SessionLocal() as session:
        yield session
