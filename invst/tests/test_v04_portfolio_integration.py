"""Tests for V0.4-D Portfolio Integration & Normalized Additive Decision Engine."""

from unittest.mock import MagicMock

import pytest

from invst.ml.v04_portfolio_integration import (
    DEFAULT_ARTHSCORE_WEIGHTS,
    compute_v04_normalized_arthscore,
)
from invst.scoring.composite_v2 import StockScorecardV2


class TestV04DPortfolioIntegration:
    """Test normalized additive scoring and cross-pillar signal agreement."""

    def test_default_weights_sum_to_one(self):
        total_w = sum(DEFAULT_ARTHSCORE_WEIGHTS.values())
        assert total_w == pytest.approx(1.0, abs=1e-5)

    def test_signal_agreement_damping(self):
        # Create mock scorecard with high fundamental quality (BQS = 85.0)
        mock_bqs = MagicMock()
        mock_bqs.bqs_score = 85.0

        mock_sc = MagicMock(spec=StockScorecardV2)
        mock_sc.symbol = "TCS"
        mock_sc.bqs_result = mock_bqs
        mock_sc.valuation_score = 60.0
        mock_sc.growth_score = 75.0
        mock_sc.risk_score = 70.0

        # Scenario 1: High Agreement (ML probability = 0.82 -> H = 82.0, close to F = 85.0)
        res_agree = compute_v04_normalized_arthscore(mock_sc, ml_probability=0.82)
        assert res_agree.agreement_factor > 0.95
        assert res_agree.arth_score > 70.0

        # Scenario 2: Severe Divergence (ML probability = 0.15 -> H = 15.0, far from F = 85.0)
        res_diverge = compute_v04_normalized_arthscore(mock_sc, ml_probability=0.15)
        # Divergence is |85 - 15| / 100 = 0.70. Penalty factor = 1 - 0.30 * 0.70 = 0.79
        assert res_diverge.agreement_factor == pytest.approx(0.79, abs=1e-2)
        # Damped score must be lower than agreed score
        assert res_diverge.arth_score < res_agree.arth_score
