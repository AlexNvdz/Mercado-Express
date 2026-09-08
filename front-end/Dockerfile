# MercadoExpress frontend (Django), managed with uv.
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Install dependencies first (better layer caching).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy the rest of the project and install it.
COPY . .
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# In production, DJANGO_ENV=production and collectstatic should already have
# been run as part of the image build/release step; kept here so the image
# is self-sufficient when built standalone.
RUN uv run manage.py collectstatic --noinput || true

# `migrate` targets Django's OWN tables only (sessions, admin, auth) -- see
# config/settings/base.py. It must run at container start, not build time:
# the sqlite file lives on a volume (see docker-compose.override.yml) that
# doesn't exist yet during `docker build`.
CMD ["sh", "-c", "uv run manage.py migrate --noinput && uv run gunicorn config.wsgi:application --bind 0.0.0.0:8000"]
