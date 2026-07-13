.RECIPEPREFIX := >

PYTHON := backend/.venv/bin/python
PIP := backend/.venv/bin/pip

.PHONY: install test test-cov lint format typecheck api infra-up infra-down

install:
> $(PIP) install -e 'backend[dev]'

test:
> cd backend && .venv/bin/python -m pytest

test-cov:
> cd backend && .venv/bin/python -m pytest \
    --cov=incrementality_api \
    --cov-report=term-missing

lint:
> cd backend && .venv/bin/python -m ruff check src tests

format:
> cd backend && .venv/bin/python -m ruff format src tests

typecheck:
> cd backend && .venv/bin/python -m mypy src

api:
> cd backend && .venv/bin/python -m uvicorn \
    incrementality_api.main:app \
    --reload \
    --port 8000

infra-up:
> docker compose up -d postgres redis

infra-down:
> docker compose down
