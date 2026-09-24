# Architecture Overview

## System Context & Design Philosophy
`invst` is a personal decision-support tool for Indian equities (NSE/BSE, Nifty 500 universe).
It solves the problem of information overload (opening 10+ browser tabs across Screener, Tickertape, Trendlyne) by producing a **single, evidence-backed recommendation per stock** in plain English, with underlying factor numbers visible.

## Key Boundaries
- **No Auto-Trading:** The system strictly outputs recommendations. Execution is 100% manual via Zerodha Kite / Groww.
- **Rebalance Cadence:** Quarterly (every 90 days), matching Indian corporate earnings reporting cycles.
- **Single-User SQLite:** Fast, local, file-backed database with WAL mode and strict Point-in-Time access guards.

## Pipeline Flow
```
Data Ingestion (NSE/BSE Bhavcopy, yfinance, News RSS)
      │
      ▼
Point-in-Time Data Access Layer (PointInTimeDataAccess)
      │
      ▼
Quant Scoring Funnel (Filters -> Quality -> Valuation -> Risk -> Sentiment)
      │
      ▼
Constrained Optimization (Max 25% single stock, Max 40% sector, 8 holdings)
      │
      ▼
Reporting & UI (Streamlit Dashboard, HTML/PDF Reports, Plain-English Rationales)
```
