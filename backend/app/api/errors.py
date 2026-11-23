"""Turn service-layer errors into HTTP responses: {"detail": ..., "code": ...}."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.ledger.service import AccountUnavailable, InsufficientFunds, InvalidAmount
from app.services.auth import (
    AccountNotActive,
    DeviceBlocked,
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidRefreshToken,
    PhoneAlreadyRegistered,
)
from app.services.errors import (
    BalanceNotZero,
    InvalidCurrentPassword,
    NotFound,
    PasswordUnchanged,
    ServiceError,
)
from app.services.payees import InvalidAccountNumber, OwnAccount, PayeeAlreadyExists
from app.services.transfers import IdempotencyKeyReused

ERROR_STATUS: dict[type[ServiceError], int] = {
    EmailAlreadyRegistered: status.HTTP_409_CONFLICT,
    PhoneAlreadyRegistered: status.HTTP_409_CONFLICT,
    InvalidCredentials: status.HTTP_401_UNAUTHORIZED,
    InvalidRefreshToken: status.HTTP_401_UNAUTHORIZED,
    AccountNotActive: status.HTTP_403_FORBIDDEN,
    DeviceBlocked: status.HTTP_403_FORBIDDEN,
    InvalidCurrentPassword: status.HTTP_400_BAD_REQUEST,
    PasswordUnchanged: status.HTTP_400_BAD_REQUEST,
    NotFound: status.HTTP_404_NOT_FOUND,
    BalanceNotZero: status.HTTP_409_CONFLICT,
    InsufficientFunds: status.HTTP_409_CONFLICT,
    AccountUnavailable: status.HTTP_409_CONFLICT,
    InvalidAmount: status.HTTP_400_BAD_REQUEST,
    InvalidAccountNumber: status.HTTP_400_BAD_REQUEST,
    OwnAccount: status.HTTP_400_BAD_REQUEST,
    PayeeAlreadyExists: status.HTTP_409_CONFLICT,
    IdempotencyKeyReused: status.HTTP_409_CONFLICT,
}


async def service_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ServiceError)
    # Walk up the class tree, so e.g. AccountNotFound gets NotFound's 404.
    status_code = next(
        (ERROR_STATUS[cls] for cls in type(exc).__mro__ if cls in ERROR_STATUS),
        status.HTTP_400_BAD_REQUEST,
    )
    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.message, "code": exc.code},
        headers=headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ServiceError, service_error_handler)
