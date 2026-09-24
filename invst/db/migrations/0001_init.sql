-- Migration: 0001_init.sql
-- Description: Initial schema for invst database
-- Date: 2026-09-20

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- 1. Historical Nifty 500 constituent list (point-in-time)
CREATE TABLE IF NOT EXISTS index_constituents_history (
    effective_date   DATE    NOT NULL,
    symbol           TEXT    NOT NULL,
    isin             TEXT,
    sector           TEXT    NOT NULL,
    source           TEXT    NOT NULL,
    PRIMARY KEY (effective_date, symbol)
);
CREATE INDEX IF NOT EXISTS idx_ich_symbol ON index_constituents_history(symbol);
CREATE INDEX IF NOT EXISTS idx_ich_effdate ON index_constituents_history(effective_date);

-- 2. Daily OHLCV (point-in-time by trade_date)
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

-- 3. Quarterly fundamentals (point-in-time by disclosed_at)
CREATE TABLE IF NOT EXISTS fundamentals_quarterly (
    symbol           TEXT    NOT NULL,
    period_end       DATE    NOT NULL,
    disclosed_at     DATE    NOT NULL,
    metric           TEXT    NOT NULL,
    value            REAL,
    unit             TEXT,
    source           TEXT    NOT NULL,
    PRIMARY KEY (symbol, period_end, metric, source)
);
CREATE INDEX IF NOT EXISTS idx_fq_pit ON fundamentals_quarterly(symbol, metric, disclosed_at);

-- 4. News + sentiment
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

-- 5. Model predictions (walk-forward, point-in-time)
CREATE TABLE IF NOT EXISTS model_predictions (
    asof_date        DATE    NOT NULL,
    symbol           TEXT    NOT NULL,
    model_name       TEXT    NOT NULL,
    p_outperform     REAL,
    rank_in_universe INTEGER,
    features_json    TEXT,
    PRIMARY KEY (asof_date, symbol, model_name)
);

-- 6. Portfolio history
CREATE TABLE IF NOT EXISTS portfolio_history (
    run_id           TEXT    NOT NULL,
    asof_date        DATE    NOT NULL,
    symbol           TEXT    NOT NULL,
    target_weight    REAL    NOT NULL,
    action           TEXT    NOT NULL,
    shares_target    INTEGER,
    rationale_text   TEXT,
    executed         INTEGER DEFAULT 0,
    PRIMARY KEY (run_id, symbol)
);

-- 7. Backtest runs
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

-- Schema version tracking (used by migrate.py)
CREATE TABLE IF NOT EXISTS schema_version (
    version          INTEGER PRIMARY KEY,
    filename         TEXT    NOT NULL,
    applied_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO schema_version (version, filename) VALUES (1, '0001_init.sql');
