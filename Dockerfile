# CHANGED: add an alias so we can copy from this stage later
FROM python:3.14-slim AS builder

# set work directory
WORKDIR /app

# Install system dependencies (Debian-based)
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  build-essential \
  curl \
  wget \
  libffi-dev \
  libpq-dev \
  && rm -rf /var/lib/apt/lists/*

# Install Poetry and create user
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/usr/local python3 - && \
  useradd --create-home --shell /bin/bash appuser && \
  chown -R appuser:appuser /app

# Upgrade system pip and virtualenv
RUN python -m pip install --no-cache-dir --upgrade pip

# Make "db-migrate" a shell command in the container
RUN echo '#!/bin/sh\nmake migrate' > /usr/local/bin/db-migrate && \
  chmod +x /usr/local/bin/db-migrate

USER appuser

# Copy dependency files and install
COPY --chown=appuser:appuser pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.in-project true && \
  poetry install --no-root && \
  rm -rf ~/.cache/pypoetry/{cache,artifacts}

# Upgrade venv pip
RUN /app/.venv/bin/python -m pip install --no-cache-dir --upgrade pip

# Copy app and collect static files
COPY --chown=appuser:appuser . .
RUN poetry run python nofos/manage.py collectstatic --noinput --verbosity 0

# FINAL CLEANUP: Remove ALL pip 25.2 artifacts before copying to final stage
USER root
RUN find / -name "*pip-25.2*" -type f -delete 2>/dev/null || true && \
  find / -path "*/pip-25.2*.dist-info" -type d -exec rm -rf {} + 2>/dev/null || true && \
  echo "Final pip artifact scan:" && \
  find / -name "*pip-25.2*" 2>/dev/null || echo "No pip 25.2 artifacts found"

# =========================
# Stage 2 "scratch" final
# - Hides upstream apt-get layers for Dockle
# - Restores PATH so ECS can find db-migrate/venv
# =========================
FROM scratch

# copy the complete filesystem from builder
COPY --from=builder / /

# ensure venv & poetry shims are on PATH
ENV PATH="/app/.venv/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin"

# REDO: runtime env vars (they don't copy from the builder image config)
ARG IS_PROD_ARG=0
ARG GITHUB_SHA_ARG

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV IS_DOCKER=1
ENV IS_PROD=${IS_PROD_ARG}
ENV GITHUB_SHA=${GITHUB_SHA_ARG}

# restore working dir and user
WORKDIR /app
USER appuser

# final container port + command
EXPOSE ${PORT:-8000}
CMD ["sh", "-c", "poetry run gunicorn --workers 8 --timeout 89 --chdir nofos --bind 0.0.0.0:${PORT:-8000} bloom_nofos.wsgi:application"]
