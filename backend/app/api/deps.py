"""Shared FastAPI dependencies: database session, client info, current customer."""

import ipaddress
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import decode_access_token
from app.models.enums import CustomerStatus
from app.models.identity import Customer
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


async def get_current_customer(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> Customer:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        # expected_type="customer": a staff token is rejected here.
        customer_id = decode_access_token(credentials.credentials, "customer")
    except jwt.InvalidTokenError:
        raise unauthorized from None

    customer = await db.get(Customer, customer_id)
    if customer is None:
        raise unauthorized
    # Kill switch: an access token issued before the freeze stops working now,
    # not 15 minutes from now.
    if customer.status != CustomerStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is frozen or closed",
        )
    return customer


CurrentCustomer = Annotated[Customer, Depends(get_current_customer)]
