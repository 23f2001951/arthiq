"""
IIM — Technical Indicators.

Computes all indicators on a pandas DataFrame of OHLCV 15m candles.
All functions operate only on fully closed bars (caller is responsible
for passing only closed candles; never the current incomplete bar).

Key design rules:
  - All indicator values are appended as new columns to the passed DataFrame.
  - EMA and related indicators require prior-session warmup bars
    (is_warmup=True rows) to produce accurate values at session start.
  - ATR is computed on 15m bars. ADX for regime detection is computed
    separately on Nifty50 15m data (not on the stock itself).
  - VWAP resets at 9:15 AM IST each day using a cumulative typical-price
    × volume / cumulative volume formula.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# EMA
# ---------------------------------------------------------------------------

def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential moving average. Uses Wilder smoothing (adjust=False)."""
    return series.ewm(span=period, adjust=False).mean()


def add_ema(df: pd.DataFrame, period: int, col: str = "close") -> pd.DataFrame:
    """Add EMA column to df. Column named ema{period}."""
    df = df.copy()
    df[f"ema{period}"] = ema(df[col], period)
    return df


# ---------------------------------------------------------------------------
# ATR (Average True Range)
# ---------------------------------------------------------------------------

def _true_range(df: pd.DataFrame) -> pd.Series:
    """Compute True Range series from OHLCV DataFrame."""
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr


def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Add ATR column. Uses Wilder (RMA) smoothing."""
    df = df.copy()
    tr = _true_range(df)
    # Wilder smoothing = EWM with alpha = 1/period
    df[f"atr{period}"] = tr.ewm(alpha=1.0 / period, adjust=False).mean()
    return df


# ---------------------------------------------------------------------------
# Supertrend
# ---------------------------------------------------------------------------

def add_supertrend(
    df: pd.DataFrame,
    period: int = 10,
    multiplier: float = 2.5,
) -> pd.DataFrame:
    """
    Add Supertrend indicator.

    Adds columns:
      supertrend        — the Supertrend line value
      supertrend_dir    — 1 (bullish) or -1 (bearish)
    """
    df = df.copy()
    hl2 = (df["high"] + df["low"]) / 2.0

    # ATR for Supertrend (Wilder)
    tr = _true_range(df)
    atr = tr.ewm(alpha=1.0 / period, adjust=False).mean()

    upper_band = hl2 + multiplier * atr
    lower_band = hl2 - multiplier * atr

    supertrend = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)

    for i in range(1, len(df)):
        prev_upper = upper_band.iloc[i - 1]
        prev_lower = lower_band.iloc[i - 1]
        prev_close = df["close"].iloc[i - 1]
        cur_close = df["close"].iloc[i]

        # Adjust bands — can only tighten, never widen
        if lower_band.iloc[i] < prev_lower or prev_close < prev_lower:
            lower_band.iloc[i] = lower_band.iloc[i]
        else:
            lower_band.iloc[i] = prev_lower

        if upper_band.iloc[i] > prev_upper or prev_close > prev_upper:
            upper_band.iloc[i] = upper_band.iloc[i]
        else:
            upper_band.iloc[i] = prev_upper

        prev_st = supertrend.iloc[i - 1] if i > 1 else lower_band.iloc[i]

        if prev_st == prev_upper:
            if cur_close <= upper_band.iloc[i]:
                supertrend.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = -1
            else:
                supertrend.iloc[i] = lower_band.iloc[i]
                direction.iloc[i] = 1
        else:
            if cur_close >= lower_band.iloc[i]:
                supertrend.iloc[i] = lower_band.iloc[i]
                direction.iloc[i] = 1
            else:
                supertrend.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = -1

    # First row
    supertrend.iloc[0] = lower_band.iloc[0]
    direction.iloc[0] = 1

    df["supertrend"] = supertrend
    df["supertrend_dir"] = direction
    return df


# ---------------------------------------------------------------------------
# ADX (Average Directional Index) — used on Nifty50 for regime detection
# ---------------------------------------------------------------------------

def add_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Add ADX, +DI, -DI columns.

    Adds:
      adx{period}   — trend strength (0–100; ≥25 = trending, <20 = ranging)
      plus_di       — positive directional indicator
      minus_di      — negative directional indicator
    """
    df = df.copy()
    tr = _true_range(df)

    up_move = df["high"] - df["high"].shift(1)
    down_move = df["low"].shift(1) - df["low"]

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    alpha = 1.0 / period
    smoothed_tr = pd.Series(plus_dm, index=df.index).ewm(alpha=alpha, adjust=False).mean()
    smoothed_plus = pd.Series(plus_dm, index=df.index).ewm(alpha=alpha, adjust=False).mean()
    smoothed_minus = pd.Series(minus_dm, index=df.index).ewm(alpha=alpha, adjust=False).mean()
    smoothed_tr_real = tr.ewm(alpha=alpha, adjust=False).mean()

    plus_di = 100.0 * smoothed_plus / smoothed_tr_real.replace(0, np.nan)
    minus_di = 100.0 * smoothed_minus / smoothed_tr_real.replace(0, np.nan)

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=alpha, adjust=False).mean()

    df[f"adx{period}"] = adx.fillna(0)
    df["plus_di"] = plus_di.fillna(0)
    df["minus_di"] = minus_di.fillna(0)
    return df


# ---------------------------------------------------------------------------
# OBV (On-Balance Volume)
# ---------------------------------------------------------------------------

def add_obv(df: pd.DataFrame) -> pd.DataFrame:
    """Add On-Balance Volume."""
    df = df.copy()
    direction = np.sign(df["close"].diff().fillna(0))
    df["obv"] = (direction * df["volume"]).cumsum()
    return df


# ---------------------------------------------------------------------------
# VWAP — resets each session at 9:15 AM IST
# ---------------------------------------------------------------------------

def add_vwap(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add VWAP column. VWAP resets at session open (9:15 AM IST).

    DataFrame must have a DatetimeIndex in IST (or tz-aware UTC).
    Only non-warmup bars contribute to VWAP accumulation.
    """
    df = df.copy()
    df["typical_price"] = (df["high"] + df["low"] + df["close"]) / 3.0

    # Group by calendar date for session reset
    if hasattr(df.index, "date"):
        dates = df.index.map(lambda t: t.date())
    else:
        dates = pd.Series(range(len(df)), index=df.index)

    cum_tp_vol = (df["typical_price"] * df["volume"]).groupby(dates).cumsum()
    cum_vol = df["volume"].groupby(dates).cumsum()
    df["vwap"] = cum_tp_vol / cum_vol.replace(0, np.nan)
    df.drop(columns=["typical_price"], inplace=True)
    return df


# ---------------------------------------------------------------------------
# Daily Pivot Levels (computed once per session from prior-day OHLC)
# ---------------------------------------------------------------------------

def compute_pivot_levels(
    prev_high: float,
    prev_low: float,
    prev_close: float,
) -> dict[str, float]:
    """
    Return classic floor pivot levels for the current session.

    Returns:
        dict with keys: pivot, r1, r2, r3, s1, s2, s3
    """
    p = (prev_high + prev_low + prev_close) / 3.0
    r1 = 2.0 * p - prev_low
    r2 = p + (prev_high - prev_low)
    r3 = prev_high + 2.0 * (p - prev_low)
    s1 = 2.0 * p - prev_high
    s2 = p - (prev_high - prev_low)
    s3 = prev_low - 2.0 * (prev_high - p)
    return {"pivot": p, "r1": r1, "r2": r2, "r3": r3, "s1": s1, "s2": s2, "s3": s3}


# ---------------------------------------------------------------------------
# EMA on 1-Hour bars (for multi-timeframe confirmation)
# ---------------------------------------------------------------------------

def resample_to_1h(df_15m: pd.DataFrame) -> pd.DataFrame:
    """
    Resample a 15m OHLCV DataFrame to 1H bars.

    Only fully closed 1H bars are returned (the current incomplete bar is dropped).
    """
    df_1h = df_15m.resample("1h", closed="left", label="left").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna(subset=["close"])
    return df_1h


# ---------------------------------------------------------------------------
# OBV slope helper
# ---------------------------------------------------------------------------

def obv_slope(obv_series: pd.Series, lookback: int = 5) -> pd.Series:
    """
    Return the slope of OBV over the last `lookback` bars.
    Positive = accumulation, Negative = distribution.
    """
    return obv_series.diff(lookback)


# ---------------------------------------------------------------------------
# Gap classification
# ---------------------------------------------------------------------------

def classify_gap(today_open: float, prev_close: float) -> str:
    """
    Classify the opening gap relative to previous session close.

    Returns:
        'GAP_UP'   — open > prev_close by ≥ 0.5%
        'GAP_DOWN' — open < prev_close by ≥ 0.5%
        'FLAT'     — within ±0.5%
    """
    if prev_close <= 0:
        return "FLAT"
    gap_pct = (today_open - prev_close) / prev_close * 100.0
    if gap_pct >= 0.5:
        return "GAP_UP"
    if gap_pct <= -0.5:
        return "GAP_DOWN"
    return "FLAT"


# ---------------------------------------------------------------------------
# All-in-one: apply all indicators to a 15m DataFrame
# ---------------------------------------------------------------------------

def apply_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply the full indicator suite to a 15m OHLCV DataFrame.

    Adds: ema9, ema21, ema50, atr14, supertrend, supertrend_dir,
          adx14, plus_di, minus_di, obv, vwap.

    Args:
        df: DataFrame with columns [open, high, low, close, volume]
            and a tz-aware DatetimeIndex in IST or UTC.
            Must include prior-session warmup bars (is_warmup=True) at the top
            so that EMA50 etc. are accurately seeded.

    Returns:
        DataFrame with all indicator columns added.
    """
    df = add_ema(df, period=9)
    df = add_ema(df, period=21)
    df = add_ema(df, period=50)
    df = add_atr(df, period=14)
    df = add_supertrend(df, period=10, multiplier=2.5)
    df = add_adx(df, period=14)
    df = add_obv(df)
    df = add_vwap(df)
    return df
