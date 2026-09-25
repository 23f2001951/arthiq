"""Unit tests for user portfolio health diagnostics and advisory."""

from __future__ import annotations

import sqlite3

from invst.cli import get_db_connection
from invst.portfolio.health import (
    UserHolding,
    UserPortfolio,
    evaluate_portfolio_health,
    load_user_holdings,
    save_user_holdings,
    list_portfolios,
    get_portfolio,
    create_portfolio,
    update_portfolio,
    delete_portfolio,
    add_or_update_holding_in_portfolio,
    remove_holding_from_portfolio,
)


def test_save_and_load_user_holdings():
    """Verify SQLite persistence for manual user holdings."""
    conn = sqlite3.connect(":memory:")
    holdings = [
        UserHolding(symbol="TCS", shares=10.0, buy_price=1400.0),
        UserHolding(symbol="INFY", shares=25.0, buy_price=1850.0),
    ]

    save_user_holdings(conn, holdings)
    loaded = load_user_holdings(conn)

    assert len(loaded) == 2
    sym_map = {h.symbol: h for h in loaded}
    assert "TCS" in sym_map
    assert sym_map["TCS"].shares == 10.0
    assert sym_map["TCS"].buy_price == 1400.0
    assert "INFY" in sym_map
    assert sym_map["INFY"].shares == 25.0
    conn.close()


def test_evaluate_portfolio_health_empty():
    """Verify empty portfolio returns clean zero-state report."""
    conn = sqlite3.connect(":memory:")
    report = evaluate_portfolio_health(conn, [])
    assert report.total_current_value == 0.0
    assert report.positions == []
    assert report.overall_health_grade == "N/A"
    conn.close()


def test_evaluate_portfolio_health_live_db():
    """Verify full health diagnosis and position actions against database."""
    conn = get_db_connection()
    holdings = [
        UserHolding(symbol="TCS", shares=10.0, buy_price=1400.0),
        UserHolding(symbol="INFY", shares=10.0, buy_price=1800.0),
        UserHolding(symbol="HDFCBANK", shares=20.0, buy_price=1200.0),
    ]

    report = evaluate_portfolio_health(conn, holdings)
    assert report.total_invested > 0.0
    assert report.total_current_value > 0.0
    assert 0.0 <= report.overall_health_score <= 100.0
    assert report.overall_health_grade in ["EXCELLENT", "GOOD", "NEEDS_ATTENTION", "HIGH_RISK"]
    assert len(report.positions) == 3

    for p in report.positions:
        assert p.symbol in ["TCS", "INFY", "HDFCBANK"]
        assert p.current_price > 0.0
        assert p.action_verdict in ["BUY_MORE", "HOLD", "TRIM", "EXIT_SELL"]
        assert len(p.action_rationale) > 5

    assert len(report.sector_exposures) >= 1
    conn.close()


def test_evaluate_portfolio_health_institutional_factors_and_horizons():
    """Verify multi-horizon scenario forecasts and factor health explanations."""
    conn = get_db_connection()
    holdings = [
        UserHolding(symbol="TCS", shares=10.0, buy_price=1400.0),
        UserHolding(symbol="INFY", shares=15.0, buy_price=1800.0),
        UserHolding(symbol="HDFCBANK", shares=20.0, buy_price=1200.0),
    ]

    report = evaluate_portfolio_health(conn, holdings)

    # 1. Factor health tiers
    assert "business_quality" in report.factor_health
    assert "valuation" in report.factor_health
    assert "risk_solvency" in report.factor_health

    bq = report.factor_health["business_quality"]
    assert bq.score > 0.0
    assert "TIER" in bq.tier
    assert len(bq.interpretation) > 10

    # 2. Multi-horizon aggregate returns
    assert "3m" in report.portfolio_horizons
    assert "6m" in report.portfolio_horizons
    assert "12m" in report.portfolio_horizons
    assert "3y" in report.portfolio_horizons

    h_3y = report.portfolio_horizons["3y"]
    assert h_3y.projected_portfolio_value > 0.0
    assert h_3y.cagr_pct is not None

    # 3. Diversification metrics
    assert report.diversification is not None
    assert report.diversification.hhi_score > 0.0
    assert report.diversification.diversification_tier in [
        "OPTIMAL_DIVERSIFICATION",
        "MODERATE_CONCENTRATION",
        "HIGH_CONCENTRATION",
    ]
    assert report.diversification.top_3_concentration_pct > 0.0

    # 4. Rebalancing blueprint
    assert report.rebalancing_blueprint is not None
    assert report.rebalancing_blueprint.rebalance_urgency in ["LOW", "MODERATE", "HIGH", "CRITICAL"]
    assert len(report.rebalancing_blueprint.strategic_summary) > 10

    conn.close()


def test_evaluate_portfolio_health_with_etf():
    """Verify ETF holdings are recognized as core stabilizers and exempt from standard stock caps."""
    conn = get_db_connection()
    holdings = [
        UserHolding(symbol="TCS", shares=10.0, buy_price=1400.0),
        UserHolding(symbol="NIFTYBEES", shares=100.0, buy_price=260.0),
    ]

    report = evaluate_portfolio_health(conn, holdings)

    nifty_pos = next((p for p in report.positions if p.symbol == "NIFTYBEES"), None)
    assert nifty_pos is not None
    assert nifty_pos.is_etf is True
    assert nifty_pos.sector.lower() == "index_etf"

    # Verify ETF asset allocation split in diversification
    assert report.diversification is not None
    assert report.diversification.etf_weight_pct > 0.0
    assert report.diversification.equity_weight_pct > 0.0

    # Check tactical parameters
    assert nifty_pos.dip_target_price > 0.0
    assert nifty_pos.stop_loss_level > 0.0

    conn.close()


def test_multiple_portfolios_and_targetlists():
    """Verify creating, listing, updating, and deleting multiple portfolios and targetlists."""
    conn = sqlite3.connect(":memory:")

    # Initial list should include default portfolio and default targetlist
    p_list = list_portfolios(conn)
    assert len(p_list) >= 2
    types = {p["portfolio_type"] for p in p_list}
    assert "PORTFOLIO" in types
    assert "TARGETLIST" in types

    # Create a custom high-growth portfolio
    p_growth = create_portfolio(
        conn,
        name="High Growth Tech",
        description="Focus on tech compounders",
        portfolio_type="PORTFOLIO",
        initial_holdings=[
            UserHolding(symbol="TCS", shares=10.0, buy_price=1400.0),
            UserHolding(symbol="INFY", shares=15.0, buy_price=1800.0),
        ],
    )
    assert p_growth.id is not None
    assert p_growth.name == "High Growth Tech"
    assert len(p_growth.holdings) == 2

    # Create a tactical target list
    p_target = create_portfolio(
        conn,
        name="Q3 Dip Buy List",
        description="Awaiting market correction to accumulate",
        portfolio_type="TARGETLIST",
    )
    assert p_target.portfolio_type == "TARGETLIST"
    assert len(p_target.holdings) == 0

    # Add a stock to the target list with target_price and notes
    add_or_update_holding_in_portfolio(
        conn,
        p_target.id,
        UserHolding(
            symbol="HDFCBANK",
            shares=25.0,
            buy_price=1200.0,
            target_price=1150.0,
            notes="Enter when RSI < 35 or price reaches 1150",
        ),
    )

    loaded_target = get_portfolio(conn, p_target.id)
    assert loaded_target is not None
    assert len(loaded_target.holdings) == 1
    h = loaded_target.holdings[0]
    assert h.symbol == "HDFCBANK"
    assert h.target_price == 1150.0
    assert "RSI < 35" in h.notes

    # Remove holding from portfolio
    remove_holding_from_portfolio(conn, p_growth.id, "TCS")
    loaded_growth = get_portfolio(conn, p_growth.id)
    assert loaded_growth is not None
    assert len(loaded_growth.holdings) == 1
    assert loaded_growth.holdings[0].symbol == "INFY"

    # Delete custom portfolio
    ok = delete_portfolio(conn, p_target.id)
    assert ok is True
    assert get_portfolio(conn, p_target.id) is None

    conn.close()
