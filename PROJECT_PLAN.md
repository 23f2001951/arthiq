# PROJECT_PLAN.md

> **Project:** Personal Investment Decision-Support Tool — Indian Equities (NSE/BSE, Nifty 500 Universe)
> **Document type:** Consolidated architecture / planning document
> **Status:** Locked decisions + proposed design. No code has been merged yet.
> **Owner:** Single user (personal tool).

---

## Table of Contents

1. [Overview & Product Definition](#1-overview--product-definition)
2. [Quant Framework](#2-quant-framework)
3. [Data Architecture](#3-data-architecture)
4. [Database](#4-database)
5. [Backtesting Engine](#5-backtesting-engine)
6. [Backend](#6-backend)
7. [ML / NLP Layer](#7-ml--nlp-layer)
8. [Frontend](#8-frontend)
9. [Monitoring](#9-monitoring)
10. [Full Repository File Structure](#10-full-repository-file-structure)
11. [Roadmap / Next Steps](#11-roadmap--next-steps)

---

## 1. Overview & Product Definition

### 1.1 Purpose

A **personal** decision-support tool that helps the user decide *what* to buy, *when* to rebalance, and *why* — across the Indian listed-equity universe. The tool replaces the current manual workflow of:

- Opening Screener.in / Tickertape / Trendlyne in ten browser tabs.
- Reading annual reports (or skipping them).
- Guessing on sector concentration.
- Constructing a portfolio on a notepad.

The tool produces a **single, written, evidence-backed recommendation per stock**, in plain English, with the underlying numbers and model signals visible. The user then **manually** executes the trades in their broker app (Zerodha Kite / Groww / Upstox / etc.).

### 1.2 Non-Goals

- **No auto-trading.** No broker API writes. The tool never places, modifies, or cancels orders.
- **No "signal service".** This is not for resale or for other users. It is one user, one portfolio.
- **No tax optimisation, estate planning, or asset-allocation outside equities.**
- **No intraday, F&O, or crypto.** Universe is NSE/BSE listed equities only, cash segment.
- **No social / community features.**
- **No live P&L chasing.** Recommendations update on a fixed cadence (quarterly).

### 1.3 Locked Default Decisions

These are the baseline assumptions. Any deviation is a deliberate override and must be logged.

| # | Decision | Locked value | Rationale |
|---|----------|--------------|-----------|
| 1 | Rebalance cadence | **Quarterly** | Matches Indian earnings cycle (results every 90 days); reduces over-trading. |
| 2 | Benchmark | **Nifty 500 TRI** | Captures ~95% of NSE market cap; broader than Nifty 50. |
| 3 | Max single-stock weight | **25 %** | Prevents single-name blow-up risk. |
| 4 | Max sector weight | **40 %** | Diversification floor while allowing conviction tilts. |
| 5 | Starting data sources | **Free / open** | yfinance, NSE bhavcopy, BSE bhavcopy, RSS feeds. |
| 6 | Backtest window | **2016-01-01 → 2026-09-30** | 10 years + ~9 months; covers pre-COVID, COVID, post-COVID regimes. |
| 7 | Survivorship-bias treatment | **Point-in-time constituents only** | Use the index-constituent list as it existed on each historical rebalance date. |
| 8 | Primary deliverable | **Report (PDF + HTML)** | Plain-English reasoning per stock + numbers table. |
| 9 | Secondary deliverable | **Streamlit dashboard** | For drill-down and ad-hoc queries. |
| 10 | Universe | **Nifty 500** (with extension to Nifty 500 + Next 50 as data permits) | Defined, investable, well-known. |

### 1.4 High-Level Workflow

```
        ┌────────────────────────────────────────┐
        │  Ingest daily prices + quarterly       │
        │  fundamentals + news (see §3, §4)      │
        └─────────────────┬──────────────────────┘
                          ▼
        ┌────────────────────────────────────────┐
        │  Score universe on Quality /           │
        │  Valuation / Risk / Sentiment (see §2) │
        └─────────────────┬──────────────────────┘
                          ▼
        ┌────────────────────────────────────────┐
        │  Optimise portfolio w/ 25 % / 40 %     │
        │  caps → top-8 holdings (see §2.6)      │
        └─────────────────┬──────────────────────┘
                          ▼
        ┌────────────────────────────────────────┐
        │  Generate plain-English report         │
        │  (Streamlit + PDF export, see §8)      │
        └─────────────────┬──────────────────────┘
                          ▼
        User executes trades manually in broker app.
```

---

## 2. Quant Framework

The framework is **multi-stage**, **rule-then-model**, and **deterministic at each stage** so that backtests and live runs share the same code path.

### 2.1 Screening Filters (Stage 0 — Universe Reduction)

Pass criteria (must satisfy **all**):

| Filter | Rule | Why |
|--------|------|-----|
| Liquidity | 30-day median traded value ≥ ₹5 cr | Ensures we can actually enter/exit. |
| Market cap | ≥ ₹1,000 cr (point-in-time) | Filters micro-caps; reduces manipulation risk. |
| Listing tenure | ≥ 3 years on NSE/BSE | Some fundamentals series need 12 quarters. |
| Float | Promoter holding ≤ 75 % | Avoids illiquid, promoter-locked names. |
| Data integrity | Has ≥ 10 of last 12 quarters of fundamentals | No point scoring on imputed numbers. |
| Exclusions | No penny stock (price < ₹10), no suspended/delisted | Mechanical safety. |

Output of Stage 0: **investable universe** (typically ~350–470 names from Nifty 500).

### 2.2 Fundamentals & Quality Scoring (Stage 1)

Five-year averages where available, with recency-weighted blending.

| Metric | Weight (within Quality) | Direction |
|--------|--------------------------|-----------|
| ROE (5-yr avg) | 25 % | Higher better |
| ROCE (5-yr avg) | 25 % | Higher better |
| Debt / Equity | 15 % | Lower better (penalty above 1.0) |
| Interest coverage (EBIT / Interest) | 10 % | Higher better |
| Earnings growth (CAGR, 5 yr) | 15 % | Higher better |
| Operating cash-flow / Net profit | 10 % | ≥ 0.8 preferred (accruals check) |

Score is **z-scored within sector** then re-scaled to 0–100. Cross-sector comparability is preserved by the z-score normalisation.

### 2.3 Valuation Scoring (Stage 2)

| Metric | Weight | Treatment |
|--------|--------|-----------|
| P/E (TTM) | 30 % | z-score vs. 5-yr sector mean ± 1.5σ. |
| P/B | 20 % | Same. |
| EV/EBITDA | 30 % | Same; preferred for capital-heavy sectors. |
| Dividend yield | 10 % | Soft preference. |
| PEG (P/E ÷ 5-yr growth) | 10 % | Sanity floor. |

All inputs use **point-in-time fundamentals** with the **price as-of the rebalance date**. Cheap vs. expensive is measured against history, not today.

### 2.4 Risk Scoring (Stage 3)

| Metric | Source | Purpose |
|--------|--------|---------|
| Annualised vol (252 d) | Daily prices | Overall riskiness. |
| Beta vs. Nifty 500 (2 yr) | Daily prices | Market sensitivity. |
| Max drawdown (3 yr) | Daily prices | Tail-risk proxy. |
| 1-yr downside deviation | Daily prices | Asymmetric risk. |
| Altman's Z-score (where computable) | Fundamentals | Distress probability. |

Risk score is **subtractive** — high-risk names lose points. Volatility is *not* a virtue in this strategy.

### 2.5 Sentiment / Momentum Overlay (Stage 4)

This is an **additive** overlay, capped so it cannot override Stage 1–3.

| Signal | Source | Cap |
|--------|--------|-----|
| Price momentum (6-12-1) | Daily prices | ±5 points |
| News sentiment (FinBERT on last 90 d headlines) | News RSS + scraper | ±5 points |
| Insider buying / promoter holding trend | Public filings | ±3 points |

Total overlay cap: **±10 points** on top of the Stage 1–3 composite.

### 2.6 Ranking & Sector-Capped Shortlist

Funnel:

```
   Investable universe  (~350–470)
        │  Quality + Valuation + Risk composite
        ▼
   Top 50 by composite
        │  Apply sector cap (no sector > 35 % of Top-50 weight)
        ▼
   Top 15 by composite (post sector cap)
        │  Apply 25 % single-stock cap during optimisation
        ▼
   Final portfolio: Top 8 holdings
```

### 2.7 Probability / ML Overlay

A walk-forward trained **gradient-boosted classifier** predicts P(outperform Nifty 500 over next 12 months | features-at-rebalance). Probability is a **tie-breaker**, never a primary ranker.

Threshold: a name must clear **both** the composite-score threshold and P ≥ 0.55 to make the shortlist.

### 2.8 Portfolio Optimisation

Method: **mean-variance with constraints** (cvxpy or scipy.optimize).

```
maximise   wᵀ μ  −  λ · wᵀ Σ w
subject to  Σ wᵢ = 1
            0 ≤ wᵢ ≤ 0.25          # single-stock cap
            Σ_{i ∈ sector s} wᵢ ≤ 0.40   for each sector s
            wᵢ = 0  for any stock not in the Stage-4 shortlist
```

μ and Σ estimated from **rolling 3-year weekly returns** ending at the rebalance date. λ tuned on the in-sample portion of the walk-forward window.

---

## 3. Data Architecture

### 3.1 Data Sources — Honest Discussion

| Source | Use | Free? | ToS / Reality |
|--------|-----|-------|---------------|
| **yfinance** (Yahoo Finance) | Daily OHLCV, splits, basic fundamentals for many NSE/BSE tickers | ✅ | Unofficial wrapper; rate-limited; can break. Acceptable for personal use with retry/circuit-breaker logic. |
| **NSE Bhavcopy** (official) | End-of-day price/volume file, downloaded daily | ✅ | Free, official. Reliable. Use as ground truth for prices. |
| **BSE Bhavcopy** | Same, BSE-listed names | ✅ | Free, official. |
| **NSE Corporate Filings** (announcements, results PDF links) | Earnings, board meeting outcomes | ✅ | Public, no API. Requires scraping. |
| **BSE Corporate Filings** | Same, BSE-listed names | ✅ | Public, scraping. |
| **News RSS / Google News RSS** | Headlines for sentiment model | ✅ | Allowed for non-commercial use; respect robots.txt. |
| **Screener.in** | Rich fundamentals UI | ❌ (ToS) | **Do NOT scrape.** Explicitly forbids scraping in their ToS. Use only as a manual cross-check. |
| **Trendlyne / Tickertape** | Same | ❌ (ToS) | Same — manual cross-check only. |
| **Tijori API** (paid) | Clean fundamentals, point-in-time | ❌ | Recommended **future upgrade**. |
| **Trendlyne API** (paid) | Same | ❌ | Recommended **future upgrade**. |
| **Finnhub / Polygon.io** (paid) | Global fundamentals, news | ❌ | Recommended **future upgrade** for cross-listing stocks. |

**Decision (locked):** start with the **free tier**. Plan for an **upgrade path** to a paid fundamentals API once the rest of the pipeline is stable.

### 3.2 Ingestion Pipeline Design

```
   ┌──────────────┐  daily 02:30 IST   ┌─────────────────┐
   │ NSE Bhavcopy │ ──────────────────▶│                 │
   └──────────────┘                    │                 │
   ┌──────────────┐  daily 02:45 IST   │  Ingestion Job  │
   │ BSE Bhavcopy │ ──────────────────▶│  (idempotent)   │
   └──────────────┘                    │                 │
   ┌──────────────┐  weekly            │                 │
   │  yfinance    │ ──────────────────▶│  → SQLite store │
   └──────────────┘                    │                 │
   ┌──────────────┐  on result date    │                 │
   │ Filings scraper ────────────────▶│                 │
   └──────────────┘                    │                 │
   ┌──────────────┐  hourly (cap)      │                 │
   │ News RSS     │ ──────────────────▶│                 │
   └──────────────┘                    └─────────────────┘
```

All ingestion is **idempotent** (`INSERT OR REPLACE` keyed on `(symbol, date, source)`). Re-running a day is safe.

### 3.3 Point-in-Time Data Integrity — Critical

**Why this matters.** A backtest that uses today's fundamentals to decide trades in 2017 is **cheating**. The "true" 2017 fundamentals were what was *publicly known on or before the 2017 rebalance date*. Using today's restated numbers inflates apparent skill.

**How we enforce it.**

1. Every fundamentals row carries a `disclosed_at` timestamp (date the filing became public).
2. Every price row carries `trade_date`.
3. The backtester only ever asks: *"what was the most-recent disclosed value of metric X for stock Y as of date D?"* — using a query of the form:

   ```sql
   SELECT value
   FROM fundamentals_quarterly
   WHERE symbol = ? AND metric = ?
     AND disclosed_at <= ?        -- <<<<< the as-of date
   ORDER BY disclosed_at DESC, period_end DESC
   LIMIT 1;
   ```

4. Index constituent history (`index_constituents_history`) records the **exact set of Nifty 500 members on each historical rebalance date**. The backtester uses that set, not today's Nifty 500.
5. Any query path that bypasses `disclosed_at` is **banned by code review** (linted).

The `PointInTimeDataAccess` class (see §5.2) is the only blessed entry point.

---

## 4. Database

### 4.1 Engine Choice

| Option | Verdict |
|--------|---------|
| **SQLite** | ✅ **Default.** Zero setup, file-backed, single-user. Sufficient for ~500 stocks × 10 years × 4 quarters ≈ 20 k fundamentals rows + ~1.3 M daily-price rows. |
| PostgreSQL | Optional later upgrade when (a) we want multi-process concurrent writes, (b) we add a paid data vendor with a streaming feed, or (c) we deploy the Streamlit app to a remote VM. Schema below is portable. |
| DuckDB | Also viable for analytics-heavy backtest queries; consider as a read-only analytical mirror. |

### 4.2 Core Tables — Schemas (SQLite)

```sql
-- 1. Historical Nifty 500 constituent list (point-in-time)
CREATE TABLE index_constituents_history (
    effective_date   DATE    NOT NULL,        -- date this membership became true
    symbol           TEXT    NOT NULL,        -- e.g. "RELIANCE"
    isin             TEXT,
    sector           TEXT    NOT NULL,
    source           TEXT    NOT NULL,        -- "nse_index_rebalance"
    PRIMARY KEY (effective_date, symbol)
);
CREATE INDEX idx_ich_symbol ON index_constituents_history(symbol);
CREATE INDEX idx_ich_effdate ON index_constituents_history(effective_date);

-- 2. Daily OHLCV (point-in-time — by trade_date)
CREATE TABLE daily_prices (
    symbol           TEXT    NOT NULL,
    trade_date       DATE    NOT NULL,
    open             REAL,
    high             REAL,
    low              REAL,
    close            REAL    NOT NULL,
    adj_close        REAL,
    volume           INTEGER,
    source           TEXT    NOT NULL,        -- "nse_bhavcopy" | "bse_bhavcopy" | "yfinance"
    PRIMARY KEY (symbol, trade_date, source)
);
CREATE INDEX idx_dp_date ON daily_prices(trade_date);
CREATE INDEX idx_dp_symbol_date ON daily_prices(symbol, trade_date);

-- 3. Quarterly fundamentals (point-in-time — by disclosed_at)
CREATE TABLE fundamentals_quarterly (
    symbol           TEXT    NOT NULL,
    period_end       DATE    NOT NULL,        -- e.g. "2024-03-31"
    disclosed_at     DATE    NOT NULL,        -- <<<<< critical for point-in-time
    metric           TEXT    NOT NULL,        -- "revenue" | "net_profit" | "roe" | ...
    value            REAL,
    unit             TEXT,                    -- "INR_cr" | "pct" | "ratio"
    source           TEXT    NOT NULL,        -- "nse_filing" | "bse_filing" | "yfinance" | "paid_api"
    PRIMARY KEY (symbol, period_end, metric, source)
);
CREATE INDEX idx_fq_pit ON fundamentals_quarterly(symbol, metric, disclosed_at);

-- 4. News + sentiment
CREATE TABLE news_sentiment (
    headline_id      TEXT    PRIMARY KEY,     -- hash(url)
    symbol           TEXT,                    -- nullable: macro news
    published_at     DATE    NOT NULL,
    headline         TEXT    NOT NULL,
    source           TEXT,                    -- "moneycontrol" | "livemint" | ...
    sentiment_score  REAL,                    -- -1..+1
    model_version    TEXT,                    -- e.g. "finbert-v1"
    ingested_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_news_symbol_date ON news_sentiment(symbol, published_at);

-- 5. Model predictions (walk-forward, point-in-time)
CREATE TABLE model_predictions (
    asof_date        DATE    NOT NULL,
    symbol           TEXT    NOT NULL,
    model_name       TEXT    NOT NULL,        -- "outperform_clf_v3"
    p_outperform     REAL,                    -- probability 0..1
    rank_in_universe INTEGER,
    features_json    TEXT,                    -- snapshot of features used
    PRIMARY KEY (asof_date, symbol, model_name)
);

-- 6. Portfolio history (the user's actual + paper portfolios)
CREATE TABLE portfolio_history (
    run_id           TEXT    NOT NULL,        -- UUID
    asof_date        DATE    NOT NULL,
    symbol           TEXT    NOT NULL,
    target_weight    REAL    NOT NULL,
    action           TEXT    NOT NULL,        -- "BUY" | "SELL" | "HOLD"
    shares_target    INTEGER,
    rationale_text   TEXT,                    -- plain-English explanation
    executed         INTEGER DEFAULT 0,       -- 1 = user confirmed manual execution
    PRIMARY KEY (run_id, symbol)
);

-- 7. Backtest runs
CREATE TABLE backtest_runs (
    run_id           TEXT    PRIMARY KEY,
    started_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at      TIMESTAMP,
    start_date       DATE    NOT NULL,
    end_date         DATE    NOT NULL,
    config_json      TEXT    NOT NULL,        -- frozen config for reproducibility
    cagr             REAL,
    sharpe           REAL,
    max_drawdown     REAL,
    turnover_avg     REAL,
    benchmark_cagr   REAL,
    status           TEXT                     -- "running" | "completed" | "failed"
);
```

### 4.3 Migrations

Use plain SQL files in `db/migrations/` named `0001_init.sql`, `0002_add_macro_features.sql`, ... Applied by a tiny `migrate.py` script that tracks applied versions in a `schema_version` table.

---

## 5. Backtesting Engine

### 5.1 Walk-Forward Quarterly Simulation

```
for rebalance_date in quarterly_dates(2016-03-31 .. 2026-06-30):
    ┌─────────────────────────────────────────────────────────┐
    │  1. universe = index_constituents_history at rebalance  │
    │  2. features = PointInTimeDataAccess(asof=rebalance)     │
    │  3. score each name  → composite + sentiment + prob     │
    │  4. optimise → target weights (8 names, caps respected) │
    │  5. trade at next day's open (no look-ahead)            │
    │  6. record portfolio_history row                        │
    │  7. mark-to-market daily until next rebalance           │
    └─────────────────────────────────────────────────────────┘
compute_metrics(equity_curve, benchmark_curve) → §5.3
```

A **walk-forward** split — never a single in-sample/out-sample split — is mandatory. Each rebalance only sees data that was public on or before that date.

### 5.2 PointInTimeDataAccess (anti-lookahead safeguard)

```python
# src/data_access.py
from datetime import date
from typing import Optional
import sqlite3

class PointInTimeDataAccess:
    """
    The ONLY blessed way to read fundamentals, prices, and constituents
    from the database for backtesting. Any code that reads the DB without
    going through this class is a code-review red flag.
    """

    def __init__(self, conn: sqlite3.Connection, asof: date):
        self.conn = conn
        self.asof = asof  # the simulated "today"

    # ---------- prices ----------
    def get_price(self, symbol: str, on_or_before: date) -> Optional[float]:
        row = self.conn.execute(
            """
            SELECT close FROM daily_prices
            WHERE symbol = ? AND trade_date <= ?
            ORDER BY trade_date DESC LIMIT 1
            """,
            (symbol, on_or_before),
        ).fetchone()
        return row[0] if row else None

    def get_price_series(self, symbol: str, start: date, end: date):
        return self.conn.execute(
            """
            SELECT trade_date, close, adj_close, volume
            FROM daily_prices
            WHERE symbol = ? AND trade_date BETWEEN ? AND ?
            ORDER BY trade_date
            """,
            (symbol, start, end),
        ).fetchall()

    # ---------- fundamentals (point-in-time!) ----------
    def get_fundamental(self, symbol: str, metric: str) -> Optional[float]:
        row = self.conn.execute(
            """
            SELECT value FROM fundamentals_quarterly
            WHERE symbol = ? AND metric = ?
              AND disclosed_at <= ?            -- <<<<<< critical
            ORDER BY disclosed_at DESC, period_end DESC
            LIMIT 1
            """,
            (symbol, metric, self.asof.isoformat()),
        ).fetchone()
        return row[0] if row else None

    def get_fundamentals_panel(self, metric: str, symbols: list[str]):
        # vectorised form for ranking
        placeholders = ",".join("?" * len(symbols))
        return self.conn.execute(
            f"""
            SELECT f.symbol, f.value
            FROM fundamentals_quarterly f
            JOIN (
                SELECT symbol, MAX(disclosed_at) AS max_disc
                FROM fundamentals_quarterly
                WHERE metric = ? AND disclosed_at <= ?
                  AND symbol IN ({placeholders})
                GROUP BY symbol
            ) latest
              ON f.symbol = latest.symbol
             AND f.disclosed_at = latest.max_disc
            WHERE f.metric = ?
            """,
            [metric, self.asof.isoformat(), *symbols, metric],
        ).fetchall()

    # ---------- universe ----------
    def get_universe(self) -> list[str]:
        rows = self.conn.execute(
            """
            SELECT symbol FROM index_constituents_history
            WHERE effective_date <= ?
              AND symbol NOT IN (
                  SELECT symbol FROM index_constituents_history
                  WHERE effective_date <= ?
                  GROUP BY symbol
                  HAVING MAX(effective_date) <= ?  -- crude "no longer a member" filter
              )
            """,
            (self.asof.isoformat(), self.asof.isoformat(), self.asof.isoformat()),
        ).fetchall()
        return [r[0] for r in rows]
```

### 5.3 Metrics Computed

| Metric | Formula / Source | Notes |
|--------|------------------|-------|
| **CAGR** | `(end/start)^(1/years) - 1` | Geometric. |
| **Sharpe** | `mean(excess_return) / std * sqrt(252)` | Excess vs. 91-day T-Bill (FRED or RBI 364-day T-Bill). |
| **Max drawdown** | `min((equity - running_max) / running_max)` | |
| **Sortino** | Like Sharpe but downside std only | |
| **Calmar** | `CAGR / abs(max_drawdown)` | |
| **Turnover (avg)** | `0.5 * Σ|w_new − w_old|` per rebalance | Annualised. |
| **Transaction cost** | `turnover * (bps + slippage)` | Default 30 bps buy + 20 bps sell. |
| **Benchmark comparison** | Same metrics on Nifty 500 TRI | Side-by-side in report. |
| **Hit rate** | `% of months portfolio > benchmark` | |
| **Worst 5-day rolling return** | tail risk | |
| **# of rebalances** | | Sanity check (should be ~40 over 10 yrs). |

### 5.4 Anti-Cheating Safeguards

| # | Safeguard | Implementation |
|---|-----------|----------------|
| 1 | No future data | `PointInTimeDataAccess` is the only entry point (lint-enforced). |
| 2 | Point-in-time constituents | `index_constituents_history` table queried by `asof`. |
| 3 | Universe integrity | Backtest refuses to start if any name's price series is missing > 5 % of expected trading days in the window. |
| 4 | Trade execution realism | Next-day-open fill (never same-day close). |
| 5 | Cost realism | Hard-coded 30 / 20 bps + configurable slippage. |
| 6 | Config freeze | `backtest_runs.config_json` is a literal copy of the config used; same config must reproduce same numbers (regression test). |
| 7 | Walk-forward only | No single in-sample fit. |
| 8 | Survivorship awareness | Delisted stocks are kept in universe until they actually leave the index — they are not retroactively removed. |

---

## 6. Backend

### 6.1 Architecture

A **Python service + CLI**. No web server. The Streamlit app (§8) is the only UI; the backend exposes Python functions and CLI subcommands.

### 6.2 Modules

| Module | Responsibility |
|--------|----------------|
| `ingestion/` | Pull from NSE/BSE/yfinance/news into SQLite. |
| `data_access.py` | `PointInTimeDataAccess` + thin SQL helpers. |
| `scoring/` | Quality / valuation / risk / sentiment / composite. |
| `optimization/` | Mean-variance optimiser with caps. |
| `backtest/` | Walk-forward engine + metrics. |
| `ml/` | Sentiment model + outperformance classifier (training & inference). |
| `reporting/` | PDF / HTML report builder + plain-English rationale. |
| `monitoring/` | Data-quality + calibration + PIT audits. |
| `cli.py` | Argparse CLI tying it all together. |

### 6.3 CLI Subcommands

```
invst ingest          # daily: refresh prices + news
invst ingest --full   # backfill fundamentals from scratch
invst score           # compute composite for current asof
invst optimize        # produce target portfolio + rationale
invst backtest        # run walk-forward backtest 2016→2026
invst report          # render PDF/HTML for latest run
invst monitor         # daily DQ + drift checks
```

### 6.4 Scheduling

| Job | When | Trigger |
|-----|------|---------|
| Daily price ingestion | Mon–Fri 03:30 IST | cron |
| News ingestion | Mon–Fri 09:00, 13:00, 17:00 IST | cron |
| Fundamentals refresh | On result-day triggers (manual / RSS watcher) | event-driven + manual |
| Quarterly score + optimise | Day after Nifty 500 rebalance + after Q4/Q1 results season | manual trigger + cron fallback |
| Quarterly report | Same | manual trigger |
| Quarterly ML retrain | Same | manual trigger |
| Backtest (full) | On-demand + after any major change to scoring | manual |

---

## 7. ML / NLP Layer

### 7.1 News Sentiment Model

- **Model:** FinBERT (ProsusAI / `yiyanghkust/finbert-tone` on HuggingFace) fine-tuned on Indian financial headlines (optional, only if a labelled dataset is built).
- **Input:** last 90 days of headlines per symbol, deduped by cosine > 0.95.
- **Output:** per-symbol sentiment score in `[-1, +1]`, plus a 90-day rolling mean and a recency-weighted mean.
- **Caveats:**
  - Headlines ≠ fundamentals. Treat as a **soft overlay**, capped (see §2.5).
  - Macro / RBI / global headlines are scored once and applied to all symbols.
- **Fallback:** if FinBERT load fails, use a VADER baseline so the pipeline still runs.

### 7.2 Outperformance Probability Model & Institutional Learnings (V0.3.1 Update)

- **Type:** Binary classifier targeting outperformance over forward 90 days ($y = I(R_{stock,90D} - R_{NIFTY500,90D} > 0)$).
- **Algorithm:** Gradient-boosted trees / Logistic regression baseline with Platt scaling.
- **Empirical V0.3.1 Finding:** Standalone ML probability yielded negative Rank IC (-0.0909) and compressed probabilities around 0.50 (Median 0.494, IQR 0.027). While Platt scaling improved Brier score (0.2761 → 0.2589), ROC-AUC remained < 0.50 (0.4374). Crucially, the ML blend underperformed the deterministic baseline in the untouched 2024–2026 test (-1.27% vs -0.02%).
- **Architectural Anchor:** **The deterministic Arth IQ engine remains the production research baseline.** The ML layer is strictly a research candidate and conviction/tilt modifier. ML never gates or decides stock selection independently.
- **V0.4 Decision Architecture:** Transition from hard $P \ge 0.55$ thresholds to a transparent **Normalized Additive Decision Framework**:
  $$\text{ArthScore}_i = w_F F_i + w_M M_i + w_E E_i + w_R R_i + w_H H_i$$
  with cross-pillar signal agreement between fundamentals and ML conviction.

### 7.3 Retraining & Model Promotion Criteria

| Activity | Cadence | Trigger |
|----------|---------|---------|
| Retrain classifier | Quarterly | After rebalance |
| Calibration check (reliability plot, Brier score, ECE) | Quarterly | After retrain |
| Discrimination check (Rank IC, Rank IC IR, ROC-AUC) | Quarterly | After retrain |
| Feature drift check (PSI per feature) | Quarterly | After retrain |
| Zero-Lookahead PIT Audit | Quarterly | Hard invariant (100% pass required) |
| Multi-Horizon & Cross-Sectional Quintile Spread ($Q5 - Q1$) | Quarterly | After retrain |

> [!IMPORTANT]
> **The 8 Model Promotion Gates:** A model is never promoted on Brier score alone. It must satisfy:
> 1. Zero PIT lookahead violations (100% pass)
> 2. Positive Spearman Rank IC (> 0.00) and IC IR (> 0.00)
> 3. Monotonic cross-sectional quintiles ($Q5 > Q1$)
> 4. Multi-epoch temporal stability
> 5. Out-of-sample alpha on a frozen untouched test partition (2024–2026 is permanently frozen)
> 6. Economic explainability
> 7. Cost resilience (brokerage, slippage, turnover)
> 8. Net portfolio improvement vs deterministic baseline.

### 7.4 Institutional Model Registry Status
- **Deterministic Baseline (V0.2.1):** `BASELINE` — Core anchor (4.60% CAGR, -38.49% MDD)
- **Full 24-Feature ML:** `REJECTED` — Systematically inverted (Rank IC -0.0909, L/S -7.28%, $Q1 > Q5$)
- **Platt + 50/50 + $\gamma=0.50$:** `REJECTED` — Underperformed baseline (4.25% CAGR, 2024–2026 delta -0.53%)
- **Reverse Signal ($1 - P$):** `RESEARCH` — Diagnostic candidate (Rank IC +0.0909, L/S +7.76%)
- **Fundamentals-Only (Set A):** `CANDIDATE` — Early positive signal (Rank IC +0.0179, 60% Pos IC, +4.99% L/S)

---

## 8. Frontend

### 8.1 Technology

**Streamlit** (Python-native, zero JS, single-user). Considered alternatives: Dash, Reflex. Streamlit wins on speed-to-first-screen.

### 8.2 Pages

| Page | Purpose | Key widgets |
|------|---------|-------------|
| **Dashboard** | At-a-glance: last run, current portfolio, vs. benchmark, next scheduled action | KPI tiles, sparklines, "Last run: YYYY-MM-DD HH:MM" |
| **Recommendations / Report** | The output of the latest quarterly run | Per-stock card with: target weight, action (BUY/SELL/HOLD), numbers table, plain-English rationale, link to source filings |
| **Backtest Results** | The 10-yr walk-forward output | Equity curve vs. benchmark, drawdown chart, metric table, per-rebalance log |
| **Portfolio History** | Past actual + paper runs | Table of all `portfolio_history` rows, filterable by date / symbol / action |
| **System Health** | Data freshness, model calibration, DQ alerts | Status badges, last-ingestion timestamp, model Brier score over time |

### 8.3 Report Output

Generated by `reporting/report.py`.

- **HTML version:** the live Streamlit page.
- **PDF version:** rendered via WeasyPrint or `pdfkit` (HTML → PDF). Same content, print-friendly.

#### Report structure (per stock)

```
┌──────────────────────────────────────────────────────────────┐
│  RELIANCE INDUSTRIES (RELIANCE) — Energy                     │
│  Composite score: 78 / 100  |  P(outperform): 0.61           │
│  Action: BUY  |  Target weight: 18 %  (from 12 %)            │
├──────────────────────────────────────────────────────────────┤
│  Why we like it (plain English):                              │
│  "Reliance's retail segment has now contributed > 35 % of    │
│   EBITDA, and the latest quarter showed operating leverage    │
│   flowing through to ROCE (16.2 % vs. 14.1 % a year ago).     │
│   Valuation is no longer stretched: P/E is 1.1σ below its     │
│   5-year sector average. Momentum is positive but not          │
│   euphoric — 6-12-1 momentum of +14 %. Sentiment from         │
│   financial press is mildly positive."                        │
├──────────────────────────────────────────────────────────────┤
│  Numbers:                                                     │
│  ROE 5-yr: 13.4 % | ROCE 5-yr: 15.1 % | D/E: 0.42           │
│  P/E TTM: 22.1 (sector avg 25.4) | EV/EBITDA: 11.8           │
│  Beta: 0.91 | Vol 1-yr: 28 % | Max DD 3-yr: -24 %            │
│  Sentiment (90 d): +0.18 | Momentum (6-12-1): +14 %          │
└──────────────────────────────────────────────────────────────┘
```

---

## 9. Monitoring

### 9.1 Data Quality Checks (Daily)

| Check | Pass criterion | Alert |
|-------|----------------|-------|
| NSE bhavcopy downloaded for today | file exists, row count > 1500 | Slack/email |
| All universe symbols have today's close | row count = universe size | page on dashboard |
| No duplicate `(symbol, trade_date)` | unique | fail loud |
| News ingestion freshness | last headline < 6 h | warn |
| Fundamentals freshness | last disclosed_at within 90 d for ≥ 80 % of universe | warn |
| Index constituents integrity | current constituents row count within ±20 of expected | warn |

### 9.2 Model Calibration (Quarterly)

| Check | Method | Action if fail |
|-------|--------|----------------|
| Brier score | rolling 4-quarter mean | compare to baseline; alert if +10 % worse |
| Reliability plot | 10-bin calibration | alert if any bin > 10 % off diagonal |
| PSI per feature | Population Stability Index | alert if any feature PSI > 0.2 |
| Out-of-sample AUC | vs. incumbent | promote only if better |

### 9.3 Point-in-Time Integrity Audit (Weekly)

A small script queries the DB and asserts:

- No `fundamentals_quarterly.disclosed_at` is in the future.
- No `disclosed_at` is more than 14 days before `period_end` (results rarely pre-announce by more).
- Every backtest run's `config_json` round-trips to an identical metric set on re-run.

### 9.4 Live vs Backtest Divergence

- Rolling 4-quarter live Sharpe vs. backtested rolling Sharpe.
- Alert if live underperforms by > 1σ for 2 consecutive quarters → trigger a strategy review.

### 9.5 Operational Cadence

| Activity | Cadence | Owner |
|----------|---------|-------|
| Daily price + news ingestion | Daily 03:30 + 09:00/13:00/17:00 IST | cron |
| Data-quality report | Daily 04:00 IST | cron |
| Fundamentals refresh (post-results) | Event-driven | manual / RSS watcher |
| Score + optimise + report | Quarterly (rebalance + 1 day) | manual + cron fallback |
| ML retrain + calibration | Quarterly (post-rebalance) | manual |
| Full backtest (regression) | On any scoring change | manual |
| PIT integrity audit | Weekly Sunday 02:00 IST | cron |
| Live vs. backtest divergence review | Quarterly | manual |

---

## 10. Full Repository File Structure

```
invst/
├── README.md
├── LICENSE
├── pyproject.toml                # project metadata
├── requirements.txt              # pinned versions
├── requirements-dev.txt          # test/lint tooling
├── .env.example                  # env-var template (no secrets)
├── .gitignore
├── .gitkeep                      # placeholder; replaced per folder
├── Makefile                      # common dev commands
│
├── config/
│   ├── settings.yaml             # paths, thresholds, caps
│   ├── scoring_weights.yaml      # §2 weights live here
│   ├── sectors.yaml              # NSE sector mapping
│   └── README.md
│
├── db/
│   ├── README.md
│   ├── invst.db                  # SQLite file (gitignored)
│   ├── migrations/
│   │   ├── 0001_init.sql
│   │   ├── 0002_add_macro_features.sql
│   │   └── 0003_add_sentiment.sql
│   ├── seed/
│   │   ├── nifty500_constituents_history.csv
│   │   └── sectors_map.csv
│   └── migrate.py                # tiny migration runner
│
├── data/
│   ├── raw/                      # .gitignored; downloaded bhavcopies, etc.
│   │   └── .gitkeep
│   ├── interim/                  # .gitignored; parsed intermediate files
│   │   └── .gitkeep
│   └── processed/                # .gitignored; cached features
│       └── .gitkeep
│
├── notebooks/
│   ├── 01_eda_universe.ipynb
│   ├── 02_scoring_calibration.ipynb
│   ├── 03_backtest_diagnostics.ipynb
│   └── 04_sentiment_model_eval.ipynb
│
├── src/
│   └── invst/
│       ├── __init__.py
│       ├── cli.py                # argparse entry point
│       ├── config.py             # YAML loader
│       ├── logging_utils.py
│       ├── data_access.py        # PointInTimeDataAccess
│       │
│       ├── ingestion/
│       │   ├── __init__.py
│       │   ├── nse_bhavcopy.py
│       │   ├── bse_bhavcopy.py
│       │   ├── yfinance_prices.py
│       │   ├── fundamentals_filings.py
│       │   ├── news_rss.py
│       │   └── macro.py          # RBI, G-Sec, oil, INR, VIX
│       │
│       ├── scoring/
│       │   ├── __init__.py
│       │   ├── filters.py        # Stage 0
│       │   ├── quality.py        # Stage 1
│       │   ├── valuation.py      # Stage 2
│       │   ├── risk.py           # Stage 3
│       │   ├── sentiment_overlay.py
│       │   └── composite.py      # combines Stages 0–4
│       │
│       ├── optimization/
│       │   ├── __init__.py
│       │   └── mean_variance.py  # cvxpy / scipy, with caps
│       │
│       ├── backtest/
│       │   ├── __init__.py
│       │   ├── engine.py         # walk-forward loop
│       │   ├── execution.py      # next-day-open fill, costs
│       │   └── metrics.py        # CAGR / Sharpe / DD / turnover
│       │
│       ├── ml/
│       │   ├── __init__.py
│       │   ├── sentiment.py      # FinBERT wrapper
│       │   ├── classifier.py     # outperformance classifier
│       │   ├── train.py          # walk-forward training
│       │   ├── calibrate.py      # reliability + Brier
│       │   └── features.py       # feature builder
│       │
│       ├── reporting/
│       │   ├── __init__.py
│       │   ├── report.py         # builds HTML + PDF
│       │   ├── rationale.py      # plain-English text generator
│       │   └── templates/
│       │       ├── report.html.j2
│       │       └── styles.css
│       │
│       └── monitoring/
│           ├── __init__.py
│           ├── data_quality.py
│           ├── pit_audit.py
│           ├── calibration.py
│           └── divergence.py
│
├── app/
│   ├── streamlit_app.py          # entry point: `streamlit run`
│   ├── pages/
│   │   ├── 1_Dashboard.py
│   │   ├── 2_Recommendations.py
│   │   ├── 3_Backtest_Results.py
│   │   ├── 4_Portfolio_History.py
│   │   └── 5_System_Health.py
│   └── components/
│       ├── stock_card.py
│       ├── kpi_tile.py
│       └── chart_helpers.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # fixtures: tmp SQLite, sample DB
│   ├── test_data_access_pit.py   # <<<< critical
│   ├── test_filters.py
│   ├── test_quality.py
│   ├── test_valuation.py
│   ├── test_risk.py
│   ├── test_optimization_caps.py
│   ├── test_backtest_engine.py
│   ├── test_metrics.py
│   ├── test_classifier_train.py
│   ├── test_sentiment.py
│   ├── test_reporting.py
│   └── test_monitoring.py
│
├── scripts/
│   ├── backfill_all.py
│   ├── run_quarterly.py
│   ├── regression_backtest.py
│   └── seed_constituents.py
│
├── docs/
│   ├── architecture.md
│   ├── data_sources.md
│   ├── point_in_time.md
│   ├── backtest_methodology.md
│   └── decision_log.md
│
└── ops/
    ├── cron.daily.example
    ├── cron.weekly.example
    └── runbooks/
        ├── missing_bhavcopy.md
        ├── model_calibration_drift.md
        └── db_corruption_recovery.md
```

---

## 11. Roadmap & Milestone Progression

### 11.1 Completed Milestones
1. **V0.1 Foundation:** Database schema (`0001_init.sql`), NSE/BSE bhavcopy & yfinance ingestion, multi-factor scoring (Quality, Valuation, Risk, Sentiment), HRP optimizer with 25% stock / 40% sector caps, and Streamlit frontend.
2. **V0.2.1 Institutional Baseline Audit:** Exact CAGR formula reconciliation, anti-future date clamping, fee sensitivity ladder, factor ablation, and frozen deterministic baseline (4.60% CAGR, -38.49% MDD).
3. **V0.3 Predictive Intelligence Engine:** 24 point-in-time engineered features, expanding walk-forward training, Platt calibration, and conviction-tilted HRP ($\gamma=1.00$).
4. **V0.3.1 Predictive Intelligence Diagnosis Complete:**
   - 12-vector diagnostic research protocol executed.
   - Zero lookahead violations across 42 rebalances / 420 checks.
   - Standalone ML hypothesis falsified out-of-sample: Spearman Rank IC = -0.0909, Long/Short return = -7.28%.
   - Untouched test partition (2024–2026) underperformed deterministic baseline (-1.27% vs -0.02%).
   - Deterministic engine confirmed as the permanent production research baseline.

### 11.2 V0.4 Roadmap: Decision Intelligence & Robust Alpha Research
- **V0.4-A — Research Integrity:** Full Nifty 500 PIT backfill, sector/industry normalization, target redesign (continuous excess & risk-adjusted targets across 30/60/90/180/252D horizons), feature timestamp audit.
- **V0.4-B — Robust Alpha:** Cross-sectional quintile spreads ($Q5 - Q1$), sector-neutral and market-neutral IC evaluation, regime-specific IC tracking, turnover-adjusted alpha.
- **V0.4-C — Decision Engine:** Normalized additive scoring function ($\text{ArthScore} = w_F F + w_M M + w_E E + w_R R + w_H H$) with cross-pillar signal agreement logic.
- **V0.4-D — Downstream Explainability ("Artha AI"):** Downstream LLM synthesis for institutional "Thesis + Evidence" generation (Why this stock, Why this weight, Why now, Invalidation triggers, Key risks) without allowing the LLM to generate raw quantitative buy signals. Broker execution remains deferred.

---

*End of PROJECT_PLAN.md*
