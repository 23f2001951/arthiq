# ArthIQ (`arthiq`)

> **Personal Quantitative Investment Decision-Support Engine for Indian Equities (NSE/BSE)**

ArthIQ is an institutional-grade quantitative investment decision-support engine targeting the Nifty 500 universe. On a quarterly rebalance cadence matching Indian corporate earnings cycles, ArthIQ ingests historical prices, corporate filings, macroeconomic indicators, and sentiment feeds to evaluate stocks across multi-stage Quality, Valuation, Risk, and NLP overlays. It constructs risk-managed, capped portfolios and generates evidence-backed, plain-English rationales in PDF/HTML reports and interactive dashboards.

---

## Repository Structure

- [`PROJECT_PLAN.md`](./PROJECT_PLAN.md): Complete architecture specification, quant framework, data pipelines, schema design, and roadmap.
- [`invst/`](./invst/): Core engine implementation:
  - [`invst/src/invst/`](./invst/src/invst/): Source package (ingestion, scoring, optimization, backtesting, ML, reporting, monitoring)
  - [`invst/app/`](./invst/app/): Streamlit interactive dashboard
  - [`invst/db/`](./invst/db/): SQLite schema migrations and static seed data
  - [`invst/config/`](./invst/config/): YAML settings, factor weights, sector mappings
  - [`invst/docs/`](./invst/docs/): Technical documentation and decision logs
  - [`invst/tests/`](./invst/tests/): Comprehensive pytest suite

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
