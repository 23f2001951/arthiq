"""Unit and Integration Tests for Arth IQ V0.3.1 Machine Learning Diagnostic Suite."""

import sqlite3
from datetime import date

import pytest

from invst.data_access import PointInTimeDataAccess
from invst.ml.calibrate import (
    compute_ece,
    compute_log_loss,
    evaluate_calibration_suite,
)
from invst.ml.diagnostics import (
    run_diagnostic_8_zero_lookahead_audit,
    run_diagnostic_10_regime_conditioned_analysis,
    run_diagnostic_11_nifty500_scaling_status,
)
from invst.ml.ranking import (
    compute_information_coefficient,
    compute_long_short_spread,
)
from invst.optimization.ml_hrp import optimize_ml_tilted_hrp_portfolio


@pytest.fixture
def memory_db():
    """In-memory SQLite database populated with standard PIT tables."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS daily_prices (
        symbol TEXT NOT NULL,
        trade_date DATE NOT NULL,
        open REAL, high REAL, low REAL, close REAL, adj_close REAL, volume INTEGER, source TEXT,
        PRIMARY KEY (symbol, trade_date)
    );
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS constituents (
        symbol TEXT PRIMARY KEY,
        sector TEXT,
        is_active BOOLEAN NOT NULL DEFAULT 1,
        updated_at DATE
    );
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS fundamentals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        period_end DATE NOT NULL,
        filing_date DATE NOT NULL,
        revenue REAL,
        operating_profit REAL,
        pat REAL,
        total_equity REAL,
        total_debt REAL,
        cash_and_equiv REAL
    );
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS fundamentals_quarterly (
        symbol TEXT NOT NULL,
        period_end DATE NOT NULL,
        disclosed_at DATE NOT NULL,
        metric TEXT NOT NULL,
        value REAL,
        unit TEXT,
        source TEXT,
        PRIMARY KEY (symbol, period_end, metric)
    );
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS macro_indicators (
        trade_date DATE NOT NULL,
        indicator_name TEXT NOT NULL,
        value REAL NOT NULL,
        source TEXT,
        PRIMARY KEY (trade_date, indicator_name)
    );
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS index_constituents_history (
        effective_date DATE NOT NULL,
        symbol TEXT NOT NULL,
        isin TEXT,
        sector TEXT,
        source TEXT,
        PRIMARY KEY (effective_date, symbol)
    );
    """)
    conn.commit()
    yield conn
    conn.close()



def test_information_coefficient_metrics():
    """Test Pearson and Spearman Rank IC computation on perfect and inverted signals."""
    # Perfectly monotonic positive signal
    preds = [0.1, 0.3, 0.5, 0.7, 0.9]
    returns = [0.02, 0.05, 0.08, 0.12, 0.20]
    ic_pos = compute_information_coefficient(preds, returns)
    assert ic_pos["spearman_rank_ic"] == 1.0
    assert ic_pos["pearson_ic"] > 0.95

    # Perfectly inverted signal
    ic_neg = compute_information_coefficient(preds, list(reversed(returns)))
    assert ic_neg["spearman_rank_ic"] == -1.0
    assert ic_neg["pearson_ic"] < -0.95

    # Degenerate / constant edge case
    ic_const = compute_information_coefficient([0.5, 0.5, 0.5], [0.01, 0.02, 0.03])
    assert ic_const["pearson_ic"] == 0.0
    assert ic_const["spearman_rank_ic"] == 0.0


def test_long_short_spread_calculation():
    """Test quantile-based Long-Short spread calculation."""
    symbols = ["TCS", "INFY", "RELIANCE", "HDFCBANK", "ICICIBANK"]
    scores = [0.90, 0.75, 0.50, 0.30, 0.10]
    returns = [0.15, 0.10, 0.02, -0.05, -0.12]

    res = compute_long_short_spread(symbols, scores, returns, top_quantile=0.20, bottom_quantile=0.20)
    assert res["long_count"] == 1
    assert res["short_count"] == 1
    assert res["long_symbols"] == ["TCS"]
    assert res["short_symbols"] == ["ICICIBANK"]
    assert res["long_return"] == 0.15
    assert res["short_return"] == -0.12
    assert pytest.approx(res["long_short_spread"], abs=1e-4) == 0.27


def test_ece_and_calibration_suite():
    """Test Expected Calibration Error (ECE), log loss, and full calibration suite."""
    y_true = [1, 1, 0, 0, 1, 0]
    y_prob_good = [0.9, 0.8, 0.2, 0.1, 0.7, 0.3]
    y_prob_poor = [0.1, 0.2, 0.8, 0.9, 0.3, 0.7]

    ece_good = compute_ece(y_true, y_prob_good, n_bins=5)
    ece_poor = compute_ece(y_true, y_prob_poor, n_bins=5)
    assert ece_good < ece_poor

    ll_good = compute_log_loss(y_true, y_prob_good)
    ll_poor = compute_log_loss(y_true, y_prob_poor)
    assert ll_good < ll_poor

    suite = evaluate_calibration_suite(y_true, y_prob_good, n_bins=5)
    assert suite["samples"] == 6
    assert suite["pos_count"] == 3
    assert suite["pos_class_pct"] == 50.0
    assert suite["brier_score"] < 0.10
    assert suite["roc_auc"] > 0.80
    assert len(suite["reliability_curve"]) > 0


def test_gamma_zero_equals_pure_hrp(memory_db):
    """Verify that gamma=0.0 in ML-HRP produces identical weights to pure HRP."""
    # Seed price data for 4 stocks
    dates = [f"2020-01-{i:02d}" for i in range(1, 30)]
    for d in dates:
        memory_db.execute("INSERT OR IGNORE INTO daily_prices VALUES ('TCS', ?, 100, 105, 95, 100, 100, 1000, 'test')", (d,))
        memory_db.execute("INSERT OR IGNORE INTO daily_prices VALUES ('INFY', ?, 100, 105, 95, 102, 102, 1000, 'test')", (d,))
        memory_db.execute("INSERT OR IGNORE INTO daily_prices VALUES ('RELIANCE', ?, 100, 105, 95, 98, 98, 1000, 'test')", (d,))
        memory_db.execute("INSERT OR IGNORE INTO daily_prices VALUES ('ICICIBANK', ?, 100, 105, 95, 101, 101, 1000, 'test')", (d,))
    memory_db.commit()

    pit = PointInTimeDataAccess(memory_db, asof=date(2020, 1, 29))
    syms = ["TCS", "INFY", "RELIANCE", "ICICIBANK"]
    sec_map = {"TCS": "IT", "INFY": "IT", "RELIANCE": "Energy", "ICICIBANK": "Financials"}

    # Highly skewed ML probabilities
    skewed_probs = {"TCS": 0.90, "INFY": 0.85, "RELIANCE": 0.15, "ICICIBANK": 0.20}

    # At gamma=0.0, conviction tilt is (p / 0.50)^0 = 1.0, so probabilities have zero effect
    res_g0 = optimize_ml_tilted_hrp_portfolio(pit, syms, sec_map, skewed_probs, gamma=0.0)

    # Neutral probabilities at gamma=1.0 also have tilt (0.5 / 0.5)^1 = 1.0
    res_neutral = optimize_ml_tilted_hrp_portfolio(pit, syms, sec_map, dict.fromkeys(syms, 0.50), gamma=1.0)

    for s in syms:
        assert pytest.approx(res_g0.weights[s], abs=1e-3) == res_neutral.weights[s]


def test_zero_lookahead_audit_clean_db(memory_db):
    """Test that zero lookahead audit runs and flags no violations on valid data."""
    dates = ["2020-01-01", "2020-04-01", "2020-07-01"]
    for d in dates:
        memory_db.execute("INSERT OR IGNORE INTO index_constituents_history (effective_date, symbol, sector) VALUES (?, 'TCS', 'IT')", (d,))
        memory_db.execute("INSERT OR IGNORE INTO daily_prices VALUES ('TCS', ?, 100, 105, 95, 100, 100, 1000, 'test')", (d,))
    memory_db.commit()

    audit_res = run_diagnostic_8_zero_lookahead_audit(memory_db, dates)
    assert audit_res["zero_lookahead_verified"] is True
    assert audit_res["violations_count"] == 0


def test_regime_conditioned_analysis_partitioning():
    """Test market regime summary partitioning."""
    fake_ranking_results = {
        "quarters": [
            {"date": "2020-03-31", "spearman_rank_ic": -0.05, "long_short_spread": -0.02, "regime_bull": False, "regime_high_vix": True},
            {"date": "2020-06-30", "spearman_rank_ic": 0.12, "long_short_spread": 0.05, "regime_bull": True, "regime_high_vix": True},
            {"date": "2020-09-30", "spearman_rank_ic": 0.08, "long_short_spread": 0.03, "regime_bull": True, "regime_high_vix": False},
            {"date": "2020-12-31", "spearman_rank_ic": 0.04, "long_short_spread": 0.01, "regime_bull": True, "regime_high_vix": False},
        ]
    }
    res = run_diagnostic_10_regime_conditioned_analysis(fake_ranking_results)
    assert res["bull_market"]["quarters"] == 3
    assert res["bear_market"]["quarters"] == 1
    assert res["high_vix"]["quarters"] == 2
    assert res["low_vix"]["quarters"] == 2
    assert res["bull_market"]["mean_rank_ic"] > 0.0


def test_nifty500_scaling_status_query(memory_db):
    """Test Nifty 500 scaling status inspection function."""
    status = run_diagnostic_11_nifty500_scaling_status(memory_db)
    assert status["roster_total"] == 500
    assert status["archetype_count"] == 6
    assert status["core_20_preserved"] is True
    assert "empirical_status" in status
