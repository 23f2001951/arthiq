# Arth IQ — Comprehensive Prototype Architecture, Implementation & Future AI Roadmap

> **Tagline:** Arth IQ — Your Personal Investment Intelligence Engine  
> **Repository:** `arth-iq` | **Engine:** `arth-iq-engine` | **Data:** `arth-iq-data`  
> **Date:** September 2026 | **Current Version:** V0.3.1-alpha (Predictive Model Validation Sprint)  
> **Completed Core:** V0.3 (Predictive Intelligence ML Engine)  
> **Frozen Baseline:** V0.2.1 (Audited Institutional Deterministic Research Baseline)

---

## 1. Executive Summary

**Arth IQ** is an institutional-grade, personal investment decision-support platform designed for Indian equities (NSE 500 universe). Built to eliminate information overload and subjective bias, Arth IQ integrates:
- **Point-in-Time (PIT) anti-lookahead financial data architecture.**
- **Multi-factor quantitative ranking** combining Quality, Sector-Aware Valuation, Risk, Growth, and Sentiment.
- **Hierarchical Risk Parity (HRP)** portfolio optimization with hard risk caps (max 25% single stock, max 40% sector).
- **V0.2.1 Audited Baseline**: Complete mathematical reconciliation (CAGR formula match, future date clamping, transaction fee sensitivity ladder, factor ablation, optimizer benchmarking).
- **V0.3 Predictive Intelligence**: Dual-track expansion introducing full Nifty 500 universe scaling alongside walk-forward calibrated machine learning (LightGBM/XGBoost) to resolve HRP cyclical drag.

This document records the exact architecture of the prototype built to date, its features, full tech stack, and the technical blueprint for the production AI/ML engine.

---

## 2. Complete Feature Breakdown of Current Prototype

### 2.1 Navigation & Global Controls
- **Branded Navbar**:
  - `Arth_IQ.png` logo with glowing amber ambient frame and live health beacon.
  - Tab navigation: **Dashboard** and **Stock Ideas**.
  - **Live IST Clock & Calendar**: Real-time ticking Indian Standard Time clock (`hh:mm:ss A`) placed directly below the current Indian Standard Date (`Day, DD Mon YYYY`) with `IST` monospace badge.
  - **Profile Quant Menu**: Houses advanced tools (**Walk-Forward Backtest Lab**, **Point-in-Time Health Audits**, **Model Weights**, **FastAPI Swagger Docs**, and **Lock Engine / Sign Out**).
- **Market Ticker Tape**:
  - Infinitely scrolling marquee featuring Nifty 50, Sensex, Bank Nifty, India VIX, top equities, USD/INR, Brent Crude, and 10Y G-Sec.
  - Persistent **NSE LIVE** radio broadcast badge with pulsing signal beacon.
- **Single-User Password Gate (`AuthGate.tsx`)**:
  - Obsidian glass card with radial blue/cyan/amber mesh glows.
  - Master password verification (`arth` default, overridable via `ARTH_IQ_PASSWORD` environment variable or `settings.yaml`).
  - Eye visibility toggle, auto-focus, haptic-style error shake animation, and 72-hour session persistence in `localStorage`.

---

### 2.2 The Five Core Quantitative Modules (Under NSE Live)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             NAVBAR (Live IST Clock)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                          NSE LIVE TICKER TAPE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ [Stock Ideas & Alpha Picks]  [Lens]  [Vault]  [Pulse]  [Edge]  (Sub-Navbar) │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 1. Stock Ideas & Alpha Picks
- **Triple View Mode Switcher**:
  1. *Top N Alpha Picks (Quick Picks)*: Concentrated selection of top $N$ equities (flexible slider from 1 to 50 stocks, default 2) optimized for immediate deployment.
  2. *Cross-Sectional Factor Matrix*: Full heatmap grid displaying Quality, Valuation, Risk, and Sentiment overlay percentiles.
  3. *Detailed Stock Cards*: Comprehensive cards displaying factor dials, plain-English rationales, and target weights.
- **Interactive Capital Deployment Calculator**:
  - Accepts any capital from ₹500 to ₹10,00,000 (1 Million) with quick preset chips (₹10K, ₹25K, ₹50K, ₹1L, ₹5L).
  - Micro-capital allocator calculating exact whole shares per stock.
  - Intelligent shortfall warnings when share prices exceed allocated slice, suggesting optimal adjustments.
- **As-Of Date Selector**: Defaulted to current live date with historical point-in-time date traversal.
- **Sector Filtering**: Dynamically filters recommendations across all 11 NSE sectors.

#### 2. Lens (Factor Diagnostic Magnifier)
- **Deep-Dive Stock Inspector**: Select any NSE 500 stock (e.g. TCS, RELIANCE, INFY, ICICIBANK, LT) or search via live filter.
- **Historical Return Spectrum**: 1D, 5D, 1M, 6M, and 1Y performance grid.
- **Four Pillar Factor Diagnostics**:
  - *Quality*: ROCE (Return on Capital Employed), Operating Profit Margin stability, Debt-to-Equity.
  - *Valuation*: Trailing P/E, 3-year median P/E discount, EV/EBITDA, Price-to-Book.
  - *Risk*: 365-day Beta, Maximum 5-day Drawdown, Annualized Volatility, Minimum Traded Value liquidity checks.
  - *Sentiment*: News velocity, media headline tone, sentiment points overlay (+0 to +10 pts).
- **Plain-English Quant Thesis**: Dynamic textual synthesis explaining why the stock is ranked in its decile.
- **Peer Standing**: Sector rank and NSE 500 percentile standing.

#### 3. Vault (Portfolio Allocation & Asset Architecture)
- **Sector Diversification Donut**: SVG-rendered visual allocation ring displaying sector exposures against hard limits.
- **Hard Risk Cap Enforcements**:
  - Max single stock weight: **25.0%** (strict upper bound).
  - Max sector exposure: **40.0%** (industry contagion barrier).
- **Execution Cost Buffers**: Explicitly models 30 bps buy commission, 20 bps sell commission, and 5 bps slippage.
- **Active Vault Allocations Table**: Displays exact symbol, sector, target weight, target shares, buy/hold action, and execution state.

#### 4. Pulse (Thematic Quant Radar)
- **Connected Factor Neural Constellation**: Interactive SVG constellation diagram connecting thematic clusters.
- **Monitored Thematic Clusters**:
  1. *AI & Enterprise Tech*: Cloud migration, GenAI architecture (TCS, INFY, HCLTECH, TECHM).
  2. *Energy Transition & Clean Capex*: Solar, hydrogen, and grid transmission (RELIANCE, NTPC, POWERGRID, TATAPOWER).
  3. *High ROCE Compounding Titans*: Moated consumer/tech leaders with >35% ROCE and negative working capital (TCS, NESTLEIND, TITAN, ITC).
  4. *Private Banking & Credit Expansion*: Retail credit expansion with declining NPA ratios (ICICIBANK, HDFCBANK, AXISBANK, KOTAKBANK).
  5. *Defense & Make-in-India Supercycle*: Indigenisation order book ramp (LT, BEL, HAL, BHARATFORG).
- **Cluster Diagnostics**: Constituent basket weights, daily price change, aggregate composite score, and sentiment velocity.

#### 5. Edge (Real-Time Signals & Event Stream)
- **Streaming Event Feed**: Continuous audit stream of company disclosures, volume breakouts, and model migrations.
- **Filter Categories**: All Signals, Earnings & Results, Volume & Breakouts, Factor Upgrades, Risk Diagnostics.
- **Point-in-Time Timestamped Badges**: Every alert is tagged with verified disclosure time to assure zero lookahead.
- **Model Impact Scoring**: Highlights real-time factor score adjustments (e.g. `+4.5 Factor Pts` on PAT beat).

---

### 2.3 Executive Dashboard (`DashboardView.tsx`)
- **Portfolio KPIs**: Latest Portfolio Value, Target Holdings (8), Max Stock Cap (25%), Max Sector Cap (40%).
- **Market Regime Arc Gauge**: SVG speedometer displaying Current Market Volatility Regime (Low Volatility / Neutral / High Volatility).
- **Capsule Bar Chart**: Modern capsule-styled performance bars highlighting top gainers vs benchmark.
- **Five Powerful Tools Bento**: Interactive 2x2+1 grid showcasing Lens, Vault, Pulse, and Edge with direct sub-tab routing.
- **Order Blotter & Sizing Calculator**: Quick calculator computing required capital and fractional allocations.

---

### 2.4 Walk-Forward Backtest Lab (`BacktestView.tsx`)
- **Out-of-Sample Quarterly Engine**: Simulates quarterly rebalances across 2016–2026 without future data leakage.
- **Metrics Summary**:
  - Compound Annual Growth Rate (CAGR) vs Benchmark CAGR.
  - Sharpe Ratio, Sortino Ratio, Calmar Ratio.
  - Maximum Drawdown (MDD) & Annualized Volatility.
  - Portfolio Turnover & Rebalance Count.
  - Hit Rate (% of quarters outperforming benchmark).
  - Worst 5-day Return.
- **Interactive Dual Equity Curve**: Recharts portfolio equity vs Nifty 500 TRI benchmark over time.
- **Historical Runs Archive**: Persisted table of backtest runs stored in SQLite.

---

### 2.5 Monitoring & Point-in-Time Health Lab (`HealthView.tsx`)
- **Zero-Lookahead Audits**:
  - Barred restatement check: Verifies financial restatements from later quarters are invisible on historical evaluation dates.
  - Unannounced quarter audit: Guarantees Q4 results are never accessed prior to official public disclosure date.
  - Future price barrier: Verifies prices after $t$ cannot be seen on as-of date $t$.
- **Data Quality Checks**:
  - Null check across critical fundamental fields (PAT, Equity, Debt, Revenue).
  - Stale price detection (>5 business days without update).
  - Price jump / corporate action outlier filter (>30% single-day change without split record).

---

## 3. Technology Stack Specification

| Tier | Technology | Purpose & Implementation |
| :--- | :--- | :--- |
| **Frontend Framework** | **React 19** + **TypeScript** | High-performance SPA with strict typing and modern hook lifecycle |
| **Bundler & Tooling** | **Vite 6** | Ultra-fast HMR and optimized production asset compilation |
| **Styling & Design System**| **Tailwind CSS 3.4** | Deep Obsidian Dark palette (`#040508`), Winsor Blue (`#1d4ed8`), Sky Cyan (`#0284c7`), Emerald (`#10b981`), Gold Amber (`#f59e0b`), Glassmorphism, Tabular Numerals |
| **Iconography** | **Lucide React** | Lightweight SVG iconography |
| **Backend API** | **FastAPI** + **Uvicorn** | High-throughput async REST API with automatic OpenAPI / Swagger generation |
| **Data Validation** | **Pydantic v2** | Strict schema validation, request/response serialization |
| **Database** | **SQLite 3** with **WAL Mode** | Local, serverless, single-file relational store with Write-Ahead Logging for high concurrency |
| **Configuration** | **PyYAML** + Custom `ConfigNode` | Hierarchical configuration management with environment variable overrides |
| **Authentication** | `secrets` + `hmac.compare_digest` | 256-bit cryptographic bearer session tokens with timing-safe comparison |
| **Testing** | **Pytest 9.1** + `pytest-cov` | 97 unit and integration tests with scoring fixtures and temporary in-memory databases |
| **Code Quality & Linting** | **Ruff** (v0.9) | Python formatting, import sorting, and strict PEP-8 compliance |

---

## 4. Current Prototype Implementation Architecture

### 4.1 Directory Structure
```
invst/
├── config/                      # YAML configuration files
│   ├── settings.yaml            # Main project, auth, risk, and backtest config
│   ├── scoring_weights.yaml     # Weights for Quality, Valuation, Risk, Composite
│   └── sectors.yaml             # NSE 500 sector mappings and caps
├── data/                        # Local raw, interim, and processed data directories
├── db/
│   ├── invst.db                 # Primary SQLite WAL database (seeded with 1,300 days)
│   └── schema.sql               # Relational table definitions and PIT indexes
├── src/invst/
│   ├── api/                     # FastAPI backend
│   │   ├── app.py               # Application factory & static SPA mounting
│   │   ├── auth.py              # Single-user session and password verification
│   │   ├── routes.py            # REST endpoints (Dashboard, Recs, Backtest, Health)
│   │   └── schemas.py           # Pydantic data schemas
│   ├── backtest/                # Walk-forward simulation engine
│   ├── data_access/             # PointInTimeDataAccess abstraction
│   ├── ingestion/               # Bhavcopy, yfinance, and news RSS parsers
│   ├── ml/                      # Machine learning classifiers & drift detectors
│   ├── monitoring/              # PIT audit rules & data quality checks
│   ├── optimization/            # Inverse-volatility weighting & cap optimizer
│   ├── reporting/               # Plain-English rationale generator & HTML reports
│   └── scoring/                 # Filters, Quality, Valuation, Risk, Sentiment modules
├── tests/                       # 97 Pytest automated integration test suite
└── frontend/                    # React 19 SPA source code
    ├── src/
    │   ├── api/client.ts        # Fetch client with token header injection
    │   ├── components/          # Reusable UI components (AuthGate, SubNav, Cards)
    │   │   ├── AuthGate.tsx     # Master password screen
    │   │   ├── StockIdeasSubNav.tsx # Sub-navbar under NSE Live
    │   │   ├── LensView.tsx     # Factor magnifier view
    │   │   ├── VaultView.tsx    # Portfolio allocation & risk caps view
    │   │   ├── PulseView.tsx    # Thematic quant radar view
    │   │   └── EdgeView.tsx     # Real-time event stream view
    │   ├── views/               # Top-level views (Dashboard, Recs, Backtest, Health)
    │   └── App.tsx              # Root application container & auth lifecycle
```

### 4.2 Multi-Factor Scoring Formulation
Every stock in the universe is evaluated through a strict multi-stage quantitative pipeline:

1. **Stage 0: Liquidity & Solvency Screening**:
   $$\text{Screened} = (\text{Median Traded Value}_{30d} \ge ₹5\text{ Cr}) \land (\text{Market Cap} \ge ₹1000\text{ Cr}) \land (\text{Price} \ge ₹10) \land (\text{Listing Age} \ge 3\text{ yrs})$$

2. **Stage 1: Quality Score (Weight: 40%)**:
   $$Q = 0.40 \cdot \text{Pct}(\text{ROCE}) + 0.35 \cdot \text{Pct}(\text{Operating Margin Stability}) + 0.25 \cdot \text{Pct}(1 / (1 + \text{Debt-to-Equity}))$$

3. **Stage 2: Valuation Score (Weight: 30%)**:
   $$V = 0.40 \cdot \text{Pct}(1 / \text{PE}) + 0.30 \cdot \text{Pct}(\text{PE}_{3y\text{ median}} / \text{PE}_{\text{current}}) + 0.30 \cdot \text{Pct}(1 / \text{EV/EBITDA})$$

4. **Stage 3: Risk Score (Weight: 30%)**:
   $$R = 0.40 \cdot \text{Pct}(1 / \text{Beta}_{365d}) + 0.35 \cdot \text{Pct}(1 / \text{Max 5D Drawdown}) + 0.25 \cdot \text{Pct}(1 / \text{Annualized Volatility})$$

5. **Stage 4: Sentiment Overlay**:
   $$\text{Composite Score} = (0.40 \cdot Q + 0.30 \cdot V + 0.30 \cdot R) + \text{Sentiment Overlay Points} \in [-10, +10]$$

---

## 5. Future AI & Machine Learning Roadmap (Production Engine)

The current prototype successfully proves the data access contracts, portfolio constraints, zero-lookahead database architecture, and visual interface. The next phase transitions from heuristic multi-factor scoring to a **dual-engine Machine Learning & LLM Reasoning system**.

```mermaid
flowchart TD
    subgraph Data Layer [1. Point-in-Time Data Infrastructure]
        A[(Point-in-Time SQLite DB)] --> B[Daily Bhavcopy & Prices]
        A --> C[Quarterly PIT Financials: 45d/60d Lag]
        A --> D[Corporate Actions & Restatements]
        A --> E[Index Constituents History: Nifty 500 PIT]
    end

    subgraph Feature & Regime Engine [2. Feature Extraction & Market Regime]
        B & C & D & E --> F[Feature Store: 24 PIT Factors]
        F --> REG[Regime Engine: Bull/Bear, Volatility Asymmetry, India VIX]
    end

    subgraph Dual Signal Generation [3. Signal Ensemble Layer]
        REG --> G[Deterministic Fundamental Engine: Quality, Moats, Valuation]
        REG --> ML1[ML Direction Model: P(Alpha > 0) via Calibrated Boosters]
        REG --> ML2[ML Magnitude Model: Expected Excess Return E(R_excess)]
    end

    subgraph Confidence & Risk Engine [4. Confidence Layer & Risk Controls]
        G & ML1 & ML2 --> CONF[Confidence Engine: Calibration x Regime Agreement x Fundamental Match]
        CONF --> RISK[Risk Engine: HRP Covariance Tree, Semivariance, Tail Risk]
        RISK --> OPT[Portfolio Optimizer: Hard Caps: Max 25% Stock, Max 40% Sector]
    end

    subgraph Decision Intelligence [5. Output & User Deliverables]
        OPT --> PORT[Portfolio Allocations: Integer Sizing & Target Weights]
        G & CONF --> THESIS[Structured Investment Thesis: Why / Risks / Invalidation Triggers]
        PORT & THESIS --> UI[Arth IQ Obsidian Dashboard & Broker Bridge]
    end
```

---

### 5.1 Phase 1: Predictive Machine Learning Core

#### A. Objective & Label Definition
Rather than predicting noisy raw stock prices, the machine learning model is trained to predict the **probability that stock $i$ will outperform the benchmark (Nifty 500 TRI) over the next 90-day holding period**:
$$y_{i, t} = \mathbb{I}\left( R_{i, [t, t+90]} - R_{\text{benchmark}, [t, t+90]} > 0 \right)$$

#### B. Walk-Forward Expanding & Rolling Window Training
To prevent data leakage and simulate real production operation:
- **Training Window:** 5 years (20 quarters) of quarterly point-in-time cross-sections.
- **Evaluation Window:** The subsequent out-of-sample quarter.
- **Roll Forward:** Step forward by 1 quarter, re-train model on the expanded dataset, and predict the next quarter.
- **Strict Cutoff:** All features are extracted strictly as of the market close of the rebalance date.

#### C. Model Architecture: Calibrated Gradient Boosting
- **Algorithms:** LightGBM and XGBoost with ranking objectives (`lambdarank` or `binary:logistic`).
- **Probability Calibration:**
  - Raw boosting outputs are calibrated using **Isotonic Regression** or **Platt Scaling** on an out-of-fold validation split.
  - Ensures that when the model outputs $P = 0.70$, exactly 70% of such picks historically outperformed the benchmark.
- **Brier Score Optimization:** Track Brier score ($BS = \frac{1}{N} \sum (p_i - y_i)^2$) and reliability diagrams to prevent overconfidence.

#### D. Engineered Feature Set
1. *Fundamental Momentum:* $\Delta \text{ROCE}_{YoY}$, $\Delta \text{Operating Margin}_{QoQ}$, Free Cash Flow Yield.
2. *Price Momentum & Reversal:* 12-Month Momentum minus 1-Month Short-Term Reversal ($M_{12-1}$).
3. *Volatility & Downside Asymmetry:* Downside Semivariance, Tail Risk, 30-day Volume Volatility.
4. *Valuation Disconnect:* Z-score of EV/EBITDA relative to the stock's own 3-year historical distribution.

---

### 5.2 Phase 2: Financial NLP & Sentiment Engine

#### A. Data Pipeline
1. **Exchange Filings:** Ingest corporate announcement PDFs from NSE/BSE announcements API.
2. **Earnings Call Transcripts:** Ingest quarterly earnings transcripts for Nifty 500 companies.
3. **Financial Media & RSS:** Ingest curated financial press releases (Economic Times, Livemint, Moneycontrol).

#### B. NLP Model Architecture
- **Embedding & Classification Model:** Fine-tuned `FinBERT` or domain-adapted small language model (SLM) trained on Indian equity disclosures.
- **Extracted Signals:**
  - *Management Guidance Sentiment:* Quantifies whether management raised, maintained, or lowered forward guidance.
  - *Capex Acceleration Index:* Detects announced greenfield/brownfield capital expenditure vs debt capacity.
  - *Governance & Red Flags:* Scans for auditor resignations, board dispute mentions, related-party transaction surges.
- **Overlay Calibration:** Converts raw sentiment scores into bounded $[-10, +10]$ point adjustments applied directly to the composite scorecard.

---

### 5.3 Phase 3: Generative AI Reasoning & Explainability

#### A. Structured LLM Rationale Generation
In production, plain-English rationales will not be hardcoded templates. Instead, an LLM agent will synthesize quantitative scorecards into natural institutional summaries:
- **Input Context to LLM:**
  - Stock symbol, sector, and current market price.
  - Percentile ranks across Quality, Valuation, Risk, and Sentiment.
  - Exact financial metrics (e.g. `ROCE = 48.2%`, `Debt/Eq = 0.00`, `P/E = 26.4 vs 3Y Med 31.2`).
  - Key positive and negative catalyst headlines.
- **Prompt Guardrails:**
  - Strict tone guidelines: Factual, concise, institutional, devoid of hype or promotional language.
  - Explicit requirement to state at least one key risk or potential headwind for balance.

#### B. Interactive Multi-Turn Quant Assistant ("Artha AI")
- Embedded chat interface where users can interrogate any recommendation:
  - *"Why is ICICI Bank ranked above HDFC Bank this quarter?"*
  - *"What happens to my portfolio risk if crude oil surges above \$90?"*
  - *"Which stocks in my Vault have the lowest beta in market corrections?"*
- Answers are generated using **Retrieval-Augmented Generation (RAG)** grounded entirely on the SQLite database and PIT disclosures.

---

### 5.4 The Arth IQ Decision Function & Confidence Engine (V0.4 Core)

Arth IQ is designed not as a simple stock predictor, but as an **institutional quantitative decision engine**. Rather than using an opaque multiplicative formula that risks runaway sensitivity, V0.4 adopts a transparent **normalized additive decision framework**:

$$\boxed{\text{ArthScore}_i = w_F F_i + w_M M_i + w_E E_i + w_R R_i + w_H H_i}$$

Where:
- $F_i$ = Fundamental conviction (Quality + Moat + Solvency) $\in [0, 100]$
- $M_i$ = ML directional conviction $\in [0, 100]$
- $E_i$ = Expected alpha magnitude
- $R_i$ = Risk-adjusted edge ($\mathbb{E}[R_{\text{excess}, i}] / \sigma_{\text{downside}, i}$)
- $H_i$ = Horizon fit (30D, 90D, 1Y, 3Y, 5Y)
- Normalized weights: $w_F + w_M + w_E + w_R + w_H = 1.0$

#### A. The Confidence Formulation & Signal Agreement
Confidence is modeled as cross-pillar consensus rather than model margin alone:
$$\text{Confidence}_i = f\left(\text{Calibration Quality}, \text{Fundamental Score}, \text{Regime Agreement}, \text{Data Quality}\right)$$
- **High Conviction Tilt:** When ML, Fundamentals, and Regime align with low calibration error (e.g. Fundamental Score = 92, ML Confidence = 73%, Risk = Low, Regime = Bull).
- **Core Anchor (ML Disagreement):** When Fundamentals are strong but ML disagrees or regime is adverse (e.g. Fundamental = 92, ML = 41%, Regime = Bear), hold core fundamental weight and do not aggressively tilt.

#### B. Two-Stage Alpha Architecture
1. **Stage 1 (Directional Classifier):** $P(R_{i, [t, t+h]} - R_{\text{bench}, [t, t+h]} > 0)$ calibrated via Platt scaling.
2. **Stage 2 (Magnitude Regressor):** Estimates expected excess alpha $\mathbb{E}[R_{\text{excess}}]$ conditioned on positive direction.
3. **Risk-Adjusted Edge:**
   $$\text{RiskAdjustedEdge}_i = \frac{\mathbb{E}[R_{\text{excess}, i}]}{\sigma_{\text{downside}, i}}$$

#### C. Horizon as a First-Class Citizen
The decision function adapts to user-specified investment horizons rather than a single fixed quarter:
- **30 Days / 90 Days:** High momentum and volatility mean-reversion awareness.
- **1 Year / 3 Years:** Multi-year ROCE compounding, moat durability, and valuation re-rating.

#### D. The Primary User Deliverable: Portfolio + Structured Thesis
Every recommendation outputs a complete portfolio allocation accompanied by a structured investment thesis:
1. **Why We Like It:** Earnings momentum, balance sheet de-leveraging, ROCE compounding.
2. **Key Risks:** Sector cyclicality, valuation multiple compression, raw material inflation.
3. **Thesis Invalidation Triggers:** ROCE drop $> 300\text{ bps}$, debt acceleration, earnings downgrade.
4. **Next Review Trigger:** Scheduled date of next quarterly board results.

---

### 5.5 Phase 5: Broker Integration & Execution Bridge

1. **Broker APIs:** Integrate with Zerodha Kite Connect API and Upstox API.
2. **One-Click Basket Orders:**
   - On quarterly rebalance day, Arth IQ compiles the exact delta between current held positions and the newly generated target holdings.
   - Generates a pre-populated basket order payload.
   - User reviews order quantities, limits, and slippage buffer, then authorizes with broker 2FA/TOTP.
3. **Execution Blotter Reconciliation:**
   - Receives post-trade execution reports from broker webhook.
   - Reconciles actual filled prices vs model theoretical prices, updating realized cash and tracking error.

---

### 5.6 Phase 6: Model Monitoring & Continuous Drift Auditing

1. **Population Stability Index (PSI):**
   - Monitors distribution shifts in feature inputs between training baseline and live inference.
   - Triggers an alert if $\text{PSI} > 0.25$, indicating that market regime shift requires model retraining.
2. **Strategy Divergence Tracking:**
   - Tracks tracking error and active share between model target portfolio and user's actual broker holdings.
3. **Automated Cron Audits:**
   - Daily cron jobs executing `run_all_data_quality_checks()` and `run_full_pit_audit()` to ensure zero corruption of historical price or fundamental records.

---

## 6. Milestone Schedule & Roadmap Summary

```
V0.2.1 (Audited Base) ───► V0.3 (ML Engine) ──────► V0.3.1 (Diagnosis Complete) ────► V0.4 (Decision Intelligence)
• SQLite PIT schema        • LightGBM walk-forward  • Standalone ML alpha falsified    • Normalized additive score
• Multi-factor scoring     • 24 PIT features        • 0 PIT lookahead violations       • Signal agreement logic
• HRP Optimizer + caps     • Expanding windows      • Negative Rank IC (-0.0909)       • Controlled 8-set ablation
• Reconciliation audit     • ML-Tilted HRP          • Platt Calibration != Alpha       • Reverse & Quintile tests
• 20-Stock core seed       • Nifty 500 roster       • 2024–2026 Test Partition Frozen  • Downstream Artha AI (LLM)
```

### Institutional Model Registry
| Model Component | Status | Empirical Rationale | Target Next Step |
|:---|:---:|:---|:---|
| **Deterministic V0.2.1 Engine** | **BASELINE** | 4.60% CAGR, -38.49% MDD, 0 PIT violations | Production research anchor |
| **Full 24-Feature ML Model** | **REJECTED** | Negative Rank IC (-0.0909), L/S -7.28%, Inverted Quintiles ($Q1 > Q5$) | Decommission as standalone |
| **Platt + 50/50 + $\gamma=0.50$** | **REJECTED** | 4.25% CAGR (underperformed 4.60% baseline; 2024–2026 delta -0.53%) | Discard as production default |
| **Reverse Signal ($1 - P$)** | **RESEARCH** | Rank IC +0.0909, L/S +7.76% (indicates systematic model inversion) | Multi-horizon diagnostic only |
| **Fundamentals-Only (Set A)** | **CANDIDATE** | Rank IC +0.0179, 60% Pos IC, +4.99% L/S return, $Q5 > Q1$ spread +0.0076 | Phase A multi-horizon validation |
| **Multi-Horizon Models (30D-252D)**| **RESEARCH** | Isolate horizon where fundamental vs momentum alpha peaks | Horizon decay testing |
| **Sector / Beta Neutral Signals**| **RESEARCH** | Test if alpha survives industry and market factor controls | Neutralization evaluation |
| **Nifty 500 Historical PIT** | **PLANNED** | Full cross-sectional sample expansion across 500 equities | Ingestion & backfill |

### The 8 Institutional Model Promotion Gates
Before any predictive model can influence portfolio allocations, it must pass 8 binary gates:
1. **Gate 1 (Data Integrity):** Zero lookahead violations across 100% of historical rebalance windows.
2. **Gate 2 (Statistical Signal):** Positive Spearman Rank IC (> 0.00) and positive Information Ratio ($\text{IC IR} > 0.00$).
3. **Gate 3 (Cross-Sectional Ranking):** Monotonic quintile progression with positive top-minus-bottom spread ($Q5 > Q1$).
4. **Gate 4 (Temporal Stability):** Signal persists across multiple economic regimes without single-period reliance.
5. **Gate 5 (Untouched Test Performance):** Positive incremental Sharpe/alpha on a frozen, unseen out-of-sample window.
6. **Gate 6 (Economic Rationale):** Documented causal economic mechanism (not spurious data-mining).
7. **Gate 7 (Transaction Cost Robustness):** Net alpha survives brokerage (30 bps buy, 20 bps sell), 5 bps slippage, and turnover drag.
8. **Gate 8 (Portfolio Value-Add):** Demonstrates empirical improvement in portfolio Sharpe, Sortino, or drawdown vs baseline.

### V0.4 Eight-Phase Research Sequence:
- **Phase A (Signal Isolation):** Independently validate Fundamentals, Valuation, Risk, Momentum, Sentiment, and Events.
- **Phase B (Leave-One-Group-Out / Interaction):** LOGO analysis isolating the exact feature family causing signal inversion.
- **Phase C (Multi-Horizon Decay):** Measure signal decay across 30D, 60D, 90D, 180D, and 252D.
- **Phase D (Factor Neutralization):** Sector-neutral and Beta-neutral testing to verify pure stock-selection edge.
- **Phase E (Nifty 500 Scale):** Re-test frozen candidate on full 500-stock PIT historical universe.
- **Phase F (Statistical Significance):** Block bootstrap 95% confidence intervals, t-statistics, and permutation tests.
- **Phase G (Fresh Untouched Test):** Evaluate on newly frozen future test partition.
- **Phase H (Hierarchical Decision Integration):** Integrate into $\text{Portfolio Conviction} = \text{Investment Thesis} \times \text{Market Context} \times \text{Risk Adjustment}$.

---

## 7. Conclusion

The **Arth IQ** prototype establishes a solid, tested foundation: a zero-lookahead point-in-time database, rigorous multi-factor scoring mechanics, portfolio risk controls, an obsidian glass frontend with five specialized tools (Stock Ideas, Lens, Vault, Pulse, Edge), and single-user password protection. 

The architecture is deliberately modular, enabling the Machine Learning probability models and LLM synthesis pipelines to drop into the existing FastAPI service without altering frontend contracts or database structures.
