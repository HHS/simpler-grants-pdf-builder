FROM python:3.10.13-alpine

# set work directory
WORKDIR /app

ARG IS_PROD_ARG=0

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1s
ENV PORT=8000

ENV IS_DOCKER=1
ENV IS_PROD=${IS_PROD_ARG}

# install linux dependencies 
RUN apk update && apk upgrade && \
  apk add gcc g++ musl-dev curl libffi-dev postgresql-dev

# install poetry to manage python dependencies
RUN curl -sSL https://install.python-poetry.org | python3 -

# install python dependencies
COPY ./pyproject.toml .
COPY ./poetry.lock .
RUN /root/.local/bin/poetry config virtualenvs.in-project true
RUN /root/.local/bin/poetry install

# copy project
COPY . .

EXPOSE $PORT

CMD /app/bloom_nofos/scripts/start_server.sh
