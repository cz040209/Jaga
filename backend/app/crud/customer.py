"""Reads and writes for the customers table."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import CustomerStatus
from app.models.identity import Customer


# ---------- Read ----------
async def get(db: AsyncSession, customer_id: int) -> Customer | None:
    return await db.get(Customer, customer_id)


async def get_by_email(db: AsyncSession, email: str) -> Customer | None:
    # lower(email) matches the uq_customers_email_lower index.
    return await db.scalar(select(Customer).where(func.lower(Customer.email) == email.lower()))


async def email_exists(db: AsyncSession, email: str) -> bool:
    found = await db.scalar(
        select(Customer.id).where(func.lower(Customer.email) == email.lower())
    )
    return found is not None


async def phone_exists(db: AsyncSession, phone_number: str) -> bool:
    found = await db.scalar(select(Customer.id).where(Customer.phone_number == phone_number))
    return found is not None


# ---------- Create ----------
async def create(
    db: AsyncSession,
    *,
    email: str,
    phone_number: str,
    full_name: str,
    password_hash: str,
    preferred_language: str,
) -> Customer:
    customer = Customer(
        email=email,
        phone_number=phone_number,
        full_name=full_name,
        password_hash=password_hash,
        preferred_language=preferred_language,
        status=CustomerStatus.ACTIVE,
        failed_login_count=0,
    )
    db.add(customer)
    await db.flush()  # assigns customer.id; raises IntegrityError on a duplicate
    return customer


# ---------- Update ----------
def update_profile(
    customer: Customer,
    *,
    full_name: str | None = None,
    preferred_language: str | None = None,
) -> None:
    if full_name is not None:
        customer.full_name = full_name
    if preferred_language is not None:
        customer.preferred_language = preferred_language


def set_password(customer: Customer, password_hash: str, now: datetime) -> None:
    customer.password_hash = password_hash
    customer.password_changed_at = now


def record_failed_login(customer: Customer) -> None:
    # SQL-side increment: correct even if two failed logins happen at once.
    customer.failed_login_count = Customer.failed_login_count + 1


def record_successful_login(customer: Customer, now: datetime) -> None:
    customer.failed_login_count = 0
    customer.last_login_at = now


def close(customer: Customer, now: datetime) -> None:
    """Soft delete: the row stays for audit, the account can no longer be used."""
    customer.status = CustomerStatus.CLOSED
    customer.closed_at = now
