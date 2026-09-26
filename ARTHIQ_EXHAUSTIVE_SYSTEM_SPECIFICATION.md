# ArthIQ Exhaustive System Specification & Quantitative Engineering Handbook
> **Complete Technical Reference for Mathematical Formulations, Code Logic, Data Engineering, and Decision Algorithms**
> **Platform:** ArthIQ (`arthiq`) | **Version:** V0.4 Institutional Reference Architecture  
> **Universe:** NSE/BSE Listed Equities (Nifty 500 Benchmark) | **Cadence:** Quarterly (Earnings-Aligned)  
> **Author:** Quantitative Engineering & Research Architecture

---

## Table of Contents

1. [Architectural Philosophy, Invariants & Design Principles](#1-architectural-philosophy-invariants--design-principles)
2. [End-to-End Data Pipeline & Point-in-Time (PIT) Ingestion Engine](#2-end-to-end-data-pipeline--point-in-time-pit-ingestion-engine)
   - 2.1 Ingestion Feeds & Parsing Logic
   - 2.2 Point-in-Time Mathematics & The Disclosure Barrier
   - 2.3 Complete Relational Database Schema (SQLite WAL & PostgreSQL DDL)
   - 2.4 The `PointInTimeDataAccess` Class Implementation
3. [Quantitative Factor Engines & Mathematical Scoring Logic](#3-quantitative-factor-engines--mathematical-scoring-logic)
   - 3.1 Stage 0: Universe Screening & Liquidity Filtering
   - 3.2 Stage 1 & Level 1: Business Score & Quality Mechanics (BQS & Growth)
   - 3.3 Stage 2 & Level 2: Valuation Engine & Reverse-DCF Solver
   - 3.4 Stage 3: Multi-Dimensional Risk & Contagion Redlines
   - 3.5 Sector Archetypes & Cross-Sectional Normalization
   - 3.6 Scenario Analysis & Probabilistic Return Trajectories
   - 3.7 Event Intelligence & Dynamic Factor Deltas
   - 3.8 The 2x2 Investment Matrix Quadrants
4. [Portfolio Construction & Real-World Execution Engine](#4-portfolio-construction--real-world-execution-engine)
   - 4.1 Hierarchical Risk Parity (HRP) Mathematical Derivation
   - 4.2 Dendrogram Clustering & Quasi-Diagonalization Algorithm
   - 4.3 Recursive Bisection Algorithm
   - 4.4 Hard Risk Caps & Dynamic Investor Profiles
   - 4.5 Integer Share Sizing & Indian Market Execution Friction
   - 4.6 ML-Tilted HRP Formulation ($\gamma$ Conviction Exponent)
5. [Machine Learning & Predictive Intelligence Engine](#5-machine-learning--predictive-intelligence-engine)
   - 5.1 The 24-Dimensional Point-in-Time Feature Store
   - 5.2 Target Formulation & Labeling Invariants
   - 5.3 Expanding Walk-Forward Cross-Validation Architecture
   - 5.4 Boosted Tree Classification & Probability Calibration
   - 5.5 The V0.3.1 Diagnostic Breakthrough & Signal Inversion Analysis
   - 5.6 Cross-Sectional Quintile Spread & 1-P Reverse Signal Diagnostic
   - 5.7 Feature Group Ablation & The Fundamentals-Only Alpha Discovery
   - 5.8 The 8 Institutional Model Promotion Gates
6. [The V0.4 Decision Intelligence Framework](#6-the-v04-decision-intelligence-framework)
   - 6.1 Normalized Additive Decision Function ($\text{ArthScore}$)
   - 6.2 Cross-Pillar Signal Agreement Mechanism
   - 6.3 Candidate Signal Suite (Candidates 1, 2, and 3)
   - 6.4 Multi-Horizon Decay Analysis (30D to 252D)
   - 6.5 Non-Parametric Bootstrap Confidence Intervals
   - 6.6 Shadow Portfolio Execution & Slippage Tracking
7. [Backend Service, Cryptographic Security & REST API](#7-backend-service-cryptographic-security--rest-api)
   - 7.1 Architecture & Directory Tree
   - 7.2 Zero-Dependency Cryptographic Authentication & RBAC
   - 7.3 Complete REST API Endpoints & Data Contracts
   - 7.4 Plain-English Investment Thesis Generation & PDF Reporting
8. [Frontend Client Architecture (React 19 + TypeScript + Tailwind)](#8-frontend-client-architecture-react-19--typescript--tailwind)
   - 8.1 Obsidian Dark Design System & Glassmorphism Tokens
   - 8.2 Live Monospace IST Clock & Persistent Ticker Marquee
   - 8.3 The Five Specialized Analytical Modules
   - 8.4 State Management, Session Lifecycle & API Client
9. [Walk-Forward Backtesting Engine & Performance Metrics](#9-walk-forward-backtesting-engine--performance-metrics)
   - 9.1 Simulation Loop Architecture
   - 9.2 Exact Financial Metric Formulations
   - 9.3 Transaction Fee Sensitivity Ladder
10. [Monitoring, Data Quality & Operational Runbooks](#10-monitoring-data-quality--operational-runbooks)
    - 10.1 Daily Data Quality Invariant Rules
    - 10.2 Weekly Point-in-Time Zero-Lookahead Audit
    - 10.3 Population Stability Index (PSI) & Drift Monitoring
    - 10.4 Cron Scheduling Specifications
11. [Step-by-Step Scratch Build Blueprint](#11-step-by-step-scratch-build-blueprint)

---

## 1. Architectural Philosophy, Invariants & Design Principles

### 1.1 The Core Problem in Retail and Semi-Institutional Investing
Retail and family-office investors in Indian equities face five structural disadvantages:
1. **Information Overload & Cognitive Fatigue:** Sifting through quarterly corporate filings, conference call transcripts, brokerage notes, and financial news leads to shallow heuristic decision-making.
2. **Lookahead & Survivorship Bias:** Popular financial portals evaluate historical performance using today's index constituents and restated earnings, leading to massive over-optimism.
3. **Conflation of Business Quality with Investment Attractiveness:** High-ROCE companies are frequently purchased at extreme valuations where 5-year expected returns are negligible or negative.
4. **Sub-Optimal Portfolio Sizing:** Conviction tilts are either excessive (single-name blowup risk) or overly diluted (index hugging), without mathematical risk parity.
5. **Execution Friction Denial:** Ignoring Securities Transaction Tax (STT), stamp duty, brokerage, and bid-ask slippage destroys theoretical backtest alpha.

### 1.2 Core Architectural Principles of ArthIQ
1. **Decision Support, Not Automated Execution:** ArthIQ generates mathematically backed target allocations and plain-English investment rationales. The user manually executes trades in their broker (Zerodha Kite, Groww, Upstox).
2. **Strict Point-in-Time (PIT) Anti-Lookahead Isolation:** Backtesting and live inference share the identical code path. If a corporate filing was disclosed on May 15, 2018, it is strictly invisible to any calculation dated May 14, 2018.
3. **Decoupled Quality vs. Price Valuation:** Enterprise durability (Business Quality) is evaluated price-agnostically before being synthesized with market valuation.
4. **Risk-First Portfolio Optimization (HRP):** Allocations are driven by correlation dendrograms and hierarchical inverse-variance bisection rather than volatile quadratic mean-variance inversion.
5. **Falsification-Driven Machine Learning:** Machine learning hypotheses are treated with scientific skepticism. Standalone predictive ML is never deployed unless it clears 8 strict institutional promotion gates.

---

## 2. End-to-End Data Pipeline & Point-in-Time (PIT) Ingestion Engine

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                INGESTION ARCHITECTURE                                  │
├───────────────────────┬────────────────────────┬───────────────────────────────────────┤
│ Source                │ Mechanism              │ Destination                           │
├───────────────────────┼────────────────────────┼───────────────────────────────────────┤
│ NSE Bhavcopy          │ HTTPS GET / CSV Parser │ `daily_prices`                        │
│ BSE Bhavcopy          │ HTTPS GET / Zip Parser │ `daily_prices` (BSE tickers)          │
│ yfinance              │ Python API (fallback)  │ `daily_prices`                        │
│ Exchange Filings      │ Scraper / XML / PDF    │ `fundamentals_quarterly`              │
│ News RSS Feeds        │ XML RSS Parsers        │ `news_sentiment`                      │
│ Macro Feeds (RBI/VIX) │ EOD Scraper            │ `daily_prices` (synthetic symbols)    │
│ Historical Index CSV  │ Static Seed File       │ `index_constituents_history`          │
└───────────────────────┴────────────────────────┴───────────────────────────────────────┘
```

### 2.1 Ingestion Feeds & Parsing Logic

#### A. NSE Bhavcopy Ingestion (`nse_bhavcopy.py`)
- **URL Pattern:** `https://archives.nseindia.com/content/historical/EQUITIES/{YYYY}/{MMM}/cm{DD}{MMM}{YYYY}bhav.csv.zip`
- **Schedule:** Monday–Friday at 18:30 IST.
- **Filter Invariant:** Only rows where `SERIES == 'EQ'` are ingested. Series such as `BE` (book entry), `BZ` (blacklisted), and `SM` (SME) are handled according to surveillance guidelines.
- **Deduplication:** Uses `INSERT OR REPLACE INTO daily_prices (symbol, trade_date, open, high, low, close, adj_close, volume, source)` with primary key `(symbol, trade_date, source)`.

#### B. Corporate Filings Ingestion (`fundamentals_filings.py`)
- Financial results (Standalone and Consolidated) are parsed for core line items: Revenue from Operations, Operating Profit (EBITDA), Profit Before Tax (PBT), Profit After Tax (PAT / Net Income), Cash Flow from Operations (CFO), Total Assets, Total Debt, Net Worth, and Share Capital.
- **Critical Timestamping:** Every record stores both `period_end` (e.g., `2023-03-31`) and `disclosed_at` (e.g., `2023-05-18`).

#### C. Macroeconomic Indicators (`macro.py`)
- Synthetic symbols are inserted into `daily_prices` to allow unified time-series queries:
  - `INDIA_VIX`: NSE Implied Volatility Index.
  - `USD_INR`: Currency exchange rate.
  - `BRENT_CRUDE`: Global crude oil price in USD/bbl.
  - `IN_10Y_GSEC`: Indian 10-Year Government Bond benchmark yield.

### 2.2 Point-in-Time Mathematics & The Disclosure Barrier

In a historical backtest evaluating a stock on rebalance date $T_{\text{asof}}$, any query for fundamental metric $M$ must satisfy:

$$\text{Value}(M, S, T_{\text{asof}}) = \operatorname*{arg\,max}_{r.\text{disclosed\_at}} \left\{ r.\text{value} \;\middle|\; r.\text{symbol} = S \land r.\text{metric} = M \land r.\text{disclosed\_at} \le T_{\text{asof}} \right\}$$

#### Mathematical Safeguards:
1. **No Future Price Leakage:** 
   $$\forall p \in \text{Prices}(S), \quad t_{\text{trade}} \le T_{\text{asof}}$$
2. **Survivorship Bias Elimination:** The universe at date $T$ is dynamically queried from index constituents:
   $$\text{Universe}(T) = \left\{ S \;\middle|\; \exists (S, t_{\text{eff}}) \in \text{index\_constituents\_history}, \, t_{\text{eff}} \le T \land \left( \forall t' \in (t_{\text{eff}}, T], \, S \text{ not delisted} \right) \right\}$$
3. **Execution Gap:** Trades computed at market close $T_{\text{asof}}$ are priced at $P_{\text{open}}(T_{\text{asof}} + 1)$.

### 2.3 Complete Relational Database Schema (SQLite WAL & PostgreSQL DDL)

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

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

-- 2. Daily Market Prices
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
    disclosed_at     DATE    NOT NULL,
    metric           TEXT    NOT NULL,
    value            REAL,
    unit             TEXT    DEFAULT 'INR_cr',
    source           TEXT    NOT NULL,
    PRIMARY KEY (symbol, period_end, metric, source)
);
CREATE INDEX IF NOT EXISTS idx_fq_pit ON fundamentals_quarterly(symbol, metric, disclosed_at);

-- 4. Corporate Events & Intelligence
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

-- 6. Model Predictions & Alpha Store
CREATE TABLE IF NOT EXISTS model_predictions (
    asof_date        DATE    NOT NULL,
    symbol           TEXT    NOT NULL,
    model_name       TEXT    NOT NULL,
    p_outperform     REAL    NOT NULL,
    rank_in_universe INTEGER,
    features_json    TEXT,
    PRIMARY KEY (asof_date, symbol, model_name)
);

-- 7. Target Portfolio History
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

-- 8. Backtest Runs Archive
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

-- 9. Shadow Portfolio & Realized Execution Tracking
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

-- 10. Multi-User Authentication & Portfolios
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

### 2.4 The `PointInTimeDataAccess` Class Implementation

The `PointInTimeDataAccess` class is the sole blessed gateway for querying the database during scoring, backtesting, and ML feature building:

```python
# invst/backend/src/invst/data_access.py
from datetime import date
from typing import Optional, List, Dict
import sqlite3

class PointInTimeDataAccess:
    """Institutional Point-in-Time Data Access Guard."""

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

    def get_fundamental_history(self, symbol: str, metric: str, n_quarters: int = 20) -> List[tuple]:
        """Fetch past quarterly reports available strictly on or before asof date."""
        return self.conn.execute(
            """
            SELECT period_end, disclosed_at, value FROM fundamentals_quarterly
            WHERE symbol = ? AND metric = ? AND disclosed_at <= ?
            ORDER BY disclosed_at DESC, period_end DESC
            LIMIT ?
            """,
            (symbol, metric, self.asof.isoformat(), n_quarters),
        ).fetchall()

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

## 3. Quantitative Factor Engines & Mathematical Scoring Logic

### 3.1 Stage 0: Universe Screening & Liquidity Filtering

The full universe of ~500 stocks is screened through a deterministic filter pipeline:

```
Nifty 500 (~500 Equities)
   │
   ├── Filter 1: 30-day Median Daily Traded Value ≥ ₹5.00 Crore
   ├── Filter 2: Point-in-Time Market Capitalization ≥ ₹1,000 Crore
   ├── Filter 3: Listing Tenure on NSE/BSE ≥ 3.0 Years (12 quarters)
   ├── Filter 4: Minimum Price ≥ ₹10.00 (Penny stock elimination)
   ├── Filter 5: Promoter Shareholding ≤ 75.0% (SEBI float compliance)
   ├── Filter 6: Data Completeness ≥ 10 of last 12 quarters reported
   └── Filter 7: Non-delisted / Non-suspended status
   │
   ▼
Investable Universe (~350 to ~470 Equities)
```

### 3.2 Stage 1 & Level 1: Business Score & Quality Mechanics (BQS & Growth)

```
┌────────────────────────────────────────────────────────────────────────┐
│ LEVEL 1 SYNTHESIS: BUSINESS SCORE (Price-Agnostic Enterprise Value)   │
│ Formula: 0.60 * Business Quality Score (BQS) + 0.40 * Growth Score     │
└────────────────────────────────────────────────────────────────────────┘
```

#### A. Business Quality Score (BQS) Mathematical Derivation
1. **Capital Allocation & Efficiency (35%):**
   - 5-Year Average Return on Capital Employed: $\text{ROCE} = \frac{\text{EBIT}}{\text{Capital Employed}}$.
   - 5-Year Average Return on Equity: $\text{ROE} = \frac{\text{Net Income}}{\text{Shareholders' Equity}}$.
2. **Operating Profit Margin Stability (25%):**
   $$\text{Margin Stability} = 1.0 - \min\left(1.0, \, \frac{\sigma(\text{OPM}_{5y})}{\mu(\text{OPM}_{5y})}\right)$$
3. **Balance Sheet Resilience (25%):**
   $$\text{Solvency Score} = \frac{1}{1 + \text{Debt-to-Equity}}$$
   Interest coverage penalty applied if $\frac{\text{EBIT}}{\text{Interest Expense}} < 3.0\times$.
4. **Modified Sloan Accrual Penalty (15%):**
   $$\text{Accrual Ratio} = \frac{\text{Net Income} - \text{CFO}}{\text{Total Assets}}$$
   - If $\text{Accrual Ratio} > +0.10$: $-15.0$ penalty points (aggressive accrual manipulation).
   - If $\text{Accrual Ratio} > +0.05$: $-8.0$ penalty points.
   - If $\text{Accrual Ratio} < -0.02$: $+5.0$ bonus points (conservative cash accounting).
5. **Governance Deductions:**
   - Promoter Pledge $> 20\%$: $-50.0$ points and hard cap $\text{BQS} \le 35.0$.
   - Auditor Qualified Opinion: $-40.0$ points and hard cap $\text{BQS} \le 35.0$.
   - Related-Party Transactions $> 5.0\%$ of revenue: $-15.0$ points.

#### B. Standalone Growth Engine
- Evaluates 3-year and 5-year revenue and net profit CAGR:
  $$\text{CAGR} = \left(\frac{\text{Metric}_t}{\text{Metric}_{t-k}}\right)^{\frac{1}{k}} - 1$$
- Sequential acceleration factor:
  $$\Delta \text{Growth} = \text{Revenue Growth}_{YoY, t} - \text{Revenue Growth}_{YoY, t-1}$$
- Return on Incremental Invested Capital (ROIIC):
  $$\text{ROIIC} = \frac{\text{EBIT}_t - \text{EBIT}_{t-1}}{\text{Invested Capital}_t - \text{Invested Capital}_{t-1}}$$

### 3.3 Stage 2 & Level 2: Valuation Engine & Reverse-DCF Solver

```
┌────────────────────────────────────────────────────────────────────────┐
│ LEVEL 2 SYNTHESIS: INVESTMENT SCORE (Attractiveness Today)             │
│ Formula: 0.40 * Business Score + 0.35 * Valuation + 0.25 * Risk        │
│ (Down-weighted by 10% if Market Execution friction is unfavorable)     │
└────────────────────────────────────────────────────────────────────────┘
```

#### A. Valuation Score Formulation
To eliminate inverse negative P/E distortions, all ratios are transformed into monotonic yields:

$$\text{Earnings Yield} = \frac{100}{\text{PE}_{TTM}}, \quad \text{FCF Yield} = \frac{\text{Free Cash Flow}}{\text{Market Cap}} \times 100$$

$$V_i = 0.40 \cdot \Phi\left(z_{\text{Earnings Yield}}\right) + 0.30 \cdot \Phi\left(z_{\text{Historical PE Discount}}\right) + 0.30 \cdot \Phi\left(z_{\text{EV/EBITDA Yield}}\right)$$

#### B. Reverse-DCF Implied Growth Solver
Computes the 5-year cash flow growth rate $g$ priced into the current stock price $P_0$:

$$P_0 = \sum_{t=1}^{5} \frac{\text{FCF}_0 \cdot (1 + g)^t}{(1 + \text{WACC})^t} + \frac{\text{FCF}_0 \cdot (1 + g)^5 \cdot (1 + g_t)}{(\text{WACC} - g_t) \cdot (1 + \text{WACC})^5}$$

Where $\text{WACC} = 11.5\%$ (Indian cost of capital) and terminal growth $g_t = 5.0\%$. Solved via binary search across $g \in [-20\%, +60\%]$.

### 3.4 Stage 3: Multi-Dimensional Risk & Contagion Redlines

Rather than simple standard deviation, ArthIQ computes 8 risk dimensions:
1. **Realized Volatility (252-day):** $\sigma_{\text{ann}} = \sigma_{\text{daily}} \times \sqrt{252}$.
2. **Tail Risk (3-Year Max Drawdown):**
   $$\text{MaxDD} = \min_{t} \left(\frac{P_t - \max_{\tau \le t} P_\tau}{\max_{\tau \le t} P_\tau}\right)$$
3. **Downside Semivariance:** Volatility of returns below $0.0\%$:
   $$\sigma_{\text{down}} = \sqrt{\frac{1}{N} \sum_{t=1}^N \min(0, R_t)^2} \times \sqrt{252}$$
4. **Market Sensitivity (Beta vs Nifty 500 over 2 years):**
   $$\beta = \frac{\text{Cov}(R_{\text{stock}}, R_{\text{bench}})}{\text{Var}(R_{\text{bench}})}$$
5. **Contagion Redlines:** Triggering any of the following sets $\text{RiskScore} \le 30.0$:
   - Realized Volatility $> 50\%$.
   - 3-Year Max Drawdown worse than $-60\%$.
   - Net Debt / EBITDA $> 4.5\times$ (Non-financials).
   - Gross NPA $> 7.0\%$ (Banks / NBFCs).

### 3.5 Sector Archetypes & Cross-Sectional Normalization

Stocks are divided into three archetypes to prevent comparing banks against software firms:

```
┌────────────────────────────────────────────────────────────────────────┐
│ Archetype 1: FINANCIALS (Banks, NBFCs, Housing Finance)                │
│ Primary Metrics: Net Interest Margin (NIM), GNPA %, NNPA %, P/ABV, ROA │
├────────────────────────────────────────────────────────────────────────┤
│ Archetype 2: INDUSTRIALS & CAPEX (Capital Goods, Infrastructure, Power)│
│ Primary Metrics: Order Book/Bill, Asset Turnover, Net Debt/EBITDA      │
├────────────────────────────────────────────────────────────────────────┤
│ Archetype 3: CONSUMER & TECH (FMCG, IT Services, Consumer Discretionary│
│ Primary Metrics: ROCE, Working Capital Days, FCF Yield, EV/Sales       │
└────────────────────────────────────────────────────────────────────────┘
```

Raw metrics $x$ are winsorized at $[5\%, 95\%]$ and standardized within sector:

$$z_{i, s} = \frac{x_{i, s} - \mu_s}{\sigma_s}, \quad \text{Score} = \Phi(z_{i, s}) \times 100$$

### 3.6 Scenario Analysis & Probabilistic Return Trajectories

Projects 1-year forward expected returns across three macro-fundamental cases:
- **Macro Regime Assessment (India VIX):**
  - High Volatility ($\text{VIX} \ge 20$): $p_{\text{bear}} = 0.35, \, p_{\text{base}} = 0.50, \, p_{\text{bull}} = 0.15$.
  - Expansionary ($\text{VIX} \le 12.5$): $p_{\text{bear}} = 0.15, \, p_{\text{base}} = 0.55, \, p_{\text{bull}} = 0.30$.
  - Neutral ($12.5 < \text{VIX} < 20$): $p_{\text{bear}} = 0.25, \, p_{\text{base}} = 0.50, \, p_{\text{bull}} = 0.25$.
- **Expected Return Calculation:**
  $$\mathbb{E}[R] = p_{\text{bear}} R_{\text{bear}} + p_{\text{base}} R_{\text{base}} + p_{\text{bull}} R_{\text{bull}}$$

### 3.7 Event Intelligence & Dynamic Factor Deltas

Real-time corporate disclosures modify base factor scores dynamically:
- **Earnings Beat ($\ge +10\%$ vs consensus):** $+4.0$ Growth, $+2.0$ Quality.
- **Large Capex Announcement ($\ge 20\%$ Net Worth):** $+3.0$ Growth, $-1.5$ Risk (leverage increase).
- **Auditor Resignation:** $-15.0$ Governance (Immediate freeze on new buying).

### 3.8 The 2x2 Investment Matrix Quadrants

```
                    High Business Score (≥ 65.0)
                               │
            QUALITY TRAP       │    CORE COMPOUNDING ALPHA
       (High Quality, High PE) │  (High Quality, Fair/Cheap PE)
                               │
Valuation < 50.0 ──────────────┼────────────── Valuation ≥ 50.0
                               │
            VALUE TRAP         │    DEEP VALUE / CYCLICAL
        (Low Quality, Cheap)   │  (Low Quality, Extreme Cheapness)
                               │
                     Low Business Score (< 65.0)
```

---

## 4. Portfolio Construction & Real-World Execution Engine

### 4.1 Hierarchical Risk Parity (HRP) Mathematical Derivation

Standard Mean-Variance Optimization requires computing $\Sigma^{-1}$. Small errors in sample covariance lead to extreme, un-investable portfolio weights. HRP solves this by operating on a tree graph.

### 4.2 Dendrogram Clustering & Quasi-Diagonalization Algorithm

1. **Correlation Distance Metric:**
   $$d_{i, j} = \sqrt{\frac{1}{2} (1 - \rho_{i, j})}$$
2. **Single-Linkage Clustering:** Computes distance between clusters $u$ and $v$:
   $$D(u, v) = \min_{i \in u, j \in v} d_{i, j}$$
3. **Quasi-Diagonalization:** Reorganizes rows and columns of covariance matrix $\Sigma$ so that highest correlations are positioned along the main diagonal:
   $$\Sigma^* = P \Sigma P^T$$

### 4.3 Recursive Bisection Algorithm

For cluster $C$ split into sub-clusters $C_1$ and $C_2$:
1. Compute cluster variance:
   $$V_k = w_k^T \Sigma_k w_k, \quad \text{where } w_k = \frac{\text{diag}(\Sigma_k)^{-1}}{\text{Tr}(\text{diag}(\Sigma_k)^{-1})}$$
2. Compute split factor $\alpha_1$:
   $$\alpha_1 = 1 - \frac{V_1}{V_1 + V_2}, \quad \alpha_2 = 1 - \alpha_1$$
3. Update weights recursively:
   $$W_{C_1} = W_C \times \alpha_1, \quad W_{C_2} = W_C \times \alpha_2$$

### 4.4 Hard Risk Caps & Dynamic Investor Profiles

| Constraint Parameter | Conservative | Moderate (Default) | Aggressive |
| :--- | :--- | :--- | :--- |
| **Target Number of Holdings** | 16 | 10 | 8 |
| **Max Single Stock Cap** | **10.0%** | **15.0%** | **25.0%** |
| **Max Sector Exposure** | **25.0%** | **35.0%** | **40.0%** |
| **Minimum BQS Quality Floor**| 70.0 | 60.0 | 50.0 |

#### Cap Clipping & Redistribution Algorithm:
```python
def apply_portfolio_caps(weights: dict[str, float], max_stock: float, max_sector: float, sector_map: dict) -> dict:
    w = dict(weights)
    for _ in range(20):
        # 1. Single stock cap
        excess = 0.0
        uncapped = []
        for s, weight in w.items():
            if weight > max_stock:
                excess += weight - max_stock
                w[s] = max_stock
            else:
                uncapped.append(s)
        if uncapped and excess > 0:
            uncapped_sum = sum(w[s] for s in uncapped)
            for s in uncapped:
                w[s] += excess * (w[s] / uncapped_sum)

        # 2. Sector cap
        sec_weights = {}
        for s, weight in w.items():
            sec = sector_map[s]
            sec_weights[sec] = sec_weights.get(sec, 0.0) + weight
        for sec, total_w in sec_weights.items():
            if total_w > max_sector:
                scale = max_sector / total_w
                for s in w:
                    if sector_map[s] == sec:
                        w[s] *= scale
        # Re-normalize
        total = sum(w.values())
        w = {s: v / total for s, v in w.items()}
    return w
```

### 4.5 Integer Share Sizing & Indian Market Execution Friction

1. **Integer Floor-Sizing:**
   $$\text{Shares}_i = \left\lfloor \frac{\text{Capital} \times w_i}{P_{i, \text{open}}} \right\rfloor$$
2. **Indian Market Friction Accounting:**
   - **STT (Securities Transaction Tax):** 10 bps on purchase and sale.
   - **Brokerage:** 30 bps buy, 20 bps sell.
   - **Stamp Duty & Exchange Fees:** 1.5 bps.
   - **Market Impact Slippage:** 5 bps.
   - **Total Round-Trip Friction:** **66.5 bps** explicitly subtracted on every portfolio turnover.

### 4.6 ML-Tilted HRP Formulation ($\gamma$ Conviction Exponent)

Modifies HRP structural risk weights using calibrated ML outperformance probabilities $p_i \in [0.0, 1.0]$:

$$m_i = \left(\frac{p_i}{0.50}\right)^\gamma$$

$$w_{\text{tilted}, i} = \frac{w_{\text{hrp}, i} \times m_i}{\sum_j (w_{\text{hrp}, j} \times m_j)}$$

- $\gamma = 0.0$: Pure structural HRP.
- $\gamma = 1.0$: Linear probability conviction tilt.

---

## 5. Machine Learning & Predictive Intelligence Engine

### 5.1 The 24-Dimensional Point-in-Time Feature Store

```python
# invst/backend/src/invst/ml/features.py
FEATURES_CATALOG = [
    # Factor Scores (4)
    "composite_score", "investment_score", "business_score", "growth_score",
    # Fundamental Capital Efficiency (3)
    "roe_5yr", "roce_5yr", "debt_equity",
    # Valuation Multiples (4)
    "pe_ttm", "pb", "ev_ebitda", "quality_to_valuation_ratio",
    # Volatility & Tail Risk (4)
    "annualised_vol", "beta", "max_drawdown", "downside_semivariance",
    # Momentum & Technicals (3)
    "momentum_6_12_1", "dist_from_52w_high", "risk_adjusted_momentum",
    # News Sentiment (1)
    "news_sentiment",
    # Macroeconomic State Variables (3)
    "macro_vix", "macro_vix_change_30d", "macro_usd_inr",
    # Sector Archetype Metrics (2)
    "market_score", "gross_npa_pct"
]
```

### 5.2 Target Formulation & Labeling Invariants

$$y_{i, t} = \mathbb{I}\left( R_{i, [t, t+90D]} - R_{\text{NIFTY500}, [t, t+90D]} > 0 \right)$$

### 5.3 Expanding Walk-Forward Cross-Validation Architecture

```
Fold 1: Train [2016-01-01 to 2019-12-31] ──► Predict Q1 2020
Fold 2: Train [2016-01-01 to 2020-03-31] ──► Predict Q2 2020
...
Fold N: Train [2016-01-01 to 2023-12-31] ──► Predict Q1 2024
[2024-01-01 to 2026-09-21]: FROZEN UNTOUCHED TEST PARTITION (ZERO RETRAINING)
```

### 5.4 Boosted Tree Classification & Probability Calibration

- **Base Estimators:** LightGBM (`LGBMClassifier`, 100 trees, learning rate 0.03, max depth 4) and XGBoost (`XGBClassifier`), with regularized `LogisticRegression` fallback.
- **Platt Scaling Calibration:** Fits logistic regression on raw logits $z$:
  $$P(y=1 | z) = \frac{1}{1 + \exp(A z + B)}$$
  Ensures that when model outputs $P = 0.65$, 65% of such historical selections outperformed the benchmark.

### 5.5 The V0.3.1 Diagnostic Breakthrough & Signal Inversion Analysis

The 12-vector institutional audit revealed a major empirical discovery:

| Configuration | CAGR | Alpha | Sharpe | Max Drawdown | Hit Rate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Deterministic Baseline (V0.2.1)** | **4.60%** | **-2.56%** | **-0.17** | **-38.49%** | **46.2%** |
| Pure ML $\gamma = 0.50$ | 4.40% | -2.75% | -0.19 | -39.01% | 45.4% |
| 50/50 Deterministic/ML Blend ($\gamma = 1.00$) | 4.64% | -2.52% | -0.16 | -39.61% | 46.9% |
| **Platt + 50/50 + $\gamma = 0.50$** | **4.25%** | **-2.90%** | **-0.20** | **-38.15%** | **44.6%** |

#### Untouched Test Partition Performance:
- **Development (2016–2020):** Baseline $8.34\%$ vs ML $\mathbf{8.96\%}$ ($+0.62\%$)
- **Validation (2021–2023):** Baseline $0.25\%$ vs ML $\mathbf{1.32\%}$ ($+1.07\%$)
- **Untouched Test (2024–2026):** Baseline $\mathbf{-0.02\%}$ vs ML $-1.27\%$ ($\mathbf{-1.25\%}$ underperformance)

> [!CAUTION]
> **Verdict:** Standalone ML failed to generalize to the untouched test partition and was **formally rejected** as a standalone portfolio ranker.

### 5.6 Cross-Sectional Quintile Spread & 1-P Reverse Signal Diagnostic

The full 24-feature ML model produced an inverted Spearman Rank IC of **-0.0909** and annualized Long/Short return of **-7.28%**.

#### 5-Quintile Return Breakdown:
- **Q1 (Lowest ML Probability):** **+3.76%**
- **Q2:** +2.98%
- **Q3:** +2.57%
- **Q4:** +2.09%
- **Q5 (Highest ML Probability):** **+1.87%**
- **Spread ($Q5 - Q1$):** **-1.89% (Complete Inversion)**

The reverse signal ($P_{\text{reverse}} = 1 - P$) achieved Rank IC of **+0.0909** and $+7.76\%$ L/S return.

### 5.7 Feature Group Ablation & The Fundamentals-Only Alpha Discovery

A controlled 8-subset ablation proved that **fundamental features hold true alpha**, while adding momentum and macro variables introduced destructive collinear interactions:

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

### 5.8 The 8 Institutional Model Promotion Gates

1. **Gate 1 (Zero PIT Lookahead):** 100% pass across historical audits.
2. **Gate 2 (Positive Statistical Signal):** Spearman Rank IC $> 0.00$ and $\text{IC IR} > 0.00$.
3. **Gate 3 (Monotonic Quintiles):** $Q5 > Q1$ spread $> 0$.
4. **Gate 4 (Temporal Stability):** Signal persists across economic regimes.
5. **Gate 5 (Untouched Test Performance):** Positive delta on frozen 2024–2026 data.
6. **Gate 6 (Economic Causality):** Documented causal mechanism.
7. **Gate 7 (Transaction Cost Resilience):** Alpha survives 66.5 bps friction.
8. **Gate 8 (Net Portfolio Value-Add):** Improves portfolio Sharpe vs baseline.

---

## 6. The V0.4 Decision Intelligence Framework

### 6.1 Normalized Additive Decision Function ($\text{ArthScore}$)

$$\boxed{\text{ArthScore}_i = \left( w_F F_i + w_M M_i + w_E E_i + w_R R_i + w_H H_i \right) \times \text{Agreement}_i}$$

- $F_i$: Fundamental Business Quality Pillar $\in [0, 100]$ (Weight $w_F = 0.30$)
- $M_i$: Valuation & Margin-of-Safety Pillar $\in [0, 100]$ (Weight $w_M = 0.25$)
- $E_i$: Earnings Growth & Acceleration Pillar $\in [0, 100]$ (Weight $w_E = 0.20$)
- $R_i$: Capital Preservation & Downside Risk Pillar $\in [0, 100]$ (Weight $w_R = 0.15$)
- $H_i$: Calibrated ML Alpha Conviction $\in [0, 100]$ (Weight $w_H = 0.10$)

### 6.2 Cross-Pillar Signal Agreement Mechanism

$$\text{Divergence}_i = \frac{|F_i - H_i|}{100}, \quad \text{Agreement}_i = \max\left(0.50, \, 1.0 - 0.30 \times \text{Divergence}_i\right)$$

If Fundamental Quality $F_i = 90$ but ML Conviction $H_i = 20$, the agreement multiplier is:
$$1.0 - (0.30 \times 0.70) = 0.79$$
Dampening the score and preventing aggressive allocation during signal conflict.

### 6.3 Candidate Signal Suite

- **Candidate 1 (Fundamentals Only):** Features `[roe_5yr, roce_5yr, debt_equity]`.
- **Candidate 2 (Fundamentals + Momentum):** Features `[roe_5yr, roce_5yr, debt_equity, momentum_6_12_1, dist_from_52w_high, risk_adjusted_momentum]`.
- **Candidate 3 (Fundamentals + Sentiment):** Features `[roe_5yr, roce_5yr, debt_equity, news_sentiment]`.

### 6.4 Multi-Horizon Decay Analysis (30D to 252D)

Signals are tracked across 5 holding periods to identify where alpha peaks:
- **30 Days:** Post-earnings drift window.
- **60 Days:** Momentum consolidation.
- **90 Days:** Quarterly reporting cycle (Default rebalance cadence).
- **180 Days / 252 Days:** Multi-quarter fundamental compounding.

### 6.5 Non-Parametric Bootstrap Confidence Intervals

Computes empirical confidence intervals via 1,000 bootstrap resamples with replacement:
$$CI_{95\%} = \left[ \text{Percentile}(2.5\%), \, \text{Percentile}(97.5\%) \right]$$

### 6.6 Shadow Portfolio Execution & Slippage Tracking

Persisted in `shadow_portfolio_records` to monitor real-world execution drag against theoretical models:
- Fill price variance vs market open.
- Tracking error vs target weights.
- Cumulative realized transaction fees.

---

## 7. Backend Service, Cryptographic Security & REST API

### 7.1 Architecture & Directory Tree

```
invst/backend/
├── src/invst/
│   ├── api/
│   │   ├── app.py          # FastAPI factory & SPA mounting
│   │   ├── auth.py         # PBKDF2-SHA256 & RFC 7519 JWT
│   │   ├── routes.py       # REST endpoints
│   │   └── schemas.py      # Pydantic v2 schemas
│   ├── scoring/            # Factor engines & Composite V2
│   ├── optimization/       # HRP optimizer
│   ├── ml/                 # Classifiers, ranking, diagnostics
│   ├── backtest/           # Walk-forward engine & metrics
│   ├── execution/          # Shadow portfolio
│   ├── monitoring/         # DQ rules & PIT audits
│   └── reporting/          # Rationale generator & PDF
```

### 7.2 Zero-Dependency Cryptographic Authentication & RBAC

- **PBKDF2 Password Hashing:** 600,000 iterations of SHA-256 HMAC with random 16-byte salt:
  $$\text{Hash} = \text{PBKDF2}_{\text{HMAC-SHA256}}(\text{Password}, \text{Salt}, 600000)$$
- **Timing-Safe Verification:** Uses `hmac.compare_digest` to prevent timing attacks.
- **JWT Tokens:** Custom zero-external-dependency RFC 7519 implementation using HS256 HMAC signatures with base64url encoding.
- **RBAC Roles:** `admin` (user management, retrain triggers) and `user` (portfolio tracking, recommendations).

### 7.3 Complete REST API Endpoints & Data Contracts

| Method | Endpoint | Access | Purpose |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/login` | Public | Authenticates credentials, returns JWT bearer token |
| `GET` | `/api/dashboard` | Auth | Portfolio value, active regime, top holdings |
| `GET` | `/api/recommendations` | Auth | Latest quarterly scorecards, weights, matrix quadrants |
| `GET` | `/api/stock/{symbol}` | Auth | Deep-dive factor scores, scenario analysis, financials |
| `POST` | `/api/backtest/run` | Auth | Executes walk-forward simulation for specified window |
| `GET` | `/api/health` | Auth | Data quality reports, PIT audit checks, drift alerts |
| `GET` | `/api/ml/status` | Auth | Model registry state, promotion gates, Rank IC metrics |
| `POST` | `/api/ml/train` | Admin | Triggers walk-forward classifier retraining |
| `POST` | `/api/portfolio/custom` | Auth | Creates and tracks user broker positions |

### 7.4 Plain-English Investment Thesis Generation & PDF Reporting

The rationale generator compiles quantitative metrics into structured institutional summaries:
- **Thesis:** Capital efficiency, earnings growth momentum, balance sheet health.
- **Valuation Context:** P/E vs 3Y sector median, reverse-DCF implied growth.
- **Key Risks:** Industry cyclicality, raw material exposure, leverage.
- **Invalidation Triggers:** Concrete thresholds (e.g., ROCE drop $> 250$ bps, D/E $> 0.85\times$) that mandate immediate liquidation.

---

## 8. Frontend Client Architecture (React 19 + TypeScript + Tailwind)

### 8.1 Obsidian Dark Design System & Glassmorphism Tokens

- **Background:** Deep Obsidian Black (`#040508`).
- **Cards:** Semi-transparent Glass (`#0b0f17` with 70% opacity, `backdrop-blur-md`, border `rgba(255,255,255,0.06)`).
- **Accents:** Winsor Blue (`#1d4ed8`), Sky Cyan (`#0284c7`), Emerald (`#10b981`), Amber (`#f59e0b`), Crimson (`#ef4444`).
- **Numerals:** Monospace tabular numbers (`font-mono tracking-tight`).

### 8.2 Live Monospace IST Clock & Persistent Ticker Marquee

- **Header Bar:** Real-time ticking Indian Standard Time (`hh:mm:ss A IST`) alongside current Indian calendar date.
- **Market Ticker:** CSS infinite marquee displaying live market rates (Nifty 50, Sensex, Bank Nifty, India VIX, Crude Oil, USD/INR, 10Y G-Sec) with a pulsing broadcast beacon.

### 8.3 The Five Specialized Analytical Modules

```
┌────────────────────────────────────────────────────────────────────────┐
│ 1. Stock Ideas & Alpha Picks                                           │
│ • QuickPicks slider (Top 1 to 50 equities)                             │
│ • Cross-sectional factor matrix heatmap                                │
│ • Capital Deployment Calculator (₹500 to ₹10 Lakhs, whole shares)      │
├────────────────────────────────────────────────────────────────────────┤
│ 2. Lens (Factor Diagnostic Magnifier)                                  │
│ • Deep-dive radar into Quality, Valuation, Risk, and Sentiment         │
│ • Historical return spectrum (1D, 5D, 1M, 6M, 1Y)                      │
│ • Bull / Base / Bear scenario probability trees                        │
├────────────────────────────────────────────────────────────────────────┤
│ 3. Vault (Portfolio Allocation & Asset Architecture)                   │
│ • Interactive SVG sector allocation donut                              │
│ • Enforced 25% single-stock and 40% sector caps                        │
│ • Explicit 66.5 bps execution friction deduction                       │
├────────────────────────────────────────────────────────────────────────┤
│ 4. Pulse (Thematic Quant Radar)                                        │
│ • Connected SVG factor constellation diagram                           │
│ • Monitored clusters: AI Tech, Clean Capex, Defense, Compounding Titans│
├────────────────────────────────────────────────────────────────────────┤
│ 5. Edge (Real-Time Signals & Event Feed)                               │
│ • Streaming audit log of corporate disclosures                         │
│ • Verified Point-in-Time exchange timestamps                           │
│ • Dynamic factor score adjustment tags (+4.5 pts on PAT beat)          │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Walk-Forward Backtesting Engine & Performance Metrics

### 9.1 Simulation Loop Architecture

```
For each quarterly rebalance date in [2016-03-31 ... 2026-06-30]:
    1. Initialize PointInTimeDataAccess(asof=rebalance_date)
    2. Extract active Nifty 500 constituents
    3. Execute Stage 0 liquidity screening
    4. Compute multi-stage quantitative scorecards
    5. Shortlist top candidates (e.g., Top 10)
    6. Extract rolling 3-year covariance matrix
    7. Execute HRP optimization with caps (max 25% stock, 40% sector)
    8. Fill trades at next-day open price (T + 1)
    9. Deduct 66.5 bps round-trip transaction friction
    10. Mark-to-market daily until next quarterly rebalance
```

### 9.2 Exact Financial Metric Formulations

$$\text{CAGR} = \left( \frac{\text{Equity}_{\text{end}}}{\text{Equity}_{\text{start}}} \right)^{\frac{1}{\text{Years}}} - 1$$

$$\text{Sharpe Ratio} = \frac{\mu(R_p - R_f)}{\sigma(R_p)} \times \sqrt{252} \quad (R_f = \text{RBI 91-Day T-Bill})$$

$$\text{Sortino Ratio} = \frac{\mu(R_p - R_f)}{\sigma_{\text{downside}}} \times \sqrt{252}$$

$$\text{Calmar Ratio} = \frac{\text{CAGR}}{|\text{Max Drawdown}|}$$

$$\text{Annualized Turnover} = \frac{1}{2 \times \text{Years}} \sum_{t=1}^T \sum_i |w_{i, t} - w_{i, t^-}|$$

### 9.3 Transaction Fee Sensitivity Ladder

| Fee Scenario | Buy Fee (bps) | Sell Fee (bps) | Slippage (bps) | Total Round-Trip (bps) | Impact on CAGR |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Zero Friction | 0.0 | 0.0 | 0.0 | 0.0 | Baseline (+0.00%) |
| Low (Discount Broker) | 10.0 | 10.0 | 2.5 | 22.5 | -0.24% |
| **Realistic (Default)**| **30.0** | **20.0** | **5.0** | **66.5** | **-0.68%** |
| High Slippage | 30.0 | 20.0 | 15.0 | 86.5 | -0.92% |
| Stress Case | 50.0 | 50.0 | 25.0 | 125.0 | -1.45% |

---

## 10. Monitoring, Data Quality & Operational Runbooks

### 10.1 Daily Data Quality Invariant Rules
1. **Row Count Check:** NSE Bhavcopy row count $> 1,500$.
2. **Missing Symbol Alert:** 100% of Nifty 500 constituents must possess valid closing prices.
3. **Price Jump Anomaly Filter:** Any single-day price movement $> \pm 30\%$ without a corresponding corporate split/bonus halts execution and alerts admin.

### 10.2 Weekly Point-in-Time Zero-Lookahead Audit
Asserts three hard database invariants across all historical records:
1. $\forall \text{ rows in } \text{fundamentals\_quarterly}, \quad \text{disclosed\_at} \le \text{CURRENT\_DATE}$.
2. $\forall \text{ rows}, \quad \text{disclosed\_at} \ge \text{period\_end} - 14\text{ days}$.
3. Deterministic backtest re-runs reproduce identical CAGR, Sharpe, and Drawdown to 4 decimal places.

### 10.3 Population Stability Index (PSI) & Drift Monitoring

$$PSI = \sum_{k=1}^K \left(\text{Actual}_k - \text{Expected}_k\right) \times \ln\left(\frac{\text{Actual}_k}{\text{Expected}_k}\right)$$

- $PSI < 0.10$: Stable.
- $0.10 \le PSI \le 0.25$: Moderate drift; warning logged.
- $PSI > 0.25$: Significant population drift; model retrain recommended.

### 10.4 Cron Scheduling Specifications

```cron
# /etc/cron.d/arthiq-ops
# Daily Bhavcopy Ingestion (Mon-Fri 18:30 IST)
30 18 * * 1-5 arthiq cd /opt/arthiq/backend && python3 -m invst.cli ingest --daily >> /var/log/arthiq/ingest.log 2>&1

# Daily Data Quality Audit (Mon-Fri 19:30 IST)
30 19 * * 1-5 arthiq cd /opt/arthiq/backend && python3 -m invst.cli monitor --dq >> /var/log/arthiq/dq.log 2>&1

# News Sentiment Scraper (Daily at 09:00, 13:00, 17:00, 21:00 IST)
0 9,13,17,21 * * * arthiq cd /opt/arthiq/backend && python3 -m invst.cli ingest --news >> /var/log/arthiq/news.log 2>&1

# Weekly PIT Zero-Lookahead Audit (Sun 02:00 IST)
0 2 * * 0 arthiq cd /opt/arthiq/backend && python3 -m invst.cli monitor --pit >> /var/log/arthiq/pit_audit.log 2>&1
```

---

## 11. Step-by-Step Scratch Build Blueprint

To rebuild the platform from a clean operating system:

```bash
# 1. Clone & Environment Setup
git clone <repo_url> arthiq && cd arthiq
cd backend
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Database Migration & Universe Seeding
python3 -m invst.db.migrate
python3 scripts/seed_constituents.py

# 3. Market Data Ingestion
python3 -m invst.cli ingest --daily

# 4. Verify Point-in-Time Audits & Promotion Gates
python3 scripts/run_v031_diagnostics.py
pytest tests/ -v

# 5. Launch Backend Service
uvicorn invst.api.app:app --host 0.0.0.0 --port 8000 --reload

# 6. Build and Launch Frontend Client
cd ../frontend
npm install
npm run dev -- --port 5173
```

---
*End of ArthIQ Exhaustive System Specification.*
