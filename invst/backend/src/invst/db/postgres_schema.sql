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

-- 18. Mutual fund scheme master and historical NAV data
CREATE TABLE IF NOT EXISTS mf_schemes (
    scheme_code INTEGER PRIMARY KEY,
    isin TEXT,
    scheme_name TEXT NOT NULL,
    fund_house TEXT NOT NULL,
    category TEXT NOT NULL,
    plan_type TEXT NOT NULL DEFAULT 'Direct',
    option_type TEXT NOT NULL DEFAULT 'Growth',
    benchmark_index TEXT DEFAULT 'Nifty 500 TRI',
    expense_ratio DOUBLE PRECISION,
    aum_cr DOUBLE PRECISION,
    fund_manager TEXT,
    crisil_rating INTEGER,
    risk_level TEXT DEFAULT 'Very High',
    inception_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_mf_category ON mf_schemes(category);
CREATE INDEX IF NOT EXISTS idx_mf_fund_house ON mf_schemes(fund_house);
CREATE INDEX IF NOT EXISTS idx_mf_isin ON mf_schemes(isin);

CREATE TABLE IF NOT EXISTS mf_nav_history (
    scheme_code INTEGER NOT NULL REFERENCES mf_schemes(scheme_code) ON DELETE CASCADE,
    nav_date DATE NOT NULL,
    nav DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (scheme_code, nav_date)
);
CREATE INDEX IF NOT EXISTS idx_mf_nav_scheme_date ON mf_nav_history(scheme_code, nav_date DESC);

CREATE TABLE IF NOT EXISTS mf_holdings (
    id SERIAL PRIMARY KEY,
    scheme_code INTEGER NOT NULL REFERENCES mf_schemes(scheme_code) ON DELETE CASCADE,
    as_of_date DATE NOT NULL,
    company_name TEXT NOT NULL,
    symbol TEXT,
    isin TEXT,
    sector TEXT,
    weight_pct DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mf_holdings_scheme ON mf_holdings(scheme_code, as_of_date);
CREATE INDEX IF NOT EXISTS idx_mf_holdings_symbol ON mf_holdings(symbol);

-- 19. User mutual-fund portfolios and SIP ledgers
CREATE TABLE IF NOT EXISTS user_mf_portfolios (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL DEFAULT 'My MF Portfolio',
    notes TEXT,
    last_saved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_user_mf_portfolios_user ON user_mf_portfolios(user_id);

CREATE TABLE IF NOT EXISTS mf_sip_schedules (
    id TEXT PRIMARY KEY,
    portfolio_id TEXT NOT NULL REFERENCES user_mf_portfolios(id) ON DELETE CASCADE,
    scheme_code INTEGER NOT NULL REFERENCES mf_schemes(scheme_code),
    folio_number TEXT,
    amount DOUBLE PRECISION NOT NULL,
    frequency TEXT DEFAULT 'MONTHLY',
    sip_day INTEGER DEFAULT 5,
    start_date DATE NOT NULL,
    end_date DATE,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    step_up_pct DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_mf_sip_portfolio ON mf_sip_schedules(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_mf_sip_status ON mf_sip_schedules(status);

CREATE TABLE IF NOT EXISTS mf_transactions (
    id TEXT PRIMARY KEY,
    portfolio_id TEXT NOT NULL REFERENCES user_mf_portfolios(id) ON DELETE CASCADE,
    sip_id TEXT REFERENCES mf_sip_schedules(id) ON DELETE SET NULL,
    scheme_code INTEGER NOT NULL REFERENCES mf_schemes(scheme_code),
    tx_date DATE NOT NULL,
    tx_type TEXT NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    units DOUBLE PRECISION NOT NULL,
    nav DOUBLE PRECISION NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_mf_tx_portfolio ON mf_transactions(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_mf_tx_scheme ON mf_transactions(scheme_code);
CREATE INDEX IF NOT EXISTS idx_mf_tx_date ON mf_transactions(tx_date);

CREATE TABLE IF NOT EXISTS mf_sip_checkins (
    id TEXT PRIMARY KEY,
    portfolio_id TEXT NOT NULL REFERENCES user_mf_portfolios(id) ON DELETE CASCADE,
    sip_id TEXT NOT NULL REFERENCES mf_sip_schedules(id) ON DELETE CASCADE,
    scheme_code INTEGER NOT NULL,
    due_date DATE NOT NULL,
    status TEXT NOT NULL,
    confirmed_date DATE,
    amount DOUBLE PRECISION NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_mf_sip_checkin_unique ON mf_sip_checkins(sip_id, due_date);
CREATE INDEX IF NOT EXISTS idx_mf_sip_checkin_portfolio ON mf_sip_checkins(portfolio_id);

-- 20. Intraday signals, event history, cached candles, and universe
CREATE TABLE IF NOT EXISTS intraday_signals (
    id SERIAL PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    strategy_ver TEXT NOT NULL DEFAULT '1.0.0',
    mode TEXT NOT NULL CHECK (mode IN ('live', 'paper', 'backtest')),
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL DEFAULT 'NSE',
    signal_type TEXT NOT NULL CHECK (signal_type IN ('LONG', 'SHORT')),
    signal_candle_time TIMESTAMP NOT NULL,
    entry_time TIMESTAMP,
    timeframe TEXT NOT NULL DEFAULT '15m',
    entry_price DOUBLE PRECISION,
    sl_price DOUBLE PRECISION NOT NULL,
    target_1 DOUBLE PRECISION NOT NULL,
    target_2 DOUBLE PRECISION,
    sl_distance DOUBLE PRECISION NOT NULL,
    reward_risk DOUBLE PRECISION NOT NULL,
    atr_at_signal DOUBLE PRECISION NOT NULL,
    confidence_score INTEGER,
    pillars_met TEXT NOT NULL,
    regime TEXT NOT NULL,
    vwap_at_signal DOUBLE PRECISION,
    pivot_at_signal DOUBLE PRECISION,
    pdh DOUBLE PRECISION,
    pdl DOUBLE PRECISION,
    todvol_ratio DOUBLE PRECISION,
    rationale TEXT,
    feature_snapshot TEXT,
    feasibility_ok INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS signal_events (
    id SERIAL PRIMARY KEY,
    signal_id INTEGER NOT NULL REFERENCES intraday_signals(id),
    event_type TEXT NOT NULL,
    event_time TIMESTAMP NOT NULL,
    price DOUBLE PRECISION,
    shares INTEGER,
    gross_pnl_r DOUBLE PRECISION,
    fees_r DOUBLE PRECISION,
    net_pnl_r DOUBLE PRECISION,
    mfe_r DOUBLE PRECISION,
    mae_r DOUBLE PRECISION,
    note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS intraday_candles (
    id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL DEFAULT '15m',
    candle_time TIMESTAMP NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume INTEGER,
    ema21 DOUBLE PRECISION,
    supertrend DOUBLE PRECISION,
    supertrend_dir INTEGER,
    atr14 DOUBLE PRECISION,
    adx14_nifty DOUBLE PRECISION,
    vwap DOUBLE PRECISION,
    obv DOUBLE PRECISION,
    todvol_ratio DOUBLE PRECISION,
    is_warmup INTEGER DEFAULT 0,
    UNIQUE (symbol, timeframe, candle_time)
);

CREATE TABLE IF NOT EXISTS volume_seasonality (
    symbol TEXT NOT NULL,
    time_slot TEXT NOT NULL,
    session_count INTEGER NOT NULL,
    mean_volume DOUBLE PRECISION NOT NULL,
    updated_at DATE NOT NULL,
    PRIMARY KEY (symbol, time_slot)
);

CREATE TABLE IF NOT EXISTS intraday_universe (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    symbol TEXT NOT NULL,
    iss_score DOUBLE PRECISION NOT NULL,
    liquidity_score DOUBLE PRECISION,
    atr_pct_15m DOUBLE PRECISION,
    momentum_score DOUBLE PRECISION,
    todvol_score DOUBLE PRECISION,
    level_setup_score DOUBLE PRECISION,
    news_score DOUBLE PRECISION,
    gap_type TEXT,
    iep_price DOUBLE PRECISION,
    selected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (date, symbol)
);

CREATE OR REPLACE VIEW v_signal_status AS
SELECT s.id, s.symbol, s.strategy_id, s.mode, s.signal_type, s.entry_price,
       s.sl_price, s.target_1, s.target_2, s.reward_risk, s.regime, s.rationale,
       s.confidence_score, s.todvol_ratio, s.vwap_at_signal, s.atr_at_signal,
       s.created_at, COALESCE(last_e.event_type, 'PENDING') AS current_status,
       last_e.net_pnl_r, last_e.mfe_r, last_e.mae_r, last_e.price AS exit_price
FROM intraday_signals s
LEFT JOIN signal_events last_e ON last_e.id = (
    SELECT id FROM signal_events WHERE signal_id = s.id
    ORDER BY created_at DESC LIMIT 1
);
