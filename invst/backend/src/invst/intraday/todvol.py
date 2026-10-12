"""
IIM — Time-of-Day Volume (TODVOL) Module.

Intraday volume follows a U-shaped pattern (heavy at open/close, light midday).
Comparing raw volume to a simple 20-bar moving average distorts the signal
because the baseline is distorted by which bars happen to be high-volume.

TODVOL corrects for this by comparing each bar's volume to the average volume
for the *same time slot* across the last N trading sessions.

Usage:
    # Build the seasonality baseline (run after market close):
    build_volume_seasonality(conn, symbols, lookback_sessions=20)

    # During live signal computation:
    ratio = get_todvol_ratio(conn, symbol, time_slot="10:30")
    volume_confirmed = ratio >= 1.4   # pullback threshold
    volume_confirmed = ratio >= 2.0   # breakout threshold
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, time
from typing import Any

import pandas as pd

logger = logging.getLogger("invst.intraday.todvol")

# Time slot format stored in DB: "HH:MM" e.g. "09:30", "10:00"
TIME_SLOT_FORMAT = "%H:%M"


def candle_time_to_slot(dt: datetime) -> str:
    """Convert a candle's timestamp to its HH:MM time slot string."""
    return dt.strftime(TIME_SLOT_FORMAT)


def build_volume_seasonality(
    conn: Any,
    symbol: str,
    lookback_sessions: int = 20,
) -> int:
    """
    Compute and persist the time-of-day volume baseline for a symbol.

    Reads historical 15m candle data from `intraday_candles`, computes
    the mean volume per time slot across the last `lookback_sessions` sessions,
    and upserts into `volume_seasonality`.

    Returns:
        Number of time slots written.
    """
    cur = conn.cursor()

    # Pull enough candles (need lookback_sessions × ~27 bars per day)
    cur.execute(
        """
        SELECT candle_time, volume
        FROM intraday_candles
        WHERE symbol = ? AND timeframe = '15m' AND is_warmup = 0
        ORDER BY candle_time DESC
        LIMIT ?
        """,
        (symbol, lookback_sessions * 30),
    )
    rows = cur.fetchall()
    if not rows:
        logger.debug("No candle data found for TODVOL baseline: %s", symbol)
        return 0

    df = pd.DataFrame(rows, columns=["candle_time", "volume"])
    df["candle_time"] = pd.to_datetime(df["candle_time"])
    df["date"] = df["candle_time"].dt.date
    df["slot"] = df["candle_time"].dt.strftime(TIME_SLOT_FORMAT)

    # Only keep up to lookback_sessions distinct dates
    unique_dates = sorted(df["date"].unique(), reverse=True)[:lookback_sessions]
    df = df[df["date"].isin(unique_dates)]

    baseline = (
        df.groupby("slot")["volume"]
        .agg(["mean", "count"])
        .reset_index()
        .rename(columns={"mean": "mean_volume", "count": "session_count"})
    )

    today_str = datetime.now().date().isoformat()
    written = 0
    for _, row in baseline.iterrows():
        conn.execute(
            """
            INSERT OR REPLACE INTO volume_seasonality
                (symbol, time_slot, session_count, mean_volume, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (symbol, row["slot"], int(row["session_count"]),
             float(row["mean_volume"]), today_str),
        )
        written += 1

    conn.commit()
    logger.info("TODVOL baseline updated: %s — %d slots", symbol, written)
    return written


def get_todvol_ratio(
    conn: Any,
    symbol: str,
    time_slot: str,
    current_volume: float,
) -> float:
    """
    Return current bar's TODVOL ratio.

    Args:
        conn: DB connection.
        symbol: NSE symbol.
        time_slot: HH:MM string (e.g. "10:30").
        current_volume: Volume of the current (closed) bar.

    Returns:
        Ratio = current_volume / baseline_mean_volume.
        Returns 0.0 if no baseline exists (treat as unconfirmed).
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT mean_volume FROM volume_seasonality
        WHERE symbol = ? AND time_slot = ?
        """,
        (symbol, time_slot),
    )
    row = cur.fetchone()
    if not row or float(row[0]) <= 0:
        return 0.0
    return current_volume / float(row[0])


def get_bulk_todvol_ratios(
    conn: Any,
    symbol: str,
    df_15m: pd.DataFrame,
) -> pd.Series:
    """
    Compute TODVOL ratios for an entire 15m DataFrame in one DB call.

    Args:
        conn: DB connection.
        symbol: NSE symbol.
        df_15m: 15m OHLCV DataFrame with DatetimeIndex.

    Returns:
        pd.Series of TODVOL ratios aligned to df_15m.index.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT time_slot, mean_volume FROM volume_seasonality WHERE symbol = ?",
        (symbol,),
    )
    baseline_rows = cur.fetchall()
    if not baseline_rows:
        return pd.Series(0.0, index=df_15m.index)

    baseline = {row[0]: float(row[1]) for row in baseline_rows}

    slots = df_15m.index.strftime(TIME_SLOT_FORMAT)
    ratios = pd.Series(
        [
            (df_15m.loc[idx, "volume"] / baseline[slot])
            if slot in baseline and baseline[slot] > 0
            else 0.0
            for idx, slot in zip(df_15m.index, slots)
        ],
        index=df_15m.index,
    )
    return ratios
