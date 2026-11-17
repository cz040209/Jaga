"""Customer auth routes. Kept thin: validate → call the service → shape the response."""

from fastapi import APIRouter, status

from app.api.deps import Client, CurrentCustomer, DbSession
from app.schemas.auth import (
    AuthResponse,
    CustomerOut,
    ErrorResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _to_response(result: auth_service.AuthResult) -> AuthResponse:
    return AuthResponse(
        customer=CustomerOut.model_validate(result.customer),
        tokens=result.tokens,
        is_new_device=result.is_new_device,
    )


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse, "description": "Email or phone already registered"}},
)
async def register(body: RegisterRequest, db: DbSession, client: Client) -> AuthResponse:
    """Create a customer account and log them in straight away."""
    return _to_response(await auth_service.register(db, body, client))


@router.post(
    "/login",
    responses={
        401: {"model": ErrorResponse, "description": "Invalid email or password"},
        403: {"model": ErrorResponse, "description": "Account frozen or device blocked"},
    },
)
async def login(body: LoginRequest, db: DbSession, client: Client) -> AuthResponse:
    """Check email + password, open a session, return an access + refresh token."""
    return _to_response(await auth_service.login(db, body, client))


@router.post(
    "/refresh",
    responses={401: {"model": ErrorResponse, "description": "Session ended; log in again"}},
)
async def refresh(body: RefreshRequest, db: DbSession, client: Client) -> TokenPair:
    """Swap a refresh token for a new token pair. The old refresh token stops working."""
    return await auth_service.refresh(db, body.refresh_token, client)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: LogoutRequest, db: DbSession) -> None:
    """End this session. Safe to call more than once."""
    await auth_service.logout(db, body.refresh_token)


@router.get("/me")
async def me(customer: CurrentCustomer) -> CustomerOut:
    """The logged-in customer. Proves the access token works."""
    return CustomerOut.model_validate(customer)
