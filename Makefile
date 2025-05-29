.PHONY: help build test lint format collectstatic migrate makemigrations showmigrations sqlflush_db

WORKDIR = nofos
USE_DOCKER ?= 0
IMAGE_NAME ?= nofos

# Check if git exists and get the hash, otherwise use 'latest'
GIT_EXISTS := $(shell which git 2>/dev/null)
ifdef GIT_EXISTS
    IMAGE_TAG := $(shell git rev-parse HEAD 2>/dev/null || echo "latest")
else
    IMAGE_TAG := latest
endif

ifeq ($(USE_DOCKER),1)
	PY_RUN_CMD = docker run --rm -w /app/$(WORKDIR) $(IMAGE_NAME) poetry run
else
	PY_RUN_CMD = poetry run
endif

MANAGE = $(PY_RUN_CMD) python manage.py

help:
	@echo "Available commands:"
	@echo "  make build           Build a docker image"
	@echo "  make test            Run all tests"
	@echo "  make lint            Run isort and black --check"
	@echo "  make format          Auto-format using isort and black"
	@echo "  make collectstatic   Run collectstatic"
	@echo "  make migrate         Run database migrations"
	@echo "  make makemigrations  Create new migrations"
	@echo "  make showmigrations  Check DB connection and show migrations"
	@echo "  make sqlflush_db     Generate SQL command to flush all data from the database"

build:
	docker build -t  $(IMAGE_NAME):latest .
	docker image tag $(IMAGE_NAME):latest $(IMAGE_NAME):$(IMAGE_TAG)
	@echo "Built image: $(IMAGE_NAME):$(IMAGE_TAG)"

test:
	cd $(WORKDIR) && $(MANAGE) test

lint:
	poetry run isort --check .
	poetry run black --check .

format:
	poetry run isort .
	poetry run black .

collectstatic:
	cd $(WORKDIR) && $(MANAGE) collectstatic --noinput

migrate:
	cd $(WORKDIR) && $(MANAGE) migrate

makemigrations:
	cd $(WORKDIR) && $(MANAGE) makemigrations

showmigrations:
	cd $(WORKDIR) && $(MANAGE) showmigrations

sqlflush_db:
	cd $(WORKDIR) && $(MANAGE) sqlflush
