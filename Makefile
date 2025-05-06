.PHONY: help build test lint format collectstatic migrate makemigrations

WORKDIR = bloom_nofos
USE_DOCKER ?= 0
IMAGE_NAME ?= bloom_nofos

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

build:
	docker build -t $(IMAGE_NAME) .

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
