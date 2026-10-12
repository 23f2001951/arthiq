# ArthIQ Exhaustive System Specification & Quantitative Engineering Handbook
> **Complete Technical Reference for Mathematical Formulations, Code Logic, Data Engineering, and Decision Algorithms**  
> **Platform:** ArthIQ (`arthiq`) | **Version:** V0.5 Unified Multi-Asset Institutional Reference Architecture  
> **Universe:** NSE/BSE Listed Equities (Nifty 500) & AMFI Direct-Growth Mutual Funds  
> **Cadence:** Quarterly Rebalance (Equities) & Monthly Tracking (SIPs / Mutual Funds)  
> **Author:** Quantitative Engineering & Research Architecture

---

## Table of Contents

1. [Architectural Philosophy, Invariants & Design Principles](#1-architectural-philosophy-invariants--design-principles)
2. [Dual-Engine Persistence & Zero-Lookahead Data Engine](#2-dual-engine-persistence--zero-lookahead-data-engine)
   - 2.1 Dual Database Engine: SQLite WAL & Neon PostgreSQL Dialect Adaptation
   - 2.2 Complete Relational Database Schema DDL (All 14 Tables & Constraints)
   - 2.3 Point-in-Time Mathematics & The Disclosure Barrier
   - 2.4 The `PointInTimeDataAccess` Class Implementation
   - 2.5 Ingestion Feeds: Bhavcopy, Corporate Filings, AMFI NAV Feed, Macro Indicators
3. [Equities Quantitative Factor Engines & Mathematical Scoring Logic](#3-equities-quantitative-factor-engines--mathematical-scoring-logic)
   - 3.1 Stage 0: Universe Screening & Liquidity Filtering
   - 3.2 Level 1: Business Score (BQS & Standalone Growth Engine)
   - 3.3 Level 2: Valuation Engine & Reverse-DCF Implied Growth Solver
   - 3.4 Multi-Dimensional Risk Engine & Contagion Redlines
   - 3.5 Sector Archetypes & Sector-Relative Normalization
   - 3.6 Scenario Analysis & Probabilistic Return Trajectories
   - 3.7 Event Intelligence & Dynamic Factor Deltas
   - 3.8 The 2x2 Investment Matrix Quadrants
4. [Equities Portfolio Construction & Indian Market Execution Friction](#4-equities-portfolio-construction--indian-market-execution-friction)
   - 4.1 Hierarchical Risk Parity (HRP) Mathematical Derivation
   - 4.2 Dendrogram Clustering & Quasi-Diagonalization Algorithm
   - 4.3 Recursive Bisection Algorithm
   - 4.4 Hard Risk Caps & Dynamic Investor Profiles
   - 4.5 Integer Share Sizing & Indian Market Execution Friction (66.5 bps)
   - 4.6 ML-Tilted HRP Formulation ($\gamma$ Conviction Exponent)
5. [Equities Machine Learning Pipeline & The V0.3.1 Diagnostic Discovery](#5-equities-machine-learning-pipeline--the-v031-diagnostic-discovery)
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
   - 6.6 Shadow Portfolio Execution & Real-Time Tracking
7. [Mutual Fund Quantitative Engine & Advisory Architecture](#7-mutual-fund-quantitative-engine--advisory-architecture)
   - 7.1 Historical NAV Pipeline & Direct-Growth Scheme Master
   - 7.2 Rolling Returns Distributions (1Y, 3Y, 5Y CAGR, Probability of Negative Return)
   - 7.3 Risk-Adjusted Metrics (Sharpe, Sortino, Treynor, Jensen's Alpha, Beta, Capture Ratios)
   - 7.4 Robust Cashflow-Based XIRR Engine (Newton-Raphson & Brentq Bisection)
   - 7.5 Cross-Fund Portfolio Stock Overlap Matrix
   - 7.6 Goal-Based Profiling & Category Asset Allocation
   - 7.7 SIP Wealth Trajectory Compounder with Step-Up Modeling
   - 7.8 Capital Gains Tax Harvesting Analyzer (Finance Act 2024 LTCG/STCG)
8. [Multi-Asset Portfolio Health Diagnosis & Sizing Blotter](#8-multi-asset-portfolio-health-diagnosis--sizing-blotter)
   - 8.1 Position-Level Health Verdicts (BUY MORE, HOLD, TRIM, EXIT SELL)
   - 8.2 Capital Delta, Target Weights & Exact Share Adjustments
   - 8.3 Sector Concentration Bounds & Contagion Checks
   - 8.4 Multi-Horizon Portfolio Wealth Projections (1Y, 3Y, 5Y)
9. [Backend Service, Cryptographic Security & REST API](#9-backend-service-cryptographic-security--rest-api)
   - 9.1 FastAPI Architecture & Directory Structure
   - 9.2 Zero-Dependency Cryptographic Authentication & RBAC
   - 9.3 Complete API Endpoint Catalog (Equities + Mutual Funds + Health)
   - 9.4 Plain-English Investment Thesis Generation & PDF Reporting
10. [Frontend Client Architecture (React 19 + TypeScript + Tailwind)](#10-frontend-client-architecture-react-19--typescript--tailwind)
    - 10.1 Obsidian Dark Design System & Glassmorphism Tokens
    - 10.2 Live Monospace IST Clock & Persistent Ticker Marquee
    - 10.3 The Specialized Analytical Modules
    - 10.4 Interactive SVG & Canvas Data Visualizations
11. [Walk-Forward Backtesting Engine & Performance Metrics](#11-walk-forward-backtesting-engine--performance-metrics)
    - 11.1 Simulation Loop Architecture
    - 11.2 Exact Financial Metric Formulations
    - 11.3 Transaction Fee Sensitivity Ladder
12. [Monitoring, Data Quality & Operational Runbooks](#12-monitoring-data-quality--operational-runbooks)
    - 12.1 Daily Data Quality Invariant Rules
    - 12.2 Weekly Point-in-Time Zero-Lookahead Audit
    - 12.3 Population Stability Index (PSI) & Drift Monitoring
    - 12.4 Cron Scheduling Specifications
13. [Step-by-Step Scratch Build Blueprint](#13-step-by-step-scratch-build-blueprint)

---

## 1. Architectural Philosophy, Invariants & Design Principles

### 1.1 The Multi-Asset Investment Problem in Indian Capital Markets
Investors managing wealth across Indian equities and mutual funds face specific hurdles:
1. **Information Fragmentation:** Managing direct equity portfolios on screener tabs while simultaneously tracking mutual fund SIPs on broker apps without consolidated factor analysis.
2. **Hidden Stock Overlap:** Investors often hold 4–6 mutual funds believing they are diversified, while 60–70% of their aggregate capital is concentrated in the identical 10 large-cap stocks (e.g., HDFC Bank, Reliance, ICICI Bank, Infosys, TCS).
3. **Lookahead & Survivorship Contamination:** Financial backtests frequently use restated financials and today's index constituent list, massively exaggerating historical returns.
4. **Execution Cost Denial:** Real-world taxes (STT @ 10 bps, STCG @ 20%, LTCG @ 12.5% above ₹1.25L), brokerage, stamp duty, and slippage substantially reduce theoretical gross performance.

### 1.2 Core Architectural Principles of ArthIQ
1. **Decision Support, Not Execution Automation:** Generates evidence-backed recommendations and plain-English rationales; the user executes trades manually in Zerodha, Groww, or Upstox.
2. **Zero-Lookahead Point-in-Time (PIT) Isolation:** Financial disclosures are indexed by `disclosed_at` exchange filing date. All backtest calculations are strictly isolated from future restatements.
3. **Decoupled Business Quality vs. Stock Valuation:** A durable business is not necessarily an attractive investment; quality and price multiples are scored independently.
4. **Institutional Risk-First Portfolio Sizing (HRP):** Allocations are driven by correlation dendrograms and hierarchical inverse-variance bisection with hard caps (max 25% single stock, max 40% sector).
5. **Dual-Engine Persistence:** Supports offline single-user SQLite WAL storage as well as cloud-native Neon Serverless PostgreSQL with transparent SQL adaptation.

---

## 2. Dual-Engine Persistence & Zero-Lookahead Data Engine

### 2.1 Dual Database Engine: SQLite WAL & Neon PostgreSQL Dialect Adaptation

The connection manager (`invst/backend/src/invst/db/engine.py`):
- Provides unified access whether running locally against `invst.db` (SQLite 3 with `PRAGMA journal_mode = WAL`) or in the cloud using Neon Serverless PostgreSQL (`psycopg2`).
- Translates SQL dialect features on the fly:
  - SQLite parameter placeholders `?` are converted to `%s` for PostgreSQL.
  - `INTEGER PRIMARY KEY AUTOINCREMENT` translates to `SERIAL PRIMARY KEY`.
  - SQLite `INSERT OR REPLACE INTO table (...)` translates to PostgreSQL `INSERT INTO table (...) ON CONFLICT (pk_columns) DO UPDATE SET ...` using a pre-configured dictionary of primary keys (`TABLE_PK_MAP`).
  - Wraps database cursors in a `Row` mapping that allows both index-based (`row[0]`) and key-based (`row["symbol"]`) column access.

### 2.2 Complete Relational Database Schema DDL (All 14 Tables & Constraints)

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
    disclosed_at     DATE    NOT NULL,
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

-- 14. User Mutual Fund Portfolios, SIP Schedules & Check-ins
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
    tx_type          TEXT    NOT NULL,
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
    status           TEXT    NOT NULL,
    confirmed_date   DATE,
    amount           REAL    NOT NULL,
    notes            TEXT,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES user_mf_portfolios(id) ON DELETE CASCADE,
    FOREIGN KEY (sip_id) REFERENCES mf_sip_schedules(id) ON DELETE CASCADE
);
```

### 2.3 Point-in-Time Mathematics & The Disclosure Barrier
$$\text{Query}(S, M, T) \equiv \operatorname*{arg\,max}_{r.\text{disclosed\_at}} \left\{ r.\text{value} \;\middle|\; r.\text{symbol} = S \land r.\text{metric} = M \land r.\text{disclosed\_at} \le T \right\}$$

### 2.4 The `PointInTimeDataAccess` Class Implementation
Encapsulates all database interactions for equities scoring, backtesting, and ML feature building:
- `get_price(symbol, on_or_before)` clamps queries strictly to `trade_date <= asof`.
- `get_fundamental(symbol, metric)` queries strictly `disclosed_at <= asof`, ordering by `disclosed_at DESC, period_end DESC LIMIT 1`.
- `get_universe()` queries `index_constituents_history` for active constituents on `asof`.

### 2.5 Ingestion Feeds: Bhavcopy, Corporate Filings, AMFI NAV Feed, Macro Indicators
- **NSE/BSE Bhavcopy:** Official daily price and volume feed parsed at 18:30 IST.
- **AMFI NAV Feed:** Ingests official daily net asset values from `https://www.amfiindia.com/spages/NAVAll.txt` at 23:00 IST.
- **Corporate Disclosures:** Parses Revenue, PAT, Net Worth, Total Debt, CFO, and Total Assets.
- **Macro Indicators:** Ingests India VIX, USD/INR, Brent Crude, and Indian 10-Year G-Sec yields.

---

## 3. Equities Quantitative Factor Engines & Mathematical Scoring Logic

### 3.1 Stage 0: Universe Screening & Liquidity Filtering
Filters Nifty 500 constituents to an investable universe (~350–470 names):
$$\text{Screened} = (\text{TradedValue}_{30d} \ge ₹5\text{ Cr}) \land (\text{MarketCap} \ge ₹1000\text{ Cr}) \land (\text{Age} \ge 3\text{ yrs}) \land (\text{Price} \ge ₹10) \land (\text{PromoterHolding} \le 75\%)$$

### 3.2 Level 1: Business Score (BQS & Standalone Growth Engine)
$$\text{Business Score} = 0.60 \times \text{BQS} + 0.40 \times \text{Growth Score}$$

- **Business Quality Score (BQS):**
  - Capital Efficiency (35%): 5-Year median ROCE and ROE.
  - Margin Stability (25%): $1.0 - \min(1.0, \sigma_{\text{OPM}} / \mu_{\text{OPM}})$.
  - Balance Sheet Solvency (25%): $1 / (1 + \text{Debt-to-Equity})$. Interest coverage penalty if $< 3.0\times$.
  - Modified Sloan Accruals (15%): $\text{Accruals} = (\text{Net Income} - \text{CFO}) / \text{Total Assets}$. Penalizes aggressive accruals with $-15.0$ pts if $> +0.10$; $+5.0$ pts if $< -0.02$.
  - Governance Deductions: Promoter pledge $> 20\%$ or auditor qualified opinion caps $\text{BQS} \le 35.0$.
- **Growth Engine:** 3-5Y Sales/PAT CAGR, sequential YoY acceleration, and ROIIC.

### 3.3 Level 2: Valuation Engine & Reverse-DCF Implied Growth Solver
$$\text{Investment Score} = 0.40 \times \text{Business Score} + 0.35 \times \text{Valuation} + 0.25 \times \text{Risk}$$
(Down-weighted by 10% if Market Execution / Liquidity is unfavorable)

- **Monotonic Yields:** $\text{Earnings Yield} = \frac{100}{\text{PE}_{TTM}}$ and $\text{FCF Yield} = \frac{\text{FCF}}{\text{Market Cap}} \times 100$.
- **Reverse-DCF Solver:** Computes implied 5-year growth rate $g$ priced into market price $P_0$:
  $$P_0 = \sum_{t=1}^5 \frac{\text{FCF}_0 \cdot (1 + g)^t}{(1 + \text{WACC})^t} + \frac{\text{FCF}_0 \cdot (1 + g)^5 \cdot (1 + g_t)}{(\text{WACC} - g_t) \cdot (1 + \text{WACC})^5}$$
  Solved via binary search across $g \in [-20\%, +60\%]$ with $\text{WACC} = 11.5\%$ and $g_t = 5.0\%$.

### 3.4 Multi-Dimensional Risk Engine & Contagion Redlines
Computes 8 risk dimensions: 252D volatility, 3Y Max Drawdown, downside semivariance, 2Y beta vs Nifty 500, Amihud illiquidity, Debt/EBITDA, GNPA/NNPA (for banks), and promoter dilution. Contagion redlines cap $\text{RiskScore} \le 30.0$ if breached.

### 3.5 Sector Archetypes & Sector-Relative Normalization
- Archetypes: Financials, Industrials/Capex, Consumer/Tech.
- Raw metrics are winsorized at $[5\%, 95\%]$ and standardized within sector before ranking:
  $$z_{i, s} = \frac{x_{i, s} - \mu_s}{\sigma_s}, \quad \text{Score}_i = \Phi(z_{i, s}) \times 100$$

### 3.6 Scenario Analysis & Probabilistic Return Trajectories
Projects forward 1-year returns across Bull, Base, and Bear cases based on India VIX regime:
$$\mathbb{E}[R] = p_{\text{bear}} R_{\text{bear}} + p_{\text{base}} R_{\text{base}} + p_{\text{bull}} R_{\text{bull}}$$

### 3.7 Event Intelligence & Dynamic Factor Deltas
Corporate announcements dynamically adjust base factor scores (e.g., $+4.0$ Growth points on quarterly PAT beat $\ge +10\%$, $-15.0$ Governance points on auditor resignation).

### 3.8 The 2x2 Investment Matrix Quadrants
1. **Core Compounding Alpha:** High Quality ($\ge 65$) + Attractive Valuation ($\ge 50$).
2. **Quality Trap / Overpriced:** High Quality ($\ge 65$) + Stretched Valuation ($< 50$).
3. **Deep Value / Cyclical Rebound:** Low Quality ($< 65$) + Extreme Cheapness ($\ge 50$).
4. **Value Trap / Distressed:** Low Quality ($< 65$) + Cheap/Depressed Multiple ($< 50$).

---

## 4. Equities Portfolio Construction & Indian Market Execution Friction

### 4.1 Hierarchical Risk Parity (HRP) Mathematical Derivation
HRP groups correlated assets into a dendrogram and allocates risk inversely to sub-cluster variance, eliminating the need for matrix inversion.

### 4.2 Dendrogram Clustering & Quasi-Diagonalization Algorithm
1. Distance: $d_{i, j} = \sqrt{\frac{1}{2} (1 - \rho_{i, j})}$.
2. Single-linkage clustering groups assets into a hierarchical tree.
3. Quasi-diagonalization reorders covariance rows/columns so correlated assets sit along the diagonal.

### 4.3 Recursive Bisection Algorithm
Cluster $C$ is split into $C_1$ and $C_2$:
$$V_k = w_k^T \Sigma_k w_k, \quad w_k = \frac{\text{diag}(\Sigma_k)^{-1}}{\text{Tr}(\text{diag}(\Sigma_k)^{-1})}$$
$$\alpha_1 = 1 - \frac{V_1}{V_1 + V_2}, \quad W_{C_1} = W_C \cdot \alpha_1, \quad W_{C_2} = W_C \cdot (1 - \alpha_1)$$

### 4.4 Hard Risk Caps & Dynamic Investor Profiles
- **Conservative:** Max 10% stock / 25% sector cap (16 target holdings).
- **Moderate (Default):** Max 15% stock / 35% sector cap (10 target holdings).
- **Aggressive:** Max 25% stock / 40% sector cap (8 target holdings).

### 4.5 Integer Share Sizing & Indian Market Execution Friction (66.5 bps)
- Whole shares: $\text{Shares}_i = \lfloor (\text{Capital} \times w_i) / P_{i, \text{open}} \rfloor$.
- Deducts 10 bps STT (buy & sell) + 30 bps buy / 20 bps sell brokerage + 1.5 bps stamp duty/exchange fees + 5 bps slippage = **66.5 bps round-trip friction** on every turnover rebalance.

### 4.6 ML-Tilted HRP Formulation ($\gamma$ Conviction Exponent)
$$m_i = \left(\frac{p_i}{0.50}\right)^\gamma, \quad w_{\text{tilted}, i} = \frac{w_{\text{hrp}, i} \times m_i}{\sum_j (w_{\text{hrp}, j} \times m_j)}$$

---

## 5. Equities Machine Learning Pipeline & The V0.3.1 Diagnostic Discovery

### 5.1 The 24-Dimensional Point-in-Time Feature Store
Extracted strictly at market close of each rebalance date:
1. `composite_score`, `investment_score`, `business_score`, `growth_score`.
2. `roe_5yr`, `roce_5yr`, `debt_equity`.
3. `pe_ttm`, `pb`, `ev_ebitda`, `quality_to_valuation_ratio`.
4. `annualised_vol`, `beta`, `max_drawdown`, `downside_semivariance`.
5. `momentum_6_12_1`, `dist_from_52w_high`, `risk_adjusted_momentum`.
6. `news_sentiment` (FinBERT / VADER).
7. `macro_vix`, `macro_vix_change_30d`, `macro_usd_inr`.
8. `market_score`, `gross_npa_pct`.

### 5.2 Target Formulation & Labeling Invariants
$$y_{i, t} = \mathbb{I}\left( R_{i, [t, t+90D]} - R_{\text{NIFTY500}, [t, t+90D]} > 0 \right)$$

### 5.3 Expanding Walk-Forward Cross-Validation Architecture
Expanding training windows with strictly zero lookahead, followed by evaluation on the frozen untouched test window (2024–2026).

### 5.4 Boosted Tree Classification & Probability Calibration
LightGBM and XGBoost probability outputs are calibrated using **Platt Scaling** to minimize Brier score.

### 5.5 The V0.3.1 Diagnostic Breakthrough & Signal Inversion Analysis
The institutional audit tested the calibrated ML model against the permanently frozen untouched test window (2024–2026):
- Baseline CAGR: 4.60% (MDD -38.49%) vs ML 4.40% vs Platt+50/50 4.25%.
- Untouched 2024–2026 Delta: **-1.25%** underperformance vs baseline.
- Standalone ML was formally rejected as a standalone portfolio decision-maker.

### 5.6 Cross-Sectional Quintile Spread & 1-P Reverse Signal Diagnostic
The full 24-feature ML model produced an inverted Spearman Rank IC of **-0.0909** and annualized Long/Short return of **-7.28%**. Cross-sectional quintiles were inverted ($Q1 = +3.76\% > Q5 = +1.87\%$). The reverse signal ($1 - P$) achieved Rank IC of **+0.0909** and $+7.76\%$ L/S return.

### 5.7 Feature Group Ablation & The Fundamentals-Only Alpha Discovery
Controlled 8-subset ablation proved that **balance sheet fundamentals hold true positive alpha**, while adding momentum and macro variables introduced destructive collinear interactions:

| Feature Subset Tested | Rank IC | IC IR | Positive Quarters | Annualized L/S Return |
| :--- | :---: | :---: | :---: | :---: |
| **Fundamentals Only (Set A: RoE, RoCE, D/E)** | **+0.0179** | **+0.07** | **60.0%** | **+4.99%** |
| Valuation Only | +0.0024 | +0.01 | 48.0% | -0.15% |
| Risk Only | +0.0311 | +0.17 | 64.0% | -2.24% |
| Momentum Only | -0.0163 | -0.06 | 52.0% | -4.71% |
| **Full 24 Features** | **-0.0909** | **-0.39** | **32.0%** | **-7.28%** |

### 5.8 The 8 Institutional Model Promotion Gates
1. Zero PIT lookahead violations (100% pass across historical audits).
2. Positive Spearman Rank IC ($> 0.00$) and Information Ratio ($\text{IC IR} > 0.00$).
3. Monotonic cross-sectional quintiles ($Q5 > Q1$).
4. Multi-regime temporal stability.
5. Untouched test outperformance on frozen 2024–2026 data.
6. Documented causal economic mechanism.
7. Resilience after full transaction friction (66.5 bps).
8. Net empirical portfolio improvement vs baseline.

---

## 6. The V0.4 Decision Intelligence Framework

### 6.1 Normalized Additive Decision Function ($\text{ArthScore}$)
$$\boxed{\text{ArthScore}_i = \left( 0.30 F_i + 0.25 M_i + 0.20 E_i + 0.15 R_i + 0.10 H_i \right) \times \text{Agreement}_i}$$

### 6.2 Cross-Pillar Signal Agreement Mechanism
$$\text{Divergence}_i = \frac{|F_i - H_i|}{100}, \quad \text{Agreement}_i = \max\left(0.50, \, 1.0 - 0.30 \times \text{Divergence}_i\right)$$
Prevents capital allocation when short-term momentum and fundamental quality disagree.

### 6.3 Candidate Signal Suite
- Candidate 1: Fundamentals Only (`roe_5yr`, `roce_5yr`, `debt_equity`).
- Candidate 2: Fundamentals + Momentum.
- Candidate 3: Fundamentals + Sentiment.

### 6.4 Multi-Horizon Decay Analysis (30D to 252D)
Signals are evaluated across 30D, 60D, 90D, 180D, and 252D horizons to isolate where predictive edge peaks.

### 6.5 Non-Parametric Bootstrap Confidence Intervals
Computes empirical confidence intervals via 1,000 bootstrap resamples with replacement ($CI_{95\%}$).

### 6.6 Shadow Portfolio Execution & Real-Time Tracking
Tracks theoretical model allocations against realized market fills and logs execution slippage in `shadow_portfolio_records`.

---

## 7. Mutual Fund Quantitative Engine & Advisory Architecture

### 7.1 Historical NAV Pipeline & Direct-Growth Scheme Master
The mutual fund ingestion pipeline (`invst/backend/src/invst/ingestion/mf_ingestion.py`):
1. Downloads daily AMFI NAV master text file.
2. Filters for Direct-Growth schemes to measure fund manager performance free of distributor trail commissions.
3. Classifies schemes across SEBI standardized categories: Large Cap, Mid Cap, Small Cap, Flexi Cap, ELSS, Balanced Advantage, Aggressive Hybrid, and Liquid.

### 7.2 Rolling Returns Distributions
Measures annualized returns across every historical window (1Y, 3Y, 5Y), eliminating point-to-point start-date bias:
- Reports Mean, Median, 25th percentile, 75th percentile, Minimum, Maximum, and Probability of Negative Return.

### 7.3 Risk-Adjusted Metrics
- **Sharpe Ratio:** $\frac{\mu(R_p - R_f)}{\sigma(R_p)} \times \sqrt{252}$ ($R_f = 6.5\%$).
- **Sortino Ratio:** Measures return per unit of downside deviation:
  $$\text{Sortino} = \frac{\mu(R_p - R_f)}{\sqrt{\frac{1}{N}\sum \min(0, R_p - R_f)^2}} \times \sqrt{252}$$
- **Treynor Ratio:** $\frac{\mu(R_p - R_f)}{\beta}$.
- **Jensen's Alpha:** $\alpha = R_p - [R_f + \beta (R_m - R_f)]$.
- **Capture Ratios:**
  $$\text{Up Capture} = \frac{\mu(R_{\text{fund}} | R_{\text{bench}} > 0)}{\mu(R_{\text{bench}} | R_{\text{bench}} > 0)} \times 100, \quad \text{Down Capture} = \frac{\mu(R_{\text{fund}} | R_{\text{bench}} < 0)}{\mu(R_{\text{bench}} | R_{\text{bench}} < 0)} \times 100$$

### 7.4 Robust Cashflow-Based XIRR Engine
Solves for internal rate of return on irregular cash flows:
$$\text{NPV}(r) = \sum_{i=1}^N \frac{C_i}{(1 + r)^{\frac{d_i - d_0}{365.25}}} = 0$$
Uses Newton-Raphson with exact first derivative, falling back to Brent's method (bisection) across bracketed intervals `[(-0.95, 0.5), (0.0, 2.0), (1.0, 10.0)]` if gradient divergence occurs.

### 7.5 Cross-Fund Portfolio Stock Overlap Matrix
Calculates pairwise and portfolio-wide stock overlap across mutual funds:
$$\text{Overlap}(A, B) = \sum_{s \in A \cap B} \min\left(w_A(s), \, w_B(s)\right)$$
Identifies portfolio redundancy and aggregates underlying company exposures across multiple funds.

### 7.6 Goal-Based Profiling & Category Asset Allocation
Maps investor risk profile and goal type to target asset allocations:
- Emergency Fund (< 3 yrs): 50% Liquid Debt, 50% Balanced Advantage.
- Tax Saving (80C): 60% ELSS, 40% Flexi Cap.
- Conservative: 50% Balanced Advantage, 30% Large Cap, 20% Passive Index.
- Moderate: 40% Flexi Cap, 30% Large Cap, 20% Balanced Advantage, 10% Mid Cap.
- Aggressive ($\ge 7$ yrs): 35% Flexi Cap, 30% Mid Cap, 20% Small Cap, 15% Passive Index.

### 7.7 SIP Wealth Trajectory Compounder with Step-Up Modeling
Simulates wealth creation under compounding with an annual top-up percentage ($s\%$ annual step-up):
$$\text{SIP Month } m: \quad C_m = C_0 \times (1 + s)^{\lfloor (m - 1) / 12 \rfloor}$$

### 7.8 Capital Gains Tax Harvesting Analyzer (Finance Act 2024)
- **Equity Funds:**
  - Short-Term Capital Gains (STCG, $< 12$ months): Taxed at **20.0%**.
  - Long-Term Capital Gains (LTCG, $\ge 12$ months): Taxed at **12.5%** with annual exemption threshold of **₹1,25,000**.
- **Tax Harvesting Strategy:** Automatically identifies unrealized long-term gains up to ₹1,25,000 to sell and immediately repurchase, resetting cost basis tax-free.

---

## 8. Multi-Asset Portfolio Health Diagnosis & Sizing Blotter

The portfolio health engine (`invst/backend/src/invst/portfolio/health.py`) diagnoses user-provided stock and mutual fund holdings:
1. **Position Health Diagnosis:** Evaluates unrealized P&L, BQS, Valuation, Risk, and Investment scores to generate an action verdict:
   - `BUY_MORE`: High Quality + Margin of Safety + Undersized weight.
   - `HOLD`: Compounding within risk bounds.
   - `TRIM`: Weight exceeds risk caps (max 25% stock / 40% sector) or valuation is stretched.
   - `EXIT_SELL`: Critical governance redline, fundamental deterioration, or loss of moat.
2. **Capital Delta & Share Sizing:** Computes exact integer shares to buy/sell and cash required/unlocked.
3. **Multi-Horizon Wealth Projections:** Estimates portfolio value at 1-Year, 3-Year, and 5-Year horizons across Bull, Base, and Bear trajectories.

---

## 9. Backend Service, Cryptographic Security & REST API

### 9.1 FastAPI Architecture & Directory Structure
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

### 9.2 Zero-Dependency Cryptographic Authentication & RBAC
- PBKDF2 with HMAC-SHA256, 600,000 iterations, random 16-byte cryptographic salt.
- Timing-safe verification via `hmac.compare_digest`.
- Zero-external-dependency RFC 7519 JWT implementation using HS256 signatures with base64url encoding.
- RBAC roles: `admin` and `user`.

### 9.3 Complete API Endpoint Catalog
- Core & Equities: `/api/auth/login`, `/api/dashboard`, `/api/recommendations`, `/api/stock/{symbol}`, `/api/backtest/run`, `/api/health`, `/api/portfolio/health`.
- Mutual Funds: `/api/mf/schemes`, `/api/mf/schemes/{code}`, `/api/mf/schemes/{code}/nav`, `/api/mf/schemes/{code}/rolling`, `/api/mf/compare`, `/api/mf/overlap`, `/api/mf/recommend`, `/api/mf/portfolios`, `/api/mf/portfolios/{id}/tax-harvesting`.

### 9.4 Plain-English Investment Thesis Generation & PDF Reporting
Generates structured institutional prose for every recommendation (Thesis, Valuation Context, Key Risks, Invalidation Triggers), exportable as print-friendly PDF via WeasyPrint / PDFKit.

---

## 10. Frontend Client Architecture (React 19 + TypeScript + Tailwind)

### 10.1 Obsidian Dark Design System & Glassmorphism Tokens
- Background: Deep Obsidian Black (`#040508`).
- Cards: Semi-transparent Glass (`#0b0f17` with 70% opacity, `backdrop-blur-md`, border `rgba(255,255,255,0.06)`).
- Numerals: Monospace tabular formatting (`font-mono tracking-tight`).

### 10.2 Live Monospace IST Clock & Persistent Ticker Marquee
- Header: Real-time ticking Indian Standard Time digital clock (`hh:mm:ss A IST`) alongside current Indian calendar date.
- Market Ticker: CSS infinite marquee displaying live market rates (Nifty 50, Sensex, Bank Nifty, India VIX, Crude Oil, USD/INR, 10Y G-Sec) with a pulsing radio broadcast beacon.

### 10.3 The Specialized Analytical Modules
- Stock Ideas: QuickPicks slider (Top 1 to 50 equities), cross-sectional factor matrix heatmap, capital deployment calculator (₹500 to ₹10 Lakhs, whole shares).
- Lens: Factor magnifier radar, historical returns spectrum (1D to 1Y), scenario trees.
- Vault: Interactive SVG sector allocation donut, 25% stock / 40% sector cap enforcement, 66.5 bps friction calculator.
- Pulse: Interactive SVG thematic constellation radar (AI Tech, Clean Capex, Defense, Compounding Titans).
- Edge: Streaming audit feed of corporate disclosures with verified exchange timestamps.
- Mutual Funds: Scheme explorer, rolling returns visualizer, SIP wealth trajectory compounder, portfolio overlap analyzer, and tax-loss harvesting engine.
- Portfolio Health: Position-level health cards, rebalance sizing blotter, and multi-horizon forecasts.

---

## 11. Walk-Forward Backtesting Engine & Performance Metrics

### 11.1 Simulation Loop Architecture
Quarterly rebalance loop matching Indian corporate earnings cycles:
1. `PointInTimeDataAccess` extracts active Nifty 500 constituents.
2. Stage 0 liquidity screening.
3. Multi-stage quantitative scorecards computed.
4. Top 10 shortlisted.
5. Rolling 3-year covariance matrix extracted.
6. HRP optimization with caps (max 25% stock, 40% sector).
7. Trades filled at next-day open price ($T + 1$).
8. 66.5 bps transaction friction deducted.
9. Mark-to-market daily until next quarterly rebalance.

### 11.2 Exact Financial Metric Formulations
- $\text{CAGR} = (\text{Equity}_{\text{end}} / \text{Equity}_{\text{start}})^{1/\text{Years}} - 1$.
- $\text{Sharpe} = \frac{\mu(R_p - R_f)}{\sigma(R_p)} \times \sqrt{252}$ ($R_f = 6.5\%$).
- $\text{Sortino} = \frac{\mu(R_p - R_f)}{\sigma_{\text{downside}}} \times \sqrt{252}$.
- $\text{Calmar} = \frac{\text{CAGR}}{|\text{Max Drawdown}|}$.
- $\text{Annualized Turnover} = \frac{1}{2 \times \text{Years}} \sum_{t=1}^T \sum_i |w_{i, t} - w_{i, t^-}|$.

### 11.3 Transaction Fee Sensitivity Ladder
Round-trip friction ranges from 0.0 bps (unrealistic gross baseline) to 66.5 bps (realistic default: STT 10 bps, brokerage 30/20 bps, stamp duty 1.5 bps, slippage 5 bps) to 125 bps (stress case).

---

## 12. Monitoring, Data Quality & Operational Runbooks

### 12.1 Daily Data Quality Invariant Rules
1. Bhavcopy row count $> 1,500$.
2. Zero missing symbols in active Nifty 500 roster.
3. Price movement anomaly filter: jumps $> \pm 30\%$ without corporate action records halt execution.

### 12.2 Weekly Point-in-Time Zero-Lookahead Audit
Asserts `disclosed_at <= CURRENT_DATE` across all records and verifies identical backtest reproducibility.

### 12.3 Population Stability Index (PSI) & Drift Monitoring
$$PSI = \sum_{k=1}^K (\text{Actual}_k - \text{Expected}_k) \times \ln\left(\frac{\text{Actual}_k}{\text{Expected}_k}\right)$$
$PSI > 0.25$ indicates significant population drift and triggers automatic retraining recommendations.

### 12.4 Cron Scheduling Specifications
- Daily Bhavcopy Ingestion: Mon–Fri 18:30 IST.
- Daily AMFI Mutual Fund NAV Ingestion: Daily 23:00 IST.
- Daily Data Quality Audit: Mon–Fri 19:30 IST.
- Weekly PIT Zero-Lookahead Audit: Sun 02:00 IST.

---

## 13. Step-by-Step Scratch Build Blueprint

To rebuild the platform from a clean operating system:

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
*End of ArthIQ Exhaustive System Specification & Quantitative Engineering Handbook.*
