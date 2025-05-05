.PHONY: help test lint format migrate makemigrations

PYTHON=poetry run python
MANAGE=poetry run python manage.py
WORKDIR=bloom_nofos

help:
	@echo "Available commands:"
	@echo "  make test            Run all tests"
	@echo "  make lint            Run isort and black --check"
	@echo "  make format          Auto-format using isort and black"
	@echo "  make collectstatic   Run collectstatic"
	@echo "  make migrate         Run database migrations"
	@echo "  make makemigrations  Create new migrations"

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
