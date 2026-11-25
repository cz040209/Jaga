# Jaga API (FastAPI). Built and started by `docker compose up`.
FROM python:3.12-slim

# uv: fast Python package manager (same version as on the dev laptop)
COPY --from=ghcr.io/astral-sh/uv:0.13.8 /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1

# Dependencies first: this layer is cached until pyproject.toml / uv.lock change.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Then the source code.
COPY . .

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8010

# Bring the database schema up to date, then start the API.
# --proxy-headers: trust X-Forwarded-For from the web container (the /api/bank
# proxy), so the API sees the customer's real IP, not the container's.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8010 --proxy-headers --forwarded-allow-ips='*'"]
