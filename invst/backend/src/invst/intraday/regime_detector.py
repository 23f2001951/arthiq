"""
IIM — Market Regime Detector.

Classifies the current intraday market regime based on ADX(14) computed
on Nifty50 15m bars — NOT on the individual stock.

Regime drives which strategies are eligible to fire:
  TRENDING_BULL  → TREND_PULLBACK (long) + INTRADAY_BREAKOUT (long)
  TRENDING_BEAR  → TREND_PULLBACK (short) + INTRADAY_BREAKOUT (short)
  AMBIGUOUS      → No new signals (ADX 20–25 gray zone)
  RANGING        → No signals in V1
  AVOID          → Engine paused (VIX > 28 or ADX logic conflict)

India VIX modifies SL width:
  VIX > 22 and ≤ 28  → SL multiplier increased by 0.5 ATR
  VIX > 28           → AVOID regime
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

import pandas as pd

from invst.intraday.indicators import add_adx, add_ema

logger = logging.getLogger("invst.intraday.regime")


class Regime(str, Enum):
    TRENDING_BULL = "TRENDING_BULL"
    TRENDING_BEAR = "TRENDING_BEAR"
    AMBIGUOUS = "AMBIGUOUS"
    RANGING = "RANGING"
    AVOID = "AVOID"


@dataclass
class RegimeState:
    regime: Regime
    adx: float
    nifty_ema21_slope: float   # positive = rising, negative = falling
    india_vix: float
    sl_atr_adjustment: float   # extra ATR to add to SL distance (0.0 normally)
    reason: str


# ADX thresholds (from V2 spec, all hard rules)
_ADX_TRENDING = 25.0
_ADX_AMBIGUOUS_LOW = 20.0
_VIX_WIDEN_SL = 22.0
_VIX_AVOID = 28.0


def classify_regime(
    nifty_15m: pd.DataFrame,
    india_vix: float,
) -> RegimeState:
    """
    Classify the current intraday market regime.

    Args:
        nifty_15m: DataFrame of Nifty50 15m candles (with warmup bars),
                   columns: [open, high, low, close, volume].
                   Must be fully closed bars only, sorted ascending.
        india_vix: Current India VIX value.

    Returns:
        RegimeState with regime classification and SL adjustment.
    """
    # Safety: always check VIX first
    if india_vix >= _VIX_AVOID:
        return RegimeState(
            regime=Regime.AVOID,
            adx=0.0,
            nifty_ema21_slope=0.0,
            india_vix=india_vix,
            sl_atr_adjustment=0.0,
            reason=f"India VIX={india_vix:.1f} ≥ {_VIX_AVOID}. Engine paused.",
        )

    if len(nifty_15m) < 15:
        return RegimeState(
            regime=Regime.AVOID,
            adx=0.0,
            nifty_ema21_slope=0.0,
            india_vix=india_vix,
            sl_atr_adjustment=0.0,
            reason="Insufficient Nifty50 bars for regime detection.",
        )

    # Compute ADX on Nifty50
    df = add_adx(nifty_15m.copy(), period=14)
    df = add_ema(df, period=21)

    current_adx = float(df["adx14"].iloc[-1])
    ema21_cur = float(df["ema21"].iloc[-1])
    ema21_prev = float(df["ema21"].iloc[-2]) if len(df) >= 2 else ema21_cur
    ema21_slope = ema21_cur - ema21_prev  # positive = uptrend, negative = downtrend

    sl_adjustment = 0.5 if india_vix > _VIX_WIDEN_SL else 0.0

    if current_adx >= _ADX_TRENDING:
        if ema21_slope >= 0:
            regime = Regime.TRENDING_BULL
            reason = (
                f"ADX={current_adx:.1f} ≥ {_ADX_TRENDING}, "
                f"EMA21 rising ({ema21_slope:+.2f}). Trending bull."
            )
        else:
            regime = Regime.TRENDING_BEAR
            reason = (
                f"ADX={current_adx:.1f} ≥ {_ADX_TRENDING}, "
                f"EMA21 falling ({ema21_slope:+.2f}). Trending bear."
            )
    elif current_adx >= _ADX_AMBIGUOUS_LOW:
        regime = Regime.AMBIGUOUS
        reason = (
            f"ADX={current_adx:.1f} in gray zone "
            f"[{_ADX_AMBIGUOUS_LOW}, {_ADX_TRENDING}). No signals."
        )
    else:
        regime = Regime.RANGING
        reason = f"ADX={current_adx:.1f} < {_ADX_AMBIGUOUS_LOW}. Ranging. No V1 signals."

    if sl_adjustment > 0:
        reason += f" VIX={india_vix:.1f} > {_VIX_WIDEN_SL}: SL widened +{sl_adjustment} ATR."

    return RegimeState(
        regime=regime,
        adx=current_adx,
        nifty_ema21_slope=ema21_slope,
        india_vix=india_vix,
        sl_atr_adjustment=sl_adjustment,
        reason=reason,
    )


def regime_allows_signals(regime: Regime) -> bool:
    """Return True if the current regime permits new signal generation."""
    return regime in (Regime.TRENDING_BULL, Regime.TRENDING_BEAR)


def signal_direction_for_regime(regime: Regime) -> str | None:
    """
    Return the allowed signal direction given the current regime.

    Returns:
        'LONG'  for TRENDING_BULL
        'SHORT' for TRENDING_BEAR
        None    for all other regimes
    """
    if regime == Regime.TRENDING_BULL:
        return "LONG"
    if regime == Regime.TRENDING_BEAR:
        return "SHORT"
    return None
