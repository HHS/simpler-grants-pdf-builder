.PHONY: help build test lint format collectstatic migrate makemigrations showmigrations sqlflush_db join_chunks decrypt_data load_data reset_and_load

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
	@echo "  make join_chunks			Reassemble data file"
	@echo "  make decrypt_data    Decrypt data/all_data_clean.json.enc into data/all_data_clean.json"
	@echo "  make load_data       Load data/all_data_clean.json into the database"
	@echo "  make reset_and_load  Run everything we need to get new data"

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

join_chunks: 		# Join chunked data in /data directory
	cat data/enc_chunk_* > data/all_data_clean.json.enc

decrypt_data: 	# Decrypt all_data_clean.json.enc to all_data_clean.json using pbkdf2
	openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 \
		-in data/all_data_clean.json.enc \
		-out data/all_data_clean.json \
		-pass pass:$(DECRYPT_PASS)

load_data: 			# Load decrypted all_data_clean.json into the database
	cd $(WORKDIR) && $(MANAGE) loaddata ../data/all_data_clean.json

reset_and_load: # This is runs the 4 commands in a since call
	cat data/enc_chunk_* > data/all_data_clean.json.enc && \
	openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 \
		-in data/all_data_clean.json.enc \
		-out data/all_data_clean.json \
		-pass pass:$(DECRYPT_PASS) && \
	cd $(WORKDIR) && \
		$(MANAGE) migrate && \
		$(MANAGE) loaddata ../data/all_data_clean.json
