"""Errors raised by the service layer.

Services raise these; app/api/errors.py turns them into HTTP status codes.
Each error has a stable machine-readable `code` (for the frontend) and a
human-readable `message` (safe to show to the customer).
"""


class ServiceError(Exception):
    code = "error"
    message = "Something went wrong"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or type(self).message
        super().__init__(self.message)


class NotFound(ServiceError):
    code = "not_found"
    message = "Not found"


class AccountNotFound(NotFound):
    code = "account_not_found"
    message = "Account not found"


class InvalidCurrentPassword(ServiceError):
    code = "invalid_password"
    message = "Your password is incorrect"


class PasswordUnchanged(ServiceError):
    code = "password_unchanged"
    message = "Your new password must be different from the current one"


class BalanceNotZero(ServiceError):
    code = "balance_not_zero"
    message = "Move all your money out before closing your account"
