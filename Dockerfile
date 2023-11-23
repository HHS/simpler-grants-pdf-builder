FROM python:3.10.13-alpine

# set work directory
WORKDIR /app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1s
ENV DATABASE_URL="postgresql://host.docker.internal/bloom_nofos?root"
ENV PORT=8000

# install linux dependencies 
RUN apk update && apk upgrade && \
  apk add --no-cache gcc g++ musl-dev curl libffi-dev postgresql-dev

# install poetry to manage python dependencies
RUN curl -sSL https://install.python-poetry.org | python3 -

# install python dependencies
COPY ./pyproject.toml .
COPY ./poetry.lock .
RUN /root/.local/bin/poetry install

# copy project
COPY . .

EXPOSE $PORT
CMD /app/bloom_nofos/scripts/start_server.sh