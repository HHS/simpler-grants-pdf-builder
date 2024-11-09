FROM python:3.11.9-alpine

# set work directory
WORKDIR /app

ARG IS_PROD_ARG=0

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1s
ENV PORT=8000

ENV IS_DOCKER=1
ENV IS_PROD=${IS_PROD_ARG}

ARG GITHUB_SHA_ARG
ENV GITHUB_SHA=${GITHUB_SHA_ARG}

# install linux dependencies
RUN apk update && apk upgrade && \
  apk add gcc g++ musl-dev curl libffi-dev postgresql-dev && \
  curl -sSL https://install.python-poetry.org | python3 -

# install python dependencies
COPY ./pyproject.toml .
COPY ./poetry.lock .
RUN /root/.local/bin/poetry config virtualenvs.in-project true && \
  /root/.local/bin/poetry install --without dev && \
  rm -rf ~/.cache/pypoetry/{cache,artifacts}

# copy project
COPY . .

# collect static files
RUN /root/.local/bin/poetry run python bloom_nofos/manage.py collectstatic --noinput

EXPOSE $PORT

# CMD /root/.local/bin/poetry run gunicorn --workers 8 --timeout 89 --chdir bloom_nofos --bind 0.0.0.0:$PORT bloom_nofos.wsgi:application

CMD ["sh", "-c", "/root/.local/bin/poetry run gunicorn --workers 8 --timeout 89 --chdir bloom_nofos --bind 0.0.0.0:$PORT bloom_nofos.wsgi:application"]
