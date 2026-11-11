SHELL := /bin/sh
BACKEND := backend
DC := docker compose
VENV := $(BACKEND)/.venv

.DEFAULT_GOAL := help

.PHONY: help init up down logs ps migrate revision seed test test-unit test-integration \
        lint fmt typecheck check shell psql clean

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

init: ## Create .env from the example and install backend deps into a venv
	@test -f .env || cp .env.example .env
	python -m venv $(VENV)
	$(VENV)/bin/python -m pip install --upgrade pip
	$(VENV)/bin/python -m pip install -e "$(BACKEND)[dev]"

up: ## Build and start the local stack
	$(DC) up -d --build

down: ## Stop the stack and remove containers
	$(DC) down

logs: ## Follow logs of all services
	$(DC) logs -f --tail=100

ps: ## Show service status
	$(DC) ps

migrate: ## Apply all Alembic migrations
	cd $(BACKEND) && .venv/bin/alembic upgrade head

revision: ## Autogenerate a migration: make revision m="add something"
	cd $(BACKEND) && .venv/bin/alembic revision --autogenerate -m "$(m)"

seed: ## Upsert reference data (sources, technologies)
	cd $(BACKEND) && .venv/bin/python -m app.cli seed

test: ## Run the full test suite
	cd $(BACKEND) && .venv/bin/pytest

test-unit: ## Run unit tests only
	cd $(BACKEND) && .venv/bin/pytest tests/unit

test-integration: ## Run integration tests (needs postgres + redis)
	cd $(BACKEND) && .venv/bin/pytest -m integration

lint: ## Lint and format-check
	cd $(BACKEND) && .venv/bin/ruff check . && .venv/bin/ruff format --check .

fmt: ## Auto-fix lint issues and format
	cd $(BACKEND) && .venv/bin/ruff check --fix . && .venv/bin/ruff format .

typecheck: ## Run mypy
	cd $(BACKEND) && .venv/bin/mypy app

check: lint typecheck test ## Everything CI runs

shell: ## Open a shell inside the API container
	$(DC) exec api sh

psql: ## Open psql against the compose database
	$(DC) exec postgres psql -U $${POSTGRES_USER:-radar} -d $${POSTGRES_DB:-radar}

clean: ## Remove caches and local build artifacts
	rm -rf $(BACKEND)/.pytest_cache $(BACKEND)/.ruff_cache $(BACKEND)/.mypy_cache $(BACKEND)/htmlcov $(BACKEND)/.coverage
