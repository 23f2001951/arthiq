"""Unit tests for Alpha, Information Ratio, Tracking Error, Beta, and Jensen's Alpha metrics."""

import numpy as np

from invst.backtest.metrics import compute_backtest_metrics


def test_metrics_ir_alpha_positive():
    """Test metrics when portfolio outperforms benchmark with steady active returns."""
    # 252 trading days (1 year)
    n_days = 253
    dates = [f"2023-01-{i:02d}" for i in range(1, 32)] * 9
    dates = dates[:n_days]

    # Benchmark: starts at 100, compounds 10% annualized
    # Portfolio: starts at 100, compounds 20% annualized
    rng = np.random.default_rng(42)
    t = np.linspace(0, 1.0, n_days)
    bench_returns = rng.normal(0.10 / 252, 0.01, n_days - 1)
    port_returns = rng.normal(0.22 / 252, 0.015, n_days - 1)

    bench_curve = [100.0]
    for r in bench_returns:
        bench_curve.append(bench_curve[-1] * (1.0 + r))

    port_curve = [100.0]
    for r in port_returns:
        port_curve.append(port_curve[-1] * (1.0 + r))

    metrics = compute_backtest_metrics(
        daily_dates=dates,
        portfolio_equity=port_curve,
        benchmark_equity=bench_curve,
        risk_free_rate=0.065,
        rebalance_count=4,
    )

    # Portfolio CAGR (~22%) > Benchmark CAGR (~10.5%)
    assert metrics.cagr > metrics.benchmark_cagr
    # Positive alpha (CAGR - benchmark_cagr)
    assert metrics.alpha > 0.05
    # Information ratio must be positive
    assert metrics.information_ratio > 0.0
    # Tracking error must be positive
    assert metrics.tracking_error > 0.0
    # Jensen's alpha must be positive
    assert metrics.jensen_alpha > 0.0
    # Rebalance count
    assert metrics.rebalance_count == 4


def test_metrics_ir_alpha_zero_active():
    """Test metrics when portfolio perfectly replicates the benchmark."""
    n_days = 100
    dates = [f"2023-01-{i:02d}" for i in range(n_days)]
    curve = [100.0 + i * 0.5 for i in range(n_days)]

    metrics = compute_backtest_metrics(
        daily_dates=dates,
        portfolio_equity=curve,
        benchmark_equity=curve,
        risk_free_rate=0.065,
    )

    assert metrics.alpha == 0.0
    assert metrics.tracking_error == 0.0
    assert metrics.information_ratio == 0.0
    assert metrics.beta == 1.0
