.PHONY: help up down logs restart test lint format typecheck seed package clean

help:
	@echo "Available commands:"
	@echo "  make up          - Start PostgreSQL container with logical decoding enabled"
	@echo "  make down        - Stop all Docker containers"
	@echo "  make logs        - Tail container logs"
	@echo "  make restart     - Restart Docker containers"
	@echo "  make test        - Run unit tests with pytest"
	@echo "  make lint        - Run ruff linter"
	@echo "  make typecheck   - Run mypy type checker"
	@echo "  make seed        - Run synthetic CDC stream producer (10 events)"
	@echo "  make package     - Package Lambda source code into dist/lambda.zip"
	@echo "  make clean       - Remove cache and build artifacts"

up:
	docker compose up -d postgres

down:
	docker compose down

logs:
	docker compose logs -f

restart:
	docker compose restart

test:
	python -m pytest tests -v

lint:
	python -m ruff check .

format:
	python -m ruff format .

typecheck:
	python -m mypy src

seed:
	python scripts/stream_producer.py --count 10 --rate 2.0

package:
	@mkdir -p dist
	@cd src && zip -r ../dist/lambda_transform.zip .
	@echo "Package created at dist/lambda_transform.zip"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf dist build .coverage
