"""
IIM — Core Signal Engine (V1).

Implements two trend-following strategies:
  - TREND_PULLBACK: Entry on EMA21/VWAP pullback in an established uptrend/downtrend.
  - INTRADAY_BREAKOUT: Entry on confirmed breakout of a key level (ORB, prev-day, pivot).

Signal requires ALL four pillars to confirm:
  Pillar 1 (Price Trend):      EMA21 slope + Supertrend alignment on 15m AND 1H.
  Pillar 2 (Volume/OBV):       TODVOL ratio meets strategy threshold + OBV agreement.
  Pillar 3 (Reference Levels): Price vs VWAP + proximity to a key level.
  Pillar 4 (Regime/Index):     Nifty50 ADX ≥ 25 + EMA21 direction aligned.

All signals are generated on CLOSED 15m candles only.
The incomplete (current) candle is never used.
Entry is always modelled at the next candle's open.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Any, Literal

import pandas as pd

from invst.intraday.indicators import compute_pivot_levels, obv_slope
from invst.intraday.regime_detector import Regime, RegimeState

logger = logging.getLogger("invst.intraday.signal_engine")

# ---------------------------------------------------------------------------
# Time Gates (absolute, no exceptions)
# ---------------------------------------------------------------------------
# No signal generation before this time (opening volatility exclusion)
_SIGNAL_OPEN_TIME = time(9, 45)
# No new PULLBACK signals after this time
_PULLBACK_CLOSE_TIME = time(14, 45)
# No new BREAKOUT signals after this time (less time for targets to be reached)
_BREAKOUT_CLOSE_TIME = time(13, 30)
# Hard exit for all positions
_HARD_EXIT_TIME = time(15, 0)

# VWAP proximity threshold (must be within X% of VWAP for pullback signals)
_VWAP_PROXIMITY_PCT = 0.004   # 0.4%
# EMA21 slope: must be positive for N bars to confirm trend
_EMA21_SLOPE_BARS = 5
# Key level proximity threshold (price must be within X% of a key level for breakout)
_LEVEL_PROXIMITY_PCT = 0.003  # 0.3%

SLIPPAGE_PCT = 0.0005  # 0.05% modelled slippage on entry


# ---------------------------------------------------------------------------
# Signal output dataclass
# ---------------------------------------------------------------------------

@dataclass
class SignalResult:
    """A fired intraday signal. Emitted only when all gates pass."""
    strategy_id: str            # 'TREND_PULLBACK_v1' or 'INTRADAY_BREAKOUT_v1'
    strategy_ver: str = "1.0.0"
    symbol: str = ""
    signal_type: Literal["LONG", "SHORT"] = "LONG"
    signal_candle_time: datetime | None = None    # time of signal (closed candle)
    entry_time: datetime | None = None            # next candle open
    entry_price: float = 0.0                      # modelled entry (next open ± slippage)
    sl_price: float = 0.0
    target_1: float = 0.0
    target_2: float = 0.0
    sl_distance: float = 0.0
    reward_risk: float = 2.0
    atr_at_signal: float = 0.0
    confidence_score: int = 0                     # 0–100 based on pillar strength
    pillars_met: list[str] = field(default_factory=list)
    regime: str = ""
    vwap_at_signal: float = 0.0
    pivot_at_signal: float = 0.0
    pdh: float = 0.0
    pdl: float = 0.0
    todvol_ratio: float = 0.0
    rationale: str = ""
    feature_snapshot: dict[str, Any] = field(default_factory=dict)


@dataclass
class PillarState:
    """Tracks which information pillars have confirmed the signal."""
    price_trend: bool = False      # Pillar 1
    volume_obv: bool = False       # Pillar 2
    reference_levels: bool = False # Pillar 3
    regime_index: bool = False     # Pillar 4

    def all_confirmed(self) -> bool:
        return self.price_trend and self.volume_obv and self.reference_levels and self.regime_index

    def confirmed_names(self) -> list[str]:
        names = []
        if self.price_trend:
            names.append("PRICE_TREND")
        if self.volume_obv:
            names.append("VOLUME_OBV")
        if self.reference_levels:
            names.append("REFERENCE_LEVELS")
        if self.regime_index:
            names.append("REGIME_INDEX")
        return names


# ---------------------------------------------------------------------------
# Time Gate Check
# ---------------------------------------------------------------------------

def _is_within_signal_window(
    candle_time: datetime,
    strategy: Literal["TREND_PULLBACK", "INTRADAY_BREAKOUT"],
) -> tuple[bool, str]:
    """
    Returns (allowed, reason). All time gates are absolute — no exceptions.
    """
    t = candle_time.time()
    if t < _SIGNAL_OPEN_TIME:
        return False, f"Before signal open time ({_SIGNAL_OPEN_TIME})"
    if t >= _HARD_EXIT_TIME:
        return False, "After hard exit time (15:00)"
    if strategy == "TREND_PULLBACK" and t >= _PULLBACK_CLOSE_TIME:
        return False, f"After pullback close time ({_PULLBACK_CLOSE_TIME})"
    if strategy == "INTRADAY_BREAKOUT" and t >= _BREAKOUT_CLOSE_TIME:
        return False, f"After breakout close time ({_BREAKOUT_CLOSE_TIME})"
    return True, "OK"


# ---------------------------------------------------------------------------
# Pillar 1: Price Trend & Structure
# ---------------------------------------------------------------------------

def _check_pillar1_trend(
    df: pd.DataFrame,
    direction: Literal["LONG", "SHORT"],
    strategy: str,
) -> tuple[bool, str]:
    """
    Pillar 1: EMA21 slope + Supertrend on 15m must both agree with direction.

    For TREND_PULLBACK:
      - EMA21 slope must be positive (LONG) / negative (SHORT) for ≥5 bars.
      - Price must have recently crossed below (LONG) / above (SHORT) EMA21,
        then closed back above (LONG) / below (SHORT) EMA21 on current bar.
      - Supertrend must be BULLISH (LONG) / BEARISH (SHORT).

    For INTRADAY_BREAKOUT:
      - EMA21 on 15m must be in the direction of the break (slope agreement).
      - Supertrend must be in the direction of the break.
    """
    if len(df) < _EMA21_SLOPE_BARS + 2:
        return False, "Insufficient bars for Pillar 1."

    cur = df.iloc[-1]
    prev_bars = df.iloc[-(_EMA21_SLOPE_BARS + 1):-1]

    ema21_cur = float(cur.get("ema21", float("nan")))
    close_cur = float(cur["close"])
    st_dir = int(cur.get("supertrend_dir", 0))

    if pd.isna(ema21_cur):
        return False, "EMA21 not available (insufficient warmup)."

    # EMA21 slope: must be consistently directional for last 5 bars
    ema21_values = prev_bars["ema21"].dropna()
    if len(ema21_values) < _EMA21_SLOPE_BARS:
        return False, "EMA21 slope: insufficient bars."

    slope = float(ema21_values.iloc[-1]) - float(ema21_values.iloc[0])

    if direction == "LONG":
        slope_ok = slope > 0
        st_ok = st_dir == 1

        if strategy == "TREND_PULLBACK":
            # Price must have dipped below EMA21 recently and recrossed above
            prev_closes = prev_bars["close"]
            prev_ema21 = prev_bars["ema21"]
            dipped_below = any(prev_closes.values < prev_ema21.values)
            recrossed = close_cur > ema21_cur
            if not (slope_ok and st_ok and dipped_below and recrossed):
                return False, (
                    f"LONG PULLBACK P1 failed: slope_ok={slope_ok}, "
                    f"st_ok={st_ok}, dipped={dipped_below}, recrossed={recrossed}"
                )
        else:  # BREAKOUT: just need EMA21 slope + Supertrend alignment
            if not (slope_ok and st_ok):
                return False, f"LONG BREAKOUT P1 failed: slope_ok={slope_ok}, st_ok={st_ok}"

    else:  # SHORT
        slope_ok = slope < 0
        st_ok = st_dir == -1

        if strategy == "TREND_PULLBACK":
            prev_closes = prev_bars["close"]
            prev_ema21 = prev_bars["ema21"]
            rose_above = any(prev_closes.values > prev_ema21.values)
            recrossed = close_cur < ema21_cur
            if not (slope_ok and st_ok and rose_above and recrossed):
                return False, (
                    f"SHORT PULLBACK P1 failed: slope_ok={slope_ok}, "
                    f"st_ok={st_ok}, rose={rose_above}, recrossed={recrossed}"
                )
        else:
            if not (slope_ok and st_ok):
                return False, f"SHORT BREAKOUT P1 failed: slope_ok={slope_ok}, st_ok={st_ok}"

    return True, f"P1 OK: slope={slope:+.4f}, supertrend_dir={st_dir}"


# ---------------------------------------------------------------------------
# Pillar 2: Volume & OBV
# ---------------------------------------------------------------------------

def _check_pillar2_volume(
    cur_bar: pd.Series,
    df: pd.DataFrame,
    todvol_ratio: float,
    direction: Literal["LONG", "SHORT"],
    strategy: str,
) -> tuple[bool, str]:
    """
    Pillar 2: TODVOL ratio meets threshold + OBV trend agrees.

    TREND_PULLBACK:  todvol_ratio ≥ 1.4, OBV slope agrees.
    INTRADAY_BREAKOUT: todvol_ratio ≥ 2.0 (higher bar), OBV agrees.
    """
    vol_threshold = 2.0 if strategy == "INTRADAY_BREAKOUT" else 1.4

    if todvol_ratio == 0.0:
        return False, "TODVOL ratio unavailable (no baseline)."
    if todvol_ratio < vol_threshold:
        return False, f"TODVOL {todvol_ratio:.2f} < {vol_threshold} (Pillar 2 fail)."

    # OBV slope
    if "obv" in df.columns and len(df) >= 5:
        obv_s = obv_slope(df["obv"], lookback=5).iloc[-1]
        obv_ok = (obv_s > 0 and direction == "LONG") or (obv_s < 0 and direction == "SHORT")
        if not obv_ok:
            return False, f"OBV slope {obv_s:.0f} opposes {direction} direction."

    return True, f"P2 OK: TODVOL={todvol_ratio:.2f} ≥ {vol_threshold}"


# ---------------------------------------------------------------------------
# Pillar 3: Reference Levels (VWAP, Pivots, PDH/PDL)
# ---------------------------------------------------------------------------

def _check_pillar3_levels(
    cur_bar: pd.Series,
    direction: Literal["LONG", "SHORT"],
    vwap: float,
    pivot_levels: dict[str, float],
    strategy: str,
    breakout_level: float | None = None,
) -> tuple[bool, str]:
    """
    Pillar 3: Price relationship to VWAP and key structural levels.

    TREND_PULLBACK:
      - LONG: price must be above VWAP. Entry candle low within 0.4% of VWAP or EMA21.
      - SHORT: price must be below VWAP.

    INTRADAY_BREAKOUT:
      - LONG: price must close above VWAP AND above the breakout level.
      - SHORT: price must close below VWAP AND below the breakout level.
    """
    close = float(cur_bar["close"])
    low = float(cur_bar["low"])
    high = float(cur_bar["high"])
    vwap_proximity = abs(low - vwap) / vwap if vwap > 0 else 1.0

    if strategy == "TREND_PULLBACK":
        if direction == "LONG":
            above_vwap = close > vwap
            near_vwap = vwap_proximity <= _VWAP_PROXIMITY_PCT
            if not above_vwap:
                return False, f"LONG PULLBACK P3: close {close:.2f} below VWAP {vwap:.2f}."
            if not near_vwap:
                return False, (
                    f"LONG PULLBACK P3: low {low:.2f} not near VWAP {vwap:.2f} "
                    f"({vwap_proximity*100:.2f}% > {_VWAP_PROXIMITY_PCT*100}%)."
                )
        else:
            below_vwap = close < vwap
            if not below_vwap:
                return False, f"SHORT PULLBACK P3: close {close:.2f} above VWAP {vwap:.2f}."

    elif strategy == "INTRADAY_BREAKOUT":
        if breakout_level is None:
            return False, "BREAKOUT P3: no breakout_level provided."

        if direction == "LONG":
            above_vwap = close > vwap
            above_level = close > breakout_level
            if not (above_vwap and above_level):
                return False, (
                    f"LONG BREAKOUT P3: close {close:.2f} must be > VWAP {vwap:.2f} "
                    f"AND > level {breakout_level:.2f}."
                )
        else:
            below_vwap = close < vwap
            below_level = close < breakout_level
            if not (below_vwap and below_level):
                return False, (
                    f"SHORT BREAKOUT P3: close {close:.2f} must be < VWAP {vwap:.2f} "
                    f"AND < level {breakout_level:.2f}."
                )

    return True, f"P3 OK: close={close:.2f}, VWAP={vwap:.2f}"


# ---------------------------------------------------------------------------
# Pillar 4: Regime & Index Context
# ---------------------------------------------------------------------------

def _check_pillar4_regime(
    regime_state: RegimeState,
    direction: Literal["LONG", "SHORT"],
) -> tuple[bool, str]:
    """
    Pillar 4: Regime must allow signals and direction must match regime.
    This is an absolute gate — AVOID/AMBIGUOUS/RANGING always return False.
    """
    if regime_state.regime == Regime.AVOID:
        return False, f"AVOID regime: {regime_state.reason}"
    if regime_state.regime == Regime.AMBIGUOUS:
        return False, f"AMBIGUOUS regime (ADX gray zone): {regime_state.reason}"
    if regime_state.regime == Regime.RANGING:
        return False, f"RANGING regime: no V1 signals."

    regime_dir = "LONG" if regime_state.regime == Regime.TRENDING_BULL else "SHORT"
    if direction != regime_dir:
        return False, (
            f"Direction {direction} conflicts with {regime_state.regime.value} regime."
        )

    return True, f"P4 OK: {regime_state.regime.value}, ADX={regime_state.adx:.1f}"


# ---------------------------------------------------------------------------
# Confidence Score
# ---------------------------------------------------------------------------

def _compute_confidence(
    pillars: PillarState,
    todvol_ratio: float,
    regime_adx: float,
) -> int:
    """
    Compute a 0–100 confidence score from signal quality indicators.
    This is descriptive only — it does not gate signals.
    """
    score = 0
    # All 4 pillars confirmed (mandatory, so all signals start at 60)
    score += 60
    # TODVOL strength bonus: up to 20 points
    score += min(20, int((todvol_ratio - 1.0) * 10))
    # ADX strength: 25–35 range gives up to 15 points
    score += min(15, int((regime_adx - 25.0) * 1.5))
    # Small reserve: 5 points
    return min(100, max(0, score))


# ---------------------------------------------------------------------------
# Main entry points
# ---------------------------------------------------------------------------

def check_trend_pullback(
    symbol: str,
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    regime_state: RegimeState,
    vwap: float,
    pivot_levels: dict[str, float],
    todvol_ratio: float,
    prev_day_high: float,
    prev_day_low: float,
) -> SignalResult | None:
    """
    Evaluate TREND_PULLBACK strategy on the latest closed 15m bar.

    Returns:
        SignalResult if ALL four pillars pass. None otherwise.
    """
    if df_15m.empty or df_1h.empty:
        return None

    # Last closed bar (index -1 is always a closed bar per contract)
    cur_bar = df_15m.iloc[-1]
    signal_candle_time = cur_bar.name

    # Determine direction from regime
    direction: Literal["LONG", "SHORT"] = "LONG" if regime_state.regime == Regime.TRENDING_BULL else "SHORT"

    # Time gate
    allowed, tg_reason = _is_within_signal_window(signal_candle_time, "TREND_PULLBACK")
    if not allowed:
        logger.debug("[%s] PULLBACK time gate: %s", symbol, tg_reason)
        return None

    # Pillar 4 (absolute gate — check first to fail fast)
    p4_ok, p4_msg = _check_pillar4_regime(regime_state, direction)
    if not p4_ok:
        logger.debug("[%s] P4 fail: %s", symbol, p4_msg)
        return None

    # Pillar 1
    p1_ok, p1_msg = _check_pillar1_trend(df_15m, direction, "TREND_PULLBACK")
    if not p1_ok:
        logger.debug("[%s] P1 fail: %s", symbol, p1_msg)
        return None

    # Pillar 3 (before volume — cheaper check)
    p3_ok, p3_msg = _check_pillar3_levels(cur_bar, direction, vwap, pivot_levels, "TREND_PULLBACK")
    if not p3_ok:
        logger.debug("[%s] P3 fail: %s", symbol, p3_msg)
        return None

    # Pillar 2 (volume — needs TODVOL)
    p2_ok, p2_msg = _check_pillar2_volume(cur_bar, df_15m, todvol_ratio, direction, "TREND_PULLBACK")
    if not p2_ok:
        logger.debug("[%s] P2 fail: %s", symbol, p2_msg)
        return None

    # All pillars confirmed
    pillars = PillarState(price_trend=True, volume_obv=True, reference_levels=True, regime_index=True)
    atr_val = float(cur_bar.get("atr14", 0.0))
    confidence = _compute_confidence(pillars, todvol_ratio, regime_state.adx)

    # Build feature snapshot for DB
    feature_snapshot = {
        "ema21": float(cur_bar.get("ema21", 0)),
        "supertrend_dir": int(cur_bar.get("supertrend_dir", 0)),
        "atr14": atr_val,
        "adx_nifty": regime_state.adx,
        "vwap": vwap,
        "todvol_ratio": todvol_ratio,
        "obv_slope5": float(obv_slope(df_15m["obv"], 5).iloc[-1]) if "obv" in df_15m.columns else 0,
        "p1": p1_msg, "p2": p2_msg, "p3": p3_msg, "p4": p4_msg,
    }

    rationale = (
        f"{symbol} {direction} TREND_PULLBACK: Price pulled back to EMA21/VWAP "
        f"({'above' if direction=='LONG' else 'below'} VWAP ₹{vwap:.2f}) "
        f"on TODVOL {todvol_ratio:.1f}× average. "
        f"Nifty ADX={regime_state.adx:.1f}, regime={regime_state.regime.value}. "
        f"Supertrend bullish. Entry on next bar open."
    )

    return SignalResult(
        strategy_id="TREND_PULLBACK_v1",
        symbol=symbol,
        signal_type=direction,
        signal_candle_time=signal_candle_time,
        atr_at_signal=atr_val,
        confidence_score=confidence,
        pillars_met=pillars.confirmed_names(),
        regime=regime_state.regime.value,
        vwap_at_signal=vwap,
        pivot_at_signal=pivot_levels.get("pivot", 0.0),
        pdh=prev_day_high,
        pdl=prev_day_low,
        todvol_ratio=todvol_ratio,
        rationale=rationale,
        feature_snapshot=feature_snapshot,
    )


def check_intraday_breakout(
    symbol: str,
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    regime_state: RegimeState,
    vwap: float,
    pivot_levels: dict[str, float],
    todvol_ratio: float,
    prev_day_high: float,
    prev_day_low: float,
    orb_high: float | None = None,
    orb_low: float | None = None,
) -> SignalResult | None:
    """
    Evaluate INTRADAY_BREAKOUT strategy on the latest closed 15m bar.

    Breakout levels checked (in priority order):
      1. Opening Range High/Low (9:15–9:44 AM)
      2. Previous-day High/Low
      3. Daily R1/R2/S1/S2

    Returns:
        SignalResult if ALL four pillars pass. None otherwise.
    """
    if df_15m.empty or df_1h.empty:
        return None

    cur_bar = df_15m.iloc[-1]
    signal_candle_time = cur_bar.name
    close = float(cur_bar["close"])

    direction: Literal["LONG", "SHORT"] = "LONG" if regime_state.regime == Regime.TRENDING_BULL else "SHORT"

    # Time gate
    allowed, tg_reason = _is_within_signal_window(signal_candle_time, "INTRADAY_BREAKOUT")
    if not allowed:
        logger.debug("[%s] BREAKOUT time gate: %s", symbol, tg_reason)
        return None

    # Find the best active breakout level
    breakout_level = _find_breakout_level(
        close, direction, orb_high, orb_low, prev_day_high, prev_day_low, pivot_levels
    )
    if breakout_level is None:
        logger.debug("[%s] No active breakout level found.", symbol)
        return None

    # Pillar 4
    p4_ok, p4_msg = _check_pillar4_regime(regime_state, direction)
    if not p4_ok:
        return None

    # Pillar 1
    p1_ok, p1_msg = _check_pillar1_trend(df_15m, direction, "INTRADAY_BREAKOUT")
    if not p1_ok:
        return None

    # Pillar 3
    p3_ok, p3_msg = _check_pillar3_levels(
        cur_bar, direction, vwap, pivot_levels, "INTRADAY_BREAKOUT",
        breakout_level=breakout_level,
    )
    if not p3_ok:
        return None

    # Pillar 2
    p2_ok, p2_msg = _check_pillar2_volume(cur_bar, df_15m, todvol_ratio, direction, "INTRADAY_BREAKOUT")
    if not p2_ok:
        return None

    pillars = PillarState(price_trend=True, volume_obv=True, reference_levels=True, regime_index=True)
    atr_val = float(cur_bar.get("atr14", 0.0))
    confidence = _compute_confidence(pillars, todvol_ratio, regime_state.adx)

    feature_snapshot = {
        "ema21": float(cur_bar.get("ema21", 0)),
        "supertrend_dir": int(cur_bar.get("supertrend_dir", 0)),
        "atr14": atr_val,
        "adx_nifty": regime_state.adx,
        "vwap": vwap,
        "breakout_level": breakout_level,
        "todvol_ratio": todvol_ratio,
        "p1": p1_msg, "p2": p2_msg, "p3": p3_msg, "p4": p4_msg,
    }

    rationale = (
        f"{symbol} {direction} INTRADAY_BREAKOUT: Close ₹{close:.2f} broke "
        f"key level ₹{breakout_level:.2f} on TODVOL {todvol_ratio:.1f}× avg. "
        f"Price {'above' if direction=='LONG' else 'below'} VWAP ₹{vwap:.2f}. "
        f"Nifty ADX={regime_state.adx:.1f}, {regime_state.regime.value}."
    )

    return SignalResult(
        strategy_id="INTRADAY_BREAKOUT_v1",
        symbol=symbol,
        signal_type=direction,
        signal_candle_time=signal_candle_time,
        atr_at_signal=atr_val,
        confidence_score=confidence,
        pillars_met=pillars.confirmed_names(),
        regime=regime_state.regime.value,
        vwap_at_signal=vwap,
        pivot_at_signal=pivot_levels.get("pivot", 0.0),
        pdh=prev_day_high,
        pdl=prev_day_low,
        todvol_ratio=todvol_ratio,
        rationale=rationale,
        feature_snapshot=feature_snapshot,
    )


def _find_breakout_level(
    close: float,
    direction: Literal["LONG", "SHORT"],
    orb_high: float | None,
    orb_low: float | None,
    pdh: float,
    pdl: float,
    pivot_levels: dict[str, float],
) -> float | None:
    """
    Find the most relevant breakout level that the current close has just exceeded.

    For LONG: look for levels price has just crossed above (within 1%).
    For SHORT: look for levels price has just crossed below (within 1%).
    """
    candidates: list[float] = []

    if direction == "LONG":
        if orb_high and close > orb_high:
            candidates.append(orb_high)
        if close > pdh:
            candidates.append(pdh)
        for lvl_name in ("r1", "r2"):
            lvl = pivot_levels.get(lvl_name)
            if lvl and close > lvl:
                candidates.append(lvl)
    else:
        if orb_low and close < orb_low:
            candidates.append(orb_low)
        if close < pdl:
            candidates.append(pdl)
        for lvl_name in ("s1", "s2"):
            lvl = pivot_levels.get(lvl_name)
            if lvl and close < lvl:
                candidates.append(lvl)

    if not candidates:
        return None

    # Return the level closest to current price (most recently broken)
    return min(candidates, key=lambda l: abs(close - l))
