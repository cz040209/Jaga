from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    Base,
    EMPTY_JSON,
    EMPTY_JSON_LIST,
    NOT_DELETED,
    IntegerPrimaryKeyMixin,
    SoftDeleteMixin,
    TimestampMixin,
    enum_type,
)
from app.models.enums import (
    AccountStatus,
    AccountType,
    Channel,
    LedgerDirection,
    PayeeCheckStatus,
    TransactionStatus,
    TransactionType,
)


class BankAccount(Base, IntegerPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "bank_accounts"

    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"),
    )
    account_number: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
    )
    account_name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_type: Mapped[AccountType] = mapped_column(
        enum_type(AccountType, "account_type"),
        nullable=False,
    )
    status: Mapped[AccountStatus] = mapped_column(
        enum_type(AccountStatus, "account_status"),
        nullable=False,
        server_default=AccountStatus.ACTIVE.value,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        server_default="MYR",
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    frozen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    freeze_reason: Mapped[str | None] = mapped_column(Text)
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    __table_args__ = (
        CheckConstraint(
            "currency = 'MYR'",
            name="ck_accounts_currency_myr",
        ),
        CheckConstraint(
            """
            (account_type = 'customer' AND customer_id IS NOT NULL)
            OR account_type IN ('merchant', 'system')
            """,
            name="ck_accounts_valid_owner",
        ),
        Index("ix_accounts_customer_status", "customer_id", "status"),
        Index(
            "uq_accounts_primary_customer",
            "customer_id",
            unique=True,
            postgresql_where=text(
                "is_primary = true "
                "AND customer_id IS NOT NULL "
                "AND status <> 'closed'"
            ),
        ),
    )


class Merchant(Base, IntegerPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "merchants"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    registration_number: Mapped[str | None] = mapped_column(String(100))
    settlement_account_id: Mapped[int] = mapped_column(
        ForeignKey("bank_accounts.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    category_code: Mapped[str | None] = mapped_column(String(10))
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    risk_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="normal",
    )
    merchant_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=EMPTY_JSON,
    )

    __table_args__ = (
        Index("ix_merchants_active_risk", "active", "risk_level"),
        Index(
            "uq_merchants_registration_number",
            "registration_number",
            unique=True,
            postgresql_where=NOT_DELETED,
        ),
    )


class MerchantQRCode(
    Base,
    IntegerPrimaryKeyMixin,
    TimestampMixin,
    SoftDeleteMixin,
):
    __tablename__ = "merchant_qr_codes"

    merchant_id: Mapped[int] = mapped_column(
        ForeignKey("merchants.id", ondelete="CASCADE"),
        nullable=False,
    )
    qr_reference: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
    )
    label: Mapped[str | None] = mapped_column(String(120))
    fixed_amount: Mapped[Decimal | None] = mapped_column(Numeric(19, 2))
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )

    __table_args__ = (
        CheckConstraint(
            "fixed_amount IS NULL OR fixed_amount > 0",
            name="ck_merchant_qr_amount_positive",
        ),
        Index(
            "ix_merchant_qr_merchant_active",
            "merchant_id",
            "active",
        ),
    )


class Payee(Base, IntegerPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "payees"

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_account_id: Mapped[int] = mapped_column(
        ForeignKey("bank_accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    nickname: Mapped[str] = mapped_column(String(120), nullable=False)
    check_status: Mapped[PayeeCheckStatus] = mapped_column(
        enum_type(PayeeCheckStatus, "payee_check_status"),
        nullable=False,
        server_default=PayeeCheckStatus.PENDING.value,
    )
    check_reasons: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=EMPTY_JSON_LIST,
    )
    checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    cooling_off_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    __table_args__ = (
        Index(
            "ix_payees_customer_created",
            "customer_id",
            "created_at",
        ),
        Index(
            "uq_payees_active_customer_target",
            "customer_id",
            "target_account_id",
            unique=True,
            postgresql_where=NOT_DELETED,
        ),
    )


class Transaction(Base, IntegerPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "transactions"

    reference: Mapped[str] = mapped_column(
        String(40),
        unique=True,
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    transaction_type: Mapped[TransactionType] = mapped_column(
        enum_type(TransactionType, "transaction_type"),
        nullable=False,
    )
    status: Mapped[TransactionStatus] = mapped_column(
        enum_type(TransactionStatus, "transaction_status"),
        nullable=False,
        server_default=TransactionStatus.PENDING.value,
    )
    channel: Mapped[Channel] = mapped_column(
        enum_type(Channel, "transaction_channel"),
        nullable=False,
    )
    initiated_by_customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"),
    )
    source_account_id: Mapped[int] = mapped_column(
        ForeignKey("bank_accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    destination_account_id: Mapped[int] = mapped_column(
        ForeignKey("bank_accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    payee_id: Mapped[int | None] = mapped_column(
        ForeignKey("payees.id", ondelete="SET NULL"),
    )
    merchant_id: Mapped[int | None] = mapped_column(
        ForeignKey("merchants.id", ondelete="SET NULL"),
    )
    reversal_of_transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="RESTRICT"),
        unique=True,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(19, 2),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        server_default="MYR",
    )
    description: Mapped[str | None] = mapped_column(String(500))
    customer_reference: Mapped[str | None] = mapped_column(String(140))
    transaction_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=EMPTY_JSON,
    )
    initiated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    held_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    failure_code: Mapped[str | None] = mapped_column(String(100))
    failure_message: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="ck_transactions_amount_positive",
        ),
        CheckConstraint(
            "currency = 'MYR'",
            name="ck_transactions_currency_myr",
        ),
        CheckConstraint(
            "source_account_id <> destination_account_id",
            name="ck_transactions_different_accounts",
        ),
        UniqueConstraint(
            "initiated_by_customer_id",
            "idempotency_key",
            name="uq_transactions_customer_idempotency",
        ),
        Index(
            "ix_transactions_source_time",
            "source_account_id",
            "initiated_at",
        ),
        Index(
            "ix_transactions_destination_time",
            "destination_account_id",
            "initiated_at",
        ),
        Index(
            "ix_transactions_status_time",
            "status",
            "initiated_at",
        ),
        Index(
            "ix_transactions_customer_time",
            "initiated_by_customer_id",
            "initiated_at",
        ),
    )


class LedgerEntry(Base, IntegerPrimaryKeyMixin):
    __tablename__ = "ledger_entries"

    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("bank_accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    direction: Mapped[LedgerDirection] = mapped_column(
        enum_type(LedgerDirection, "ledger_direction"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(19, 2),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        server_default="MYR",
    )
    sequence_number: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="ck_ledger_amount_positive",
        ),
        CheckConstraint(
            "currency = 'MYR'",
            name="ck_ledger_currency_myr",
        ),
        UniqueConstraint(
            "transaction_id",
            "sequence_number",
            name="uq_ledger_transaction_sequence",
        ),
        Index(
            "ix_ledger_account_time",
            "account_id",
            "created_at",
        ),
        Index("ix_ledger_transaction", "transaction_id"),
    )