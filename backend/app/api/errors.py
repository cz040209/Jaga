"""Turn service-layer errors into HTTP responses: {"detail": ..., "code": ...}."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.services.auth import (
    AccountNotActive,
    DeviceBlocked,
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidRefreshToken,
    PhoneAlreadyRegistered,
)
from app.services.errors import (
    InvalidCurrentPassword,
    NotFound,
    PasswordUnchanged,
    ServiceError,
)

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
}


async def service_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ServiceError)
    status_code = ERROR_STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST)
    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.message, "code": exc.code},
        headers=headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ServiceError, service_error_handler)
