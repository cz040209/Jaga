"""Customer self-service routes under /customers/me.

A bank never hard-deletes a customer: DELETE /customers/me closes the account
(status 'closed'); deleting a session signs that device out.
"""

from typing import Any

from fastapi import APIRouter, status

from app.api.deps import CurrentAuth, CurrentCustomer, DbSession
from app.schemas.auth import CustomerOut, ErrorResponse
from app.schemas.customer import (
    ChangePasswordRequest,
    CloseAccountRequest,
    CustomerUpdate,
    DeviceOut,
    DeviceUpdate,
    RevokedSessions,
    SessionOut,
)
from app.services import customers as customer_service

router = APIRouter(prefix="/customers/me", tags=["customers"])

OpenApiResponses = dict[int | str, dict[str, Any]]

NOT_FOUND: OpenApiResponses = {
    404: {"model": ErrorResponse, "description": "Not found (or not yours)"}
}
BAD_PASSWORD: OpenApiResponses = {
    400: {"model": ErrorResponse, "description": "Password incorrect / unchanged"}
}


# ---------- Profile ----------
@router.get("")
async def get_profile(customer: CurrentCustomer) -> CustomerOut:
    """Your profile."""
    return CustomerOut.model_validate(customer)


@router.patch("")
async def update_profile(
    body: CustomerUpdate, customer: CurrentCustomer, db: DbSession
) -> CustomerOut:
    """Change your name and/or preferred language. Send only the fields to change."""
    updated = await customer_service.update_profile(db, customer, body)
    return CustomerOut.model_validate(updated)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT, responses=BAD_PASSWORD)
async def close_account(body: CloseAccountRequest, auth: CurrentAuth, db: DbSession) -> None:
    """Close your account (soft delete). Every device is signed out. Requires your password."""
    await customer_service.close_account(db, auth.customer, body.password)


@router.post("/password", responses=BAD_PASSWORD)
async def change_password(
    body: ChangePasswordRequest, auth: CurrentAuth, db: DbSession
) -> RevokedSessions:
    """Change your password. Other devices are signed out; this one stays logged in."""
    revoked = await customer_service.change_password(
        db, auth.customer, body, current_session_id=auth.session.id
    )
    return RevokedSessions(revoked_sessions=revoked)


# ---------- Sessions ----------
@router.get("/sessions")
async def list_sessions(auth: CurrentAuth, db: DbSession) -> list[SessionOut]:
    """Where you're logged in. `is_current` marks the session making this request."""
    rows = await customer_service.list_sessions(db, auth.customer.id)
    return [
        SessionOut.model_validate(row).model_copy(update={"is_current": row.id == auth.session.id})
        for row in rows
    ]


@router.delete("/sessions")
async def revoke_other_sessions(auth: CurrentAuth, db: DbSession) -> RevokedSessions:
    """Sign out every other device. To sign out this one, use POST /auth/logout."""
    revoked = await customer_service.revoke_other_sessions(
        db, auth.customer.id, current_session_id=auth.session.id
    )
    return RevokedSessions(revoked_sessions=revoked)


@router.delete(
    "/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT, responses=NOT_FOUND
)
async def revoke_session(session_id: int, auth: CurrentAuth, db: DbSession) -> None:
    """Sign out one device. Its access token stops working immediately."""
    await customer_service.revoke_session(db, auth.customer.id, session_id)


# ---------- Devices ----------
@router.get("/devices")
async def list_devices(auth: CurrentAuth, db: DbSession) -> list[DeviceOut]:
    """Devices that have logged in to your account."""
    devices = await customer_service.list_devices(db, auth.customer.id)
    return [
        DeviceOut.model_validate(device).model_copy(
            update={"is_current": device.id == auth.session.device_id}
        )
        for device in devices
    ]


@router.patch("/devices/{device_id}", responses=NOT_FOUND)
async def rename_device(
    device_id: int, body: DeviceUpdate, auth: CurrentAuth, db: DbSession
) -> DeviceOut:
    """Give a device a friendly name, e.g. "Aisyah's iPhone"."""
    device = await customer_service.rename_device(
        db, auth.customer.id, device_id, body.display_name
    )
    return DeviceOut.model_validate(device).model_copy(
        update={"is_current": device.id == auth.session.device_id}
    )


@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT, responses=NOT_FOUND)
async def forget_device(device_id: int, auth: CurrentAuth, db: DbSession) -> None:
    """Sign the device out and forget it: its next login counts as a new device."""
    await customer_service.forget_device(db, auth.customer.id, device_id)
