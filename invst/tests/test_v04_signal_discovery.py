"""Tests for V0.4 Signal Discovery & Model Promotion Gates."""

import pytest

from invst.ml.diagnostics import evaluate_model_promotion_gates
from invst.ml.ranking import (
    ALL_24_FEATS,
    FEATURE_SUBSETS,
    compute_bootstrap_confidence_interval,
)


class TestBootstrapConfidenceInterval:
    """Test non-parametric bootstrap confidence interval estimation."""

    def test_empty_series(self):
        res = compute_bootstrap_confidence_interval([])
        assert res["ci_lower"] == 0.0
        assert res["ci_upper"] == 0.0
        assert res["prob_positive"] == 0.0
        assert res["mean"] == 0.0

    def test_strictly_positive_series(self):
        values = [0.05, 0.04, 0.06, 0.05, 0.03, 0.07]
        res = compute_bootstrap_confidence_interval(values, n_bootstraps=500, random_state=42)
        assert res["mean"] == pytest.approx(0.05, abs=1e-3)
        assert res["ci_lower"] > 0.0
        assert res["ci_upper"] > res["ci_lower"]
        assert res["prob_positive"] == 1.0

    def test_strictly_negative_series(self):
        values = [-0.08, -0.05, -0.10, -0.06, -0.07]
        res = compute_bootstrap_confidence_interval(values, n_bootstraps=500, random_state=42)
        assert res["ci_upper"] < 0.0
        assert res["prob_positive"] == 0.0

    def test_reproducibility_with_seed(self):
        values = [0.01, -0.02, 0.05, 0.03, -0.01, 0.04]
        res1 = compute_bootstrap_confidence_interval(values, n_bootstraps=300, random_state=123)
        res2 = compute_bootstrap_confidence_interval(values, n_bootstraps=300, random_state=123)
        assert res1["ci_lower"] == res2["ci_lower"]
        assert res1["ci_upper"] == res2["ci_upper"]


class TestFeatureSubsetsConfiguration:
    """Verify LOGO and pairwise feature subsets integrity."""

    def test_logo_subsets_exist(self):
        expected_logo = [
            "logo_fundamentals",
            "logo_valuation",
            "logo_risk",
            "logo_momentum",
        ]
        for k in expected_logo:
            assert k in FEATURE_SUBSETS, f"Missing LOGO subset: {k}"
            assert len(FEATURE_SUBSETS[k]) > 0, f"Empty LOGO subset: {k}"

    def test_pairwise_subsets_exist(self):
        expected_pairs = [
            "pair_fund_val",
            "pair_fund_risk",
            "pair_fund_mom",
            "pair_fund_sent",
        ]
        for k in expected_pairs:
            assert k in FEATURE_SUBSETS, f"Missing pairwise subset: {k}"
            assert len(FEATURE_SUBSETS[k]) > 0, f"Empty pairwise subset: {k}"

    def test_set_a_fundamentals_clean(self):
        fund_features = FEATURE_SUBSETS["set_a"]
        assert "roe_5yr" in fund_features
        assert "roce_5yr" in fund_features
        assert "debt_equity" in fund_features
        # Must not contain price momentum or beta
        assert "momentum_6_12_1" not in fund_features
        assert "beta" not in fund_features

    def test_set_h_contains_all_features(self):
        full_features = FEATURE_SUBSETS["set_h"]
        assert len(full_features) == len(ALL_24_FEATS)
        assert set(full_features) == set(ALL_24_FEATS)


class TestInstitutionalModelPromotionGates:
    """Verify the 8 binary gates evaluation logic."""

    def test_rejected_verdict_for_destructive_signal(self):
        summary = {
            "mean_rank_ic": -0.0909,
            "rank_ic_ir": -1.25,
            "q5_minus_q1": -0.0189,
            "pct_positive_ic": 32.0,
            "annualized_ls_return": -0.0728,
        }
        res = evaluate_model_promotion_gates(
            summary,
            pit_violations=0,
            untouched_test_delta=-0.53,
            portfolio_cagr_delta=-0.35,
        )
        assert res["verdict"] == "REJECTED"
        assert res["gates"]["Gate 1: Zero Lookahead Violations"] is True
        assert res["gates"]["Gate 2: Statistical Signal (IC > 0 & IR > 0)"] is False
        assert res["gates"]["Gate 3: Cross-Sectional Ranking (Q5 > Q1)"] is False
        assert res["gates"]["Gate 5: Untouched Test Delta > 0"] is False

    def test_candidate_verdict_for_promising_signal(self):
        summary = {
            "mean_rank_ic": +0.0179,
            "rank_ic_ir": +0.35,
            "q5_minus_q1": +0.0076,
            "pct_positive_ic": 60.0,
            "annualized_ls_return": +0.0499,
        }
        res = evaluate_model_promotion_gates(
            summary,
            pit_violations=0,
            untouched_test_delta=None,  # pending untouched OOS
            portfolio_cagr_delta=None,
        )
        assert res["verdict"] == "CANDIDATE"
        assert res["gates"]["Gate 1: Zero Lookahead Violations"] is True
        assert res["gates"]["Gate 2: Statistical Signal (IC > 0 & IR > 0)"] is True
        assert res["gates"]["Gate 3: Cross-Sectional Ranking (Q5 > Q1)"] is True
        assert res["gates"]["Gate 4: Multi-Epoch Temporal Stability"] is True
        assert res["gates"]["Gate 7: Cost Robustness (L/S Return > 0)"] is True

    def test_lookahead_violation_fails_gate_1(self):
        summary = {
            "mean_rank_ic": +0.05,
            "rank_ic_ir": +1.0,
            "q5_minus_q1": +0.02,
            "pct_positive_ic": 70.0,
            "annualized_ls_return": +0.10,
        }
        res = evaluate_model_promotion_gates(summary, pit_violations=2)
        assert res["gates"]["Gate 1: Zero Lookahead Violations"] is False
        assert res["verdict"] != "PROMOTED"

    def test_promoted_verdict_when_all_conditions_satisfied(self):
        summary = {
            "mean_rank_ic": +0.04,
            "rank_ic_ir": +0.80,
            "q5_minus_q1": +0.03,
            "pct_positive_ic": 65.0,
            "annualized_ls_return": +0.08,
        }
        res = evaluate_model_promotion_gates(
            summary,
            pit_violations=0,
            untouched_test_delta=1.20,
            portfolio_cagr_delta=1.50,
        )
        assert res["verdict"] == "PROMOTED"
        assert res["passed_count"] == 8


class TestV04ASignalDiscoverySuite:
    """Test candidate specifications and scorecard generation in v04_signal_discovery."""

    def test_candidate_specs_integrity(self):
        from invst.ml.v04_signal_discovery import CANDIDATE_SPECS, HORIZON_SPECS

        assert len(CANDIDATE_SPECS) == 3
        cand_ids = [c["candidate_id"] for c in CANDIDATE_SPECS]
        assert "cand_1_fundamentals" in cand_ids
        assert "cand_2_fund_momentum" in cand_ids
        assert "cand_3_fund_sentiment" in cand_ids

        # Verify feature modes exist in FEATURE_SUBSETS
        for c in CANDIDATE_SPECS:
            mode = c["feature_mode"]
            assert mode in FEATURE_SUBSETS
            assert set(c["features"]) == set(FEATURE_SUBSETS[mode])

        # Verify horizons
        days = [h[1] for h in HORIZON_SPECS]
        assert days == [30, 60, 90, 180, 252]

    def test_generate_v04a_candidate_scorecard(self):
        from invst.ml.v04_signal_discovery import (
            CANDIDATE_SPECS,
            generate_v04a_candidate_scorecard,
        )

        mock_data = [
            {
                "spec": CANDIDATE_SPECS[0],
                "primary_summary": {
                    "mean_rank_ic": 0.0179,
                    "rank_ic_ir": 0.07,
                    "rank_ic_ci_lower": -0.0847,
                    "rank_ic_ci_upper": 0.1094,
                    "rank_ic_prob_positive": 0.60,
                    "pct_positive_ic": 60.0,
                    "annualized_ls_return": 0.0499,
                    "q5_minus_q1": 0.0076,
                    "monotonic_quarters_pct": 20.0,
                },
                "horizons": [],
            },
            {
                "spec": CANDIDATE_SPECS[1],
                "primary_summary": {
                    "mean_rank_ic": 0.0315,
                    "rank_ic_ir": 0.12,
                    "rank_ic_ci_lower": -0.0778,
                    "rank_ic_ci_upper": 0.1296,
                    "rank_ic_prob_positive": 0.65,
                    "pct_positive_ic": 48.0,
                    "annualized_ls_return": 0.0368,
                    "q5_minus_q1": -0.0026,
                    "monotonic_quarters_pct": 0.0,
                },
                "horizons": [],
            },
        ]

        scorecard = generate_v04a_candidate_scorecard(mock_data, pit_violations=0)
        assert len(scorecard) == 2
        # Highest Rank IC sorted first
        assert scorecard[0]["candidate_id"] == "cand_2_fund_momentum"
        assert scorecard[1]["candidate_id"] == "cand_1_fundamentals"
        assert scorecard[1]["verdict"] == "CANDIDATE"
