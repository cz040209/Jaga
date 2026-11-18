"""Customer self-service: profile, password, sessions, devices, closing the account.

Business rules live here; database access goes through app/crud.
"""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password_async, verify_password_async
from app.crud import customer as customer_crud
from app.crud import customer_session as session_crud
from app.crud import device as device_crud
from app.models.enums import SessionStatus
from app.models.identity import Customer, CustomerSession, Device
from app.schemas.customer import ChangePasswordRequest, CustomerUpdate
from app.services.errors import InvalidCurrentPassword, NotFound, PasswordUnchanged


def _now() -> datetime:
    return datetime.now(UTC)


# ---------- Profile ----------
async def update_profile(db: AsyncSession, customer: Customer, data: CustomerUpdate) -> Customer:
    customer_crud.update_profile(
        customer,
        full_name=data.full_name,
        preferred_language=data.preferred_language,
    )
    await db.commit()
    await db.refresh(customer)
    return customer


async def change_password(
    db: AsyncSession,
    customer: Customer,
    data: ChangePasswordRequest,
    *,
    current_session_id: int,
) -> int:
    """Change the password and sign out every OTHER device. Returns how many were signed out.

    Signing out other devices matters: if someone else knew the old password
    and is logged in, changing it must kick them out.
    """
    if not await verify_password_async(data.current_password, customer.password_hash):
        raise InvalidCurrentPassword()
    if await verify_password_async(data.new_password, customer.password_hash):
        raise PasswordUnchanged()

    now = _now()
    customer_crud.set_password(customer, await hash_password_async(data.new_password), now)
    revoked = await session_crud.revoke_all_for_customer(
        db,
        customer.id,
        reason="password_changed",
        now=now,
        except_session_id=current_session_id,
    )
    await db.commit()
    return revoked


async def close_account(db: AsyncSession, customer: Customer, password: str) -> None:
    """Soft delete: status 'closed', every session revoked, data kept for audit."""
    if not await verify_password_async(password, customer.password_hash):
        raise InvalidCurrentPassword()

    now = _now()
    customer_crud.close(customer, now)
    await session_crud.revoke_all_for_customer(db, customer.id, reason="account_closed", now=now)
    await db.commit()


# ---------- Sessions ----------
async def list_sessions(db: AsyncSession, customer_id: int) -> Sequence[CustomerSession]:
    return await session_crud.list_active_for_customer(db, customer_id)


async def revoke_session(db: AsyncSession, customer_id: int, session_id: int) -> None:
    """Sign out one device. Someone else's session id behaves exactly like a missing one."""
    session_row = await session_crud.get_for_customer(db, customer_id, session_id)
    if session_row is None or session_row.status != SessionStatus.ACTIVE:
        raise NotFound("Session not found")
    session_crud.revoke(session_row, reason="revoked_by_customer", now=_now())
    await db.commit()


async def revoke_other_sessions(
    db: AsyncSession, customer_id: int, *, current_session_id: int
) -> int:
    """'Sign out everywhere else'. The current session stays; use /auth/logout for that."""
    revoked = await session_crud.revoke_all_for_customer(
        db,
        customer_id,
        reason="revoked_by_customer",
        now=_now(),
        except_session_id=current_session_id,
    )
    await db.commit()
    return revoked


# ---------- Devices ----------
async def list_devices(db: AsyncSession, customer_id: int) -> Sequence[Device]:
    return await device_crud.list_for_customer(db, customer_id)


async def _get_own_device(db: AsyncSession, customer_id: int, device_id: int) -> Device:
    device = await device_crud.get_for_customer(db, customer_id, device_id)
    if device is None:
        raise NotFound("Device not found")
    return device


async def rename_device(
    db: AsyncSession, customer_id: int, device_id: int, display_name: str
) -> Device:
    device = await _get_own_device(db, customer_id, device_id)
    device_crud.rename(device, display_name)
    await db.commit()
    await db.refresh(device)
    return device


async def forget_device(db: AsyncSession, customer_id: int, device_id: int) -> None:
    """Sign the device out and forget it (soft delete), so its next login counts as new."""
    device = await _get_own_device(db, customer_id, device_id)
    now = _now()
    await session_crud.revoke_all_for_device(db, device.id, reason="device_forgotten", now=now)
    device_crud.soft_delete(device, now)
    await db.commit()
