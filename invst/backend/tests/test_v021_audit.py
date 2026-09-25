"""Unit tests for Arth IQ V0.2.1 Audit and Reconciliation Suite."""

from datetime import date

from invst.backtest.audit import (
    audit_cagr_reconciliation,
)
from invst.backtest.engine import BacktestResult, generate_quarterly_dates
from invst.backtest.metrics import compute_backtest_metrics


def test_cagr_reconciliation_exact_formula():
    """Verify that reported CAGR mathematically matches (V_end / V_start)^(1/years) - 1."""
    # 10.0-year series
    d_start = date(2016, 1, 1)
    d_end = date(2026, 1, 1)
    dates = [d_start.isoformat(), d_end.isoformat()]

    p_curve = [1_000_000.0, 2_000_000.0]  # 2x in 10.0 years -> (2.0)^(0.1) - 1 ≈ 7.1773%
    b_curve = [1_000_000.0, 1_800_000.0]  # 1.8x in 10.0 years

    metrics = compute_backtest_metrics(
        daily_dates=dates,
        portfolio_equity=p_curve,
        benchmark_equity=b_curve,
        risk_free_rate=0.065,
    )

    mock_res = BacktestResult(
        run_id="test_reconcile",
        metrics=metrics,
        equity_dates=dates,
        portfolio_equity=p_curve,
        benchmark_equity=b_curve,
        rebalance_history=[],
    )

    reconcile = audit_cagr_reconciliation(mock_res)
    assert reconcile["reconciled_cleanly"] is True
    assert reconcile["strategy_cagr_discrepancy"] < 0.0001
    assert reconcile["benchmark_cagr_discrepancy"] < 0.0001
    assert abs(reconcile["formula_strategy_cagr"] - 0.0718) < 0.001


def test_anti_future_date_clamping():
    """Verify that quarterly dates and backtest ranges do not exceed current date."""
    today = date.today()
    q_dates = generate_quarterly_dates(date(2025, 1, 1), date(2030, 12, 31))
    for q in q_dates:
        assert q <= today


def test_capture_and_payoff_ratios():
    """Test upside/downside capture and payoff ratio calculations."""
    # Create daily returns with variability so tracking error is non-zero
    p_returns = [0.02, -0.005, 0.015, 0.01, -0.002, 0.025, -0.01, 0.018, 0.005, 0.02]
    b_returns = [0.01, -0.010, 0.010, 0.005, -0.005, 0.015, -0.015, 0.010, 0.002, 0.012]

    n_days = len(p_returns) + 1
    dates = [f"2023-01-{i+1:02d}" for i in range(n_days)]

    p_eq = [100.0]
    for r in p_returns:
        p_eq.append(p_eq[-1] * (1.0 + r))

    b_eq = [100.0]
    for r in b_returns:
        b_eq.append(b_eq[-1] * (1.0 + r))

    metrics = compute_backtest_metrics(
        daily_dates=dates,
        portfolio_equity=p_eq,
        benchmark_equity=b_eq,
    )

    assert metrics.upside_capture > 1.0  # Captures more upside than benchmark
    assert metrics.alpha > 0.0
    assert metrics.tracking_error > 0.0
    assert metrics.information_ratio > 0.0

