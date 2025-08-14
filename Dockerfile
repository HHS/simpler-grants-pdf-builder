# Stage 1: Build environment
FROM python:3.13-slim AS builder

WORKDIR /app

ARG IS_PROD_ARG=0
ARG GITHUB_SHA_ARG

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1s
ENV IS_DOCKER=1
ENV IS_PROD=${IS_PROD_ARG}
ENV GITHUB_SHA=${GITHUB_SHA_ARG}

# Install all dependencies (your existing steps)
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  build-essential \
  curl \
  wget \
  libffi-dev \
  libpq-dev && \
  rm -rf /var/lib/apt/lists/*

# Patch system libraries for CVEs
RUN apt-get update && \
  apt-get install -y --only-upgrade \
  libcap2 \
  login \
  passwd \
  libsystemd0 \
  libudev1 \
  libgnutls30 && \
  rm -rf /var/lib/apt/lists/*

# Install Poetry & appuser
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/usr/local python3 - && \
  useradd --create-home --shell /bin/bash appuser && \
  chown -R appuser:appuser /app

# Make "db-migrate" a shell command in the container
RUN echo '#!/bin/sh\nmake migrate' > /usr/local/bin/db-migrate && \
  chmod +x /usr/local/bin/db-migrate

USER appuser

# Install Python deps
COPY --chown=appuser:appuser pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.in-project true && \
  poetry install --no-root && \
  rm -rf ~/.cache/pypoetry/{cache,artifacts}

# Copy the full application
COPY --chown=appuser:appuser . .
RUN poetry run python nofos/manage.py collectstatic --noinput --verbosity 0

# Stage 2: New "clean" image with no upstream apt-get history
FROM scratch

# Copy everything
COPY --from=builder / /

# Restore environment from builder stage
ENV PATH="/app/.venv/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin"

WORKDIR /app
USER appuser

EXPOSE ${PORT:-8000}
CMD ["sh", "-c", "poetry run gunicorn --workers 8 --timeout 89 --chdir nofos --bind 0.0.0.0:${PORT:-8000} bloom_nofos.wsgi:application"]
