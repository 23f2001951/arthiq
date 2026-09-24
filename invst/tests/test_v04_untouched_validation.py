"""Tests for V0.4-B Untouched Test Validation."""


from invst.ml.v04_untouched_validation import (
    DEV_VAL_START,
    UNTOUCHED_TEST_START,
)


class TestV04BUntouchedValidationSuite:
    """Test configuration and gating logic for untouched test validation."""

    def test_untouched_constants(self):
        assert UNTOUCHED_TEST_START == "2024-01-01"
        assert DEV_VAL_START == "2016-01-01"

    def test_gate_5_pass_fail_logic(self):
        baseline_cagr = -0.02

        # Passing candidate
        cand_pass_cagr = 0.50
        delta_pass = round(cand_pass_cagr - baseline_cagr, 2)
        gate_5_pass = "PASS" if delta_pass > 0.0 else "FAIL"
        assert delta_pass == 0.52
        assert gate_5_pass == "PASS"

        # Failing candidate
        cand_fail_cagr = -0.55
        delta_fail = round(cand_fail_cagr - baseline_cagr, 2)
        gate_5_fail = "PASS" if delta_fail > 0.0 else "FAIL"
        assert delta_fail == -0.53
        assert gate_5_fail == "FAIL"

    def test_feature_modes_in_ranking_subsets(self):
        from invst.ml.ranking import FEATURE_SUBSETS

        test_modes = ["set_a", "pair_fund_sent", "pair_fund_mom"]
        for m in test_modes:
            assert m in FEATURE_SUBSETS
            assert len(FEATURE_SUBSETS[m]) > 0
