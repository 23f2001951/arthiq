.PHONY: help install install-reqs test lint format migrate ingest backtest report run-app clean

VENV ?= venv
PYTHON ?= $(VENV)/bin/python
PIP ?= $(VENV)/bin/pip

help:
	@echo "invst development commands (using $(VENV)):"
	@echo "  make venv          Create virtual environment and install all dependencies"
	@echo "  make install       Install package in editable mode with development dependencies"
	@echo "  make install-reqs  Install dependencies using requirements.txt and requirements-dev.txt"
	@echo "  make test          Run test suite with verbose output using $(PYTHON)"
	@echo "  make lint          Run ruff linter on src/ and tests/"
	@echo "  make format        Format code using ruff"
	@echo "  make migrate       Run database schema migrations"
	@echo "  make ingest        Run data ingestion CLI"
	@echo "  make backtest      Run backtesting engine CLI"
	@echo "  make report        Generate investment decision report CLI"
	@echo "  make serve         Start FastAPI + React web interface"
	@echo "  make run-app       Start Streamlit web interface"
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
	$(PYTHON) -m pytest tests/ -v

lint:
	$(VENV)/bin/ruff check src/ tests/

format:
	$(VENV)/bin/ruff format src/ tests/

migrate:
	$(PYTHON) db/migrate.py

ingest:
	$(PYTHON) -m invst.cli ingest

backtest:
	$(PYTHON) -m invst.cli backtest

report:
	$(PYTHON) -m invst.cli report

run-app:
	streamlit run app/streamlit_app.py

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

serve:
	$(PYTHON) -m invst.cli serve


clean:
	rm -rf __pycache__ .pytest_cache .ruff_cache build/ dist/ *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.py[cod]" -delete 2>/dev/null || true
