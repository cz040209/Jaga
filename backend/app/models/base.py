from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, DateTime, Enum as SQLALchemyEnum, Identity, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

def enum_type(enum_class: type[StrEnum], name: str) -> SQLALchemyEnum:
    return SQLALchemyEnum(
        enum_class,
        name=name,
        values_callable=lambda members: [member.value for member in members],
        validate_strings=True,
    )

class IntegerPrimaryKeyMixin:
    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(start=1, increment=1),
        primary_key=True,
    )

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


EMPTY_JSON = text("'{}'::jsonb")
EMPTY_JSON_LIST = text("'[]'::jsonb")