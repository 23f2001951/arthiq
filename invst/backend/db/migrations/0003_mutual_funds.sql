-- Migration: 0003_mutual_funds.sql
-- Description: Schema for Mutual Fund intelligence, SIP schedules, transactions, and portfolio diagnostics
-- Date: 2026-09-26

PRAGMA foreign_keys = ON;

-- Clean up any prior empty prototype tables
DROP TABLE IF EXISTS sip_holdings;
DROP TABLE IF EXISTS mf_nav_cache;
DROP TABLE IF EXISTS mf_schemes;

-- 1. Mutual Fund Schemes Master
CREATE TABLE IF NOT EXISTS mf_schemes (
    scheme_code     INTEGER PRIMARY KEY,
    isin            TEXT,
    scheme_name     TEXT    NOT NULL,
    fund_house      TEXT    NOT NULL,
    category        TEXT    NOT NULL,
    plan_type       TEXT    NOT NULL DEFAULT 'Direct',
    option_type     TEXT    NOT NULL DEFAULT 'Growth',
    benchmark_index TEXT    DEFAULT 'Nifty 500 TRI',
    expense_ratio   REAL,
    aum_cr          REAL,
    fund_manager    TEXT,
    crisil_rating   INTEGER,
    risk_level      TEXT    DEFAULT 'Very High',
    inception_date  DATE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_mf_category ON mf_schemes(category);
CREATE INDEX IF NOT EXISTS idx_mf_fund_house ON mf_schemes(fund_house);
CREATE INDEX IF NOT EXISTS idx_mf_isin ON mf_schemes(isin);

-- 2. Daily NAV History
CREATE TABLE IF NOT EXISTS mf_nav_history (
    scheme_code     INTEGER NOT NULL,
    nav_date        DATE    NOT NULL,
    nav             REAL    NOT NULL,
    PRIMARY KEY (scheme_code, nav_date),
    FOREIGN KEY (scheme_code) REFERENCES mf_schemes(scheme_code) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_mf_nav_scheme_date ON mf_nav_history(scheme_code, nav_date DESC);

-- 3. Scheme Holdings (Monthly portfolio disclosures)
CREATE TABLE IF NOT EXISTS mf_holdings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    scheme_code     INTEGER NOT NULL,
    as_of_date      DATE    NOT NULL,
    company_name    TEXT    NOT NULL,
    symbol          TEXT,
    isin            TEXT,
    sector          TEXT,
    weight_pct      REAL    NOT NULL,
    FOREIGN KEY (scheme_code) REFERENCES mf_schemes(scheme_code) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_mf_holdings_scheme ON mf_holdings(scheme_code, as_of_date);
CREATE INDEX IF NOT EXISTS idx_mf_holdings_symbol ON mf_holdings(symbol);

-- 4. User Mutual Fund Portfolios
CREATE TABLE IF NOT EXISTS user_mf_portfolios (
    id              TEXT    PRIMARY KEY,
    user_id         INTEGER NOT NULL,
    name            TEXT    NOT NULL DEFAULT 'My MF Portfolio',
    notes           TEXT,
    last_saved_at   TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_user_mf_portfolios_user ON user_mf_portfolios(user_id);

-- 5. SIP Schedules (Active, Paused, Closed)
CREATE TABLE IF NOT EXISTS mf_sip_schedules (
    id              TEXT    PRIMARY KEY,
    portfolio_id    TEXT    NOT NULL,
    scheme_code     INTEGER NOT NULL,
    folio_number    TEXT,
    amount          REAL    NOT NULL,
    frequency       TEXT    DEFAULT 'MONTHLY',
    sip_day         INTEGER DEFAULT 5,
    start_date      DATE    NOT NULL,
    end_date        DATE,
    status          TEXT    NOT NULL DEFAULT 'ACTIVE',
    step_up_pct     REAL    DEFAULT 0.0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES user_mf_portfolios(id) ON DELETE CASCADE,
    FOREIGN KEY (scheme_code) REFERENCES mf_schemes(scheme_code)
);
CREATE INDEX IF NOT EXISTS idx_mf_sip_portfolio ON mf_sip_schedules(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_mf_sip_status ON mf_sip_schedules(status);

-- 6. Transactions Ledger
CREATE TABLE IF NOT EXISTS mf_transactions (
    id              TEXT    PRIMARY KEY,
    portfolio_id    TEXT    NOT NULL,
    sip_id          TEXT,
    scheme_code     INTEGER NOT NULL,
    tx_date         DATE    NOT NULL,
    tx_type         TEXT    NOT NULL,
    amount          REAL    NOT NULL,
    units           REAL    NOT NULL,
    nav             REAL    NOT NULL,
    notes           TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES user_mf_portfolios(id) ON DELETE CASCADE,
    FOREIGN KEY (sip_id) REFERENCES mf_sip_schedules(id) ON DELETE SET NULL,
    FOREIGN KEY (scheme_code) REFERENCES mf_schemes(scheme_code)
);
CREATE INDEX IF NOT EXISTS idx_mf_tx_portfolio ON mf_transactions(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_mf_tx_scheme ON mf_transactions(scheme_code);
CREATE INDEX IF NOT EXISTS idx_mf_tx_date ON mf_transactions(tx_date);

-- 7. Monthly SIP Check-in Confirmation Ledger
CREATE TABLE IF NOT EXISTS mf_sip_checkins (
    id              TEXT    PRIMARY KEY,
    portfolio_id    TEXT    NOT NULL,
    sip_id          TEXT    NOT NULL,
    scheme_code     INTEGER NOT NULL,
    due_date        DATE    NOT NULL,
    status          TEXT    NOT NULL, -- 'PAID', 'SKIPPED', 'PENDING'
    confirmed_date  DATE,
    amount          REAL    NOT NULL,
    notes           TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES user_mf_portfolios(id) ON DELETE CASCADE,
    FOREIGN KEY (sip_id) REFERENCES mf_sip_schedules(id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_mf_sip_checkin_unique ON mf_sip_checkins(sip_id, due_date);
CREATE INDEX IF NOT EXISTS idx_mf_sip_checkin_portfolio ON mf_sip_checkins(portfolio_id);
