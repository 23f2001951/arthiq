# ArthIQ Platform Master Architecture & Implementation Blueprint
> **The Definitive Engineering and Quantitative Specification for Building the Platform from Scratch**  
> **Platform Name:** ArthIQ (`arthiq`) | **Version:** V0.5 Unified Multi-Asset Institutional Reference  
> **Universe:** Indian Listed Equities (NSE/BSE Nifty 500) & Indian Mutual Funds (AMFI Scheme Universe)  
> **Cadence:** Quarterly Rebalance (Equities) & Monthly Execution Tracking (SIPs / Mutual Funds)  
> **Author/Owner:** Quantitative Investment Decision Engine Architecture

---

## Table of Contents
1. [Executive Summary & Platform Scope](#1-executive-summary--platform-scope)
2. [Unified System Architecture & Data Flow](#2-unified-system-architecture--data-flow)
3. [Dual-Engine Persistence & Zero-Lookahead Data Architecture](#3-dual-engine-persistence--zero-lookahead-data-architecture)
   - 3.1 Dual Database Engine: SQLite WAL & Neon PostgreSQL Adaptation
   - 3.2 Complete Relational Database Schema (All 14 Tables & Indexes)
   - 3.3 Zero-Lookahead Point-in-Time (PIT) Data Access Layer (`PointInTimeDataAccess`)
   - 3.4 AMFI Mutual Fund Ingestion & Historical NAV Engine
4. [Equities Quantitative Factor & Scoring Engines](#4-equities-quantitative-factor--scoring-engines)
   - 4.1 Stage 0: Universe Screening & Liquidity Filtering
   - 4.2 Decoupled Two-Level Architecture: Business Score vs. Investment Score
   - 4.3 Sector Archetypes & Cross-Sectional Normalization
   - 4.4 Scenario Analysis & Probabilistic Return Trajectories
   - 4.5 Event Intelligence & Dynamic Factor Deltas
   - 4.6 The 2x2 Investment Matrix Quadrants
5. [Equities Portfolio Optimization & Indian Execution Friction](#5-equities-portfolio-optimization--indian-execution-friction)
   - 5.1 Hierarchical Risk Parity (HRP) Mathematical Derivation
   - 5.2 Tree Dendrogram Clustering & Quasi-Diagonalization
   - 5.3 Recursive Bisection & Investor Profile Caps (Conservative, Moderate, Aggressive)
   - 5.4 Whole-Share Integer Allocation & Real-World Indian Friction (66.5 bps)
6. [Equities Machine Learning Pipeline & The V0.3.1 Diagnostic Discovery](#6-equities-machine-learning-pipeline--the-v031-diagnostic-discovery)
   - 6.1 The 24-Dimensional Point-in-Time Feature Store
   - 6.2 Target Formulation & Expanding Walk-Forward Sequence
   - 6.3 Boosted Tree Calibration (Platt Scaling vs Isotonic)
   - 6.4 The V0.3.1 Diagnostic Revelation: Standalone ML Falsification
   - 6.5 Systematic Signal Inversion & Quintile Spread ($Q1 > Q5$)
   - 6.6 Feature Group Ablation & The Fundamentals-Only Alpha Discovery
   - 6.7 The 8 Institutional Model Promotion Gates
7. [The V0.4 Decision Intelligence Architecture](#7-the-v04-decision-intelligence-architecture)
   - 7.1 Normalized Additive Decision Function ($\text{ArthScore}$)
   - 7.2 Cross-Pillar Signal Agreement Mechanism
   - 7.3 Candidate Signal Zoo (Candidates 1, 2, and 3)
   - 7.4 Multi-Horizon Decay Analysis (30D to 252D)
   - 7.5 Shadow Portfolio Execution & Real-Time Tracking
8. [Mutual Fund Intelligence, Analytics & Advisory Engine](#8-mutual-fund-intelligence-analytics--advisory-engine)
   - 8.1 Quantitative Performance Metrics (CAGR, Rolling Returns Distributions)
   - 8.2 Risk-Adjusted Ratios (Sharpe, Sortino, Treynor, Jensen's Alpha, Beta, Capture Ratios)
   - 8.3 Robust Cashflow-Based XIRR Solver (Newton-Raphson & Bisection)
   - 8.4 Cross-Fund Portfolio Stock Overlap Matrix
   - 8.5 Goal-Based Advisory & Asset Allocation Profiling
   - 8.6 SIP Wealth Trajectory Compounder with Step-Up Modeling
   - 8.7 Capital Gains Tax Harvesting Analyzer (Finance Act 2024 LTCG/STCG)
9. [Multi-Asset Portfolio Health & Sizing Blotter](#9-multi-asset-portfolio-health--sizing-blotter)
   - 9.1 Position-Level Health Diagnosis (BUY MORE, HOLD, TRIM, EXIT SELL)
   - 9.2 Capital Delta & Share Adjustments
   - 9.3 Portfolio Aggregate Factor Scores & Multi-Horizon Projections (1Y, 3Y, 5Y)
10. [Backend REST API, Security & Distributed Infrastructure](#10-backend-rest-api-security--distributed-infrastructure)
    - 10.1 FastAPI Architecture & Directory Structure
    - 10.2 Cryptographic Authentication (PBKDF2-SHA256 & RFC 7519 JWT)
    - 10.3 Complete API Endpoint Catalog (Equities + Mutual Funds + Health)
    - 10.4 Automated Plain-English Rationale Generation & PDF Reports
11. [Modern Obsidian Frontend Client (React 19 + TypeScript + Vite)](#11-modern-obsidian-frontend-client-react-19--typescript--vite)
    - 11.1 Obsidian Dark Design System & Glassmorphism Tokens
    - 11.2 Live IST Monospace Clock & Ticker Tape Marquee
    - 11.3 Analytical Modules (Stock Ideas, Lens, Vault, Pulse, Edge, Mutual Funds, Health)
    - 11.4 Interactive Visualizations (Charts, Dials, Radar, Donut, Ladders)
12. [Walk-Forward Backtesting, Audits & Operational Runbooks](#12-walk-forward-backtesting-audits--operational-runbooks)
    - 12.1 Walk-Forward Simulation Engine & Performance Metrics
    - 12.2 Daily Data Quality Invariants & Weekly PIT Audits
    - 12.3 Automated Cron Schedules
13. [End-to-End Build Blueprint: From Zero to Full Deployment](#13-end-to-end-build-blueprint-from-zero-to-full-deployment)

---

## 1. Executive Summary & Platform Scope

**ArthIQ** is an institutional-grade, multi-asset quantitative investment decision-support engine engineered specifically for Indian equities (NSE/BSE Nifty 500 universe) and Indian Mutual Funds (AMFI universe). The platform systematically transforms unstructured financial disclosures, price feeds, macro indicators, and mutual fund portfolio disclosures into deterministic, risk-managed investment portfolios with plain-English rationales.

### Core Deliverables
1. **Direct Equity Decision Support:** Quarterly factor-ranked stock allocations using decoupled Business Quality and Valuation scoring, optimized via Hierarchical Risk Parity (HRP) with strict 25% single-stock and 40% sector caps.
2. **Mutual Fund & SIP Advisory:** Complete AMFI scheme database, rolling return distributions, risk-adjusted ratios, cross-fund stock overlap matrices, goal-based portfolio generation, XIRR performance tracking, and capital gains tax harvesting under the Indian Finance Act 2024.
3. **Multi-Asset Portfolio Health Engine:** Real-time health diagnostic of the user's actual broker and mutual fund holdings, generating position-level rebalance instructions (BUY MORE / HOLD / TRIM / EXIT SELL).
4. **Empirically Audited Predictive ML:** Fully tested expanding walk-forward ML models governed by 8 institutional promotion gates, protecting the user from overfit black-box predictions.

---

## 2. Unified System Architecture & Data Flow

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                    FRONTEND LAYER                                      │
│                React 19 + TypeScript + Vite 6 + Tailwind CSS (Obsidian Glass)          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  │
│  │ Stock Ideas  │ │     Lens     │ │    Vault     │ │ Mutual Funds │ │  Portfolio   │  │
│  │ (QuickPicks) │ │ (Diagnostics)│ │ (HRP Alloc)  │ │ (SIP & XIRR) │ │ Health Lab   │  │
│  └──────▲───────┘ └──────▲───────┘ └──────▲───────┘ └──────▲───────┘ └──────▲───────┘  │
└─────────┼────────────────┼────────────────┼────────────────┼────────────────┼──────────┘
          │                │                │                │                │
          └────────────────┴────────┬───────┴────────────────┴────────────────┘
                                    │ Bearer Token HTTP/REST (JSON)
┌───────────────────────────────────▼────────────────────────────────────────────────────┐
│                                FASTAPI BACKEND SERVICE                                 │
│  ┌────────────────────────┐ ┌────────────────────────┐ ┌────────────────────────────┐  │
│  │  Equities Quant Engine │ │  Mutual Fund Engine    │ │   Portfolio Health Engine  │  │
│  │  • Business Score (BQS)│ │  • AMFI NAV & Rolling  │ │   • Position Actions       │  │
│  │  • Valuation & Risk V2 │ │  • Overlap Matrix      │ │   • Rebalance Shares       │  │
│  │  • HRP Optimizer & Caps│ │  • XIRR Solver & Taxes │ │   • Multi-Horizon Forecast │  │
│  └───────────▲────────────┘ └───────────▲────────────┘ └─────────────▲──────────────┘  │
│              │                          │                            │                 │
│              └──────────────────────────┼────────────────────────────┘                 │
│                                         │                                              │
│                        ┌────────────────▼────────────────┐                             │
│                        │   PointInTimeDataAccess & Engine│                             │
│                        │   (SQLite WAL / Neon PostgreSQL)│                             │
│                        └────────────────▲────────────────┘                             │
└─────────────────────────────────────────┼──────────────────────────────────────────────┘
                                          │ Parameterized Dialect-Adapted SQL
┌─────────────────────────────────────────▼──────────────────────────────────────────────┐
│                              PERSISTENCE & DATA STORAGE                                │
│       Local: SQLite 3 (WAL Mode, High Concurrency)  │  Cloud: Neon PostgreSQL          │
│  ┌─────────────────────────┐ ┌─────────────────────────┐ ┌──────────────────────────┐  │
│  │ daily_prices (OHLCV)    │ │ fundamentals_quarterly  │ │ index_constituents_hist  │  │
│  ├─────────────────────────┤ ├─────────────────────────┤ ├──────────────────────────┤  │
│  │ mf_schemes & nav_history│ │ mf_holdings (Portfolios)│ │ user_mf_portfolios & tx  │  │
│  ├─────────────────────────┤ ├─────────────────────────┤ ├──────────────────────────┤  │
│  │ users & user_portfolios │ │ model_predictions (ML)  │ │ shadow_portfolio_records │  │
│  └─────────────────────────┘ └─────────────────────────┘ └──────────────────────────┘  │
└─────────────────────────────────────────▲──────────────────────────────────────────────┘
                                          │ Scheduled Ingestion Jobs
┌─────────────────────────────────────────┴──────────────────────────────────────────────┐
│                             EXTERNAL DATA FEEDS & SOURCES                              │
│   NSE Bhavcopy (EOD)  │  BSE Bhavcopy  │  AMFI NAV Feed (Daily)  │  Yahoo Finance      │
│   Exchange Filings    │  News RSS      │  Macro Indicators (VIX) │  Static Seed Data   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Dual-Engine Persistence & Zero-Lookahead Data Architecture

### 3.1 Dual Database Engine: SQLite WAL & Neon PostgreSQL Adaptation

The persistence layer (`invst/backend/src/invst/db/engine.py`) provides unified connectivity across local and cloud environments:
- **Local Development / Pytest:** Zero-configuration SQLite 3 with Write-Ahead Logging (`PRAGMA journal_mode = WAL`) and sub-millisecond query performance.
- **Production / Cloud:** Neon Serverless PostgreSQL with connection pooling and SSL encryption.
- **Transparent Dialect Translation:**
  - Converts SQLite `?` parameter placeholders to PostgreSQL `%s`.
  - Replaces `INTEGER PRIMARY KEY AUTOINCREMENT` with `SERIAL PRIMARY KEY`.
  - Translates `INSERT OR REPLACE INTO table (...)` to PostgreSQL `INSERT INTO table (...) ON CONFLICT (pk_columns) DO UPDATE SET ...`.
  - Implements a dict-accessible row mapper compatible with `sqlite3.Row` across both database drivers.

### 3.2 Complete Relational Database Schema (All 14 Tables & Indexes)

```sql
-- 1. Point-in-Time Index Constituents History
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
    event_type       TEXT    NOT NULL,
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
    sentiment_score  REAL,
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
    action           TEXT    NOT NULL,
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

-- 10. Multi-User Authentication & Equities Portfolios
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

-- 11. Mutual Fund Schemes Master
CREATE TABLE IF NOT EXISTS mf_schemes (
    scheme_code      INTEGER PRIMARY KEY,
    isin             TEXT,
    scheme_name      TEXT    NOT NULL,
    fund_house       TEXT    NOT NULL,
    category         TEXT    NOT NULL,
    plan_type        TEXT    NOT NULL DEFAULT 'Direct',
    option_type      TEXT    NOT NULL DEFAULT 'Growth',
    benchmark_index  TEXT    DEFAULT 'Nifty 500 TRI',
    expense_ratio    REAL,
    aum_cr           REAL,
    fund_manager     TEXT,
    crisil_rating    INTEGER,
    risk_level       TEXT    DEFAULT 'Very High',
    inception_date   DATE,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_mf_category ON mf_schemes(category);
CREATE INDEX IF NOT EXISTS idx_mf_fund_house ON mf_schemes(fund_house);
CREATE INDEX IF NOT EXISTS idx_mf_isin ON mf_schemes(isin);

-- 12. Mutual Fund Daily NAV History
CREATE TABLE IF NOT EXISTS mf_nav_history (
    scheme_code      INTEGER NOT NULL,
    nav_date         DATE    NOT NULL,
    nav              REAL    NOT NULL,
    PRIMARY KEY (scheme_code, nav_date),
    FOREIGN KEY (scheme_code) REFERENCES mf_schemes(scheme_code) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_mf_nav_scheme_date ON mf_nav_history(scheme_code, nav_date DESC);

-- 13. Scheme Portfolio Holdings (Monthly Disclosures)
CREATE TABLE IF NOT EXISTS mf_holdings (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    scheme_code      INTEGER NOT NULL,
    as_of_date       DATE    NOT NULL,
    company_name     TEXT    NOT NULL,
    symbol           TEXT,
    isin             TEXT,
    sector           TEXT,
    weight_pct       REAL    NOT NULL,
    FOREIGN KEY (scheme_code) REFERENCES mf_schemes(scheme_code) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_mf_holdings_scheme ON mf_holdings(scheme_code, as_of_date);
CREATE INDEX IF NOT EXISTS idx_mf_holdings_symbol ON mf_holdings(symbol);

-- 14. User Mutual Fund Portfolios & SIP Schedules
CREATE TABLE IF NOT EXISTS user_mf_portfolios (
    id               TEXT    PRIMARY KEY,
    user_id          INTEGER NOT NULL,
    name             TEXT    NOT NULL DEFAULT 'My MF Portfolio',
    notes            TEXT,
    last_saved_at    TIMESTAMP,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mf_sip_schedules (
    id               TEXT    PRIMARY KEY,
    portfolio_id     TEXT    NOT NULL,
    scheme_code      INTEGER NOT NULL,
    folio_number     TEXT,
    amount           REAL    NOT NULL,
    frequency        TEXT    DEFAULT 'MONTHLY',
    sip_day          INTEGER DEFAULT 5,
    start_date       DATE    NOT NULL,
    end_date         DATE,
    status           TEXT    NOT NULL DEFAULT 'ACTIVE',
    step_up_pct      REAL    DEFAULT 0.0,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES user_mf_portfolios(id) ON DELETE CASCADE,
    FOREIGN KEY (scheme_code) REFERENCES mf_schemes(scheme_code)
);

CREATE TABLE IF NOT EXISTS mf_transactions (
    id               TEXT    PRIMARY KEY,
    portfolio_id     TEXT    NOT NULL,
    sip_id           TEXT,
    scheme_code      INTEGER NOT NULL,
    tx_date          DATE    NOT NULL,
    tx_type          TEXT    NOT NULL, -- 'BUY', 'SELL', 'SIP'
    amount           REAL    NOT NULL,
    units            REAL    NOT NULL,
    nav              REAL    NOT NULL,
    notes            TEXT,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES user_mf_portfolios(id) ON DELETE CASCADE,
    FOREIGN KEY (sip_id) REFERENCES mf_sip_schedules(id) ON DELETE SET NULL,
    FOREIGN KEY (scheme_code) REFERENCES mf_schemes(scheme_code)
);

CREATE TABLE IF NOT EXISTS mf_sip_checkins (
    id               TEXT    PRIMARY KEY,
    portfolio_id     TEXT    NOT NULL,
    sip_id           TEXT    NOT NULL,
    scheme_code      INTEGER NOT NULL,
    due_date         DATE    NOT NULL,
    status           TEXT    NOT NULL, -- 'PAID', 'SKIPPED', 'PENDING'
    confirmed_date   DATE,
    amount           REAL    NOT NULL,
    notes            TEXT,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES user_mf_portfolios(id) ON DELETE CASCADE,
    FOREIGN KEY (sip_id) REFERENCES mf_sip_schedules(id) ON DELETE CASCADE
);
```

### 3.3 Zero-Lookahead Point-in-Time (PIT) Data Access Layer

The `PointInTimeDataAccess` class guarantees zero lookahead leakage by clamping all time-series queries to `self.asof`:
- `get_price(symbol, on_or_before)` queries strictly `trade_date <= asof`.
- `get_fundamental(symbol, metric)` queries strictly `disclosed_at <= asof`, ordering by `disclosed_at DESC, period_end DESC LIMIT 1`.
- `get_universe()` queries `index_constituents_history` for stocks whose effective membership date preceded the simulated rebalance.

### 3.4 AMFI Mutual Fund Ingestion & Historical NAV Engine

The mutual fund ingestion pipeline (`invst/backend/src/invst/ingestion/mf_ingestion.py`):
1. Downloads the official daily AMFI NAV master file (`https://www.amfiindia.com/spages/NAVAll.txt`).
2. Parses semicolon-delimited scheme lines: `Scheme Code;ISIN Div Payout/ISIN Growth;ISIN Div Reinvestment;Scheme Name;Net Asset Value;Date`.
3. Filters for **Direct-Growth** plans to evaluate pure fund-manager alpha free of intermediary distributor commissions.
4. Categorizes funds using regex classification across 8 standardized SEBI categories:
   - Equity: Large Cap, Mid Cap, Small Cap, Flexi Cap, ELSS (Tax Saving).
   - Hybrid: Balanced Advantage (BAF), Aggressive Hybrid.
   - Debt: Liquid, Short Duration.

---

## 4. Equities Quantitative Factor & Scoring Engines

### 4.1 Stage 0: Universe Screening & Liquidity Filtering

Filters the Nifty 500 down to an investable universe (~350–470 names):
1. 30-Day Median Daily Traded Value $\ge ₹5.00\text{ Crore}$.
2. Point-in-Time Market Capitalization $\ge ₹1,000\text{ Crore}$.
3. Listing Tenure on NSE/BSE $\ge 3.0\text{ Years}$ (12 quarters of filings).
4. Minimum Share Price $\ge ₹10.00$ (Eliminates micro-penny manipulation).
5. Promoter Shareholding $\le 75.0\%$ (SEBI minimum public float compliance).
6. Data Completeness: $\ge 10$ of the last 12 quarters reported.

### 4.2 Decoupled Two-Level Architecture: Business Score vs. Investment Score

```
┌────────────────────────────────────────────────────────────────────────┐
│ LEVEL 1: BUSINESS SCORE (Enterprise Durability & Moat Depth)          │
│ Formula: 0.60 * Business Quality Score (BQS) + 0.40 * Growth Score     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ LEVEL 2: INVESTMENT SCORE (Attractiveness of Purchasing Today)         │
│ Formula: 0.40 * Business Score + 0.35 * Valuation + 0.25 * Risk        │
│ (Down-weighted by 10% if Market Execution / Liquidity is unfavorable)  │
└────────────────────────────────────────────────────────────────────────┘
```

#### A. Business Quality Score (BQS) Formulation
- **Capital Allocation (35%):** 5-Year median ROCE and ROE.
- **Operating Margin Stability (25%):** $1.0 - \min(1.0, \sigma_{\text{OPM}} / \mu_{\text{OPM}})$.
- **Balance Sheet Resilience (25%):** $1 / (1 + \text{Debt-to-Equity})$. Penalized if Interest Coverage $< 3.0\times$.
- **Modified Sloan Accrual Penalty (15%):**
  $$\text{Accrual Ratio} = \frac{\text{Net Income} - \text{CFO}}{\text{Total Assets}}$$
  Penalizes aggressive paper revenues: $-15.0$ pts if ratio $> +0.10$; $+5.0$ pts if ratio $< -0.02$.
- **Governance Deductions:** Promoter pledge $> 20\%$ or auditor qualified opinion immediately caps $\text{BQS} \le 35.0$.

#### B. Valuation Engine & Reverse-DCF Solver
Transforms multiples into monotonic yields: $\text{Earnings Yield} = \frac{100}{\text{PE}_{TTM}}$ and $\text{FCF Yield} = \frac{\text{FCF}}{\text{Market Cap}} \times 100$.

Computes the 5-year annualized cash flow growth rate $g$ priced into market price $P_0$:
$$P_0 = \sum_{t=1}^5 \frac{\text{FCF}_0 \cdot (1 + g)^t}{(1 + \text{WACC})^t} + \frac{\text{FCF}_0 \cdot (1 + g)^5 \cdot (1 + g_t)}{(\text{WACC} - g_t) \cdot (1 + \text{WACC})^5}$$
Binary search across $g \in [-20\%, +60\%]$ with $\text{WACC} = 11.5\%$ and terminal growth $g_t = 5.0\%$.

### 4.3 Sector Archetypes & Cross-Sectional Normalization
- **Financials:** Net Interest Margin (NIM), GNPA %, NNPA %, P/ABV, ROA.
- **Industrials & Capex:** Order Book-to-Bill, Asset Turnover, Net Debt/EBITDA.
- **Consumer & Tech:** ROCE, Working Capital Days, FCF Yield, EV/Sales.
- All metrics are winsorized at $[5\%, 95\%]$ and standardized within sector before cross-sector ranking:
  $$z_{i, s} = \frac{x_{i, s} - \mu_s}{\sigma_s}, \quad \text{Score}_i = \Phi(z_{i, s}) \times 100$$

### 4.4 Scenario Analysis & Probabilistic Return Trajectories
Projects 1-year forward expected returns across Bull, Base, and Bear scenarios based on market regime (India VIX):
$$\mathbb{E}[R] = p_{\text{bear}} R_{\text{bear}} + p_{\text{base}} R_{\text{base}} + p_{\text{bull}} R_{\text{bull}}$$

### 4.5 Event Intelligence & Dynamic Factor Deltas
Corporate announcements stream into an event parser that adjusts base factor scores dynamically (e.g., $+4.0$ Growth points on quarterly PAT beat $\ge +10\%$, $-15.0$ Governance points on auditor resignation).

### 4.6 The 2x2 Investment Matrix Quadrants
1. **Core Compounding Alpha:** High Quality ($\ge 65$) + Attractive Valuation ($\ge 50$).
2. **Quality Trap / Overpriced:** High Quality ($\ge 65$) + Stretched Valuation ($< 50$).
3. **Deep Value / Cyclical Rebound:** Low Quality ($< 65$) + Extreme Cheapness ($\ge 50$).
4. **Value Trap / Distressed:** Low Quality ($< 65$) + Cheap/Depressed Multiple ($< 50$).

---

## 5. Equities Portfolio Optimization & Indian Execution Friction

### 5.1 Hierarchical Risk Parity (HRP) Mathematical Derivation
HRP eliminates the instability of inverting the covariance matrix $\Sigma^{-1}$ by allocating risk down a hierarchical dendrogram tree.

### 5.2 Tree Dendrogram Clustering & Quasi-Diagonalization
1. **Distance Metric:** $d_{i, j} = \sqrt{\frac{1}{2} (1 - \rho_{i, j})}$.
2. **Clustering:** Single-linkage clustering computes cluster distance:
   $$D(u, v) = \min_{i \in u, j \in v} d_{i, j}$$
3. **Quasi-Diagonalization:** Reorganizes rows and columns of covariance $\Sigma$ so that highest correlations are positioned adjacent along the main diagonal.

### 5.3 Recursive Bisection & Investor Profile Caps
Cluster $C$ is bisected into $C_1$ and $C_2$:
$$V_k = w_k^T \Sigma_k w_k, \quad \text{where } w_k = \frac{\text{diag}(\Sigma_k)^{-1}}{\text{Tr}(\text{diag}(\Sigma_k)^{-1})}$$
$$\alpha_1 = 1 - \frac{V_1}{V_1 + V_2}, \quad W_{C_1} = W_C \times \alpha_1, \quad W_{C_2} = W_C \times (1 - \alpha_1)$$

#### Hard Investor Profile Caps:
- **Conservative:** Max 10% single-stock, 25% sector cap (16 target holdings).
- **Moderate (Default):** Max 15% single-stock, 35% sector cap (10 target holdings).
- **Aggressive:** Max 25% single-stock, 40% sector cap (8 target holdings).

### 5.4 Whole-Share Integer Allocation & Real-World Indian Friction
1. **Integer Share Floor-Sizing:** $\text{Shares}_i = \left\lfloor \frac{\text{Capital} \times w_i}{P_{i, \text{open}}} \right\rfloor$.
2. **Round-Trip Transaction Friction (66.5 bps):**
   - 10 bps STT on delivery purchase & sale.
   - 30 bps buy / 20 bps sell brokerage commission.
   - 1.5 bps stamp duty & exchange turnover fees.
   - 5 bps market impact slippage.
   - **Total 66.5 bps** explicitly subtracted from realized returns on every turnover rebalance.

---

## 6. Equities Machine Learning Pipeline & The V0.3.1 Diagnostic Discovery

### 6.1 The 24-Dimensional Point-in-Time Feature Store
Extracted strictly at market close on each rebalance date:
1. `composite_score`, `investment_score`, `business_score`, `growth_score`.
2. `roe_5yr`, `roce_5yr`, `debt_equity`.
3. `pe_ttm`, `pb`, `ev_ebitda`, `quality_to_valuation_ratio`.
4. `annualised_vol`, `beta`, `max_drawdown`, `downside_semivariance`.
5. `momentum_6_12_1`, `dist_from_52w_high`, `risk_adjusted_momentum`.
6. `news_sentiment` (FinBERT / VADER).
7. `macro_vix`, `macro_vix_change_30d`, `macro_usd_inr`.
8. `market_score`, `gross_npa_pct`.

### 6.2 Target Formulation & Expanding Walk-Forward Sequence
$$y_{i, t} = \mathbb{I}\left( R_{i, [t, t+90D]} - R_{\text{NIFTY500}, [t, t+90D]} > 0 \right)$$
Trained via expanding historical cross-sections with strictly zero data leakage.

### 6.3 Boosted Tree Calibration
LightGBM and XGBoost probability outputs are calibrated using **Platt Scaling** ($P(y=1|z) = \frac{1}{1 + \exp(Az + B)}$) to minimize Brier score and Expected Calibration Error (ECE).

### 6.4 The V0.3.1 Diagnostic Revelation: Standalone ML Falsification
The institutional audit tested the calibrated ML model against the permanently frozen untouched test window (2024–2026):
- **Development (2016–2020):** Baseline 8.34% vs ML **8.96%** (+0.62%)
- **Validation (2021–2023):** Baseline 0.25% vs ML **1.32%** (+1.07%)
- **Untouched Test (2024–2026):** Baseline **-0.02%** vs ML -1.27% (**-1.25% underperformance**)

> [!CAUTION]
> **Production Decision:** Standalone ML failed out-of-sample alpha verification and was rejected as the primary portfolio decision-maker. The deterministic engine remains the permanent baseline.

### 6.5 Systematic Signal Inversion & Quintile Spread
The full 24-feature ML model produced an inverted Spearman Rank IC of **-0.0909** and annualized Long/Short return of **-7.28%**:
```
Q1 (Lowest ML Probability):  +3.76% Mean Excess Return
Q2:                          +2.98%
Q3:                          +2.57%
Q4:                          +2.09%
Q5 (Highest ML Probability): +1.87%
Spread (Q5 - Q1):            -1.89% (Complete Inversion)
```
The reverse signal ($1 - P$) achieved a positive Rank IC of **+0.0909** and $+7.76\%$ L/S return.

### 6.6 Feature Group Ablation & The Fundamentals-Only Alpha Discovery
Controlled 8-subset ablation isolated the cause: **Balance sheet fundamentals hold genuine positive alpha**, while adding momentum and macro variables created destructive collinear interactions:

| Feature Subset Tested | Rank IC | IC IR | Positive Quarters | Annualized L/S Return |
| :--- | :---: | :---: | :---: | :---: |
| **Fundamentals Only (Set A: RoE, RoCE, D/E)** | **+0.0179** | **+0.07** | **60.0%** | **+4.99%** |
| Valuation Only | +0.0024 | +0.01 | 48.0% | -0.15% |
| Risk Only | +0.0311 | +0.17 | 64.0% | -2.24% |
| Momentum Only | -0.0163 | -0.06 | 52.0% | -4.71% |
| **Full 24 Features** | **-0.0909** | **-0.39** | **32.0%** | **-7.28%** |

### 6.7 The 8 Institutional Model Promotion Gates
Before any model can alter portfolio weights, it must pass 8 binary gates:
1. Zero lookahead PIT violations (100% pass across historical audits).
2. Positive Spearman Rank IC ($> 0.00$) and Information Ratio ($\text{IC IR} > 0.00$).
3. Monotonic cross-sectional quintiles ($Q5 > Q1$).
4. Multi-regime temporal stability.
5. Untouched test outperformance on frozen 2024–2026 data.
6. Documented causal economic mechanism.
7. Resilience after full transaction friction (66.5 bps).
8. Net empirical portfolio improvement vs baseline.

---

## 7. The V0.4 Decision Intelligence Architecture

### 7.1 Normalized Additive Decision Function ($\text{ArthScore}$)
$$\boxed{\text{ArthScore}_i = \left( 0.30 F_i + 0.25 M_i + 0.20 E_i + 0.15 R_i + 0.10 H_i \right) \times \text{Agreement}_i}$$
Where $F_i$ = Fundamental Quality, $M_i$ = Valuation Multiple, $E_i$ = Earnings Growth, $R_i$ = Capital Preservation, and $H_i$ = Calibrated ML Conviction.

### 7.2 Cross-Pillar Signal Agreement Mechanism
$$\text{Divergence}_i = \frac{|F_i - H_i|}{100}, \quad \text{Agreement}_i = \max\left(0.50, \, 1.0 - 0.30 \times \text{Divergence}_i\right)$$
Prevents capital allocation when short-term momentum and fundamental quality disagree.

### 7.3 Candidate Signal Zoo
- **Candidate 1 (Fundamentals Only):** Features `[roe_5yr, roce_5yr, debt_equity]`.
- **Candidate 2 (Fundamentals + Momentum):** Features `[roe_5yr, roce_5yr, debt_equity, momentum_6_12_1, dist_from_52w_high, risk_adjusted_momentum]`.
- **Candidate 3 (Fundamentals + Sentiment):** Features `[roe_5yr, roce_5yr, debt_equity, news_sentiment]`.

### 7.4 Multi-Horizon Decay Analysis (30D to 252D)
Signals are evaluated across 30D, 60D, 90D, 180D, and 252D horizons to isolate where predictive edge peaks.

### 7.5 Shadow Portfolio Execution & Real-Time Tracking
Tracks theoretical model allocations against realized market fills and logs execution slippage in `shadow_portfolio_records`.

---

## 8. Mutual Fund Intelligence, Analytics & Advisory Engine

### 8.1 Quantitative Performance Metrics
1. **Annualized CAGR:** $\text{CAGR} = \left(\frac{\text{NAV}_{\text{end}}}{\text{NAV}_{\text{start}}}\right)^{\frac{1}{\text{Years}}} - 1$.
2. **Rolling Returns Distribution:** Eliminates point-to-point recency bias by measuring returns starting on every single calendar day across 1Y, 3Y, and 5Y windows. Reports Mean, Median, 25th percentile, 75th percentile, and negative return probability.

### 8.2 Risk-Adjusted Performance Ratios
- **Sharpe Ratio:** $\frac{\mu(R_p - R_f)}{\sigma(R_p)} \times \sqrt{252}$ ($R_f = 6.5\%$ RBI 91-day T-Bill).
- **Sortino Ratio:** Measures return per unit of downside risk:
  $$\text{Sortino} = \frac{\mu(R_p - R_f)}{\sqrt{\frac{1}{N}\sum \min(0, R_p - R_f)^2}} \times \sqrt{252}$$
- **Treynor Ratio:** $\frac{\mu(R_p - R_f)}{\beta}$.
- **Jensen's Alpha:** $\alpha = R_p - [R_f + \beta (R_m - R_f)]$.
- **Upside / Downside Capture Ratios:** Measures performance relative to the benchmark during positive vs. negative benchmark months:
  $$\text{Up Capture} = \frac{\mu(R_{\text{fund}} | R_{\text{bench}} > 0)}{\mu(R_{\text{bench}} | R_{\text{bench}} > 0)} \times 100$$
  $$\text{Down Capture} = \frac{\mu(R_{\text{fund}} | R_{\text{bench}} < 0)}{\mu(R_{\text{bench}} | R_{\text{bench}} < 0)} \times 100$$

### 8.3 Robust Cashflow-Based XIRR Solver
Solves for the internal rate of return on irregular SIP and lump-sum cash flows:
$$\text{NPV}(r) = \sum_{i=1}^N \frac{C_i}{(1 + r)^{\frac{d_i - d_0}{365.25}}} = 0$$
Implemented using **Newton-Raphson** with exact first-derivative evaluation, falling back to **Brent's method (bisection)** across bracketed intervals `[(-0.95, 0.5), (0.0, 2.0), (1.0, 10.0)]` if gradient divergence occurs.

### 8.4 Cross-Fund Portfolio Stock Overlap Matrix
Calculates pairwise and portfolio-wide stock overlap across mutual funds:
$$\text{Overlap}(A, B) = \sum_{s \in A \cap B} \min\left(w_A(s), \, w_B(s)\right)$$
Identifies portfolio redundancy and aggregates underlying company exposures across multiple funds.

### 8.5 Goal-Based Advisory & Asset Allocation Profiling
Maps user goals and risk capacity to optimal category distributions:
- **Emergency Fund / Short Horizon (< 3 yrs):** 50% Liquid Debt, 50% Balanced Advantage.
- **Tax Saving (80C):** 60% ELSS, 40% Flexi Cap.
- **Conservative:** 50% Balanced Advantage, 30% Large Cap, 20% Passive Index.
- **Moderate (Balanced Growth):** 40% Flexi Cap, 30% Large Cap, 20% Balanced Advantage, 10% Mid Cap.
- **Aggressive Multi-Cap Alpha ($\ge 7$ yrs):** 35% Flexi Cap, 30% Mid Cap, 20% Small Cap, 15% Passive Index.

### 8.6 SIP Wealth Trajectory Compounder with Step-Up Modeling
Simulates wealth creation under compounding with an annual top-up percentage ($s\%$ annual step-up):
$$\text{SIP Month } m: \quad C_m = C_0 \times (1 + s)^{\lfloor (m - 1) / 12 \rfloor}$$

### 8.7 Capital Gains Tax Harvesting Analyzer (Finance Act 2024)
- **Equity Funds:**
  - **Short-Term Capital Gains (STCG, $< 12$ months):** Taxed at **20.0%**.
  - **Long-Term Capital Gains (LTCG, $\ge 12$ months):** Taxed at **12.5%** with annual exemption threshold of **₹1,25,000**.
- **Tax Harvesting Strategy:** Automatically identifies unrealized long-term gains up to ₹1,25,000 to sell and immediately repurchase, resetting cost basis tax-free.

---

## 9. Multi-Asset Portfolio Health & Sizing Blotter

The portfolio health engine (`invst/backend/src/invst/portfolio/health.py`) diagnoses user-provided stock and mutual fund holdings:
1. **Position Health Diagnosis:** Evaluates unrealized P&L, BQS, Valuation, Risk, and Investment scores to generate an action verdict:
   - `BUY_MORE`: High Quality + Margin of Safety + Undersized weight.
   - `HOLD`: Compounding within risk bounds.
   - `TRIM`: Weight exceeds risk caps (max 25% stock / 40% sector) or valuation is stretched.
   - `EXIT_SELL`: Critical governance redline, fundamental deterioration, or loss of moat.
2. **Capital Delta & Share Sizing:** Computes exact integer shares to buy/sell and cash required/unlocked.
3. **Multi-Horizon Wealth Projections:** Estimates portfolio value at 1-Year, 3-Year, and 5-Year horizons across Bull, Base, and Bear trajectories.

---

## 10. Backend REST API, Security & Distributed Infrastructure

### 10.1 FastAPI Architecture & Directory Structure
```
invst/backend/
├── src/invst/
│   ├── api/
│   │   ├── app.py          # FastAPI application factory & SPA routing
│   │   ├── auth.py         # PBKDF2-SHA256 & RFC 7519 JWT
│   │   ├── routes.py       # Equities & Portfolio REST endpoints
│   │   ├── mf_routes.py    # Mutual Fund REST endpoints
│   │   ├── schemas.py      # Equities Pydantic v2 schemas
│   │   └── mf_schemas.py   # Mutual Fund Pydantic v2 schemas
│   ├── db/
│   │   └── engine.py       # SQLite WAL & Neon PostgreSQL dual engine
│   ├── scoring/            # Scoring engines (Equities & MF)
│   ├── optimization/       # HRP optimizer
│   ├── ml/                 # Classifiers, ranking, diagnostics
│   ├── portfolio/          # Health diagnosis & MF portfolio service
│   ├── backtest/           # Walk-forward backtesting engine
│   └── monitoring/         # DQ checks & PIT audit engine
```

### 10.2 Cryptographic Authentication (PBKDF2-SHA256 & RFC 7519 JWT)
- **Password Hashing:** PBKDF2 with HMAC-SHA256, 600,000 iterations, random 16-byte cryptographic salt.
- **Timing-Safe Comparison:** `hmac.compare_digest` prevents timing analysis.
- **Zero-Dependency JWT:** Built-in RFC 7519 implementation using HS256 HMAC signatures with base64url encoding.
- **Role-Based Access Control (RBAC):** `admin` and `user` role enforcement on protected endpoints.

### 10.3 Complete API Endpoint Catalog

#### Equities & Core Endpoints:
- `POST /api/auth/login`: Authenticate and receive bearer JWT.
- `GET /api/dashboard`: Portfolio summary, market regime, top holdings.
- `GET /api/recommendations`: Latest quarterly scorecards, weights, matrix quadrants.
- `GET /api/stock/{symbol}`: Deep-dive factor scores, scenario projections, financials.
- `POST /api/backtest/run`: Execute walk-forward simulation across specified dates.
- `GET /api/health`: Data quality status, PIT audit invariants, drift alerts.
- `GET /api/portfolio/health`: Comprehensive health diagnosis of user's equity holdings.

#### Mutual Fund Endpoints:
- `GET /api/mf/schemes`: Search and filter AMFI schemes master.
- `GET /api/mf/schemes/{code}`: Scheme details, trailing returns, risk metrics.
- `GET /api/mf/schemes/{code}/nav`: Daily historical NAV time series.
- `GET /api/mf/schemes/{code}/rolling`: Rolling returns distribution (1Y, 3Y, 5Y).
- `GET /api/mf/compare`: Side-by-side fund comparison.
- `POST /api/mf/overlap`: Pairwise cross-fund portfolio stock overlap matrix.
- `POST /api/mf/recommend`: Goal-based mutual fund basket and asset allocation.
- `GET /api/mf/portfolios`: User mutual fund portfolios, holdings, and overall XIRR.
- `POST /api/mf/portfolios/{id}/transactions`: Record buy/sell/SIP transactions.
- `GET /api/mf/portfolios/{id}/tax-harvesting`: Realized & unrealized gains with ₹1.25L LTCG harvesting analyzer.

### 10.4 Automated Plain-English Rationale Generation & PDF Reports
Generates structured institutional prose for every recommendation:
- **Thesis:** Capital efficiency, earnings momentum, margin durability.
- **Valuation Context:** P/E vs 3Y sector median, reverse-DCF implied growth.
- **Key Risks:** Industry cyclicality, raw material exposure, leverage.
- **Invalidation Triggers:** Concrete thresholds (e.g., ROCE drop $> 250\text{ bps}$, D/E $> 0.85\times$) that mandate immediate liquidation.
- Exportable as print-friendly PDF via WeasyPrint / PDFKit.

---

## 11. Modern Obsidian Frontend Client (React 19 + TypeScript + Vite)

### 11.1 Obsidian Dark Design System & Glassmorphism Tokens
- **Backgrounds:** Deep Obsidian Black (`#040508`), Card Glass (`#0b0f17` with 70% opacity and `backdrop-blur-md`).
- **Accent Primaries:** Winsor Blue (`#1d4ed8`), Sky Cyan (`#0284c7`), Emerald (`#10b981`), Amber (`#f59e0b`), Crimson (`#ef4444`).
- **Numerals:** Monospace tabular formatting (`font-mono tracking-tight`).

### 11.2 Live IST Monospace Clock & Ticker Tape Marquee
- **Header:** Real-time ticking Indian Standard Time digital clock (`hh:mm:ss A IST`) alongside current Indian calendar date.
- **Market Ticker:** CSS infinite marquee displaying live market rates (Nifty 50, Sensex, Bank Nifty, India VIX, Crude Oil, USD/INR, 10Y G-Sec) with a pulsing radio broadcast beacon.

### 11.3 Analytical Modules
- **Stock Ideas:** QuickPicks slider (Top 1 to 50 equities), cross-sectional factor matrix heatmap, capital deployment calculator (₹500 to ₹10 Lakhs, whole shares).
- **Lens:** Factor magnifier radar, historical returns spectrum (1D to 1Y), scenario trees.
- **Vault:** Interactive SVG sector allocation donut, 25% stock / 40% sector cap enforcement, 66.5 bps friction calculator.
- **Pulse:** Interactive SVG thematic constellation radar (AI Tech, Clean Capex, Defense, Compounding Titans).
- **Edge:** Streaming audit feed of corporate disclosures with verified exchange timestamps.
- **Mutual Funds:** Scheme explorer, rolling returns visualizer, SIP wealth trajectory compounder, portfolio overlap analyzer, and tax-loss harvesting engine.
- **Portfolio Health:** Position-level health cards, rebalance sizing blotter, and multi-horizon forecasts.

---

## 12. Walk-Forward Backtesting, Audits & Operational Runbooks

### 12.1 Walk-Forward Simulation Engine & Performance Metrics
- **Quarterly Cadence:** Rebalances quarterly matching Indian corporate earnings cycles.
- **Metrics Computed:** CAGR, Sharpe Ratio, Sortino Ratio, Calmar Ratio, Annualized Turnover, Maximum Drawdown, Hit Rate vs Nifty 500 TRI.
- **Realistic Friction:** 66.5 bps round-trip transaction costs deducted on every rebalance.

### 12.2 Daily Data Quality Invariants & Weekly PIT Audits
- **Daily DQ:** Verifies Bhavcopy row count $> 1,500$, zero missing symbols in Nifty 500, and flags price jumps $> \pm 30\%$ without corporate action records.
- **Weekly PIT Audit:** Sunday 02:00 IST audit asserting `disclosed_at <= CURRENT_DATE` and verifying identical backtest reproducibility.

### 12.3 Automated Cron Schedules
```cron
# /etc/cron.d/arthiq-ops
# 1. Daily Bhavcopy Ingestion (Mon-Fri 18:30 IST)
30 18 * * 1-5 arthiq cd /opt/arthiq/backend && python3 -m invst.cli ingest --daily >> /var/log/arthiq/ingest.log 2>&1

# 2. Daily AMFI Mutual Fund NAV Ingestion (Daily 23:00 IST)
0 23 * * * arthiq cd /opt/arthiq/backend && python3 -m invst.cli ingest --mf >> /var/log/arthiq/mf_ingest.log 2>&1

# 3. Daily Data Quality Audit (Mon-Fri 19:30 IST)
30 19 * * 1-5 arthiq cd /opt/arthiq/backend && python3 -m invst.cli monitor --dq >> /var/log/arthiq/dq.log 2>&1

# 4. Weekly PIT Zero-Lookahead Audit (Sun 02:00 IST)
0 2 * * 0 arthiq cd /opt/arthiq/backend && python3 -m invst.cli monitor --pit >> /var/log/arthiq/pit_audit.log 2>&1
```

---

## 13. End-to-End Build Blueprint: From Zero to Full Deployment

Follow these exact operational steps to rebuild the entire platform from scratch:

```bash
# Step 1: Clone & Setup Backend Environment
git clone <repo_url> arthiq && cd arthiq/backend
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Step 2: Database Migration & Seeding
python3 -m invst.db.migrate
python3 scripts/seed_constituents.py

# Step 3: Market Data & Mutual Fund Ingestion
python3 -m invst.cli ingest --daily
python3 -m invst.cli ingest --mf

# Step 4: Verify Unit & Integration Tests (100% pass required)
pytest tests/ -v

# Step 5: Launch FastAPI Backend
uvicorn invst.api.app:app --host 0.0.0.0 --port 8000 --reload
# Verify Swagger documentation at: http://localhost:8000/docs

# Step 6: Setup & Launch Frontend Client
cd ../frontend
npm install
npm run build
npm run dev -- --port 5173
```

---
*End of ArthIQ Master Architecture & Implementation Blueprint.*
