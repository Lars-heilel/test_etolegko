SHELL := /bin/bash

.PHONY: install dev dev-api dev-web db-up db-down migrate revision test test-api test-web lint lint-api lint-web fmt typecheck typecheck-api typecheck-web clean

install:
	cd apps/api && uv sync
	cd apps/web && pnpm install

dev:
	$(MAKE) -j2 dev-api dev-web

dev-api:
	cd apps/api && uv run fastapi dev app/main.py --port 8000

dev-web:
	cd apps/web && pnpm dev

db-up:
	docker compose -f infra/docker-compose.yml up -d db

db-down:
	docker compose -f infra/docker-compose.yml down

migrate:
	cd apps/api && uv run alembic upgrade head

revision:
	cd apps/api && uv run alembic revision --autogenerate -m "$(m)"

test: test-api test-web

test-api:
	cd apps/api && uv run pytest -q

test-web:
	cd apps/web && pnpm test

lint: lint-api lint-web

lint-api:
	cd apps/api && uv run ruff check .

lint-web:
	cd apps/web && pnpm lint && pnpm fsd:lint

fmt:
	cd apps/api && uv run ruff format .

typecheck: typecheck-api typecheck-web

typecheck-api:
	cd apps/api && uv run mypy app

typecheck-web:
	cd apps/web && pnpm typecheck

clean:
	rm -rf apps/web/dist apps/api/.pytest_cache apps/api/.mypy_cache apps/api/.ruff_cache
