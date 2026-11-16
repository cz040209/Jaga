# Jaga Backend

FastAPI service for the mock bank, the real-time fraud engine and AI features.

## Setup

```bash
cd backend
uv sync              # creates .venv and installs dependencies
uv run pytest        # run tests
uv run ruff check .  # lint
```

## Layout

| Folder | Purpose |
|---|---|
| `app/api/` | HTTP routes (kept thin) |
| `app/core/` | Config, security, database session |
| `app/models/` | SQLAlchemy database tables |
| `app/schemas/` | Pydantic request/response shapes |
| `app/ledger/` | Double-entry money movement |
| `tests/` | pytest unit tests |

More folders (`detectors/`, `decision/`, `bus/`, ...) are added in later phases.
