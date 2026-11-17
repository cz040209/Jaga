from app.models.base import Base
from app.models import (  # noqa: F401  (registers tables on Base)
    arena,
    audit,
    banking,
    cases,
    fraud,
    identity,
    messaging,
    risk,
)

__all__ = ["Base"]
