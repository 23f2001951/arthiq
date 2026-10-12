"""
IIM — Backtest Runner (Phase 0 gate).

Runs the signal engine against historical 15m data and computes:
  - Expectancy after costs (E_net in R)
  - 90% bootstrap confidence interval on E_net
  - Profit Factor
  - Max consecutive drawdown in R

A strategy passes to production only if ALL five gates pass:
  GATE A: E_net > +0.15R
  GATE B: Lower bound of 90% bootstrap CI on E_net > 0.0R
  GATE C: Profit Factor > 1.4
  GATE D: Max consecutive R drawdown < 6R
  GATE E: Sample size ≥ 200 closed trades

Entry: next-candle open (no lookahead).
Exit: T1 or SL, whichever closes first on a closed candle.
Costs: modelled brokerage + STT + exchange + slippage (~0.18R per trade typical).

Usage:
    from invst.intraday.backtest_runner import run_backtest
    results = run_backtest(symbol="RELIANCE", strategy="TREND_PULLBACK")
    print(results.gate_summary())
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

import numpy as np
import pandas as pd

from invst.intraday.indicators import (
    apply_all_indicators,
    classify_gap,
    compute_pivot_levels,
    resample_to_1h,
)
from invst.intraday.regime_detector import RegimeState, classify_regime, Regime
from invst.intraday.signal_engine import check_intraday_breakout, check_trend_pullback
from invst.intraday.sl_target_engine import compute_sl_target, estimate_remaining_range

logger = logging.getLogger("invst.intraday.backtest")

# Transaction cost model (per V2 spec)
# Based on Zerodha intraday, ₹2000 stock, 1.5 ATR ≈ ₹30 SL distance
# ₹40 brokerage + STT + exchange + slippage ≈ ₹55 round-trip → ~0.18R
COST_PER_TRADE_R = 0.18


@dataclass
class TradeResult:
    signal_id: str
    symbol: str
    strategy_id: str
    signal_type: str
    entry_time: datetime
    entry_price: float
    sl_price: float
    target_1: float
    exit_time: datetime | None
    exit_price: float | None
    gross_pnl_r: float   # in R units (positive = win, negative = loss)
    fees_r: float
    net_pnl_r: float
    outcome: str          # 'T1_HIT', 'SL_HIT', 'EXPIRED'
    mfe_r: float = 0.0
    mae_r: float = 0.0


@dataclass
class BacktestResults:
    strategy_id: str
    symbol: str
    start_date: str
    end_date: str
    trades: list[TradeResult] = field(default_factory=list)
    # Computed metrics (populated by compute_metrics())
    total_trades: int = 0
    win_trades: int = 0
    loss_trades: int = 0
    win_rate: float = 0.0
    avg_win_r: float = 0.0
    avg_loss_r: float = 0.0
    expectancy_gross: float = 0.0
    expectancy_net: float = 0.0
    profit_factor: float = 0.0
    max_drawdown_r: float = 0.0
    ci_lower: float = 0.0
    ci_upper: float = 0.0
    backtest_run_id: str = ""

    # Gate results
    gate_a: bool = False  # E_net > +0.15R
    gate_b: bool = False  # CI lower > 0.0R
    gate_c: bool = False  # PF > 1.4
    gate_d: bool = False  # Max drawdown < 6R
    gate_e: bool = False  # Sample ≥ 200

    def compute_metrics(self, n_bootstrap: int = 1000, ci: float = 0.90) -> None:
        """Compute all metrics from self.trades in-place."""
        if not self.trades:
            return

        pnls = [t.net_pnl_r for t in self.trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        self.total_trades = len(pnls)
        self.win_trades = len(wins)
        self.loss_trades = len(losses)
        self.win_rate = self.win_trades / self.total_trades if self.total_trades else 0.0
        self.avg_win_r = float(np.mean(wins)) if wins else 0.0
        self.avg_loss_r = float(np.mean(losses)) if losses else 0.0
        self.expectancy_net = float(np.mean(pnls))
        gross_pnls = [t.gross_pnl_r for t in self.trades]
        self.expectancy_gross = float(np.mean(gross_pnls))

        gross_wins = sum(p for p in gross_pnls if p > 0)
        gross_losses = abs(sum(p for p in gross_pnls if p < 0))
        self.profit_factor = (gross_wins / gross_losses) if gross_losses > 0 else float("inf")

        # Max consecutive drawdown in R
        running = 0.0
        max_dd = 0.0
        for p in pnls:
            if p < 0:
                running += abs(p)
                max_dd = max(max_dd, running)
            else:
                running = 0.0
        self.max_drawdown_r = max_dd

        # Bootstrap CI on expectancy
        bs_means = []
        for _ in range(n_bootstrap):
            sample = random.choices(pnls, k=len(pnls))
            bs_means.append(float(np.mean(sample)))
        alpha = (1.0 - ci) / 2.0
        bs_means.sort()
        lo_idx = int(alpha * n_bootstrap)
        hi_idx = int((1.0 - alpha) * n_bootstrap) - 1
        self.ci_lower = bs_means[lo_idx]
        self.ci_upper = bs_means[hi_idx]

        # Gate evaluation
        self.gate_a = self.expectancy_net > 0.15
        self.gate_b = self.ci_lower > 0.0
        self.gate_c = self.profit_factor > 1.4
        self.gate_d = self.max_drawdown_r < 6.0
        self.gate_e = self.total_trades >= 200

    def all_gates_pass(self) -> bool:
        return self.gate_a and self.gate_b and self.gate_c and self.gate_d and self.gate_e

    def gate_summary(self) -> str:
        lines = [
            f"=== Backtest Results: {self.strategy_id} | {self.symbol} ===",
            f"  Period: {self.start_date} → {self.end_date}",
            f"  Trades: {self.total_trades} | Win rate: {self.win_rate:.1%}",
            f"  E_gross: {self.expectancy_gross:+.4f}R | E_net (after costs): {self.expectancy_net:+.4f}R",
            f"  90% CI: [{self.ci_lower:+.4f}R, {self.ci_upper:+.4f}R]",
            f"  Profit Factor: {self.profit_factor:.3f}",
            f"  Max Consec Drawdown: {self.max_drawdown_r:.2f}R",
            "",
            f"  GATE A (E_net > +0.15R):         {'✅ PASS' if self.gate_a else '❌ FAIL'} ({self.expectancy_net:+.4f}R)",
            f"  GATE B (CI lower > 0.0R):         {'✅ PASS' if self.gate_b else '❌ FAIL'} ({self.ci_lower:+.4f}R)",
            f"  GATE C (PF > 1.4):                {'✅ PASS' if self.gate_c else '❌ FAIL'} ({self.profit_factor:.3f})",
            f"  GATE D (Max drawdown < 6R):       {'✅ PASS' if self.gate_d else '❌ FAIL'} ({self.max_drawdown_r:.2f}R)",
            f"  GATE E (≥ 200 trades):            {'✅ PASS' if self.gate_e else '❌ FAIL'} ({self.total_trades})",
            "",
            f"  OVERALL: {'✅ PRODUCTION READY' if self.all_gates_pass() else '❌ NOT READY FOR PRODUCTION'}",
        ]
        return "\n".join(lines)


def _simulate_trade(
    signal_bar_idx: int,
    df: pd.DataFrame,
    entry_price: float,
    sl_price: float,
    target_1: float,
    signal_type: str,
) -> tuple[float, float, float, float, str]:
    """
    Simulate a trade from signal bar to T1 or SL, on closed candles only.

    Entry is at the open of the bar immediately after signal_bar_idx.
    Exit is detected on closed candles: T1 or SL.
    Hard exit at 3:00 PM IST regardless.

    Returns:
        (gross_pnl_r, mfe_r, mae_r, exit_price, outcome)
    """
    sign = 1 if signal_type == "LONG" else -1
    sl_dist = abs(entry_price - sl_price)
    if sl_dist <= 0:
        return -1.0, 0.0, -1.0, sl_price, "SL_HIT"

    best_price = entry_price  # for MFE
    worst_price = entry_price  # for MAE

    for i in range(signal_bar_idx + 2, len(df)):
        bar = df.iloc[i]
        bar_time = bar.name
        if hasattr(bar_time, "time") and bar_time.time() >= datetime.strptime("15:00", "%H:%M").time():
            # Hard exit at 3:00 PM
            exit_price = float(bar["open"])
            pnl_r = sign * (exit_price - entry_price) / sl_dist
            mfe_r = sign * (best_price - entry_price) / sl_dist
            mae_r = sign * (worst_price - entry_price) / sl_dist
            return pnl_r - COST_PER_TRADE_R, mfe_r, mae_r, exit_price, "EXPIRED"

        high = float(bar["high"])
        low = float(bar["low"])

        if signal_type == "LONG":
            # Update MFE/MAE
            best_price = max(best_price, high)
            worst_price = min(worst_price, low)
            # Check T1 (optimistic: use high)
            if high >= target_1:
                pnl_r = (target_1 - entry_price) / sl_dist
                mfe_r = (best_price - entry_price) / sl_dist
                mae_r = (worst_price - entry_price) / sl_dist
                return pnl_r - COST_PER_TRADE_R, mfe_r, mae_r, target_1, "T1_HIT"
            # Check SL (conservative: use low)
            if low <= sl_price:
                pnl_r = (sl_price - entry_price) / sl_dist
                mfe_r = (best_price - entry_price) / sl_dist
                mae_r = (worst_price - entry_price) / sl_dist
                return pnl_r - COST_PER_TRADE_R, mfe_r, mae_r, sl_price, "SL_HIT"
        else:
            best_price = min(best_price, low)
            worst_price = max(worst_price, high)
            if low <= target_1:
                pnl_r = (entry_price - target_1) / sl_dist
                mfe_r = (entry_price - best_price) / sl_dist
                mae_r = (entry_price - worst_price) / sl_dist
                return pnl_r - COST_PER_TRADE_R, mfe_r, mae_r, target_1, "T1_HIT"
            if high >= sl_price:
                pnl_r = (entry_price - sl_price) / sl_dist
                mfe_r = (entry_price - best_price) / sl_dist
                mae_r = (entry_price - worst_price) / sl_dist
                return pnl_r - COST_PER_TRADE_R, mfe_r, mae_r, sl_price, "SL_HIT"

    # End of data
    last_close = float(df.iloc[-1]["close"])
    pnl_r = sign * (last_close - entry_price) / sl_dist
    mfe_r = sign * (best_price - entry_price) / sl_dist
    mae_r = sign * (worst_price - entry_price) / sl_dist
    return pnl_r - COST_PER_TRADE_R, mfe_r, mae_r, last_close, "EXPIRED"


def run_backtest(
    df_15m: pd.DataFrame,
    nifty_15m: pd.DataFrame,
    strategy: Literal["TREND_PULLBACK", "INTRADAY_BREAKOUT"],
    symbol: str,
    india_vix_series: pd.Series | None = None,
    n_bootstrap: int = 1000,
) -> BacktestResults:
    """
    Run offline backtest of a strategy over historical 15m data.

    Args:
        df_15m: Historical 15m OHLCV for the stock (with is_warmup column).
        nifty_15m: Historical 15m OHLCV for Nifty50 (aligned).
        strategy: Which strategy to test.
        symbol: NSE symbol (for labelling).
        india_vix_series: Series of daily India VIX values (optional, default 14.0).
        n_bootstrap: Number of bootstrap iterations for CI.

    Returns:
        BacktestResults with all metrics and gate evaluations.
    """
    strategy_id = f"{strategy}_v1"
    start_date = str(df_15m.index[0].date())
    end_date = str(df_15m.index[-1].date())

    # Apply all indicators to stock data
    df = apply_all_indicators(df_15m.copy())
    nifty = apply_all_indicators(nifty_15m.copy())

    # Group into sessions
    if hasattr(df.index, "date"):
        all_dates = sorted(df.index.map(lambda t: t.date()).unique())
    else:
        logger.error("DataFrame must have a DatetimeIndex.")
        return BacktestResults(strategy_id=strategy_id, symbol=symbol,
                               start_date=start_date, end_date=end_date)

    trades: list[TradeResult] = []

    for day_idx, trade_date in enumerate(all_dates):
        if day_idx == 0:
            continue  # Need prior day for pivots

        prev_date = all_dates[day_idx - 1]

        # Get prior day bars for pivot computation
        prev_mask = df.index.map(lambda t: t.date()) == prev_date
        prev_day_bars = df[prev_mask & ~df.get("is_warmup", pd.Series(False, index=df.index)).astype(bool)]
        if prev_day_bars.empty:
            continue

        pdh = float(prev_day_bars["high"].max())
        pdl = float(prev_day_bars["low"].min())
        pdclose = float(prev_day_bars["close"].iloc[-1])
        pivot_levels = compute_pivot_levels(pdh, pdl, pdclose)

        # Get current day's live (non-warmup) bars
        day_mask = df.index.map(lambda t: t.date()) == trade_date
        day_df = df[day_mask]
        if len(day_df) < 4:
            continue

        # Today's open for gap classification
        today_open = float(day_df["open"].iloc[0])
        gap_type = classify_gap(today_open, pdclose)

        # ORB: high/low of 9:15–9:44 AM bars (for BREAKOUT strategy)
        orb_bars = day_df[day_df.index.map(lambda t: t.time() < datetime.strptime("09:45", "%H:%M").time())]
        orb_high = float(orb_bars["high"].max()) if not orb_bars.empty else None
        orb_low = float(orb_bars["low"].min()) if not orb_bars.empty else None

        # India VIX for the day
        vix_val = 14.0
        if india_vix_series is not None:
            try:
                vix_val = float(india_vix_series.loc[str(trade_date)])
            except KeyError:
                pass

        # Nifty bars for regime
        nifty_day_mask = nifty.index.map(lambda t: t.date()) == trade_date
        nifty_day = nifty[nifty_day_mask]

        # Walk through each closed bar from 9:45 onward
        eligible_bars = day_df[day_df.index.map(lambda t: t.time() >= datetime.strptime("09:45", "%H:%M").time())]

        position_open = False  # one position per day per strategy in backtest

        for bar_idx_local, (ts, row) in enumerate(eligible_bars.iterrows()):
            if position_open:
                break

            # Build lookback window up to and including this bar (closed)
            global_bar_idx = df.index.get_loc(ts)
            lookback = df.iloc[:global_bar_idx + 1]
            nifty_lookback = nifty[nifty.index <= ts]

            if len(lookback) < 30 or nifty_lookback.empty:
                continue

            regime_state = classify_regime(nifty_lookback.tail(60), vix_val)
            if regime_state.regime in (Regime.AVOID, Regime.AMBIGUOUS, Regime.RANGING):
                continue

            vwap_val = float(row.get("vwap", 0.0) or 0.0)
            todvol_val = float(row.get("todvol_ratio", 0.0) or 0.0)

            # In backtest, use a neutral todvol if seasonality not available
            if todvol_val == 0.0:
                # Rough approximation: compare to 20-bar average volume
                vol_20avg = float(lookback["volume"].tail(20).mean())
                todvol_val = float(row["volume"]) / vol_20avg if vol_20avg > 0 else 0.0

            df_1h = resample_to_1h(lookback)

            if strategy == "TREND_PULLBACK":
                signal = check_trend_pullback(
                    symbol=symbol,
                    df_15m=lookback,
                    df_1h=df_1h,
                    regime_state=regime_state,
                    vwap=vwap_val,
                    pivot_levels=pivot_levels,
                    todvol_ratio=todvol_val,
                    prev_day_high=pdh,
                    prev_day_low=pdl,
                )
            else:
                signal = check_intraday_breakout(
                    symbol=symbol,
                    df_15m=lookback,
                    df_1h=df_1h,
                    regime_state=regime_state,
                    vwap=vwap_val,
                    pivot_levels=pivot_levels,
                    todvol_ratio=todvol_val,
                    prev_day_high=pdh,
                    prev_day_low=pdl,
                    orb_high=orb_high,
                    orb_low=orb_low,
                )

            if signal is None:
                continue

            # Next bar for entry price
            next_bar_idx = global_bar_idx + 1
            if next_bar_idx >= len(df):
                continue
            next_bar = df.iloc[next_bar_idx]
            entry_price = float(next_bar["open"])

            # Compute SL/Target
            remaining_range = estimate_remaining_range(lookback, ts.to_pydatetime())
            daily_atr = float(lookback["atr14"].iloc[-1]) * 26  # rough daily ATR
            sl_result = compute_sl_target(
                entry_price=entry_price,
                direction=signal.signal_type,
                atr_15m=signal.atr_at_signal,
                sl_atr_adjustment=regime_state.sl_atr_adjustment,
                now=ts.to_pydatetime(),
                expected_remaining_range=remaining_range,
                daily_atr=daily_atr,
            )

            if not sl_result.feasible:
                continue

            # Simulate trade
            gross_pnl_r, mfe_r, mae_r, exit_price, outcome = _simulate_trade(
                signal_bar_idx=global_bar_idx,
                df=df,
                entry_price=entry_price,
                sl_price=sl_result.sl_price,
                target_1=sl_result.target_1,
                signal_type=signal.signal_type,
            )

            trades.append(TradeResult(
                signal_id=f"{symbol}_{ts.isoformat()}",
                symbol=symbol,
                strategy_id=strategy_id,
                signal_type=signal.signal_type,
                entry_time=next_bar.name.to_pydatetime(),
                entry_price=entry_price,
                sl_price=sl_result.sl_price,
                target_1=sl_result.target_1,
                exit_time=None,
                exit_price=exit_price,
                gross_pnl_r=gross_pnl_r + COST_PER_TRADE_R,
                fees_r=COST_PER_TRADE_R,
                net_pnl_r=gross_pnl_r,
                outcome=outcome,
                mfe_r=mfe_r,
                mae_r=mae_r,
            ))
            position_open = True

    results = BacktestResults(
        strategy_id=strategy_id,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        trades=trades,
        backtest_run_id=f"{strategy_id}_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    )
    results.compute_metrics(n_bootstrap=n_bootstrap)
    return results
