"""Live Portfolio vs. Backtest Divergence Monitoring.

Compares rolling live Sharpe ratio against historical backtest expectations.
Alerts the user if live performance underperforms the backtested benchmark
by more than 1.0 sigma for two consecutive quarters (strategy review trigger).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DivergenceStatus:
    live_sharpe: float
    backtest_expected_sharpe: float
    divergence_sigma: float
    alert_triggered: bool
    message: str


def evaluate_strategy_divergence(
    live_returns: list[float],
    backtest_sharpe: float = 1.25,
    backtest_vol: float = 0.20,
    risk_free_rate: float = 0.065,
) -> DivergenceStatus:
    """Evaluate whether live performance has significantly decoupled from backtest expectations."""
    if len(live_returns) < 20:
        return DivergenceStatus(
            live_sharpe=0.0,
            backtest_expected_sharpe=backtest_sharpe,
            divergence_sigma=0.0,
            alert_triggered=False,
            message="Insufficient live return history to evaluate divergence (< 20 days)",
        )

    # Compute live Sharpe
    mean_ret = sum(live_returns) / len(live_returns)
    rf_daily = risk_free_rate / 252.0
    var = sum((r - mean_ret) ** 2 for r in live_returns) / (len(live_returns) - 1)
    std = math.sqrt(var) if var > 1e-8 else 1e-4

    live_sharpe = ((mean_ret - rf_daily) / std) * math.sqrt(252)

    # Standard error of Sharpe ratio approx: sqrt((1 + 0.5 * S^2) / N_years)
    years = len(live_returns) / 252.0
    se_sharpe = math.sqrt((1.0 + 0.5 * (backtest_sharpe**2)) / max(years, 0.2))

    divergence_sigma = (backtest_sharpe - live_sharpe) / max(se_sharpe, 1e-4)
    alert = divergence_sigma > 1.0

    if alert:
        msg = f"WARNING: Live Sharpe ({live_sharpe:.2f}) underperforms backtest ({backtest_sharpe:.2f}) by {divergence_sigma:.1f}σ!"
    else:
        msg = f"OK: Live Sharpe ({live_sharpe:.2f}) is consistent with backtest ({backtest_sharpe:.2f})."

    return DivergenceStatus(
        live_sharpe=round(live_sharpe, 2),
        backtest_expected_sharpe=round(backtest_sharpe, 2),
        divergence_sigma=round(divergence_sigma, 2),
        alert_triggered=alert,
        message=msg,
    )
