FROM python:3.12-slim

# uv: fast Python package manager
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/

WORKDIR /app

# Install dependencies first (cached unless pyproject/uv.lock change)
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --no-install-project

# Then copy the source code
COPY . .

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

# app/main.py is not written yet; this starts working once it exists
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
