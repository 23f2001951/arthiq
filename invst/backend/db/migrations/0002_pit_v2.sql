-- Migration: 0002_pit_v2.sql
-- Description: Bi-temporal Point-in-Time schema hardening for Arth IQ V0.2
-- Date: 2026-09-20

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- 1. Bi-Temporal Fundamentals Store
CREATE TABLE IF NOT EXISTS fundamentals_pit (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol              TEXT    NOT NULL,
    period_end          DATE    NOT NULL,
    metric              TEXT    NOT NULL,
    raw_value           REAL,
    restated_value      REAL,
    unit                TEXT    DEFAULT 'INR_CR',
    filing_timestamp    DATETIME NOT NULL,
    effective_date      DATE    NOT NULL,
    revision_seq        INTEGER DEFAULT 0,
    valid_from          DATE    NOT NULL,
    valid_to            DATE    DEFAULT '9999-12-31',
    source              TEXT    NOT NULL,
    source_url          TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_funder_pit_lookup 
ON fundamentals_pit(symbol, metric, effective_date, valid_from, valid_to);
CREATE INDEX IF NOT EXISTS idx_funder_pit_period 
ON fundamentals_pit(symbol, period_end, metric);

-- 2. Corporate Actions & Capital Adjustments
CREATE TABLE IF NOT EXISTS corporate_actions_pit (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol              TEXT    NOT NULL,
    action_type         TEXT    NOT NULL, -- SPLIT, BONUS, RIGHTS, DIVIDEND
    ex_date             DATE    NOT NULL,
    record_date         DATE,
    ratio_numerator     REAL,
    ratio_denominator   REAL,
    dividend_amount     REAL,
    filing_timestamp    DATETIME NOT NULL,
    effective_date      DATE    NOT NULL,
    source              TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ca_lookup ON corporate_actions_pit(symbol, effective_date);
CREATE INDEX IF NOT EXISTS idx_ca_exdate ON corporate_actions_pit(symbol, ex_date);

-- 3. Structured Corporate Events Feed
CREATE TABLE IF NOT EXISTS corporate_events_pit (
    event_id            TEXT    PRIMARY KEY,
    symbol              TEXT    NOT NULL,
    event_type          TEXT    NOT NULL, -- EARNINGS_BEAT, REGULATORY_ACTION, MANAGEMENT_RESIGNATION, LITIGATION, CAPEX
    headline            TEXT    NOT NULL,
    direction           TEXT    NOT NULL, -- POSITIVE, NEGATIVE, NEUTRAL
    materiality_score   REAL    NOT NULL, -- 0.0 to 1.0 (calibrated impact)
    confidence_score    REAL    NOT NULL, -- 0.0 to 1.0
    affected_factors    TEXT    NOT NULL, -- JSON array e.g. ["GOVERNANCE", "RISK"]
    event_timestamp     DATETIME NOT NULL,
    effective_date      DATE    NOT NULL,
    source              TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_lookup ON corporate_events_pit(symbol, effective_date);
CREATE INDEX IF NOT EXISTS idx_events_type ON corporate_events_pit(event_type, effective_date);

-- 4. Scorecards V2 History (Decoupled Business & Investment Scores)
CREATE TABLE IF NOT EXISTS scorecards_v2_history (
    asof_date            DATE    NOT NULL,
    symbol               TEXT    NOT NULL,
    sector_archetype     TEXT    NOT NULL,
    business_score       REAL    NOT NULL,
    growth_score         REAL    NOT NULL,
    growth_confidence    REAL    NOT NULL,
    valuation_score      REAL    NOT NULL,
    risk_score           REAL    NOT NULL,
    market_score         REAL    NOT NULL,
    investment_score     REAL    NOT NULL,
    scenario_bear_ret    REAL,
    scenario_base_ret    REAL,
    scenario_bull_ret    REAL,
    metrics_json         TEXT    NOT NULL,
    PRIMARY KEY (asof_date, symbol)
);
CREATE INDEX IF NOT EXISTS idx_sc2_lookup ON scorecards_v2_history(asof_date, investment_score);
CREATE INDEX IF NOT EXISTS idx_sc2_business ON scorecards_v2_history(asof_date, business_score);
