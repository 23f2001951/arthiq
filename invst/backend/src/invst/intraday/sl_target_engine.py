"""
IIM — SL, Target & Feasibility Engine.

Computes ATR-based dynamic Stop Loss and Targets, then checks feasibility
against time remaining and stock daily range before a signal is emitted.

Rules (from V2 spec, all hard):
  sl_distance = 1.5 × ATR(14, 15m) + sl_atr_adjustment (from VIX)
  target_1    = entry + 2.0 × sl_distance   (R:R = 1:2)
  target_2    = entry + 3.0 × sl_distance   (R:R = 1:3)
  T3 is NOT computed in V1.

Feasibility gate (both conditions must pass):
  1. T1 must be reachable: T1 distance ≤ 0.7 × expected_remaining_range
  2. T1 must be within half the stock's typical daily range.

Trailing stop (post-T1 hit):
  After T1: SL moves to breakeven.
  After T2: SL moves to T1 price.
  Residual: 2.0 ATR trailing stop.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Literal

import numpy as np
import pandas as pd

logger = logging.getLogger("invst.intraday.sl_target")

# Hard exit time — all positions must be closed by 3:00 PM IST
_HARD_EXIT_TIME = time(15, 0)
_15M_BAR_SECONDS = 15 * 60


@dataclass
class SLTargetResult:
    """Output of compute_sl_target()."""
    entry_price: float
    sl_price: float
    target_1: float
    target_2: float
    sl_distance: float
    reward_risk: float            # = T1 distance / SL distance = 2.0
    atr_at_signal: float
    feasible: bool
    feasibility_reason: str = ""
    direction: Literal["LONG", "SHORT"] = "LONG"


def compute_sl_target(
    entry_price: float,
    direction: Literal["LONG", "SHORT"],
    atr_15m: float,
    sl_atr_adjustment: float,
    now: datetime,
    expected_remaining_range: float,
    daily_atr: float,
) -> SLTargetResult:
    """
    Compute SL, T1, T2 and run the feasibility gate.

    Args:
        entry_price: Modelled entry (next candle's expected open).
        direction: 'LONG' or 'SHORT'.
        atr_15m: ATR(14) on 15m bars at signal time (closed bars).
        sl_atr_adjustment: Extra ATR to add to SL distance (from VIX regime).
        now: Current datetime (IST). Used for time-remaining calculation.
        expected_remaining_range: Estimated remaining session range in price.
        daily_atr: ATR(14) on daily bars (for T1/daily range gate).

    Returns:
        SLTargetResult.
    """
    sl_dist = (1.5 + sl_atr_adjustment) * atr_15m
    t1_dist = 2.0 * sl_dist
    t2_dist = 3.0 * sl_dist

    sign = 1 if direction == "LONG" else -1
    sl_price = entry_price - sign * sl_dist
    target_1 = entry_price + sign * t1_dist
    target_2 = entry_price + sign * t2_dist

    # Feasibility gate 1: T1 must fit within 70% of remaining session range
    feasible_range = t1_dist <= 0.70 * expected_remaining_range
    # Feasibility gate 2: T1 must be within 50% of stock's typical daily range
    feasible_daily = t1_dist <= 0.50 * daily_atr

    feasible = feasible_range and feasible_daily
    reasons = []
    if not feasible_range:
        reasons.append(
            f"T1 distance ({t1_dist:.2f}) > 70% of remaining range ({0.70*expected_remaining_range:.2f})"
        )
    if not feasible_daily:
        reasons.append(
            f"T1 distance ({t1_dist:.2f}) > 50% of daily ATR ({0.50*daily_atr:.2f})"
        )

    return SLTargetResult(
        entry_price=entry_price,
        sl_price=round(sl_price, 2),
        target_1=round(target_1, 2),
        target_2=round(target_2, 2),
        sl_distance=round(sl_dist, 2),
        reward_risk=2.0,
        atr_at_signal=round(atr_15m, 4),
        feasible=feasible,
        feasibility_reason="; ".join(reasons) if reasons else "OK",
        direction=direction,
    )


def estimate_remaining_range(
    df_15m: pd.DataFrame,
    now: datetime,
    lookback_sessions: int = 20,
) -> float:
    """
    Estimate the expected price range from `now` until 3:00 PM IST,
    based on historical same-time-of-day patterns.

    Args:
        df_15m: Historical 15m OHLCV DataFrame (multiple sessions, warmup included).
        now: Current datetime.
        lookback_sessions: Number of prior sessions to average over.

    Returns:
        Estimated remaining range in price points.
        Falls back to 2.0 × current ATR if insufficient data.
    """
    if df_15m.empty:
        return 0.0

    current_time = now.time()

    # Group by date
    if hasattr(df_15m.index, "date"):
        dates = sorted(df_15m.index.map(lambda t: t.date()).unique())
    else:
        return 0.0

    ranges: list[float] = []
    for d in dates[-lookback_sessions:]:
        day_mask = df_15m.index.map(lambda t: t.date()) == d
        day_bars = df_15m[day_mask]
        # Filter to bars from current_time to 15:00
        future_bars = day_bars[
            day_bars.index.map(lambda t: t.time() >= current_time and t.time() < _HARD_EXIT_TIME)
        ]
        if len(future_bars) < 2:
            continue
        high = future_bars["high"].max()
        low = future_bars["low"].min()
        ranges.append(high - low)

    if not ranges:
        # Fallback: current ATR × number of remaining bars
        bars_remaining = max(1, int(
            (_HARD_EXIT_TIME.hour * 60 + _HARD_EXIT_TIME.minute -
             current_time.hour * 60 - current_time.minute) / 15
        ))
        atr_now = float(df_15m["atr14"].iloc[-1]) if "atr14" in df_15m.columns else 0.0
        return atr_now * max(1.0, bars_remaining ** 0.5)

    return float(np.mean(ranges))


def apply_trailing_stop(
    current_price: float,
    direction: Literal["LONG", "SHORT"],
    result: SLTargetResult,
    t1_hit: bool,
    t2_hit: bool,
    atr_15m: float,
) -> float:
    """
    Compute the current stop loss price given trade progress.

    Logic:
      Before T1: SL fixed at original sl_price.
      After T1:  SL moves to breakeven (entry_price).
      After T2:  SL moves to T1 price. Residual uses 2.0 ATR trailing.

    Returns:
        Updated SL price.
    """
    sign = 1 if direction == "LONG" else -1

    if not t1_hit:
        return result.sl_price

    if not t2_hit:
        # SL at breakeven
        return result.entry_price

    # SL at T1; also apply 2× ATR trailing
    trailing_sl = current_price - sign * 2.0 * atr_15m
    # Take the more conservative (protective) stop
    if direction == "LONG":
        return max(result.target_1, trailing_sl)
    else:
        return min(result.target_1, trailing_sl)
