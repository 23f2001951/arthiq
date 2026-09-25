"""Comprehensive Backtest Performance Metrics.

Calculates key risk-adjusted returns and drawdown metrics:
- CAGR (Compound Annual Growth Rate)
- Sharpe Ratio (annualized, excess over risk-free rate)
- Sortino Ratio (downside deviation risk-adjusted return)
- Calmar Ratio (CAGR / Max Drawdown)
- Max Drawdown (peak-to-trough)
- Average Annualized Turnover
- Hit Rate (% of months beating benchmark)
- Worst 5-day rolling return
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


@dataclass
class BacktestMetrics:
    """Consolidated backtest performance scorecard."""

    cagr: float
    sharpe: float
    sortino: float
    calmar: float
    max_drawdown: float
    annualized_vol: float
    turnover_avg: float
    hit_rate: float
    worst_5d_return: float
    rebalance_count: int
    benchmark_cagr: float
    benchmark_sharpe: float
    benchmark_max_drawdown: float
    alpha: float = 0.0
    information_ratio: float = 0.0
    tracking_error: float = 0.0
    beta: float = 1.0
    jensen_alpha: float = 0.0
    upside_capture: float = 1.0
    downside_capture: float = 1.0
    payoff_ratio: float = 1.0


def compute_drawdown_series(equity_curve: Sequence[float]) -> tuple[list[float], float]:
    """Compute drawdown series and maximum drawdown."""
    if not equity_curve:
        return [], 0.0

    drawdowns: list[float] = []
    running_max = equity_curve[0]
    max_dd = 0.0

    for val in equity_curve:
        if val > running_max:
            running_max = val
        dd = (val - running_max) / running_max if running_max > 0 else 0.0
        drawdowns.append(dd)
        if dd < max_dd:
            max_dd = dd

    return drawdowns, max_dd


def compute_backtest_metrics(
    daily_dates: list[str],
    portfolio_equity: list[float],
    benchmark_equity: list[float] | None = None,
    turnover_per_rebalance: list[float] | None = None,
    risk_free_rate: float = 0.065,
    rebalance_count: int = 0,
) -> BacktestMetrics:
    """Compute all quantitative performance metrics from backtest equity series."""
    n_days = len(portfolio_equity)
    if n_days < 2:
        return BacktestMetrics(
            cagr=0.0,
            sharpe=0.0,
            sortino=0.0,
            calmar=0.0,
            max_drawdown=0.0,
            annualized_vol=0.0,
            turnover_avg=0.0,
            hit_rate=0.0,
            worst_5d_return=0.0,
            rebalance_count=rebalance_count,
            benchmark_cagr=0.0,
            benchmark_sharpe=0.0,
            benchmark_max_drawdown=0.0,
        )

    # Compute exact elapsed years from date series if available
    from datetime import date as dt_date

    years = max(n_days / 252.0, 0.01)
    if daily_dates and len(daily_dates) >= 2:
        try:
            d_start = dt_date.fromisoformat(daily_dates[0])
            d_end = dt_date.fromisoformat(daily_dates[-1])
            calendar_days = (d_end - d_start).days
            if calendar_days > 0:
                years = max(calendar_days / 365.25, 0.01)
        except (ValueError, TypeError):
            pass

    # 1. CAGR
    start_eq = portfolio_equity[0]
    end_eq = portfolio_equity[-1]
    cagr = (end_eq / start_eq) ** (1.0 / years) - 1.0 if start_eq > 0 else 0.0

    # 2. Daily returns
    p_arr = np.array(portfolio_equity)
    daily_returns = (p_arr[1:] - p_arr[:-1]) / p_arr[:-1]

    # Daily risk-free rate
    rf_daily = risk_free_rate / 252.0
    excess_returns = daily_returns - rf_daily

    vol_daily = float(np.std(daily_returns, ddof=1)) if len(daily_returns) > 1 else 0.0
    ann_vol = vol_daily * math.sqrt(252)

    # 3. Sharpe
    sharpe = float(np.mean(excess_returns)) / max(vol_daily, 1e-6) * math.sqrt(252)

    # 4. Sortino
    downside_returns = np.minimum(0.0, daily_returns - rf_daily)
    downside_std = (
        math.sqrt(float(np.mean(downside_returns**2))) if len(downside_returns) > 0 else 1e-6
    )
    sortino = float(np.mean(excess_returns)) / max(downside_std, 1e-6) * math.sqrt(252)

    # 5. Drawdown & Calmar
    _, max_dd = compute_drawdown_series(portfolio_equity)
    calmar = cagr / abs(max_dd) if abs(max_dd) > 1e-4 else 0.0

    # 6. Worst 5-day rolling return
    if n_days >= 6:
        rolling_5d = (p_arr[5:] - p_arr[:-5]) / p_arr[:-5]
        worst_5d = float(np.min(rolling_5d))
    else:
        worst_5d = 0.0

    # 7. Turnover average
    avg_turnover = float(np.mean(turnover_per_rebalance)) if turnover_per_rebalance else 0.0
    # Annualized turnover (assuming quarterly rebalance = 4/yr)
    ann_turnover = avg_turnover * 4.0

    # 8. Benchmark metrics & Hit rate
    bench_cagr = 0.0
    bench_sharpe = 0.0
    bench_max_dd = 0.0
    hit_rate = 0.0
    alpha = 0.0
    information_ratio = 0.0
    tracking_error = 0.0
    beta = 1.0
    jensen_alpha = 0.0

    if benchmark_equity and len(benchmark_equity) == n_days:
        b_start = benchmark_equity[0]
        b_end = benchmark_equity[-1]
        bench_cagr = (b_end / b_start) ** (1.0 / years) - 1.0 if b_start > 0 else 0.0

        b_arr = np.array(benchmark_equity)
        b_daily = (b_arr[1:] - b_arr[:-1]) / b_arr[:-1]
        b_excess = b_daily - rf_daily
        b_vol = float(np.std(b_daily, ddof=1)) if len(b_daily) > 1 else 1e-6
        bench_sharpe = float(np.mean(b_excess)) / max(b_vol, 1e-6) * math.sqrt(252)
        _, bench_max_dd = compute_drawdown_series(benchmark_equity)

        # Active returns, tracking error, information ratio
        active_daily = daily_returns - b_daily
        te_daily = float(np.std(active_daily, ddof=1)) if len(active_daily) > 1 else 0.0
        tracking_error = te_daily * math.sqrt(252)
        if te_daily > 1e-6:
            information_ratio = (float(np.mean(active_daily)) / te_daily) * math.sqrt(252)
        else:
            information_ratio = 0.0

        # Annualized excess return (Alpha)
        alpha = cagr - bench_cagr

        # Beta & Jensen's Alpha
        if len(b_daily) > 1 and len(daily_returns) > 1:
            cov_mat = np.cov(daily_returns, b_daily)
            cov_pb = float(cov_mat[0, 1])
            var_b = float(cov_mat[1, 1])
            beta = cov_pb / max(var_b, 1e-8)
        else:
            beta = 1.0

        # Jensen's Alpha: (R_p - R_f) - beta * (R_b - R_f)
        p_excess_ann = cagr - risk_free_rate
        b_excess_ann = bench_cagr - risk_free_rate
        jensen_alpha = p_excess_ann - (beta * b_excess_ann)

        # Upside / Downside Capture Ratio
        pos_bench = b_daily > 0
        neg_bench = b_daily < 0
        pos_b_mean = float(np.mean(b_daily[pos_bench])) if np.sum(pos_bench) > 0 else 1.0
        neg_b_mean = float(np.mean(b_daily[neg_bench])) if np.sum(neg_bench) > 0 else -1.0
        upside_capture = (
            float(np.mean(daily_returns[pos_bench])) / pos_b_mean
            if np.sum(pos_bench) > 0 and abs(pos_b_mean) > 1e-8
            else 1.0
        )
        downside_capture = (
            float(np.mean(daily_returns[neg_bench])) / neg_b_mean
            if np.sum(neg_bench) > 0 and abs(neg_b_mean) > 1e-8
            else 1.0
        )

        # Payoff ratio: average win active return / average loss active return
        pos_active = active_daily > 0
        neg_active = active_daily < 0
        avg_win = float(np.mean(active_daily[pos_active])) if np.sum(pos_active) > 0 else 0.0
        avg_loss = abs(float(np.mean(active_daily[neg_active]))) if np.sum(neg_active) > 0 else 1e-6
        payoff_ratio = avg_win / avg_loss if avg_loss > 1e-6 else 1.0

        # Monthly hit rate (resample ~21 days/month)
        month_step = 21
        p_monthly = (p_arr[month_step::month_step] - p_arr[:-month_step:month_step]) / p_arr[
            :-month_step:month_step
        ]
        b_monthly = (b_arr[month_step::month_step] - b_arr[:-month_step:month_step]) / b_arr[
            :-month_step:month_step
        ]

        if len(p_monthly) > 0 and len(b_monthly) > 0:
            hits = np.sum(p_monthly > b_monthly[: len(p_monthly)])
            hit_rate = float(hits / len(p_monthly))
    else:
        upside_capture = 1.0
        downside_capture = 1.0
        payoff_ratio = 1.0

    return BacktestMetrics(
        cagr=round(cagr, 4),
        sharpe=round(sharpe, 3),
        sortino=round(sortino, 3),
        calmar=round(calmar, 3),
        max_drawdown=round(max_dd, 4),
        annualized_vol=round(ann_vol, 4),
        turnover_avg=round(ann_turnover, 4),
        hit_rate=round(hit_rate, 4),
        worst_5d_return=round(worst_5d, 4),
        rebalance_count=rebalance_count,
        benchmark_cagr=round(bench_cagr, 4),
        benchmark_sharpe=round(bench_sharpe, 3),
        benchmark_max_drawdown=round(bench_max_dd, 4),
        alpha=round(alpha, 4),
        information_ratio=round(information_ratio, 3),
        tracking_error=round(tracking_error, 4),
        beta=round(beta, 3),
        jensen_alpha=round(jensen_alpha, 4),
        upside_capture=round(upside_capture, 3),
        downside_capture=round(downside_capture, 3),
        payoff_ratio=round(payoff_ratio, 3),
    )
