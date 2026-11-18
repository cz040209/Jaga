"""Shared FastAPI dependencies: database session, client info, current customer."""

import ipaddress
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import decode_access_token_claims
from app.crud import customer as customer_crud
from app.crud import customer_session as session_crud
from app.models.enums import CustomerStatus, SessionStatus
from app.models.identity import Customer, CustomerSession
from app.services.auth import ClientInfo

DbSession = Annotated[AsyncSession, Depends(get_session)]

# auto_error=False: we raise our own 401 with a consistent message.
bearer_scheme = HTTPBearer(auto_error=False)


def get_client_info(request: Request) -> ClientInfo:
    host = request.client.host if request.client else None
    try:
        ip = str(ipaddress.ip_address(host)) if host else None
    except ValueError:
        ip = None
    user_agent = request.headers.get("user-agent")
    return ClientInfo(ip_address=ip, user_agent=user_agent[:1000] if user_agent else None)


Client = Annotated[ClientInfo, Depends(get_client_info)]


@dataclass(frozen=True)
class AuthContext:
    """The logged-in customer and the session (device login) the request belongs to."""

    customer: Customer
    session: CustomerSession


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_auth_context(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> AuthContext:
    if credentials is None:
        raise _unauthorized()
    try:
        # expected_type="customer": a staff token is rejected here.
        claims = decode_access_token_claims(credentials.credentials, "customer")
    except jwt.InvalidTokenError:
        raise _unauthorized() from None
    if claims.session_id is None:
        raise _unauthorized()

    # The session must still be active: logging out a device, changing the
    # password or the kill switch takes effect on the very next request,
    # not when the 15-minute access token expires.
    session_row = await session_crud.get(db, claims.session_id)
    if (
        session_row is None
        or session_row.customer_id != claims.subject_id
        or session_row.status != SessionStatus.ACTIVE
        or session_row.expires_at <= datetime.now(UTC)
    ):
        raise _unauthorized()

    customer = await customer_crud.get(db, claims.subject_id)
    if customer is None:
        raise _unauthorized()
    if customer.status != CustomerStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is frozen or closed",
        )
    return AuthContext(customer=customer, session=session_row)


CurrentAuth = Annotated[AuthContext, Depends(get_auth_context)]


async def get_current_customer(auth: CurrentAuth) -> Customer:
    return auth.customer


CurrentCustomer = Annotated[Customer, Depends(get_current_customer)]
