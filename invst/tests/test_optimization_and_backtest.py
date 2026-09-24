"""Unit and integration tests for portfolio optimization and backtest engine."""

import sqlite3

import numpy as np

from invst.backtest.engine import run_walk_forward_backtest
from invst.backtest.execution import execute_rebalance
from invst.backtest.metrics import compute_backtest_metrics
from invst.optimization.mean_variance import OptimizationResult, optimize_portfolio

# ── Portfolio Optimization Constraints Tests ──────────────────────────


def test_optimization_caps_and_constraints():
    symbols = [f"SYM_{i}" for i in range(10)]
    sector_map = {
        "SYM_0": "tech",
        "SYM_1": "tech",
        "SYM_2": "tech",
        "SYM_3": "tech",
        "SYM_4": "finance",
        "SYM_5": "finance",
        "SYM_6": "finance",
        "SYM_7": "auto",
        "SYM_8": "auto",
        "SYM_9": "pharma",
    }
    mu = np.array([0.15, 0.18, 0.14, 0.20, 0.12, 0.11, 0.13, 0.10, 0.09, 0.08])
    sigma = np.eye(10) * 0.04

    res = optimize_portfolio(
        symbols=symbols,
        sector_map=sector_map,
        mu=mu,
        sigma=sigma,
        target_holdings=8,
        max_stock_weight=0.25,
        max_sector_weight=0.40,
    )

    assert isinstance(res, OptimizationResult)
    weights = res.weights

    # 1. Holdings count <= 8
    assert len(weights) <= 8

    # 2. Sum of weights == 1.0 (within numerical tolerance)
    assert abs(sum(weights.values()) - 1.0) < 1e-3

    # 3. Single-stock cap <= 25% (0.25)
    for sym, w in weights.items():
        assert w <= 0.2501, f"{sym} weight {w} exceeded 0.25"
        assert w >= 0.0, f"{sym} weight {w} is negative"

    # 4. Sector cap <= 40% (0.40)
    for sec, sec_w in res.sector_allocations.items():
        assert sec_w <= 0.4001, f"Sector {sec} weight {sec_w} exceeded 0.40"


# ── Trade Execution Tests ─────────────────────────────────────────────


def test_trade_execution_turnover_and_costs():
    w_curr = {"STOCK_A": 0.50, "STOCK_B": 0.50}
    w_target = {"STOCK_A": 0.25, "STOCK_B": 0.25, "STOCK_C": 0.50}
    prices = {"STOCK_A": 100.0, "STOCK_B": 200.0, "STOCK_C": 50.0}

    exec_res = execute_rebalance(
        target_weights=w_target,
        current_weights=w_curr,
        prices=prices,
        portfolio_value=1_000_000.0,
        buy_cost_bps=30.0,
        sell_cost_bps=20.0,
        slippage_bps=5.0,
    )

    # Turnover: dw = |0.25-0.5| + |0.25-0.5| + |0.5-0| = 0.25 + 0.25 + 0.50 = 1.0
    # Two-sided turnover = 0.5 * 1.0 = 0.50
    assert abs(exec_res.turnover - 0.50) < 1e-4

    # Confirm order actions
    order_map = {o.symbol: o for o in exec_res.orders}
    assert order_map["STOCK_A"].action == "SELL"
    assert order_map["STOCK_B"].action == "SELL"
    assert order_map["STOCK_C"].action == "BUY"
    assert order_map["STOCK_C"].shares == int((1_000_000 * 0.50) / 50.0)
    assert exec_res.total_cost > 0


# ── Backtest Performance Metrics Tests ────────────────────────────────


def test_metrics_calculation():
    dates = [f"2023-01-{i:02d}" for i in range(1, 22)]
    # Equity curve doubling over 20 days: 100 -> 200
    equity = [100.0 * (1.0 + (i * 0.05)) for i in range(21)]
    bench = [100.0 * (1.0 + (i * 0.02)) for i in range(21)]

    metrics = compute_backtest_metrics(
        daily_dates=dates,
        portfolio_equity=equity,
        benchmark_equity=bench,
        turnover_per_rebalance=[0.25],
        rebalance_count=1,
    )

    assert metrics.cagr > 0
    assert metrics.sharpe > 0
    assert metrics.max_drawdown <= 0.0
    assert metrics.rebalance_count == 1
    assert metrics.cagr > metrics.benchmark_cagr


# ── Walk-Forward Simulation End-to-End Test ───────────────────────────


def test_walk_forward_backtest_engine(scoring_db: sqlite3.Connection):
    # Test simulation over Q1 2024
    res = run_walk_forward_backtest(
        conn=scoring_db,
        start_date="2024-01-01",
        end_date="2024-03-31",
        initial_capital=1_000_000.0,
        benchmark_symbol="NIFTY500",
    )

    assert res.run_id is not None
    assert len(res.portfolio_equity) > 0
    assert len(res.benchmark_equity) == len(res.portfolio_equity)

    # Verify backtest_runs DB record
    cur = scoring_db.execute(
        "SELECT status, cagr, sharpe FROM backtest_runs WHERE run_id = ?", (res.run_id,)
    )
    row = cur.fetchone()
    assert row is not None
    assert row[0] == "completed"

    # Verify portfolio_history entries
    cur2 = scoring_db.execute(
        "SELECT COUNT(*) FROM portfolio_history WHERE run_id = ?", (res.run_id,)
    )
    hist_count = cur2.fetchone()[0]
    assert hist_count > 0
