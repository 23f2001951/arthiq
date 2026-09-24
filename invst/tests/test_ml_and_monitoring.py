"""Tests for Machine Learning, Calibration, and Monitoring modules."""

import sqlite3
from datetime import date

import numpy as np

from invst.data_access import PointInTimeDataAccess
from invst.ml.calibrate import compute_brier_score, compute_psi, compute_reliability_curve
from invst.ml.classifier import OutperformanceClassifier
from invst.ml.features import build_ml_feature_dataset, extract_symbol_ml_features
from invst.ml.sentiment import (
    SentimentScorer,
    rule_based_financial_sentiment,
    score_unprocessed_news_in_db,
)
from invst.monitoring.data_quality import run_all_data_quality_checks
from invst.monitoring.divergence import evaluate_strategy_divergence
from invst.monitoring.pit_audit import audit_future_disclosure_dates, run_full_pit_audit

# ── Sentiment Model Tests ─────────────────────────────────────────────


def test_rule_based_sentiment():
    pos = "HDFC Bank posts surge in quarterly profit and beats revenue estimates"
    neg = "Company suffers plunge in margins and receives regulatory penalty"
    neutral = "Company announces venue for upcoming annual general meeting"

    assert rule_based_financial_sentiment(pos) > 0.0
    assert rule_based_financial_sentiment(neg) < 0.0
    assert rule_based_financial_sentiment(neutral) == 0.0


def test_sentiment_scorer_and_db_update(tmp_db: sqlite3.Connection):
    scorer = SentimentScorer(use_transformer=False)
    assert scorer.score_text("Company shares surge to record high") > 0.0

    # Insert unprocessed news
    tmp_db.execute(
        """
        INSERT INTO news_sentiment (headline_id, symbol, published_at, headline, source, sentiment_score)
        VALUES ('h_test', 'RELIANCE', '2024-01-15', 'Reliance wins massive clean energy contract', 'mint', NULL)
        """
    )
    tmp_db.commit()

    updated = score_unprocessed_news_in_db(tmp_db, scorer=scorer)
    assert updated == 1

    score = tmp_db.execute(
        "SELECT sentiment_score FROM news_sentiment WHERE headline_id = 'h_test'"
    ).fetchone()[0]
    assert score is not None
    assert score > 0.0


# ── Feature Builder and Classifier Tests ──────────────────────────────


def test_feature_extraction_and_classifier(scoring_db: sqlite3.Connection):
    pit = PointInTimeDataAccess(scoring_db, asof=date(2024, 3, 31))
    feats = extract_symbol_ml_features(pit, "STOCK_A")

    assert "composite_score" in feats
    assert "roe_5yr" in feats
    assert "pe_ttm" in feats
    assert "annualised_vol" in feats
    assert "momentum_6_12_1" in feats

    # Test dataset builder
    X, symbols, feature_names = build_ml_feature_dataset(
        pit, ["STOCK_A", "STOCK_B"], {"STOCK_A": 85.0, "STOCK_B": 45.0}
    )
    assert X.shape == (2, len(feature_names))

    # Synthetic training
    X_train = np.random.randn(50, len(feature_names)).astype(np.float32)
    y_train = (X_train[:, 0] > 0).astype(int)

    clf = OutperformanceClassifier(model_type="logistic", threshold=0.55)
    clf.train(X_train, y_train)
    probs = clf.predict_proba(X)

    assert len(probs) == 2
    assert all(0.0 <= p <= 1.0 for p in probs)

    passed = clf.filter_by_probability(symbols, probs)
    assert isinstance(passed, list)


# ── Calibration & Drift (PSI) Tests ───────────────────────────────────


def test_brier_score_and_reliability_curve():
    y_true = [1, 1, 0, 0, 1]
    y_prob = [0.9, 0.8, 0.1, 0.2, 0.7]

    brier = compute_brier_score(y_true, y_prob)
    assert 0.0 <= brier <= 0.20

    curve = compute_reliability_curve(y_true, y_prob, n_bins=5)
    assert len(curve) > 0


def test_psi_drift_detection():
    expected = np.random.normal(0, 1, 1000)
    actual_same = np.random.normal(0, 1, 1000)
    actual_drifted = np.random.normal(2.0, 1.5, 1000)

    psi_same = compute_psi(expected, actual_same)
    assert psi_same < 0.10  # No significant drift

    psi_drift = compute_psi(expected, actual_drifted)
    assert psi_drift > 0.20  # Significant drift detected


# ── Monitoring & Audits Tests ─────────────────────────────────────────


def test_data_quality_and_pit_audits(scoring_db: sqlite3.Connection):
    dq_results = run_all_data_quality_checks(scoring_db, asof=date(2024, 3, 31))
    assert len(dq_results) == 3
    assert all(r.passed for r in dq_results)

    pit_results = run_full_pit_audit(scoring_db, asof=date(2024, 3, 31))
    assert len(pit_results) == 4
    assert all(r.passed for r in pit_results)

    # Insert a future disclosure to test audit failure detection
    scoring_db.execute(
        """
        INSERT INTO fundamentals_quarterly (symbol, period_end, disclosed_at, metric, value, unit, source)
        VALUES ('STOCK_A', '2024-03-31', '2099-01-01', 'roe', 20.0, 'pct', 'nse')
        """
    )
    scoring_db.commit()

    failed_audit = audit_future_disclosure_dates(scoring_db, asof=date(2024, 3, 31))
    assert failed_audit.passed is False
    assert failed_audit.violations_count == 1


def test_strategy_divergence():
    # Strong live performance (25% return, low vol)
    live_returns_good = [0.001 for _ in range(100)]
    res_good = evaluate_strategy_divergence(live_returns_good, backtest_sharpe=1.0)
    assert res_good.alert_triggered is False

    # Poor live performance (negative returns)
    live_returns_bad = [-0.003 for _ in range(100)]
    res_bad = evaluate_strategy_divergence(live_returns_bad, backtest_sharpe=1.5)
    assert res_bad.alert_triggered is True
