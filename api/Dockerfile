# Multi-stage Dockerfile for the FastAPI backend + ARQ workers.
# Same image is used for both services — the docker-compose `command:`
# field chooses which entrypoint to run.

FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

# uv is the fast pip replacement we use throughout the project
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /app

# Copy the shared library first (its hashes change less often than api/)
COPY shared/ /app/shared/

# Then api dependency manifest, install deps, finally copy source. This
# layering means a code change doesn't bust the dependency layer.
COPY api/pyproject.toml /app/api/pyproject.toml

WORKDIR /app/api
RUN uv sync --frozen --no-install-project 2>/dev/null || uv sync --no-install-project

# Source code (also volume-mounted in dev for hot reload)
COPY api/ /app/api/

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
