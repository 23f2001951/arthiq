"""Unit and Integration Tests for Arth IQ V0.3 Machine Learning Pipeline and ML-Tilted HRP."""

import sqlite3
from datetime import date

import numpy as np
import pytest

from invst.data_access import PointInTimeDataAccess
from invst.ingestion.backfill_pit import run_historical_backfill
from invst.ml.calibrate import compute_brier_score, compute_psi, compute_reliability_curve
from invst.ml.classifier import OutperformanceClassifier
from invst.ml.features import (
    compute_forward_excess_label,
    compute_forward_return,
    extract_symbol_ml_features,
)
from invst.optimization.ml_hrp import optimize_ml_tilted_hrp_portfolio


@pytest.fixture
def memory_db():
    """In-memory SQLite database populated with standard PIT tables."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")

    # Create required tables
    conn.execute("""
    CREATE TABLE IF NOT EXISTS daily_prices (
        symbol TEXT NOT NULL,
        trade_date DATE NOT NULL,
        open REAL, high REAL, low REAL, close REAL, adj_close REAL, volume INTEGER, source TEXT,
        PRIMARY KEY (symbol, trade_date)
    );
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS index_constituents_history (
        effective_date DATE NOT NULL,
        symbol TEXT NOT NULL,
        isin TEXT, sector TEXT, source TEXT,
        PRIMARY KEY (effective_date, symbol)
    );
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS fundamentals_pit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL, period_end DATE NOT NULL, metric TEXT NOT NULL,
        raw_value REAL, restated_value REAL, unit TEXT, filing_timestamp DATETIME,
        effective_date DATE NOT NULL, revision_seq INTEGER, valid_from DATE, valid_to DATE,
        source TEXT, source_url TEXT
    );
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS fundamentals_quarterly (
        symbol TEXT NOT NULL, period_end DATE NOT NULL, disclosed_at DATE NOT NULL,
        metric TEXT NOT NULL, value REAL, unit TEXT, source TEXT,
        PRIMARY KEY (symbol, period_end, metric)
    );
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS corporate_actions_pit (
        id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT, action_type TEXT,
        ex_date DATE, record_date DATE, ratio_numerator REAL, ratio_denominator REAL,
        dividend_amount REAL, filing_timestamp DATETIME, effective_date DATE, source TEXT
    );
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS corporate_events_pit (
        event_id TEXT PRIMARY KEY, symbol TEXT, event_type TEXT, headline TEXT,
        direction TEXT, materiality_score REAL, confidence_score REAL,
        affected_factors TEXT, event_timestamp DATETIME, effective_date DATE, source TEXT
    );
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS news_sentiment (
        symbol TEXT NOT NULL, published_at DATETIME NOT NULL,
        sentiment_score REAL, headline TEXT, source TEXT
    );
    """)

    run_historical_backfill(conn, start_year=2021, end_year=2023, universe_mode="sample20")
    yield conn
    conn.close()


def test_ml_feature_extraction(memory_db):
    """Verify feature extractor computes valid 24-dimensional feature dictionary without lookahead."""
    pit = PointInTimeDataAccess(memory_db, asof=date(2022, 6, 30))
    feats = extract_symbol_ml_features(pit, "TCS", composite_score=68.5)

    assert "composite_score" in feats
    assert "roe_5yr" in feats
    assert "roce_5yr" in feats
    assert "debt_equity" in feats
    assert "pe_ttm" in feats
    assert "momentum_6_12_1" in feats
    assert "dist_from_52w_high" in feats
    assert "macro_vix" in feats
    assert "macro_usd_inr" in feats
    assert "downside_semivariance" in feats
    assert feats["dist_from_52w_high"] <= 0.0001
    assert feats["macro_vix"] > 0.0


def test_forward_return_and_excess_labeling(memory_db):
    """Test forward return computation and binary excess return label."""
    asof = date(2022, 3, 31)
    ret_tcs = compute_forward_return(memory_db, "TCS", asof, horizon_days=90)
    assert ret_tcs is not None

    lbl_info = compute_forward_excess_label(memory_db, "TCS", "NIFTY500", asof, horizon_days=90)
    assert lbl_info is not None
    label, excess = lbl_info
    assert label in (0, 1)
    assert isinstance(excess, float)


def test_outperformance_classifier_training_and_calibration():
    """Verify OutperformanceClassifier trains, calibrates, and outputs bounded probabilities."""
    rng = np.random.RandomState(42)
    X = rng.normal(0, 1, size=(80, 10))
    # Synthetic relationship
    y = (X[:, 0] + 0.5 * X[:, 1] + rng.normal(0, 0.5, size=80) > 0).astype(int)

    feat_names = [f"feat_{i}" for i in range(10)]
    clf = OutperformanceClassifier(model_type="logistic", threshold=0.50)
    clf.train(X, y, feature_names=feat_names)

    assert clf.is_trained is True
    assert clf.last_brier_score < 0.28

    X_test = rng.normal(0, 1, size=(10, 10))
    probs = clf.predict_proba(X_test)
    assert len(probs) == 10
    assert np.all(probs >= 0.05)
    assert np.all(probs <= 0.95)


def test_ml_tilted_hrp_weights_and_caps(memory_db):
    """Verify that ML-Tilted HRP incorporates probability tilts while enforcing 25% single-stock cap."""
    pit = PointInTimeDataAccess(memory_db, asof=date(2022, 12, 31))
    symbols = ["TCS", "INFY", "HDFCBANK", "ICICIBANK", "RELIANCE", "LT"]
    sec_map = {
        "TCS": "information_technology",
        "INFY": "information_technology",
        "HDFCBANK": "financial_services",
        "ICICIBANK": "financial_services",
        "RELIANCE": "oil_gas_consumable_fuels",
        "LT": "capital_goods",
    }

    # Skewed conviction: high on TCS & ICICIBANK, low on others
    probs = {
        "TCS": 0.82,
        "INFY": 0.35,
        "HDFCBANK": 0.40,
        "ICICIBANK": 0.78,
        "RELIANCE": 0.45,
        "LT": 0.50,
    }

    res = optimize_ml_tilted_hrp_portfolio(
        pit=pit,
        symbols=symbols,
        sector_map=sec_map,
        ml_probabilities=probs,
        capital=1_000_000.0,
        investor_profile="AGGRESSIVE",
        gamma=1.0,
    )

    # 1. Weights sum to ~1.0
    total_w = sum(res.weights.values())
    assert abs(total_w - 1.0) < 0.01

    # 2. Single-stock cap enforced (<= 25%)
    for sym, w in res.weights.items():
        assert w <= 0.2501, f"{sym} weight {w} exceeded 25% cap"

    # 3. Conviction tilt effect: TCS should have higher weight than INFY
    assert res.weights["TCS"] > res.weights["INFY"]
    assert res.weights["ICICIBANK"] > res.weights["HDFCBANK"]


def test_calibration_diagnostics():
    """Verify Brier score, PSI, and reliability curve computations."""
    y_true = [1, 1, 0, 0, 1, 0, 1, 0]
    y_prob = [0.85, 0.75, 0.20, 0.15, 0.65, 0.30, 0.90, 0.40]

    brier = compute_brier_score(y_true, y_prob)
    assert brier < 0.15

    curve = compute_reliability_curve(y_true, y_prob, n_bins=5)
    assert len(curve) > 0

    rng = np.random.RandomState(42)
    exp = rng.normal(0.0, 1.0, size=500)
    act = rng.normal(0.01, 1.01, size=500)
    psi = compute_psi(exp, act)
    assert psi < 0.10  # Minimal distribution drift
