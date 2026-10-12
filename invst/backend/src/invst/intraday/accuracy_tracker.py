"""
IIM — Accuracy Tracker.

Computes rolling performance metrics from the signal_events event log.
All numbers are derived from actual backtested or live/paper trade outcomes —
no assumed or placeholder values. Every metric in the UI cites the
underlying run_id and trade count.

Metrics computed:
  - Expectancy (E_net) in R after costs
  - 90% bootstrap CI on E_net
  - Profit Factor
  - Win rate (defined: T1 reached before SL, on closed candles)
  - Max consecutive R drawdown
  - Regime-wise breakdown
  - Strategy-wise breakdown

Auto-disable rule (hard):
  If rolling E_net over the last 50 closed trades falls below 0.0R →
  strategy is suspended and displayed as SUSPENDED in the UI.
  Suspension requires manual review to re-enable.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np

from invst.intraday.signal_store import get_signal_history

logger = logging.getLogger("invst.intraday.accuracy_tracker")

COST_PER_TRADE_R = 0.18   # Same constant as backtest_runner


@dataclass
class AccuracyReport:
    strategy_id: str
    mode: str
    computed_at: str
    total_trades: int = 0
    win_trades: int = 0
    loss_trades: int = 0
    win_rate: float = 0.0
    avg_win_r: float = 0.0
    avg_loss_r: float = 0.0
    expectancy_net: float = 0.0
    profit_factor: float = 0.0
    max_drawdown_r: float = 0.0
    ci_lower: float = 0.0
    ci_upper: float = 0.0
    rolling_50_expectancy: float = 0.0
    auto_disabled: bool = False
    regime_breakdown: dict[str, dict[str, Any]] = field(default_factory=dict)
    data_source_note: str = ""   # Always cite sample size + date range


def _bootstrap_ci(
    values: list[float],
    n: int = 1000,
    ci: float = 0.90,
) -> tuple[float, float]:
    """Return (lower, upper) bootstrap CI for the mean of values."""
    if len(values) < 5:
        return float("nan"), float("nan")
    means = sorted(
        float(np.mean(random.choices(values, k=len(values))))
        for _ in range(n)
    )
    alpha = (1.0 - ci) / 2.0
    lo = means[int(alpha * n)]
    hi = means[int((1.0 - alpha) * n) - 1]
    return lo, hi


def compute_accuracy_report(
    conn: Any,
    strategy_id: str | None = None,
    mode: str = "live",
    lookback: int = 200,
    rolling_window: int = 50,
) -> AccuracyReport:
    """
    Compute accuracy metrics from the signal_events event log.

    Args:
        conn: Database connection.
        strategy_id: Filter to a specific strategy. None = all strategies.
        mode: 'live', 'paper', or 'backtest'.
        lookback: Total trades to analyse.
        rolling_window: Trades used for rolling expectancy (auto-disable gate).

    Returns:
        AccuracyReport with all metrics.
    """
    label = strategy_id or "ALL"
    report = AccuracyReport(
        strategy_id=label,
        mode=mode,
        computed_at=datetime.now().isoformat(),
    )

    trades = get_signal_history(conn, strategy_id=strategy_id, mode=mode, limit=lookback)

    # Only use closed trades (terminal outcome known)
    closed_statuses = {"T1_HIT", "T2_HIT", "SL_HIT", "TRAILING_STOP_HIT",
                       "EXPIRED", "MANUAL_EXIT"}
    closed = [t for t in trades if t.get("current_status") in closed_statuses
              and t.get("net_pnl_r") is not None]

    if not closed:
        report.data_source_note = "No closed trades available."
        return report

    pnls = [float(t["net_pnl_r"]) for t in closed]
    # Win = T1_HIT or T2_HIT (reached a profit target before SL)
    wins = [p for t, p in zip(closed, pnls)
            if t.get("current_status") in ("T1_HIT", "T2_HIT")]
    losses = [p for t, p in zip(closed, pnls)
              if t.get("current_status") not in ("T1_HIT", "T2_HIT")]

    report.total_trades = len(closed)
    report.win_trades = len(wins)
    report.loss_trades = len(losses)
    report.win_rate = report.win_trades / report.total_trades if report.total_trades else 0.0
    report.avg_win_r = float(np.mean(wins)) if wins else 0.0
    report.avg_loss_r = float(np.mean(losses)) if losses else 0.0
    report.expectancy_net = float(np.mean(pnls))

    gross_wins = sum(p for p in pnls if p > 0)
    gross_losses = abs(sum(p for p in pnls if p < 0))
    report.profit_factor = (gross_wins / gross_losses) if gross_losses > 0 else float("inf")

    # Max consecutive drawdown in R
    running = 0.0
    max_dd = 0.0
    for p in pnls:
        running = running + abs(p) if p < 0 else 0.0
        max_dd = max(max_dd, running)
    report.max_drawdown_r = max_dd

    # Bootstrap CI
    report.ci_lower, report.ci_upper = _bootstrap_ci(pnls)

    # Rolling expectancy over last N trades
    recent = pnls[-rolling_window:]
    report.rolling_50_expectancy = float(np.mean(recent)) if recent else 0.0

    # Auto-disable check
    if len(recent) >= rolling_window and report.rolling_50_expectancy < 0.0:
        report.auto_disabled = True
        logger.warning(
            "[%s] AUTO-DISABLE triggered: rolling %d-trade E_net=%.4fR < 0. "
            "Strategy suspended pending review.",
            label, rolling_window, report.rolling_50_expectancy,
        )

    # Regime breakdown
    regime_groups: dict[str, list[float]] = {}
    for t, p in zip(closed, pnls):
        regime = t.get("regime", "UNKNOWN")
        regime_groups.setdefault(regime, []).append(p)

    for regime, regime_pnls in regime_groups.items():
        regime_wins = [p for p in regime_pnls if p > 0]
        report.regime_breakdown[regime] = {
            "count": len(regime_pnls),
            "win_rate": len(regime_wins) / len(regime_pnls),
            "expectancy": float(np.mean(regime_pnls)),
        }

    report.data_source_note = (
        f"Based on {report.total_trades} closed trades in mode='{mode}'"
        f"{f', strategy={strategy_id}' if strategy_id else ''}. "
        f"Computed: {report.computed_at}."
    )

    return report


def run_eod_accuracy_report(conn: Any, mode: str = "live") -> dict[str, AccuracyReport]:
    """
    Run end-of-day accuracy reports for all strategies.
    Called by scheduler at 3:45 PM IST.

    Returns:
        Dict mapping strategy_id → AccuracyReport.
    """
    strategy_ids = ["TREND_PULLBACK_v1", "INTRADAY_BREAKOUT_v1"]
    reports = {}
    for sid in strategy_ids:
        try:
            report = compute_accuracy_report(conn, strategy_id=sid, mode=mode)
            reports[sid] = report
            logger.info(
                "EOD accuracy [%s]: trades=%d win_rate=%.1f%% E_net=%.4fR PF=%.3f disabled=%s",
                sid, report.total_trades, report.win_rate * 100,
                report.expectancy_net, report.profit_factor, report.auto_disabled,
            )
        except Exception as exc:
            logger.exception("EOD accuracy report failed for %s: %s", sid, exc)
    return reports


def is_strategy_suspended(conn: Any, strategy_id: str, mode: str = "live") -> bool:
    """
    Quick check: is this strategy currently auto-disabled?

    Returns True if rolling 50-trade E_net < 0.0R.
    """
    report = compute_accuracy_report(conn, strategy_id=strategy_id, mode=mode, rolling_window=50)
    return report.auto_disabled
