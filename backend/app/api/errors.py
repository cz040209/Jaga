"""Turn service-layer errors into HTTP responses."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.services.auth import (
    AccountNotActive,
    AuthError,
    DeviceBlocked,
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidRefreshToken,
    PhoneAlreadyRegistered,
)

AUTH_ERROR_STATUS: dict[type[AuthError], int] = {
    EmailAlreadyRegistered: status.HTTP_409_CONFLICT,
    PhoneAlreadyRegistered: status.HTTP_409_CONFLICT,
    InvalidCredentials: status.HTTP_401_UNAUTHORIZED,
    InvalidRefreshToken: status.HTTP_401_UNAUTHORIZED,
    AccountNotActive: status.HTTP_403_FORBIDDEN,
    DeviceBlocked: status.HTTP_403_FORBIDDEN,
}


async def auth_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AuthError)
    status_code = AUTH_ERROR_STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST)
    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.message, "code": exc.code},
        headers=headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AuthError, auth_error_handler)
