# ArthIQ (`arthiq`)

> **Personal Quantitative Investment Decision-Support Engine for Indian Equities (NSE/BSE)**

ArthIQ is an institutional-grade quantitative investment decision-support engine targeting the Nifty 500 universe. On a quarterly rebalance cadence matching Indian corporate earnings cycles, ArthIQ ingests historical prices, corporate filings, macroeconomic indicators, and sentiment feeds to evaluate stocks across multi-stage Quality, Valuation, Risk, and NLP overlays. It constructs risk-managed, capped portfolios and generates evidence-backed, plain-English rationales in PDF/HTML reports and interactive dashboards.

---

## Repository Structure

- [`PROJECT_PLAN.md`](./PROJECT_PLAN.md): Complete architecture specification, quant framework, data pipelines, schema design, and roadmap.
- [`invst/`](./invst/):
  - [`invst/frontend/`](./invst/frontend/): React 18 + Vite 6 + Tailwind CSS SPA, optimized with code-splitting and Nginx container.
  - [`invst/backend/`](./invst/backend/): Python 3.11+ institutional quantitative investment engine and FastAPI REST API.
    - [`invst/backend/src/invst/`](./invst/backend/src/invst/): Ingestion, scoring, optimization, backtesting, ML, reporting, and monitoring.
    - [`invst/backend/db/`](./invst/backend/db/): SQLite schema migrations and static seed data.
    - [`invst/backend/config/`](./invst/backend/config/): YAML settings, factor weights, and sector mappings.
    - [`invst/backend/tests/`](./invst/backend/tests/): Comprehensive pytest suite.
  - [`invst/docker-compose.yml`](./invst/docker-compose.yml): Production & local container orchestration.

---

## Quickstart

### 1. Setup Virtual Environment

```bash
cd invst
python3 -m venv venv
source venv/bin/activate
make install
```

### 2. Configure Environment & Database

```bash
cp .env.example .env
make migrate
```

### 3. Run Pipeline

```bash
# Ingest market data, fundamentals, and macro indicators
make ingest

# Run backtest
make backtest

# Launch Streamlit dashboard
make run-app
```

For full details, see [`invst/README.md`](./invst/README.md) and [`PROJECT_PLAN.md`](./PROJECT_PLAN.md).

---

## License

MIT License — Personal project.
