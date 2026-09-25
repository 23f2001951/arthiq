"""Unit tests for stock_analyzer and multi-horizon scenarios."""

from __future__ import annotations

import sqlite3

from invst.data_access import PointInTimeDataAccess
from invst.scoring.scenarios import evaluate_multi_horizon_scenarios
from invst.scoring.stock_analyzer import analyze_stock_on_demand, determine_action_verdict


def test_determine_action_verdict():
    """Verify matrix quadrant and action verdict mappings."""
    # Redline triggered
    q, act, badge, worthy = determine_action_verdict(80.0, 70.0, ["High promoter pledge"])
    assert act == "REDLINE_REJECT"
    assert worthy is False

    # Compounder
    q, act, badge, worthy = determine_action_verdict(75.0, 65.0, [])
    assert act == "STRONG_BUY"
    assert worthy is True
    assert "Alpha" in q

    # Quality Trap
    q, act, badge, worthy = determine_action_verdict(80.0, 35.0, [])
    assert act == "HOLD_WAIT"
    assert worthy is False
    assert "Trap" in q

    # Value Trap
    q, act, badge, worthy = determine_action_verdict(40.0, 30.0, [])
    assert act == "AVOID"
    assert worthy is False


def test_multi_horizon_scenarios():
    """Verify 3M, 6M, 12M, and 3Y scenario projections and mathematical consistency."""
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE daily_prices (
            symbol TEXT, trade_date DATE, open REAL, high REAL, low REAL, close REAL, adj_close REAL, volume INTEGER, source TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE fundamentals_quarterly (
            symbol TEXT, period_end DATE, disclosed_at DATE, metric TEXT, value REAL, unit TEXT, source TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO daily_prices VALUES ('TCS', '2026-09-21', 1000.0, 1020.0, 990.0, 1000.0, 1000.0, 50000, 'test')"
    )
    conn.commit()

    from datetime import date
    pit = PointInTimeDataAccess(conn, asof=date(2026, 9, 21))

    res = evaluate_multi_horizon_scenarios(
        pit=pit,
        symbol="TCS",
        growth_cagr=15.0,
        earnings_yield=4.0,
        current_price_override=1000.0,
    )

    assert res.symbol == "TCS"
    assert res.current_price == 1000.0

    # 3M checks
    assert res.h3m.months == 3
    assert res.h3m.target_price_bear < 1000.0
    assert res.h3m.target_price_bull > 1000.0
    assert res.h3m.expected_return_pct > 0.0

    # 6M checks
    assert res.h6m.months == 6
    assert res.h6m.return_bull_pct > res.h3m.return_bull_pct

    # 12M checks
    assert res.h12m.months == 12
    assert res.h12m.expected_return_pct is not None

    # 3Y checks
    assert res.h3y.months == 36
    assert res.h3y.cagr_pct is not None
    assert res.h3y.expected_return_pct > res.h12m.expected_return_pct


def test_analyze_stock_on_demand_offline_db():
    """Verify analyze_stock_on_demand works seamlessly against DB records."""
    from invst.cli import get_db_connection
    conn = get_db_connection()

    res = analyze_stock_on_demand(conn, "INFY", fetch_live=False)
    assert res.symbol == "INFY"
    assert res.current_price > 0.0
    assert 0.0 <= res.business_quality_score <= 100.0
    assert 0.0 <= res.investment_score <= 100.0
    assert res.action_verdict in ["STRONG_BUY", "TACTICAL_BUY", "HOLD_WAIT", "AVOID", "REDLINE_REJECT"]
    assert res.horizon_3m.expected_return_pct is not None
    assert res.horizon_12m.expected_return_pct is not None
    assert len(res.thesis_rationale) > 20

    # Verify tactical execution plan
    assert res.tactical_action is not None
    assert res.tactical_action.dip_target_price > 0.0
    assert res.tactical_action.stop_loss_level > 0.0
    assert len(res.tactical_action.verdict_reasoning) > 30

    # Verify score breakdowns
    assert res.score_breakdowns is not None
    assert "Tier" in res.score_breakdowns.business_quality.tier or "Franchise" in res.score_breakdowns.business_quality.tier or "Moat" in res.score_breakdowns.business_quality.tier
    assert len(res.score_breakdowns.valuation.interpretation) > 15

    # Verify research report
    assert res.research_report is not None
    assert len(res.research_report.executive_summary) > 30
    assert len(res.research_report.fundamental_moat) > 30

    conn.close()


def test_etf_stock_analyzer():
    """Verify that ETFs are properly recognized and never misclassified as distressed value traps."""
    from invst.cli import get_db_connection
    conn = get_db_connection()

    res = analyze_stock_on_demand(conn, "NIFTYBEES", fetch_live=False)
    assert res.is_etf is True
    assert res.sector_archetype == "INDEX_ETF"
    assert res.business_quality_score >= 80.0
    assert res.action_verdict != "AVOID"
    assert "Value Trap" not in res.matrix_quadrant
    assert res.is_investment_worthy is True
    assert res.tactical_action.dip_target_price > 0.0
    assert "diversified" in res.tactical_action.verdict_reasoning.lower() or "index" in res.tactical_action.verdict_reasoning.lower()

    # Test Gold ETF
    gold_res = analyze_stock_on_demand(conn, "GOLDBEES", fetch_live=False)
    assert gold_res.is_etf is True
    assert gold_res.sector_archetype == "COMMODITY_ETF"
    assert gold_res.action_verdict != "AVOID"
    assert gold_res.is_investment_worthy is True

    conn.close()


def test_analyze_stock_on_demand_invalid_symbol_raises_not_found():
    """Verify that invalid/non-existent symbols raise ValueError instead of returning fake 100.0 price."""
    import pytest
    from invst.cli import get_db_connection

    conn = get_db_connection()
    with pytest.raises(ValueError, match="No stock or ETF found"):
        analyze_stock_on_demand(conn, "NONEXISTENT_TICKER_XYZ", fetch_live=False)
    conn.close()

