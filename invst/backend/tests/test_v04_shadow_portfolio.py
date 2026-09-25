"""Tests for V0.4-E Shadow Portfolio Operational Tracking Harness."""

import pytest

from invst.execution.v04_shadow_portfolio import (
    DualShadowTrackingHarness,
    ShadowPortfolioState,
    ShadowPosition,
)


class TestV04EShadowPortfolio:
    """Test position accounting, equity calculation, and dual-shadow harness."""

    def test_shadow_position_update(self):
        pos = ShadowPosition(
            symbol="INFY",
            shares=100,
            avg_price=1500.0,
            current_price=1500.0,
        )
        # Price increases to 1650
        pos.update_market_value(1650.0, total_portfolio_equity=1_000_000.0)
        assert pos.market_value == 165_000.0
        assert pos.unrealized_pnl == 15_000.0
        assert pos.unrealized_pnl_pct == 10.0
        assert pos.weight == pytest.approx(0.165, abs=1e-3)

    def test_shadow_portfolio_state_calculate_equity(self):
        state = ShadowPortfolioState(
            portfolio_id="test_port",
            name="Test Portfolio",
            strategy_type="PRODUCTION_BASELINE",
            initial_capital=100_000.0,
            cash=40_000.0,
            asof_date="2024-01-01",
        )
        pos = ShadowPosition(
            symbol="TCS",
            shares=20,
            avg_price=3000.0,
            current_price=3500.0,
            market_value=70_000.0,
        )
        state.positions["TCS"] = pos
        equity = state.calculate_equity()
        assert equity == 110_000.0
        assert state.cumulative_return == 10.0

    def test_dual_shadow_tracking_harness_init(self):
        harness = DualShadowTrackingHarness(initial_capital=500_000.0, start_date="2024-01-01")
        assert harness.initial_capital == 500_000.0
        assert harness.production_portfolio.strategy_type == "PRODUCTION_BASELINE"
        assert harness.research_portfolio.strategy_type == "RESEARCH_CANDIDATE"
        assert harness.production_portfolio.cash == 500_000.0
        assert harness.research_portfolio.cash == 500_000.0

    def test_rebalance_portfolio_with_costs(self):
        harness = DualShadowTrackingHarness(initial_capital=1_000_000.0, start_date="2024-01-01")
        port = harness.production_portfolio
        target_weights = {"INFY": 0.50, "TCS": 0.50}
        prices = {"INFY": 1500.0, "TCS": 3000.0}

        rebal_res = harness.rebalance_portfolio(
            portfolio=port,
            target_weights=target_weights,
            prices=prices,
            rebal_date="2024-01-02",
        )

        assert rebal_res["turnover"] == pytest.approx(0.5, abs=1e-2)
        assert rebal_res["cost_incurred"] > 0.0
        assert "INFY" in port.positions
        assert "TCS" in port.positions
        assert port.positions["INFY"].shares > 0
        assert port.positions["TCS"].shares > 0
        assert port.cash < 1_000_000.0
        assert port.total_costs_paid > 0.0
        assert port.rebalance_count == 1
