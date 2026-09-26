# ArthIQ Platform Master Architecture & Implementation Blueprint
> **The Definitive Engineering and Quantitative Specification for Building the Platform from Scratch**
> **Platform Name:** ArthIQ (`arthiq`) | **Version:** V0.4 Institutional Reference
> **Universe:** Indian Equities (NSE/BSE, Nifty 500 Universe) | **Cadence:** Quarterly Rebalance (Earnings-Cycle Aligned)
> **Author/Owner:** Quantitative Investment Decision Engine Specification

---

## Table of Contents
1. [Executive Summary & System Vision](#1-executive-summary--system-vision)
2. [High-Level System Architecture & Component Interaction](#2-high-level-system-architecture--component-interaction)
3. [Data Architecture & Zero-Lookahead Point-in-Time (PIT) Engine](#3-data-architecture--zero-lookahead-point-in-time-pit-engine)
   - 3.1 Data Sources & Ingestion Contracts
   - 3.2 PIT Invariant Theory & Anti-Lookahead Safeguards
   - 3.3 Complete Relational Database Schema (SQLite WAL & PostgreSQL DDL)
   - 3.4 Data Access Abstraction Layer (`PointInTimeDataAccess`)
4. [Quantitative Factor & Multi-Stage Scoring Engines](#4-quantitative-factor--multi-stage-scoring-engines)
   - 4.1 Universe Screening & Liquidity Filtering (Stage 0)
   - 4.2 Decoupled Two-Level Valuation & Business Scoring (V0.2 Engine)
   - 4.3 Sector Archetypes & Sector-Relative Normalization
   - 4.4 Scenario Analysis & Probabilistic Expected Returns
   - 4.5 Event Intelligence & Dynamic Factor Deltas
5. [Portfolio Optimization & Real-World Execution Engine](#5-portfolio-optimization--real-world-execution-engine)
   - 5.1 Hierarchical Risk Parity (HRP) Mathematical Formulation
   - 5.2 Quasi-Diagonalization & Recursive Bisection Algorithms
   - 5.3 Hard Risk Caps & Dynamic Investor Profiles
   - 5.4 Whole-Share Allocation & Indian Execution Cost Friction (STT, Stamp Duty, Slippage)
6. [Machine Learning & Predictive Intelligence Engine (V0.3 / V0.3.1 / V0.4)](#6-machine-learning--predictive-intelligence-engine-v03--v031--v04)
   - 6.1 The 24-Dimensional Point-in-Time Feature Store
   - 6.2 Target Formulation & Labeling Invariants
   - 6.3 Expanding Walk-Forward Cross-Validation Architecture
   - 6.4 Model Architecture & Probability Calibration (Platt Scaling vs Isotonic)
   - 6.5 The V0.3.1 Diagnostic Breakthrough: Empirical Falsification of Standalone ML
   - 6.6 Cross-Sectional Quintile Inversion & 1-P Reverse Signal Diagnostic
   - 6.7 Feature Group Ablation & The Fundamentals-Only Alpha Discovery
   - 6.8 The 8 Institutional Model Promotion Gates
7. [The V0.4 Decision Intelligence Framework](#7-the-v04-decision-intelligence-framework)
   - 7.1 Normalized Additive Decision Function ($\text{ArthScore}$)
   - 7.2 Cross-Pillar Signal Agreement Mechanism
   - 7.3 Candidate Signal Zoo (Candidates 1, 2, and 3)
   - 7.4 Multi-Horizon Decay Analysis (30D to 252D)
   - 7.5 Shadow Portfolio Tracking & Real-Time Slippage Monitoring
8. [Backend API & Service Infrastructure](#8-backend-api--service-infrastructure)
   - 8.1 Technology Stack & Directory Structure
   - 8.2 Security, Cryptographic Authentication & RBAC
   - 8.3 RESTful Endpoint Specifications & Schemas
   - 8.4 Automated Plain-English Rationale Generation & PDF Reporting
9. [Frontend Client Architecture (React 19 + TypeScript + Tailwind CSS)](#9-frontend-client-architecture-react-19--typescript--tailwind-css)
   - 9.1 Obsidian Dark Design System & Visual Tokens
   - 9.2 Real-Time Navigation, IST Monospace Clock & Live Ticker Marquee
   - 9.3 The Five Core Analytical Modules (Stock Ideas, Lens, Vault, Pulse, Edge)
   - 9.4 State Management, Session Lifecycle & API Client
10. [Walk-Forward Backtesting & Performance Analytics](#10-walk-forward-backtesting--performance-analytics)
    - 10.1 Walk-Forward Simulation Loop
    - 10.2 Mathematical Metric Formulations (CAGR, Sharpe, Sortino, Calmar, Turnover)
    - 10.3 Transaction Fee Sensitivity Ladder
11. [Monitoring, Data Quality & Operational Runbooks](#11-monitoring-data-quality--operational-runbooks)
    - 11.1 Daily Data Quality Invariant Checks
    - 11.2 Weekly Point-in-Time Audit Engine
    - 11.3 Population Stability Index (PSI) & Concept Drift Detection
    - 11.4 Cron Automation Schedules
12. [End-to-End Build Blueprint: From Zero to Production](#12-end-to-end-build-blueprint-from-zero-to-production)
    - Step 1: Directory Setup & Python Virtual Environment
    - Step 2: Database Migration & Static Universe Seeding
    - Step 3: Core Quantitative & Data Access Implementation
    - Step 4: Machine Learning Pipeline & Diagnostics Suite
    - Step 5: FastAPI REST Backend Implementation
    - Step 6: Vite + React 19 Frontend Deployment
    - Step 7: Verification Suite Execution

---

## 1. Executive Summary & System Vision

**ArthIQ** is an institutional-grade, personal quantitative investment decision-support engine specifically designed for Indian equities (NSE/BSE Nifty 500 universe). The platform systematically replaces manual, emotionally biased retail workflows—such as browsing multiple financial portals, unstructured annual report skimming, and naive heuristic portfolio construction—with a mathematically rigorous, auditable, and automated decision-making engine.

### Core Mission & Philosophies
1. **Decision Support, Not Black-Box Automation:** The system produces evidence-backed, mathematically grounded buy/sell/hold target allocations alongside plain-English investment rationales. The user retains manual execution authority via their broker app (Zerodha Kite, Groww, Upstox), preventing runaway trading errors.
2. **Strict Zero-Lookahead Point-in-Time (PIT) Integrity:** Backtests and live inference share the exact same code path. Financial data, restatements, and constituent lists are strictly queried as of what was publicly known on the rebalance date.
3. **Decoupled Quality vs. Price Valuation:** Enterprise durability (Business Quality) is evaluated independently from market price (Valuation Multiple) before synthesis into an Investment Score.
4. **Institutional Risk-First Portfolio Construction:** Allocations are generated using Hierarchical Risk Parity (HRP) with strict mathematical caps (max 25% single stock, max 40% sector) and real-world Indian transaction cost modeling (STT, stamp duty, brokerage, slippage).
5. **Empirical Discipline in Machine Learning:** Standalone ML predictions are never accepted blindly. Extensive diagnostic audits (Spearman Rank IC, Information Ratios, monotonic quintile spreads $Q5 > Q1$, and frozen out-of-sample partitions) govern model promotion.

---

## 2. High-Level System Architecture & Component Interaction

The platform follows a layered, decoupled service architecture:

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    FRONTEND LAYER                                       │
│                       React 19 + TypeScript + Vite 6 + Tailwind CSS                     │
│   ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌─────────┐   │
│   │  Stock Ideas  │ │     Lens      │ │     Vault     │ │     Pulse     │ │  Edge   │   │
│   │  (QuickPicks) │ │ (Diagnostics) │ │  (HRP Alloc)  │ │   (Thematic)  │ │ (Events)│   │
│   └───────▲───────┘ └───────▲───────┘ └───────▲───────┘ └───────▲───────┘ └────▲────┘   │
└───────────┼─────────────────┼─────────────────┼─────────────────┼──────────────┼────────┘
            │                 │                 │                 │              │
            └─────────────────┴────────┬────────┴─────────────────┴──────────────┘
                                       │ Bearer Token HTTP/REST (JSON)
┌──────────────────────────────────────▼──────────────────────────────────────────────────┐
│                                   FASTAPI BACKEND SERVICE                               │
│                         Authentication / Pydantic v2 Serialization                       │
│  ┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────────────────┐  │
│  │   Scoring Engine V2   │ │     HRP Optimizer     │ │      ML Alpha Service         │  │
│  │  (BQS, Growth, Val,   │ │ (Clustering, Bisection│ │ (Expanding Walk-Forward,      │  │
│  │   Risk, Matrix Quad)  │ │  25% Stock / 40% Sec) │ │  Calibrated Boosters, Platt)  │  │
│  └───────────▲───────────┘ └───────────▲───────────┘ └───────────────▲───────────────┘  │
│              │                         │                             │                  │
│              └─────────────────────────┼─────────────────────────────┘                  │
│                                        │                                                │
│                        ┌───────────────▼───────────────┐                                │
│                        │    PointInTimeDataAccess      │                                │
│                        │ (Zero-Lookahead Anti-Leakage) │                                │
│                        └───────────────▲───────────────┘                                │
└────────────────────────────────────────┼────────────────────────────────────────────────┘
                                         │ Direct SQL Parameterized Queries
┌────────────────────────────────────────▼────────────────────────────────────────────────┐
│                                DATA STORAGE & PERSISTENCE                               │
│                 SQLite 3 (WAL Mode, High Concurrency) / PostgreSQL Core                 │
│  ┌─────────────────────────┐ ┌─────────────────────────┐ ┌───────────────────────────┐  │
│  │  daily_prices           │ │  fundamentals_quarterly │ │ index_constituents_history│  │
│  │  (OHLCV, Adj Close)     │ │  (disclosed_at stamped) │ │ (Historical Nifty 500 PIT)│  │
│  └─────────────────────────┘ └─────────────────────────┘ └───────────────────────────┘  │
│  ┌─────────────────────────┐ ┌─────────────────────────┐ ┌───────────────────────────┐  │
│  │  corporate_events       │ │  news_sentiment         │ │ shadow_portfolio_records  │  │
│  │  (Filings, Board Meets) │ │  (FinBERT Scores)       │ │ (Execution & Drift Logs)  │  │
│  └─────────────────────────┘ └─────────────────────────┘ └───────────────────────────┘  │
└────────────────────────────────────────▲────────────────────────────────────────────────┘
                                         │ Idempotent Ingestion Scripts (cron / event)
┌────────────────────────────────────────┴────────────────────────────────────────────────┐
│                              EXTERNAL DATA INGESTION FEEDS                              │
│   NSE Bhavcopy (EOD)  │  BSE Bhavcopy  │  Yahoo Finance  │  Macro Feeds (VIX, Crude)    │
│   NSE Filings RSS     │  Financial Media Scraping        │  Static Indices Seed CSVs    │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Architecture & Zero-Lookahead Point-in-Time (PIT) Engine

### 3.1 Data Sources & Ingestion Contracts

| Source | Role | Update Cadence | Storage Mechanism | Failure Policy |
| :--- | :--- | :--- | :--- | :--- |
| **NSE Bhavcopy** | Official ground-truth daily OHLCV for NSE listed equities | Daily at 18:30 IST | Raw CSV parsed into `daily_prices` | Strict fallback to yfinance if exchange archive unavailable |
| **BSE Bhavcopy** | Auxiliary OHLCV for dual-listed/BSE securities | Daily at 19:00 IST | Parsed into `daily_prices` | Skip if symbol exists on NSE |
| **yfinance Prices** | Secondary redundancy feed & historical gap filling | Weekly or on-demand | Normalized into `daily_prices` | Rate-limited batching (max 5 req/sec) with exponential backoff |
| **Corporate Filings (NSE/BSE)** | Financial disclosures (Revenue, PAT, Net Worth, Debt) | Event-driven (Results season) | Stored in `fundamentals_quarterly` with disclosure date | Flag unannounced quarters; never impute future values |
| **Macroeconomic Feeds** | India VIX, USD/INR, 10-Yr G-Sec Yield, Brent Crude | Daily at 20:00 IST | Appended to `daily_prices` as synthetic symbols | Use latest available business day close |
| **Financial News RSS** | Curated headlines (ET, Moneycontrol, Livemint) | 4x daily (09:00, 13:00, 17:00, 21:00 IST) | Raw headlines into `news_sentiment` | Fallback to VADER baseline if NLP model times out |

### 3.2 PIT Invariant Theory & Anti-Lookahead Safeguards

A quantitative backtest that uses restated earnings or unannounced quarters to determine positions in 2018 is corrupted. ArthIQ enforces three unbreakable mathematical invariants:
1. **The Disclosure Barrier ($t_{\text{disclosed}} \le t_{\text{asof}}$):** Financial statements are only visible on or after the exact calendar day they were formally submitted to the exchange.
2. **The Effective Date Invariant:** A stock cannot be screened into the universe unless it was an active constituent of the Nifty 500 on the simulated date $t_{\text{asof}}$. Survivorship bias is eliminated by querying `index_constituents_history`.
3. **Execution Lag ($t_{\text{trade}} > t_{\text{asof}}$):** Portfolio rebalance decisions computed on the close of day $t_{\text{asof}}$ are executed at the **open price of day $t+1$**. Same-day closing execution is strictly prohibited.

### 3.3 Complete Relational Database Schema (SQLite WAL & PostgreSQL DDL)

```sql
-- Pragmas for SQLite High Concurrency Performance
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

-- 1. Point-in-Time Index Constituents
CREATE TABLE IF NOT EXISTS index_constituents_history (
    effective_date   DATE    NOT NULL,
    symbol           TEXT    NOT NULL,
    isin             TEXT,
    sector           TEXT    NOT NULL,
    source           TEXT    NOT NULL DEFAULT 'nse_index_rebalance',
    PRIMARY KEY (effective_date, symbol)
);
CREATE INDEX IF NOT EXISTS idx_ich_symbol ON index_constituents_history(symbol);
CREATE INDEX IF NOT EXISTS idx_ich_effdate ON index_constituents_history(effective_date);

-- 2. Daily Market Prices (OHLCV)
CREATE TABLE IF NOT EXISTS daily_prices (
    symbol           TEXT    NOT NULL,
    trade_date       DATE    NOT NULL,
    open             REAL,
    high             REAL,
    low              REAL,
    close            REAL    NOT NULL,
    adj_close        REAL,
    volume           INTEGER,
    source           TEXT    NOT NULL,
    PRIMARY KEY (symbol, trade_date, source)
);
CREATE INDEX IF NOT EXISTS idx_dp_date ON daily_prices(trade_date);
CREATE INDEX IF NOT EXISTS idx_dp_symbol_date ON daily_prices(symbol, trade_date);

-- 3. Point-in-Time Quarterly Fundamentals
CREATE TABLE IF NOT EXISTS fundamentals_quarterly (
    symbol           TEXT    NOT NULL,
    period_end       DATE    NOT NULL,
    disclosed_at     DATE    NOT NULL, -- Invariant barrier
    metric           TEXT    NOT NULL,
    value            REAL,
    unit             TEXT    DEFAULT 'INR_cr',
    source           TEXT    NOT NULL,
    PRIMARY KEY (symbol, period_end, metric, source)
);
CREATE INDEX IF NOT EXISTS idx_fq_pit ON fundamentals_quarterly(symbol, metric, disclosed_at);

-- 4. Corporate Disclosures & Event Intelligence
CREATE TABLE IF NOT EXISTS corporate_events (
    event_id         TEXT    PRIMARY KEY,
    symbol           TEXT    NOT NULL,
    disclosed_at     TIMESTAMP NOT NULL,
    event_type       TEXT    NOT NULL, -- 'EARNINGS_BEAT', 'ORDER_WIN', 'MANAGEMENT_CHANGE'
    headline         TEXT    NOT NULL,
    details_json     TEXT,
    impact_score     REAL    DEFAULT 0.0,
    source           TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ce_symbol_dt ON corporate_events(symbol, disclosed_at);

-- 5. News Sentiment Feed
CREATE TABLE IF NOT EXISTS news_sentiment (
    headline_id      TEXT    PRIMARY KEY,
    symbol           TEXT,
    published_at     DATE    NOT NULL,
    headline         TEXT    NOT NULL,
    source           TEXT,
    sentiment_score  REAL,    -- [-1.0, +1.0]
    model_version    TEXT,
    ingested_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_news_symbol_date ON news_sentiment(symbol, published_at);

-- 6. Model Training & Outperformance Predictions
CREATE TABLE IF NOT EXISTS model_predictions (
    asof_date        DATE    NOT NULL,
    symbol           TEXT    NOT NULL,
    model_name       TEXT    NOT NULL,
    p_outperform     REAL    NOT NULL,
    rank_in_universe INTEGER,
    features_json    TEXT,
    PRIMARY KEY (asof_date, symbol, model_name)
);

-- 7. Target Portfolio History & Rebalance Execution
CREATE TABLE IF NOT EXISTS portfolio_history (
    run_id           TEXT    NOT NULL,
    asof_date        DATE    NOT NULL,
    symbol           TEXT    NOT NULL,
    target_weight    REAL    NOT NULL,
    action           TEXT    NOT NULL, -- 'BUY', 'SELL', 'HOLD'
    shares_target    INTEGER NOT NULL,
    rationale_text   TEXT,
    executed         INTEGER DEFAULT 0,
    PRIMARY KEY (run_id, symbol)
);

-- 8. Backtest Run Metadata
CREATE TABLE IF NOT EXISTS backtest_runs (
    run_id           TEXT    PRIMARY KEY,
    started_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at      TIMESTAMP,
    start_date       DATE    NOT NULL,
    end_date         DATE    NOT NULL,
    config_json      TEXT    NOT NULL,
    cagr             REAL,
    sharpe           REAL,
    max_drawdown     REAL,
    turnover_avg     REAL,
    benchmark_cagr   REAL,
    status           TEXT
);

-- 9. Shadow Portfolio & Execution Tracking
CREATE TABLE IF NOT EXISTS shadow_portfolio_records (
    record_id        TEXT    PRIMARY KEY,
    rebalance_date   DATE    NOT NULL,
    symbol           TEXT    NOT NULL,
    target_weight    REAL    NOT NULL,
    simulated_fill_price REAL NOT NULL,
    slippage_bps     REAL    NOT NULL,
    turnover_weight  REAL    NOT NULL,
    execution_status TEXT    DEFAULT 'FILLED'
);

-- 10. Multi-User Authentication & Profiles
CREATE TABLE IF NOT EXISTS users (
    id               TEXT PRIMARY KEY,
    email            TEXT UNIQUE NOT NULL,
    password_hash    TEXT NOT NULL,
    full_name        TEXT NOT NULL,
    role             TEXT NOT NULL DEFAULT 'user',
    status           TEXT NOT NULL DEFAULT 'active',
    created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login       TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_portfolios (
    id               TEXT PRIMARY KEY,
    user_id          TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name             TEXT NOT NULL,
    initial_capital  REAL NOT NULL DEFAULT 100000.0,
    current_cash     REAL NOT NULL DEFAULT 100000.0,
    created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### 3.4 Data Access Abstraction Layer (`PointInTimeDataAccess`)

Every query executed during scoring, backtesting, or ML training **must** pass through `PointInTimeDataAccess`. Direct database queries that could leak future rows are rejected by code invariants:

```python
# src/invst/data_access.py
from datetime import date
from typing import Optional, List, Dict
import sqlite3

class PointInTimeDataAccess:
    """Institutional Anti-Lookahead Data Access Gateway."""

    def __init__(self, conn: sqlite3.Connection, asof: date):
        self.conn = conn
        self.asof = asof  # Simulated 'Today' barrier

    def get_price(self, symbol: str, on_or_before: Optional[date] = None) -> Optional[float]:
        target_date = on_or_before or self.asof
        row = self.conn.execute(
            """
            SELECT close FROM daily_prices
            WHERE symbol = ? AND trade_date <= ?
            ORDER BY trade_date DESC LIMIT 1
            """,
            (symbol, target_date.isoformat()),
        ).fetchone()
        return float(row[0]) if row and row[0] is not None else None

    def get_price_series(self, symbol: str, start: date, end: date) -> List[tuple]:
        # Clamped strictly to self.asof to eliminate future leakage
        clamped_end = min(end, self.asof)
        return self.conn.execute(
            """
            SELECT trade_date, open, high, low, close, adj_close, volume
            FROM daily_prices
            WHERE symbol = ? AND trade_date BETWEEN ? AND ?
            ORDER BY trade_date ASC
            """,
            (symbol, start.isoformat(), clamped_end.isoformat()),
        ).fetchall()

    def get_fundamental(self, symbol: str, metric: str) -> Optional[float]:
        """Point-in-time lookup respecting the disclosed_at invariant."""
        row = self.conn.execute(
            """
            SELECT value FROM fundamentals_quarterly
            WHERE symbol = ? AND metric = ? AND disclosed_at <= ?
            ORDER BY disclosed_at DESC, period_end DESC
            LIMIT 1
            """,
            (symbol, metric, self.asof.isoformat()),
        ).fetchone()
        return float(row[0]) if row and row[0] is not None else None

    def get_universe(self) -> List[str]:
        """Fetch active Nifty 500 constituents as of self.asof."""
        rows = self.conn.execute(
            """
            SELECT symbol FROM index_constituents_history
            WHERE effective_date <= ?
            GROUP BY symbol
            HAVING MAX(effective_date) <= ?
            """,
            (self.asof.isoformat(), self.asof.isoformat()),
        ).fetchall()
        return [r[0] for r in rows]
```

---

## 4. Quantitative Factor & Multi-Stage Scoring Engines

### 4.1 Universe Screening & Liquidity Filtering (Stage 0)

Every rebalance cycle begins by filtering the Nifty 500 down to an **Investable Universe**:

$$\text{Screened}_i = \begin{cases} 
1 & \text{if } (\text{TradedValue}_{30d, i} \ge ₹5\text{ Cr}) \land (\text{MarketCap}_i \ge ₹1000\text{ Cr}) \land (\text{Age}_i \ge 3\text{ yrs}) \land (\text{Price}_i \ge ₹10) \\
0 & \text{otherwise}
\end{cases}$$

Names with promoter holdings $> 75\%$ or $> 2$ missing quarters of fundamentals in the last 12 quarters are dropped.

### 4.2 Decoupled Two-Level Valuation & Business Scoring (V0.2 Engine)

Retail investors frequently conflate a good business with a good investment. ArthIQ separates these concepts into two explicit tiers:

```
┌────────────────────────────────────────────────────────────────────────┐
│ LEVEL 1: BUSINESS SCORE (Price-Agnostic Enterprise Durability)         │
│ Formula: 0.60 * Business Quality Score (BQS) + 0.40 * Growth Score     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ LEVEL 2: INVESTMENT SCORE (Attractiveness of Purchasing Today)         │
│ Formula: 0.40 * Business Score + 0.35 * Valuation + 0.25 * Risk Score  │
│ (Down-weighted by 10% if Execution/Liquidity is unfavorable)           │
└────────────────────────────────────────────────────────────────────────┘
```

#### A. Business Quality Score (BQS) Formulation
1. **Capital Efficiency (35%):** 5-Year median Return on Capital Employed (ROCE) and Return on Equity (ROE).
2. **Margin Durability (25%):** Operating Profit Margin (OPM) stability measured via $\text{std}(\text{OPM}_{5y}) / \text{mean}(\text{OPM}_{5y})$.
3. **Balance Sheet Resilience (25%):** Solvency score evaluated via $1 / (1 + \text{Debt-to-Equity})$. Interest coverage (EBIT / Interest) $\ge 4.0\times$.
4. **Corporate Governance & Earnings Quality (15%):** Cash Flow from Operations to EBITDA ratio ($\text{CFO} / \text{EBITDA} \ge 0.80$).

#### B. Growth Engine Formulation
Evaluates 3-Year and 5-Year CAGR across Sales and Net Profit, combined with quarterly earnings acceleration ($\text{EPS Growth}_{YoY} - \text{EPS Growth}_{Prior YoY}$).

#### C. Valuation Engine Formulation
Valuation is evaluated relative to the company's own historical multiple distribution:

$$V_i = 0.40 \cdot \text{Pct}\left(\frac{1}{\text{PE}_{TTM}}\right) + 0.30 \cdot \text{Pct}\left(\frac{\text{PE}_{3y\text{ median}}}{\text{PE}_{\text{current}}}\right) + 0.30 \cdot \text{Pct}\left(\frac{1}{\text{EV/EBITDA}}\right)$$

#### D. Risk Engine Formulation
Subtractive risk assessment penalizing excessive volatility, market sensitivity, and drawdown risk:

$$R_i = 0.40 \cdot \text{Pct}\left(\frac{1}{\text{Beta}_{2y}}\right) + 0.35 \cdot \text{Pct}\left(\frac{1}{|\text{MaxDD}_{3y}|}\right) + 0.25 \cdot \text{Pct}\left(\frac{1}{\sigma_{\text{ann}, 252d}}\right)$$

### 4.3 Sector Archetypes & Sector-Relative Normalization

Different sectors exhibit fundamentally different accounting metrics. ArthIQ categorizes stocks into three distinct archetypes:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           SECTOR ARCHETYPES                             │
├───────────────────────┬─────────────────────────┬───────────────────────┤
│ 1. FINANCIALS         │ 2. INDUSTRIALS & CAPEX  │ 3. CONSUMER & TECH    │
│ (Banks, NBFCs, Ins.)  │ (Capital Goods, Infra)  │ (FMCG, IT Services)   │
│ • Net Interest Margin │ • Fixed Asset Turnover  │ • Brand Moat & ROCE   │
│ • Gross & Net NPA     │ • Order Book / Rev Ratio│ • Working Capital Days│
│ • Capital Adequacy    │ • Debt / EBITDA         │ • FCF Conversion      │
│ • Excluded: D/E, ROCE │ • Heavy EV/EBITDA Focus │ • EV/Sales & P/E Focus│
└───────────────────────┴─────────────────────────┴───────────────────────┘
```

Within each sector, all raw factors are winsorized at the 5th and 95th percentiles and transformed into sector z-scores before cross-sector ranking:

$$z_{i, s} = \frac{x_{i, s} - \mu_s}{\sigma_s}, \quad \text{Score}_{i} = \Phi(z_{i, s}) \times 100$$

### 4.4 Scenario Analysis & Probabilistic Expected Returns

For each candidate security, the system computes probabilistic future value distributions across three distinct macro-fundamental scenarios:

$$\mathbb{E}[R_i] = p_{\text{bull}} R_{i, \text{bull}} + p_{\text{base}} R_{i, \text{base}} + p_{\text{bear}} R_{i, \text{bear}}$$

- **Bull Case ($p = 0.25$):** Sales growth $+200\text{ bps}$ above 5Y CAGR, valuation expands to 75th percentile historical P/E.
- **Base Case ($p = 0.50$):** Median 5Y CAGR sustained, valuation reverts to 3Y median P/E.
- **Bear Case ($p = 0.25$):** Earnings contract by 15%, valuation multiple compresses to 25th percentile historical P/E.

### 4.5 Event Intelligence & Dynamic Factor Deltas

Real-time corporate disclosures stream into an event parser that adjusts base factor scores dynamically:
- **Earnings Beat ($\ge +10\%$ vs consensus):** $+4.0$ Growth points, $+2.0$ Quality points.
- **Major Capex Announcement ($\ge 20\%$ Net Worth):** $+3.0$ Growth points, $-1.5$ Risk points (short-term leverage increase).
- **Auditor Resignation / Qualified Opinion:** $-15.0$ Governance points (Immediate hard freeze from new buying).

---

## 5. Portfolio Optimization & Real-World Execution Engine

### 5.1 Hierarchical Risk Parity (HRP) Mathematical Formulation

Standard Markowitz mean-variance optimization requires inverting a covariance matrix ($\Sigma^{-1}$), which magnifies noise and produces unstable, extreme portfolio weights. ArthIQ utilizes Marcos López de Prado's **Hierarchical Risk Parity (HRP)**, which operates directly on the hierarchical structure of correlations without matrix inversion.

### 5.2 Quasi-Diagonalization & Recursive Bisection Algorithms

```
Correlation Matrix (ρ) ──► Distance Matrix D(i,j) ──► Hierarchical Tree ──► Quasi-Diagonal Order ──► Recursive Bisection Weights
```

1. **Correlation Distance Metric:**
   $$d_{i, j} = \sqrt{\frac{1}{2} (1 - \rho_{i, j})}$$

2. **Hierarchical Tree Clustering:** Assets are grouped using single-linkage clustering based on distance $d_{i, j}$.

3. **Quasi-Diagonalization:** Reorganizes rows and columns of the covariance matrix $\Sigma$ such that highly correlated assets are placed adjacent to each other along the diagonal.

4. **Recursive Bisection:**
   For a given cluster $C$, split into sub-clusters $C_1$ and $C_2$. Compute the variance of each sub-cluster:
   $$V_k = w_k^T \Sigma_k w_k, \quad \text{where } w_k = \frac{\text{diag}(\Sigma_k)^{-1}}{\text{Tr}(\text{diag}(\Sigma_k)^{-1})}$$
   The allocation factor $\alpha_1$ for cluster $C_1$ is:
   $$\alpha_1 = 1 - \frac{V_1}{V_1 + V_2}, \quad \alpha_2 = 1 - \alpha_1$$
   Weights are updated recursively: $W_{C_1} = W_C \cdot \alpha_1$ and $W_{C_2} = W_C \cdot \alpha_2$.

### 5.3 Hard Risk Caps & Dynamic Investor Profiles

To balance diversification with conviction, hard constraints are applied iteratively:

| Parameter | Conservative Profile | Moderate Profile (Default) | Aggressive Profile |
| :--- | :--- | :--- | :--- |
| **Target Holdings** | 16 stocks | 10 stocks | 8 stocks |
| **Max Single Stock Cap** | **10.0%** | **15.0%** | **25.0%** |
| **Max Sector Exposure** | **25.0%** | **35.0%** | **40.0%** |
| **Minimum BQS Quality Floor**| 70.0 / 100 | 60.0 / 100 | 50.0 / 100 |

Excess weights exceeding single-stock caps are clipped and redistributed proportionally among non-capped holdings via an iterative projection algorithm.

### 5.4 Whole-Share Allocation & Indian Execution Cost Friction

Retail brokerages require integer share purchases. ArthIQ implements a floor-sizing algorithm:

$$\text{Shares}_i = \left\lfloor \frac{\text{Capital} \times w_i}{P_{i, \text{open}}} \right\rfloor$$

#### Transaction Cost Accounting Matrix:
- **Securities Transaction Tax (STT):** 10 bps ($0.10\%$) on delivery purchase and sale.
- **Brokerage Commission:** 30 bps ($0.30\%$) buy, 20 bps ($0.20\%$) sell.
- **Stamp Duty & Exchange Fees:** 1.5 bps ($0.015\%$).
- **Market Impact Slippage:** 5 bps ($0.05\%$) standard, scaled up for lower-liquidity names.
- **Total Round-Trip Friction:** **66.5 bps** explicitly subtracted from simulated backtest returns.

---

## 6. Machine Learning & Predictive Intelligence Engine (V0.3 / V0.3.1 / V0.4)

### 6.1 The 24-Dimensional Point-in-Time Feature Store

Every rebalance cross-section builds a 24-dimensional feature vector per stock:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        THE 24-FEATURE CATALOG                          │
├────────────────────────────────────────────────────────────────────────┤
│ 1. composite_score         13. news_sentiment                          │
│ 2. investment_score        14. dist_from_52w_high                      │
│ 3. business_score          15. downside_semivariance                   │
│ 4. growth_score            16. macro_vix                               │
│ 5. roe_5yr                 17. macro_vix_change_30d                    │
│ 6. roce_5yr                18. macro_usd_inr                           │
│ 7. debt_equity             19. quality_to_valuation_ratio              │
│ 8. pe_ttm                  20. risk_adjusted_momentum                  │
│ 9. pb                      21. market_score                            │
│ 10. ev_ebitda              22. gross_npa_pct (Financials)              │
│ 11. annualised_vol         23. order_book_to_bill (Industrials)        │
│ 12. beta                   24. working_capital_days (Consumer)         │
└────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Target Formulation & Labeling Invariants

Rather than attempting to forecast noisy, non-stationary raw asset prices, the model is trained as a binary classifier predicting forward excess return over the Nifty 500 TRI:

$$y_{i, t} = \mathbb{I}\left( R_{i, [t, t+90D]} - R_{\text{NIFTY500}, [t, t+90D]} > 0 \right)$$

### 6.3 Expanding Walk-Forward Cross-Validation Architecture

Traditional k-fold cross-validation leaks future regime information to past samples. ArthIQ enforces an expanding walk-forward sequence:

```
2016 ──► 2020: Train (Fold 1) ──► Predict Q1 2021 (OOS)
2016 ──► Q1 2021: Train (Fold 2) ──► Predict Q2 2021 (OOS)
...
2016 ──► Q4 2023: Train (Fold N) ──► Predict Q1 2024 (OOS)
[2024-01-01 to 2026-09-21]: PERMANENTLY FROZEN UNTOUCHED TEST PARTITION
```

### 6.4 Model Architecture & Probability Calibration

- **Base Estimators:** LightGBM (`LGBMClassifier`) and XGBoost (`XGBClassifier`) with early stopping, falling back to L2-regularized `LogisticRegression` when native tree libraries are uncompiled.
- **Probability Calibration:** Boosted models produce distorted margins. ArthIQ evaluates:
  - **Platt Scaling (`sigmoid`):** Fits a logistic sigmoid to raw margins via out-of-fold cross-validation.
  - **Isotonic Regression:** Non-parametric monotonic binning.
  - **Validation Metrics:** Brier Score ($BS = \frac{1}{N} \sum (p_i - y_i)^2$) and Expected Calibration Error (ECE).

### 6.5 The V0.3.1 Diagnostic Breakthrough: Empirical Falsification of Standalone ML

The V0.3.1 research cycle executed a rigorous 12-vector institutional audit that revealed a crucial empirical truth:

| Model / Configuration | CAGR | Alpha | Sharpe | Max Drawdown | Hit Rate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Deterministic Baseline (V0.2.1)** | **4.60%** | **-2.56%** | **-0.17** | **-38.49%** | **46.2%** |
| Pure ML $\gamma = 0.50$ | 4.40% | -2.75% | -0.19 | -39.01% | 45.4% |
| 50/50 Deterministic/ML Blend ($\gamma = 1.00$) | 4.64% | -2.52% | -0.16 | -39.61% | 46.9% |
| **Platt + 50/50 + $\gamma = 0.50$** | **4.25%** | **-2.90%** | **-0.20** | **-38.15%** | **44.6%** |

#### The Untouched Out-of-Sample Performance Breakdown:
- **Development (2016–2020):** Baseline $8.34\%$ vs ML $\mathbf{8.96\%}$ ($+0.62\%$)
- **Validation (2021–2023):** Baseline $0.25\%$ vs ML $\mathbf{1.32\%}$ ($+1.07\%$)
- **Frozen Untouched Test (2024–2026):** Baseline $\mathbf{-0.02\%}$ vs ML $-1.27\%$ ($\mathbf{-1.25\%}$ underperformance)

> [!CAUTION]
> **Architectural Decision:** Standalone ML probability failed to generate positive out-of-sample alpha and was **rejected as the primary portfolio decision-maker**. The deterministic engine remains the permanent production baseline.

### 6.6 Cross-Sectional Quintile Inversion & 1-P Reverse Signal Diagnostic

Diagnostic evaluation revealed that the 24-feature ML model was systematically inverted:
- **Spearman Rank IC:** **-0.0909**
- **Information Ratio (IC IR):** **-0.39**
- **Annualized Long/Short Return:** **-7.28%**

#### Cross-Sectional Quintile Return Spread:
```
Q1 (Lowest ML Probability):  +3.76% Mean Excess Return
Q2:                          +2.98%
Q3:                          +2.57%
Q4:                          +2.09%
Q5 (Highest ML Probability): +1.87%
Spread (Q5 - Q1):            -1.89% (Complete Inversion)
```

Testing a reversed signal ($P_{\text{reverse}} = 1 - P$) yielded an IC of **+0.0909** and L/S return of **+7.76%**. However, rather than naively deploying $1 - P$, the system mandated feature ablation to uncover the root cause.

### 6.7 Feature Group Ablation & The Fundamentals-Only Alpha Discovery

A controlled 8-subset feature ablation isolated the exact source of signal inversion:

| Feature Subset Tested | Rank IC | IC IR | Positive IC Quarters | Annualized L/S Return |
| :--- | :---: | :---: | :---: | :---: |
| **Fundamentals Only (Set A)** | **+0.0179** | **+0.07** | **60.0%** | **+4.99%** |
| Valuation Only | +0.0024 | +0.01 | 48.0% | -0.15% |
| Risk Only | +0.0311 | +0.17 | 64.0% | -2.24% |
| Momentum Only | -0.0163 | -0.06 | 52.0% | -4.71% |
| Fundamentals + Valuation | -0.0648 | -0.25 | 48.0% | -3.11% |
| Fundamentals + Risk | -0.0359 | -0.15 | 52.0% | -1.33% |
| Fundamentals + Valuation + Risk | -0.0798 | -0.37 | 28.0% | -6.32% |
| **Full 24 Features** | **-0.0909** | **-0.39** | **32.0%** | **-7.28%** |

**Conclusion:** Pure fundamental balance sheet variables (RoE, RoCE, Debt/Equity) hold genuine predictive alpha. Adding technical momentum, valuation multiples, and macro variables introduced destructive collinear interactions that inverted the model.

### 6.8 The 8 Institutional Model Promotion Gates

No model can be promoted to production without clearing all 8 binary gates:
1. **Gate 1 (Zero PIT Lookahead):** 100% pass rate across historical rebalance audits.
2. **Gate 2 (Positive Statistical Signal):** Spearman Rank IC $> 0.00$ and $\text{IC IR} > 0.00$.
3. **Gate 3 (Monotonic Quintiles):** $Q5 > Q1$ spread $> 0$.
4. **Gate 4 (Temporal Stability):** Signal persists across multiple economic regimes.
5. **Gate 5 (Untouched Test Performance):** Positive incremental return on frozen test data.
6. **Gate 6 (Economic Causality):** Documented, intuitive economic hypothesis.
7. **Gate 7 (Transaction Cost Resilience):** Net alpha survives 66.5 bps round-trip friction.
8. **Gate 8 (Net Portfolio Value-Add):** Empirically improves portfolio Sharpe vs baseline.

---

## 7. The V0.4 Decision Intelligence Framework

### 7.1 Normalized Additive Decision Function ($\text{ArthScore}$)

V0.4 abandons opaque multiplicative scoring in favor of a transparent, bounded additive framework:

$$\boxed{\text{ArthScore}_i = \left( w_F F_i + w_M M_i + w_E E_i + w_R R_i + w_H H_i \right) \times \text{Agreement}_i}$$

Where:
- $F_i$: Fundamental Business Quality Pillar $\in [0, 100]$ (Weight $w_F = 0.30$)
- $M_i$: Valuation & Margin-of-Safety Pillar $\in [0, 100]$ (Weight $w_M = 0.25$)
- $E_i$: Earnings Growth & Acceleration Pillar $\in [0, 100]$ (Weight $w_E = 0.20$)
- $R_i$: Capital Preservation & Downside Risk Pillar $\in [0, 100]$ (Weight $w_R = 0.15$)
- $H_i$: Calibrated ML Alpha Conviction $\in [0, 100]$ (Weight $w_H = 0.10$)

### 7.2 Cross-Pillar Signal Agreement Mechanism

To prevent aggressive tilts when fundamentals and quantitative momentum diverge:

$$\text{Divergence}_i = \frac{|F_i - H_i|}{100}$$

$$\text{Agreement}_i = \max\left(0.50, \, 1.0 - \left(\alpha_{\text{agreement}} \times \text{Divergence}_i\right)\right) \quad (\text{Default } \alpha_{\text{agreement}} = 0.30)$$

When Fundamental Quality is 90 but ML Conviction is 20, the divergence ($0.70$) applies a penalty factor of $0.79$, dampening the score and preventing capital misallocation.

### 7.3 Candidate Signal Zoo (Candidates 1, 2, and 3)

- **Candidate 1 (Fundamentals Only):** Features `[roe_5yr, roce_5yr, debt_equity]`. Pure long-term compounding.
- **Candidate 2 (Fundamentals + Momentum):** Features `[roe_5yr, roce_5yr, debt_equity, momentum_6_12_1, dist_from_52w_high, risk_adjusted_momentum]`. Filters out stagnant value traps.
- **Candidate 3 (Fundamentals + Sentiment):** Features `[roe_5yr, roce_5yr, debt_equity, news_sentiment]`. Provides early shock resistance.

### 7.4 Multi-Horizon Decay Analysis (30D to 252D)

Signals are tracked across 5 holding periods to identify where alpha peaks:
- **30 Days:** Captures short-term post-earnings announcement drift (PEAD).
- **60 Days:** Transition window.
- **90 Days:** Quarterly corporate disclosure cycle (Default cadence).
- **180 Days / 252 Days:** Multi-quarter fundamental compounding horizon.

### 7.5 Shadow Portfolio Tracking & Real-Time Slippage Monitoring

Every rebalance recommendation generates a persistent shadow tracking record in `shadow_portfolio_records`. As live market ticks arrive, the shadow engine logs:
- Theoretical execution price vs. actual market open.
- Realized execution slippage.
- Portfolio drift relative to target HRP weights.

---

## 8. Backend API & Service Infrastructure

### 8.1 Technology Stack & Directory Structure

- **Runtime:** Python 3.11+
- **Web Framework:** FastAPI with Uvicorn ASGI server
- **Data Validation:** Pydantic v2
- **Data Science Core:** NumPy, SciPy, Pandas, Scikit-Learn, LightGBM, XGBoost
- **Database:** SQLite 3 (WAL mode) with automated SQL migration runner

```
invst/backend/
├── app/
│   └── streamlit_app.py          # Legacy Python UI
├── config/
│   ├── settings.yaml             # Core operational settings & thresholds
│   ├── scoring_weights.yaml      # Multi-factor weights
│   └── sectors.yaml              # Sector mappings & caps
├── db/
│   ├── migrations/               # Incremental SQL migrations
│   ├── seed/                     # Nifty 500 constituents CSVs
│   └── migrate.py                # Schema migration executor
├── src/invst/
│   ├── api/                      # REST endpoints & schemas
│   ├── backtest/                 # Walk-forward backtest simulation engine
│   ├── data_access.py            # PointInTimeDataAccess abstraction
│   ├── execution/                # Shadow portfolio & broker bridge
│   ├── ingestion/                # Bhavcopy, filings, macro parsers
│   ├── ml/                       # Features, classifier, diagnostics, ranking
│   ├── monitoring/               # Data quality, PIT audits, drift
│   ├── optimization/             # HRP optimizer & caps
│   ├── portfolio/                # User portfolio health tracking
│   ├── reporting/                # Plain-English rationales & PDF generation
│   └── scoring/                  # BQS, Growth, Valuation, Risk, Composite V2
└── tests/                        # 97+ automated pytest test suite
```

### 8.2 Security, Cryptographic Authentication & RBAC

- **Password Hashing:** PBKDF2 with SHA-256 HMAC (600,000 iterations) or BCrypt with automatic salting.
- **Timing-Safe Comparison:** `hmac.compare_digest` prevents side-channel timing attacks.
- **Session Tokens:** 256-bit cryptographically secure bearer tokens (`secrets.token_urlsafe(32)`).
- **Role-Based Access Control (RBAC):** `admin` (user management, model retraining) and `user` (portfolio tracking, recommendations).

### 8.3 RESTful Endpoint Specifications & Schemas

| Endpoint | Method | Role | Description |
| :--- | :---: | :--- | :--- |
| `/api/auth/login` | POST | Public | Authenticates credentials and returns bearer token |
| `/api/dashboard` | GET | Authenticated | Portfolio summary, market regime, top holdings |
| `/api/recommendations` | GET | Authenticated | Latest quarterly V0.2 scorecards and target allocations |
| `/api/stock/{symbol}` | GET | Authenticated | Deep-dive factor diagnostics, historical financials, scenario trees |
| `/api/backtest/run` | POST | Authenticated | Executes walk-forward simulation across specified date range |
| `/api/health` | GET | Authenticated | Data quality report, PIT audit invariants, model calibration |
| `/api/ml/status` | GET | Authenticated | Registry state, Promotion Gate scorecard, Rank IC trends |
| `/api/ml/train` | POST | Admin | Triggers expanding walk-forward retraining job |
| `/api/portfolio/custom` | POST | Authenticated | Creates and tracks user's actual broker positions |

### 8.4 Automated Plain-English Rationale Generation & PDF Reporting

The rationale generator compiles quantitative metrics into structured, institutional prose:

```
[STOCK]: RELIANCE INDUSTRIES (RELIANCE) — Energy Archetype
[SCORE]: Investment Score: 78 / 100 | Business Score: 82 / 100 | Matrix: Core Compounding Alpha
[THESIS]:
Reliance demonstrates superior capital efficiency with 5-year average ROCE of 16.2% 
and operating margin resilience. Valuation is compelling with TTM P/E trading 1.1σ below 
its 3-year sector median. Free cash flow generation comfortably covers debt servicing 
with Interest Coverage at 5.4x.

[KEY RISKS & HEADWINDS]:
Downside sensitivity to global refining margin contraction and telecommunications 
capex expansion cycle.

[INVALIDATION CRITERIA]:
ROCE degradation > 250 bps or gross debt-to-equity exceeding 0.85x.
```

---

## 9. Frontend Client Architecture (React 19 + TypeScript + Tailwind CSS)

### 9.1 Obsidian Dark Design System & Visual Tokens

The frontend uses a custom-tailored institutional dark theme:
- **Backgrounds:** Deep Obsidian Black (`#040508`), Card Glass (`#0b0f17` with 70% opacity and `backdrop-blur-md`).
- **Accent Primaries:** Winsor Blue (`#1d4ed8`), Sky Cyan (`#0284c7`).
- **Status Indicators:** Emerald Alpha (`#10b981`), Amber Warning (`#f59e0b`), Crimson Drawdown (`#ef4444`).
- **Typography:** Tabular monospace numerals (`font-mono tracking-tight`) for financial data grids.

### 9.2 Real-Time Navigation, IST Monospace Clock & Live Ticker Marquee

- **Header Bar:** Displays current Indian Standard Date alongside a live ticking IST digital clock (`hh:mm:ss A IST`).
- **Market Ticker:** Infinite CSS marquee displaying real-time ticks for Nifty 50, Sensex, Bank Nifty, India VIX, Brent Crude, USD/INR, and 10Y G-Sec with pulsing radio broadcast beacon.

### 9.3 The Five Core Analytical Modules

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      FIVE CORE FRONTEND MODULES                         │
├─────────────────┬─────────────────┬─────────────────────────────────────┤
│ 1. Stock Ideas  │ QuickPicks      │ Configurable Top-N slider (1-50)    │
│                 │ Matrix Grid     │ Cross-sectional factor heatmaps     │
│                 │ Capital Calc    │ Integer share sizing for ₹500-₹10L  │
├─────────────────┼─────────────────┼─────────────────────────────────────┤
│ 2. Lens         │ Factor Dials    │ BQS, Valuation, Risk, Sentiment     │
│                 │ Scenarios       │ Bull / Base / Bear probability tree │
│                 │ Quant Thesis    │ Plain-English institutional summary │
├─────────────────┼─────────────────┼─────────────────────────────────────┤
│ 3. Vault        │ Asset Donut     │ SVG interactive sector breakdown    │
│                 │ Risk Caps       │ Max 25% single-stock, 40% sector    │
│                 │ Friction Calc   │ Round-trip STT and slippage buffer  │
├─────────────────┼─────────────────┼─────────────────────────────────────┤
│ 4. Pulse        │ Quant Radar     │ Interactive SVG cluster constellation│
│                 │ Thematic Baskets│ AI Tech, Clean Capex, Defense, Banks│
├─────────────────┼─────────────────┼─────────────────────────────────────┤
│ 5. Edge         │ Event Feed      │ Streaming audit trail of disclosures│
│                 │ PIT Badges      │ Verified exchange timestamp tags    │
│                 │ Score Deltas    │ Real-time factor adjustments        │
└─────────────────┴─────────────────┴─────────────────────────────────────┘
```

---

## 10. Walk-Forward Backtesting & Performance Analytics

### 10.1 Walk-Forward Simulation Loop

```python
# Pseudocode of the Walk-Forward Loop
for rebalance_date in quarterly_dates(start_date, end_date):
    # 1. Obtain point-in-time universe
    pit = PointInTimeDataAccess(conn, asof=rebalance_date)
    universe = pit.get_universe()
    
    # 2. Compute multi-stage quantitative scores
    scorecards = compute_scorecards_v2(pit, symbols=universe)
    
    # 3. Filter top candidates
    shortlist = scorecards[:top_n]
    
    # 4. Extract rolling 3-year covariance matrix
    cov_matrix = pit.get_rolling_covariance(shortlist, lookback_days=756)
    
    # 5. Optimize weights via HRP with 25% stock / 40% sector caps
    hrp_result = compute_hrp_weights(cov_matrix)
    
    # 6. Execute fill at next-day open price (t + 1)
    fill_prices = pit.get_open_prices(rebalance_date + 1)
    
    # 7. Deduct transaction friction (66.5 bps)
    portfolio.rebalance(hrp_result.weights, fill_prices, friction_bps=66.5)
    
    # 8. Mark-to-market daily until next quarterly rebalance
    portfolio.mark_to_market_daily(rebalance_date, next_rebalance_date)
```

### 10.2 Mathematical Metric Formulations

$$\text{CAGR} = \left( \frac{\text{Equity}_{\text{end}}}{\text{Equity}_{\text{start}}} \right)^{\frac{1}{\text{Years}}} - 1$$

$$\text{Sharpe} = \frac{\mu_{R_p - R_f}}{\sigma_{R_p}} \times \sqrt{252} \quad (\text{Benchmark } R_f = \text{RBI 91-Day T-Bill})$$

$$\text{Sortino} = \frac{\mu_{R_p - R_f}}{\sigma_{\text{downside}}} \times \sqrt{252}, \quad \text{where } \sigma_{\text{downside}} = \sqrt{\frac{1}{N} \sum \min(0, R_p - R_f)^2}$$

$$\text{Max Drawdown} = \min_{t} \left( \frac{\text{Equity}_t - \max_{\tau \le t} \text{Equity}_\tau}{\max_{\tau \le t} \text{Equity}_\tau} \right)$$

$$\text{Annualized Turnover} = \frac{1}{2 \times \text{Years}} \sum_{t=1}^{T} \sum_{i} |w_{i, t} - w_{i, t^-}|$$

---

## 11. Monitoring, Data Quality & Operational Runbooks

### 11.1 Daily Data Quality Invariant Checks
1. **Row Count Verification:** NSE Bhavcopy file must contain $> 1,500$ rows.
2. **Missing Symbol Alert:** Every Nifty 500 constituent must have a valid close price for trading day $t$.
3. **Price Jump Anomaly Filter:** Any single-day price movement $> \pm 30\%$ without a corresponding stock split or bonus issue in corporate actions triggers an immediate halt and manual review.

### 11.2 Weekly Point-in-Time Audit Engine
Runs every Sunday at 02:00 IST to assert:
- $\forall \text{ rows in } \text{fundamentals\_quarterly}: \text{disclosed\_at} \le \text{CURRENT\_DATE}$.
- $\forall \text{ rows}: \text{disclosed\_at} \ge \text{period\_end} - 14\text{ days}$.
- Re-running the identical backtest configuration JSON reproduces the exact CAGR, Sharpe, and Drawdown to 4 decimal places.

### 11.3 Population Stability Index (PSI) & Concept Drift Detection

$$PSI = \sum_{k=1}^{K} \left( \text{Actual}_k - \text{Expected}_k \right) \times \ln\left(\frac{\text{Actual}_k}{\text{Expected}_k}\right)$$

- $PSI < 0.10$: Stable distribution; no action needed.
- $0.10 \le PSI \le 0.25$: Moderate drift; log warning.
- $PSI > 0.25$: Significant population drift; triggers automatic retrain recommendation and notifies admin.

### 11.4 Cron Automation Schedules

```cron
# /etc/cron.d/arthiq-ops
# 1. Daily Bhavcopy Ingestion (Mon-Fri 18:30 IST)
30 18 * * 1-5 arthiq cd /opt/arthiq/backend && python3 -m invst.cli ingest --daily >> /var/log/arthiq/ingest.log 2>&1

# 2. Daily Data Quality Audit (Mon-Fri 19:30 IST)
30 19 * * 1-5 arthiq cd /opt/arthiq/backend && python3 -m invst.cli monitor --dq >> /var/log/arthiq/dq.log 2>&1

# 3. News Sentiment Scraper (Daily at 09:00, 13:00, 17:00, 21:00 IST)
0 9,13,17,21 * * * arthiq cd /opt/arthiq/backend && python3 -m invst.cli ingest --news >> /var/log/arthiq/news.log 2>&1

# 4. Weekly Point-in-Time Zero-Lookahead Audit (Sun 02:00 IST)
0 2 * * 0 arthiq cd /opt/arthiq/backend && python3 -m invst.cli monitor --pit >> /var/log/arthiq/pit_audit.log 2>&1
```

---

## 12. End-to-End Build Blueprint: From Zero to Production

Follow these exact operational steps to rebuild and run the entire ArthIQ platform from scratch on a clean system:

### Step 1: Directory Setup & Python Virtual Environment
```bash
# Create project root directory
mkdir -p arthiq && cd arthiq

# Clone repository or initialize structure
git init

# Setup backend environment
cd backend
python3.11 -m venv venv
source venv/bin/activate

# Install locked dependencies
pip install --upgrade pip setuptools wheel
pip install fastapi uvicorn pydantic pyyaml numpy scipy pandas scikit-learn
# Optional tree boosters (or rely on built-in regularized logistic fallback)
pip install lightgbm xgboost
# Testing & linting
pip install pytest pytest-cov ruff httpx
```

### Step 2: Database Migration & Static Universe Seeding
```bash
# Initialize SQLite database with Write-Ahead Logging & core tables
python3 -m invst.db.migrate

# Seed historical Nifty 500 constituents and sector mappings
python3 scripts/seed_constituents.py

# Verify database integrity
sqlite3 db/invst.db "PRAGMA journal_mode;" # Returns: wal
sqlite3 db/invst.db "SELECT count(*) FROM index_constituents_history;"
```

### Step 3: Core Quantitative & Data Access Implementation
1. Copy or implement `src/invst/data_access.py` (`PointInTimeDataAccess`).
2. Implement Stage 0 screening filters in `src/invst/scoring/filters.py`.
3. Implement Business Quality (`quality.py`), Valuation (`valuation_v2.py`), and Risk (`risk_v2.py`).
4. Implement the Level 1/Level 2 synthesis in `src/invst/scoring/composite_v2.py`.
5. Implement the HRP optimizer in `src/invst/optimization/hrp.py`.

### Step 4: Machine Learning Pipeline & Diagnostics Suite
1. Implement point-in-time feature extraction in `src/invst/ml/features.py`.
2. Implement calibrated classifier and Platt scaling in `src/invst/ml/classifier.py`.
3. Implement walk-forward diagnostic scripts (`src/invst/ml/diagnostics.py`).
4. Execute diagnostic validation script to verify Gate 1-8 evaluations:
```bash
python3 scripts/run_v031_diagnostics.py
```

### Step 5: FastAPI REST Backend Implementation
```bash
# Launch FastAPI development server
uvicorn invst.api.app:app --host 0.0.0.0 --port 8000 --reload
# Verify OpenAPI documentation is live at: http://localhost:8000/docs
```

### Step 6: Vite + React 19 Frontend Deployment
```bash
cd ../frontend

# Install node dependencies
npm install

# Build production assets
npm run build

# Or launch local hot-reloading development server
npm run dev -- --port 5173
```

### Step 7: Verification Suite Execution
```bash
cd ../backend
# Execute complete unit and integration test suite (must pass 100%)
pytest tests/ -v
```

---
*End of Master Architecture Blueprint.*
