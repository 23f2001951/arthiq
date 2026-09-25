-- Arth IQ — PostgreSQL Production Schema for Neon Serverless PostgreSQL
-- Compatible with PostgreSQL 14+ / Neon

-- 1. Users Table (Enterprise RBAC)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    password_hash TEXT,
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    user_type VARCHAR(50) NOT NULL DEFAULT 'PRO_INVESTOR',
    status VARCHAR(50) NOT NULL DEFAULT 'INVITED',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(LOWER(email));

-- 2. User Portfolios (Separate Table)
CREATE TABLE IF NOT EXISTS user_portfolios (
    id VARCHAR(100) NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_user_portfolios_user ON user_portfolios(user_id);

-- 3. User Portfolio Holdings
CREATE TABLE IF NOT EXISTS user_portfolio_holdings (
    portfolio_id VARCHAR(100) NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL,
    shares DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    buy_price DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    target_price DOUBLE PRECISION,
    notes TEXT DEFAULT '',
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (portfolio_id, user_id, symbol),
    FOREIGN KEY (portfolio_id, user_id) REFERENCES user_portfolios(id, user_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_user_holdings_user ON user_portfolio_holdings(user_id);

-- 4. User Target Lists (Separate Table for tactical dips / watchlists)
CREATE TABLE IF NOT EXISTS user_target_lists (
    id VARCHAR(100) NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_user_target_lists_user ON user_target_lists(user_id);

-- 5. User Target List Items
CREATE TABLE IF NOT EXISTS user_target_list_items (
    list_id VARCHAR(100) NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL,
    shares DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    buy_price DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    target_price DOUBLE PRECISION,
    notes TEXT DEFAULT '',
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (list_id, user_id, symbol),
    FOREIGN KEY (list_id, user_id) REFERENCES user_target_lists(id, user_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_target_list_items_user ON user_target_list_items(user_id);

-- 6. Daily Prices
CREATE TABLE IF NOT EXISTS daily_prices (
    symbol VARCHAR(50) NOT NULL,
    trade_date DATE NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION NOT NULL,
    adj_close DOUBLE PRECISION,
    volume BIGINT,
    source VARCHAR(50) NOT NULL,
    PRIMARY KEY (symbol, trade_date, source)
);
CREATE INDEX IF NOT EXISTS idx_daily_prices_sym_date ON daily_prices(symbol, trade_date DESC);

-- 7. Fundamentals Quarterly
CREATE TABLE IF NOT EXISTS fundamentals_quarterly (
    symbol VARCHAR(50) NOT NULL,
    period_end DATE NOT NULL,
    disclosed_at DATE NOT NULL,
    metric VARCHAR(100) NOT NULL,
    value DOUBLE PRECISION,
    unit VARCHAR(50),
    source VARCHAR(50) NOT NULL,
    PRIMARY KEY (symbol, period_end, metric, source)
);
CREATE INDEX IF NOT EXISTS idx_fundamentals_quarterly_sym ON fundamentals_quarterly(symbol, period_end DESC);

-- 8. Fundamentals Point-in-Time (PIT)
CREATE TABLE IF NOT EXISTS fundamentals_pit (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    period_end DATE NOT NULL,
    metric VARCHAR(100) NOT NULL,
    raw_value DOUBLE PRECISION,
    restated_value DOUBLE PRECISION,
    unit VARCHAR(50) DEFAULT 'INR_CR',
    filing_timestamp TIMESTAMPTZ NOT NULL,
    effective_date DATE NOT NULL,
    revision_seq INTEGER DEFAULT 0,
    valid_from DATE NOT NULL,
    valid_to DATE DEFAULT '9999-12-31',
    source VARCHAR(50) NOT NULL,
    source_url TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_fundamentals_pit_sym_date ON fundamentals_pit(symbol, effective_date DESC);

-- 9. Corporate Actions PIT
CREATE TABLE IF NOT EXISTS corporate_actions_pit (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    ex_date DATE NOT NULL,
    record_date DATE,
    ratio_numerator DOUBLE PRECISION,
    ratio_denominator DOUBLE PRECISION,
    dividend_amount DOUBLE PRECISION,
    filing_timestamp TIMESTAMPTZ NOT NULL,
    effective_date DATE NOT NULL,
    source VARCHAR(50) NOT NULL
);

-- 10. Corporate Events PIT
CREATE TABLE IF NOT EXISTS corporate_events_pit (
    event_id VARCHAR(100) PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    headline TEXT NOT NULL,
    direction VARCHAR(50) NOT NULL,
    materiality_score DOUBLE PRECISION NOT NULL,
    confidence_score DOUBLE PRECISION NOT NULL,
    affected_factors TEXT NOT NULL,
    event_timestamp TIMESTAMPTZ NOT NULL,
    effective_date DATE NOT NULL,
    source VARCHAR(50) NOT NULL
);

-- 11. Index Constituents History
CREATE TABLE IF NOT EXISTS index_constituents_history (
    effective_date DATE NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    isin VARCHAR(50),
    sector VARCHAR(100) NOT NULL,
    source VARCHAR(50) NOT NULL,
    PRIMARY KEY (effective_date, symbol)
);

-- 12. Scorecards V2 History
CREATE TABLE IF NOT EXISTS scorecards_v2_history (
    asof_date DATE NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    sector_archetype VARCHAR(100) NOT NULL,
    business_score DOUBLE PRECISION NOT NULL,
    growth_score DOUBLE PRECISION NOT NULL,
    growth_confidence DOUBLE PRECISION NOT NULL,
    valuation_score DOUBLE PRECISION NOT NULL,
    risk_score DOUBLE PRECISION NOT NULL,
    market_score DOUBLE PRECISION NOT NULL,
    investment_score DOUBLE PRECISION NOT NULL,
    scenario_bear_ret DOUBLE PRECISION,
    scenario_base_ret DOUBLE PRECISION,
    scenario_bull_ret DOUBLE PRECISION,
    metrics_json TEXT NOT NULL,
    PRIMARY KEY (asof_date, symbol)
);

-- 13. Model Predictions
CREATE TABLE IF NOT EXISTS model_predictions (
    asof_date DATE NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    p_outperform DOUBLE PRECISION,
    rank_in_universe INTEGER,
    features_json TEXT,
    PRIMARY KEY (asof_date, symbol, model_name)
);

-- 14. News Sentiment
CREATE TABLE IF NOT EXISTS news_sentiment (
    headline_id VARCHAR(255) PRIMARY KEY,
    symbol VARCHAR(50),
    published_at DATE NOT NULL,
    headline TEXT NOT NULL,
    source VARCHAR(100),
    sentiment_score DOUBLE PRECISION,
    model_version VARCHAR(50),
    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 15. Backtest Runs
CREATE TABLE IF NOT EXISTS backtest_runs (
    run_id VARCHAR(100) PRIMARY KEY,
    started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMPTZ,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    config_json TEXT NOT NULL,
    cagr DOUBLE PRECISION,
    sharpe DOUBLE PRECISION,
    max_drawdown DOUBLE PRECISION,
    turnover_avg DOUBLE PRECISION,
    benchmark_cagr DOUBLE PRECISION,
    status VARCHAR(50)
);

-- 16. Portfolio History
CREATE TABLE IF NOT EXISTS portfolio_history (
    run_id VARCHAR(100) NOT NULL,
    asof_date DATE NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    target_weight DOUBLE PRECISION NOT NULL,
    action VARCHAR(50) NOT NULL,
    shares_target INTEGER,
    rationale_text TEXT,
    executed INTEGER DEFAULT 0,
    PRIMARY KEY (run_id, symbol)
);

-- 17. Schema Version Tracker
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    applied_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
