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
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore patterns
├── Makefile                  # Development automation commands
├── pyproject.toml            # Build metadata, dependencies & tool configs
├── requirements.txt          # Core dependencies
├── requirements-dev.txt      # Development & test tooling
├── README.md                 # Project documentation
│
├── app/                      # Streamlit interactive UI
│   ├── streamlit_app.py      # Main dashboard entrypoint
│   ├── pages/                # Multi-page views (Dashboard, Recommendations, Backtest, etc.)
│   └── components/           # Reusable UI widgets and chart helpers
│
├── config/                   # Configuration files
│   ├── settings.yaml         # System thresholds, paths, caps
│   ├── scoring_weights.yaml  # Factor scoring weights
│   └── sectors.yaml          # NSE sector mappings
│
├── data/                     # Local data storage (gitignored)
│   ├── raw/                  # Downloaded bhavcopies, filings, RSS dumps
│   ├── interim/              # Parsed intermediate datasets
│   └── processed/            # Feature matrices and cached tables
│
├── db/                       # Database layer
│   ├── invst.db              # Local SQLite database (gitignored)
│   ├── migrate.py            # Migration runner
│   ├── migrations/           # SQL migration scripts
│   └── seed/                 # Static data (Nifty 500 historical constituents, sectors)
│
├── docs/                     # Documentation and architecture diagrams
├── notebooks/                # Jupyter research and EDA notebooks
├── ops/                      # Operational runbooks and maintenance scripts
│
├── src/                      # Source package
│   └── invst/
│       ├── cli.py            # CLI entry point (`invst`)
│       ├── config.py         # Configuration loader
│       ├── data_access.py    # Point-in-time data access layer
│       ├── logging_utils.py  # Structured logging utilities
│       ├── ingestion/        # Bhavcopy, yfinance, filings, macro, and news scrapers
│       ├── scoring/          # Stage 0-4 screening, scoring, and composite ranking
│       ├── optimization/     # Mean-variance optimization with portfolio caps
│       ├── backtest/         # Walk-forward backtesting engine, execution & metrics
│       ├── ml/               # Sentiment models (FinBERT), classifiers & calibration
│       ├── reporting/        # Report generator & plain-English rationale builder
│       └── monitoring/       # Data quality, PIT audits, and divergence monitors
│
└── tests/                    # Automated test suite (pytest)
    ├── conftest.py           # Test fixtures and in-memory SQLite setup
    └── test_*.py             # Unit and integration tests
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
