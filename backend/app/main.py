from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api import accounts, auth, customers, inbox, payees, transfers
from app.api.errors import register_exception_handlers
from app.core.cache import redis_client
from app.core.config import settings
from app.core.db import engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    yield                        # the app runs here
    await engine.dispose()       # on shutdown: close DB connections
    await redis_client.aclose()  # and Redis connections

app = FastAPI(title=settings.app_name, lifespan=lifespan)
register_exception_handlers(app)
app.include_router(auth.router)
app.include_router(customers.router)
app.include_router(accounts.router)
app.include_router(payees.router)
app.include_router(transfers.router)
app.include_router(inbox.router)

@app.get("/health")
async def health() -> dict[str, str]:
    status = {"api": "ok"}

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        status["db"] = "ok"
    except Exception as exc:
        status["db"] = f"error: {exc}"

    try:
        await redis_client.ping()
        status["redis"] = "ok"
    except Exception as exc:
        status["redis"] = f"error: {exc}"

    return status