.DEFAULT_GOAL := help
PYTHON_PACKAGES := api cli core db utils tests migrations
LOCAL_DB := postgresql+asyncpg://postgres:postgres@localhost:5432/micro_cache
SAMPLE := '{"list_1":["first string","second string","third string"],"list_2":["other string","another string","last string"]}'

.PHONY: help install lint format typecheck check test test-unit db migrate run cli up down

help: ## list targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-10s %s\n", $$1, $$2}'

install: ## install dependencies into .venv
	uv sync

lint: ## ruff check and format check
	uv run ruff check .
	uv run ruff format --check .

format: ## apply ruff fixes and formatting
	uv run ruff check --fix .
	uv run ruff format .

typecheck: ## mypy strict on every package
	uv run mypy $(PYTHON_PACKAGES)

check: lint typecheck test ## everything CI runs

test: ## full suite; starts a Postgres testcontainer unless TEST_DATABASE_URL is set
	uv run pytest -W error

test-unit: ## unit tests only, no database
	uv run pytest tests/unit -W error

db: ## start only Postgres from compose, published on localhost:5432
	docker compose up -d db

migrate: ## apply migrations to the database in .env
	uv run alembic upgrade head

run: ## API with reload against the database in .env (see `make db`)
	uv run uvicorn api.app:create_app --factory --reload --port 8000

cli: ## send the task sample three times to a running API
	uv run cache-cli -r 3 -j $(SAMPLE)

up: ## build and start the whole stack
	docker compose up --build

down: ## stop the stack and drop its volume
	docker compose down -v
