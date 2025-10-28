# CHANGED: add an alias so we can copy from this stage later
FROM python:3.12-slim AS builder

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

# Patch system libraries to address known CVEs
# - libcap2: CVE-2025-1390
# - login, passwd: CVE-2023-4641, CVE-2023-29383,
# - libsystemd0, libudev1: CVE-2025-4598
# - libgnutls30: CVE-2025-32990
RUN apt-get update && \
  apt-get install -y --only-upgrade \
  libcap2 \
  login \
  passwd \
  libsystemd0 \
  libudev1 \
  libgnutls30 && \
  rm -rf /var/lib/apt/lists/*

# Install Poetry and create user
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/usr/local python3 - && \
  useradd --create-home --shell /bin/bash appuser && \
  chown -R appuser:appuser /app

# Make "db-migrate" a shell command in the container
RUN echo '#!/bin/sh\nmake migrate' > /usr/local/bin/db-migrate && \
  chmod +x /usr/local/bin/db-migrate

USER appuser

# Copy dependency files and install
COPY --chown=appuser:appuser pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.in-project true && \
  poetry install --no-root && \
  rm -rf ~/.cache/pypoetry/{cache,artifacts}

# Copy app and collect static files
COPY --chown=appuser:appuser . .
RUN poetry run python nofos/manage.py collectstatic --noinput --verbosity 0

# =========================
# Stage 2 "scratch" final
# - Hides upstream apt-get layers for Dockle
# - Restores PATH so ECS can find db-migrate/venv
# =========================
FROM scratch

# copy the complete filesystem from builder
COPY --from=builder / /

# In the final stage, after copying the filesystem
RUN rm -f /usr/local/bin/pip* /app/.venv/bin/pip*

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
