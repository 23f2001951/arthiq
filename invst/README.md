# invst

A personal investment decision-support tool for Indian equities (NSE/BSE, targeting the Nifty 500 universe) that replaces fragmented research workflows with disciplined, quantitative portfolio selection. On a quarterly rebalance cadence matching Indian earnings cycles, `invst` ingests historical prices, corporate filings, macroeconomic indicators, and sentiment feeds to evaluate stocks across multi-stage Quality, Valuation, Risk, and NLP overlays. It then constructs a risk-managed, capped portfolio (max 25% single-stock, max 40% sector) and generates evidence-backed, plain-English rationales in PDF/HTML reports and an interactive Streamlit dashboard. The tool enforces strict point-in-time data integrity to prevent lookahead bias and focuses strictly on decision support; trade execution remains entirely manual.

For full architectural details, methodology, and design choices, see [PROJECT_PLAN.md](../PROJECT_PLAN.md).

---

## Quickstart

### 1. Prerequisites

- Python 3.11 or higher
- SQLite 3.35+
- (Optional) `weasyprint` system dependencies (Pango/Cairo) for PDF report generation

### 2. Setup Virtual Environment

```bash
cd invst
python3 -m venv venv
source venv/bin/activate
```

Or simply run `make venv` which automatically creates `venv` and installs all dependencies.

### 3. Install Dependencies

Install the package in editable mode with development dependencies:

```bash
make install
```

Or using standard requirements files:

```bash
make install-reqs
```

### 4. Configure Environment

Copy the example environment configuration file and adjust settings as needed:

```bash
cp .env.example .env
```

### 5. Run Database Migrations

Initialise the SQLite database schema and seed data:

```bash
make migrate
```

### 6. Run Ingestion, Backtest & Reports

```bash
# Ingest market data, fundamentals, and macro indicators
make ingest

# Run walk-forward backtest across historical regimes
make backtest

# Generate quarterly investment recommendation reports (HTML + PDF)
make report

# Launch the interactive Streamlit dashboard
make run-app
```

---

## Project Structure

```
invst/
├── docker-compose.yml          # Container orchestration (Frontend + Backend)
├── Makefile                    # Root orchestration commands
├── README.md                   # Project documentation
│
├── frontend/                   # React 18 + Vite 6 + Tailwind SPA
│   ├── Dockerfile              # Multi-stage Nginx container
│   ├── nginx.conf              # SPA routing fallback & reverse-proxy config
│   ├── package.json
│   ├── vite.config.ts
│   └── src/                    # Components, views, API client
│
├── backend/                    # Python Quant Engine & FastAPI service
│   ├── Dockerfile              # Python 3.11-slim container
│   ├── Makefile                # Backend developer commands
│   ├── pyproject.toml          # Build metadata & dependencies
│   ├── requirements.txt        # Production dependencies
│   ├── requirements-dev.txt    # Dev & test tooling
│   ├── app/                    # Streamlit interactive UI (legacy)
│   ├── config/                 # settings.yaml, scoring_weights.yaml, sectors.yaml
│   ├── data/                   # Raw, interim, processed data storage (gitignored)
│   ├── db/                     # SQLite migrations, seed data & migrate.py
│   ├── docs/                   # Architecture, specs & decision logs
│   ├── notebooks/              # Jupyter research and EDA notebooks
│   ├── ops/                    # Operational runbooks and cron scripts
│   ├── src/invst/              # Reusable Python package (API, scoring, ML, optimization)
│   └── tests/                  # Automated pytest test suite
```

---

## Development & Testing

Common developer tasks are automated through `Makefile`:

- **Run tests:** `make test`
- **Lint code:** `make lint`
- **Format code:** `make format`
- **Clean caches:** `make clean`

---

## Architecture & Roadmap

For deep dives on quant stages, scoring metrics, data pipelines, ML classification, and phase-by-phase roadmaps, refer to:

- [PROJECT_PLAN.md](../PROJECT_PLAN.md)

---

## License

MIT License — Personal project.
