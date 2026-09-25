.PHONY: help install install-reqs test lint format migrate ingest backtest report serve run-app clean

VENV ?= venv
PYTHON ?= $(VENV)/bin/python
PIP ?= $(VENV)/bin/pip

help:
	@echo "ArthIQ Backend commands (using $(VENV)):"
	@echo "  make venv          Create virtual environment and install all dependencies"
	@echo "  make install       Install package in editable mode with development dependencies"
	@echo "  make install-reqs  Install dependencies using requirements.txt and requirements-dev.txt"
	@echo "  make test          Run test suite using pytest"
	@echo "  make lint          Run ruff linter on src/ and tests/"
	@echo "  make format        Format code using ruff"
	@echo "  make migrate       Run database schema migrations"
	@echo "  make ingest        Run data ingestion CLI"
	@echo "  make backtest      Run backtesting engine CLI"
	@echo "  make report        Generate investment decision report CLI"
	@echo "  make serve         Start FastAPI application"
	@echo "  make clean         Clean build, cache, and test artifacts"

venv:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt -r requirements-dev.txt -e .

install:
	$(PIP) install -e '.[dev]'

install-reqs:
	$(PIP) install -r requirements.txt && $(PIP) install -r requirements-dev.txt

test:
	pytest tests/ -v

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

migrate:
	python3 db/migrate.py

ingest:
	python3 -m invst.cli ingest

backtest:
	python3 -m invst.cli backtest

report:
	python3 -m invst.cli report

serve:
	uvicorn invst.api.app:app --host 0.0.0.0 --port 8000 --reload

clean:
	rm -rf __pycache__ .pytest_cache .ruff_cache build/ dist/ *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.py[cod]" -delete 2>/dev/null || true
