.PHONY: help install install-dev install-all test lint format clean run docker-build docker-run

help:
	@echo "DataOps Agent - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install production dependencies with uv"
	@echo "  make install-dev      Install with dev dependencies"
	@echo "  make install-all      Install all optional dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make test            Run tests with pytest"
	@echo "  make test-cov        Run tests with coverage report"
	@echo "  make lint            Run linting checks (ruff, mypy)"
	@echo "  make format          Format code (black, isort, ruff)"
	@echo "  make pre-commit      Install pre-commit hooks"
	@echo ""
	@echo "Running:"
	@echo "  make run             Run orchestrator locally"
	@echo "  make dev             Start LangGraph dev server"
	@echo "  make server          Start FastAPI server (future)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build    Build Docker image"
	@echo "  make docker-run      Run Docker container"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean           Remove build artifacts and cache"

install:
	uv pip install -e .

install-dev:
	uv pip install -e ".[dev]"

install-all:
	uv pip install -e ".[all]"

test:
	uv run pytest tests/ -v

test-cov:
	uv run pytest tests/ -v --cov=src --cov-report=html --cov-report=term

test-unit:
	uv run pytest tests/ -v -m unit

test-integration:
	uv run pytest tests/ -v -m integration

lint:
	uv run ruff check src/ tests/
	uv run mypy src/

format:
	uv run black src/ tests/
	uv run isort src/ tests/
	uv run ruff check --fix src/ tests/

pre-commit:
	uv run pre-commit install

run:
	uv run python main.py

dev:
	uv run langgraph dev

server:
	uv run uvicorn src.api.server:app --reload --host 0.0.0.0 --port 8000

docker-build:
	docker build -t dataops-agent:latest -f infrastructure/docker/Dockerfile .

docker-run:
	docker run -p 8000:8000 --env-file .env dataops-agent:latest

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# UV-specific commands
uv-sync:
	uv pip sync requirements.txt

uv-lock:
	uv pip compile pyproject.toml -o requirements.txt

uv-upgrade:
	uv pip compile --upgrade pyproject.toml -o requirements.txt
