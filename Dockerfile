FROM python:3.13-slim

# set work directory
WORKDIR /app

ARG IS_PROD_ARG=0
ARG GITHUB_SHA_ARG

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1s
ENV PORT=8000

ENV IS_DOCKER=1
ENV IS_PROD=${IS_PROD_ARG}
ENV GITHUB_SHA=${GITHUB_SHA_ARG}

# copy project
COPY . .

# Install system dependencies (Debian-based)
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  build-essential \
  curl \
  libffi-dev \
  libpq-dev \
  && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
  ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Copy dependency files first
COPY pyproject.toml poetry.lock ./

# Configure Poetry and install dependencies
RUN poetry config virtualenvs.in-project true && \
  poetry install --no-root --without dev && \
  rm -rf ~/.cache/pypoetry/{cache,artifacts}


# Copy the rest of the app
COPY . .

# Collect static files
RUN poetry run python bloom_nofos/manage.py collectstatic --noinput --verbosity 0


# Expose port and run server
EXPOSE $PORT
CMD ["sh", "-c", "poetry run gunicorn --workers 8 --timeout 89 --chdir bloom_nofos --bind 0.0.0.0:$PORT bloom_nofos.wsgi:application"]
