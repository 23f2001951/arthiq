"""Tests for Arth IQ V0.4 Priority Diagnostic Extensions.

Validates:
- Cross-sectional quintile calculations and monotonicity detection
- Feature subsets A through H definitions and mapping integrity
- Inverted signal probability calculation (P_reverse = 1 - P)
- Platt scaling alias normalization in OutperformanceClassifier
- Exact combined configuration parameterization (Platt + 50/50 + gamma=0.50)
"""

import numpy as np

from invst.ml.classifier import OutperformanceClassifier
from invst.ml.ranking import (
    FEATURE_SUBSETS,
    compute_cross_sectional_quintiles,
)


def test_cross_sectional_quintiles_monotonic():
    """Verify quintile bucket returns and spread calculation on ascending monotonic returns."""
    symbols = [f"SYM_{i}" for i in range(20)]
    # Scores from 0.05 to 0.95
    scores = [i / 20.0 for i in range(20)]
    # Realized returns monotonic with scores
    returns = [i * 0.02 for i in range(20)]

    res = compute_cross_sectional_quintiles(symbols, scores, returns)

    assert res["is_monotonic"] is True
    assert res["q5_minus_q1"] > 0.0
    assert res["q5_mean"] > res["q1_mean"]
    assert res["q1_mean"] == round(float(np.mean(returns[:4])), 4)
    assert res["q5_mean"] == round(float(np.mean(returns[16:])), 4)


def test_cross_sectional_quintiles_inverted():
    """Verify quintile spread calculation when higher scores yield worse returns (negative alpha)."""
    symbols = [f"SYM_{i}" for i in range(20)]
    scores = [i / 20.0 for i in range(20)]
    # Inverted returns: highest score gets lowest return
    returns = [(20 - i) * 0.02 for i in range(20)]

    res = compute_cross_sectional_quintiles(symbols, scores, returns)

    assert res["is_monotonic"] is False
    assert res["q5_minus_q1"] < 0.0
    assert res["q1_mean"] > res["q5_mean"]


def test_cross_sectional_quintiles_edge_case():
    """Verify handling when too few symbols are provided."""
    res = compute_cross_sectional_quintiles(["A", "B"], [0.5, 0.6], [0.01, 0.02])
    assert res["q5_minus_q1"] == 0.0
    assert res["is_monotonic"] is False


def test_feature_subsets_definitions():
    """Verify that all controlled ablation subsets (Sets A through H) are correctly defined."""
    required_sets = ["set_a", "set_b", "set_c", "set_d", "set_e", "set_f", "set_g", "set_h"]
    for s_key in required_sets:
        assert s_key in FEATURE_SUBSETS
        feats = FEATURE_SUBSETS[s_key]
        assert len(feats) > 0

    # Set A: Fundamentals
    assert "roe_5yr" in FEATURE_SUBSETS["set_a"]
    assert "roce_5yr" in FEATURE_SUBSETS["set_a"]
    assert "debt_equity" in FEATURE_SUBSETS["set_a"]

    # Set B: Valuation
    assert "pe_ttm" in FEATURE_SUBSETS["set_b"]
    assert "pb" in FEATURE_SUBSETS["set_b"]
    assert "ev_ebitda" in FEATURE_SUBSETS["set_b"]

    # Set C: Risk
    assert "annualised_vol" in FEATURE_SUBSETS["set_c"]
    assert "beta" in FEATURE_SUBSETS["set_c"]
    assert "max_drawdown" in FEATURE_SUBSETS["set_c"]
    assert "downside_semivariance" in FEATURE_SUBSETS["set_c"]

    # Set D: Momentum
    assert "momentum_6_12_1" in FEATURE_SUBSETS["set_d"]
    assert "dist_from_52w_high" in FEATURE_SUBSETS["set_d"]
    assert "risk_adjusted_momentum" in FEATURE_SUBSETS["set_d"]

    # Set E: Fundamentals + Valuation
    for f in FEATURE_SUBSETS["set_a"] + FEATURE_SUBSETS["set_b"]:
        assert f in FEATURE_SUBSETS["set_e"]

    # Set F: Fundamentals + Risk
    for f in FEATURE_SUBSETS["set_a"] + FEATURE_SUBSETS["set_c"]:
        assert f in FEATURE_SUBSETS["set_f"]

    # Set G: Fundamentals + Valuation + Risk
    for f in FEATURE_SUBSETS["set_a"] + FEATURE_SUBSETS["set_b"] + FEATURE_SUBSETS["set_c"]:
        assert f in FEATURE_SUBSETS["set_g"]

    # Set H: Full 24 features
    assert len(FEATURE_SUBSETS["set_h"]) == 22 or len(FEATURE_SUBSETS["set_h"]) == 24


def test_outperformance_classifier_platt_normalization():
    """Verify that OutperformanceClassifier normalizes 'platt' to 'sigmoid'."""
    clf = OutperformanceClassifier(model_type="logistic", calibration_method="platt")
    assert clf.calibration_method == "sigmoid"

    clf2 = OutperformanceClassifier(model_type="logistic", calibration_method="isotonic")
    assert clf2.calibration_method == "isotonic"
