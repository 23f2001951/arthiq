"""
IIM — Signal Store.

Persists signals and events to the database following strict append-only rules:
  - intraday_signals:  append-only (never updated).
  - signal_events:     append-only event log (status changes, outcomes, MFE/MAE).
  - v_signal_status:   derived view — current status is always the latest event.

All reads use the view v_signal_status for current state.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger("invst.intraday.signal_store")

# ---------------------------------------------------------------------------
# DB Migration: Create intraday tables
# ---------------------------------------------------------------------------

INTRADAY_SCHEMA_SQL = """
-- Signal table: APPEND ONLY. Never UPDATE this table.
CREATE TABLE IF NOT EXISTS intraday_signals (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id         TEXT NOT NULL,
    strategy_ver        TEXT NOT NULL DEFAULT '1.0.0',
    mode                TEXT NOT NULL CHECK(mode IN ('live','paper','backtest')),
    symbol              TEXT NOT NULL,
    exchange            TEXT NOT NULL DEFAULT 'NSE',
    signal_type         TEXT NOT NULL CHECK(signal_type IN ('LONG','SHORT')),
    signal_candle_time  TIMESTAMP NOT NULL,
    entry_time          TIMESTAMP,
    timeframe           TEXT NOT NULL DEFAULT '15m',
    entry_price         REAL,
    sl_price            REAL NOT NULL,
    target_1            REAL NOT NULL,
    target_2            REAL,
    sl_distance         REAL NOT NULL,
    reward_risk         REAL NOT NULL,
    atr_at_signal       REAL NOT NULL,
    confidence_score    INTEGER,
    pillars_met         TEXT NOT NULL,
    regime              TEXT NOT NULL,
    vwap_at_signal      REAL,
    pivot_at_signal     REAL,
    pdh                 REAL,
    pdl                 REAL,
    todvol_ratio        REAL,
    rationale           TEXT,
    feature_snapshot    TEXT,
    feasibility_ok      INTEGER NOT NULL DEFAULT 1,
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Event log: all state transitions. APPEND ONLY.
CREATE TABLE IF NOT EXISTS signal_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id       INTEGER NOT NULL REFERENCES intraday_signals(id),
    event_type      TEXT NOT NULL,
    event_time      TIMESTAMP NOT NULL,
    price           REAL,
    shares          INTEGER,
    gross_pnl_r     REAL,
    fees_r          REAL,
    net_pnl_r       REAL,
    mfe_r           REAL,
    mae_r           REAL,
    note            TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Candle cache (15m bars with pre-computed indicators, includes warmup bars)
CREATE TABLE IF NOT EXISTS intraday_candles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol          TEXT NOT NULL,
    timeframe       TEXT NOT NULL DEFAULT '15m',
    candle_time     TIMESTAMP NOT NULL,
    open            REAL, high REAL, low REAL, close REAL, volume INTEGER,
    ema21           REAL,
    supertrend      REAL,
    supertrend_dir  INTEGER,
    atr14           REAL,
    adx14_nifty     REAL,
    vwap            REAL,
    obv             REAL,
    todvol_ratio    REAL,
    is_warmup       INTEGER DEFAULT 0,
    UNIQUE(symbol, timeframe, candle_time)
);

-- Time-of-day volume baseline (20-session avg per time slot)
CREATE TABLE IF NOT EXISTS volume_seasonality (
    symbol          TEXT NOT NULL,
    time_slot       TEXT NOT NULL,
    session_count   INTEGER NOT NULL,
    mean_volume     REAL NOT NULL,
    updated_at      DATE NOT NULL,
    PRIMARY KEY(symbol, time_slot)
);

-- Today's selected intraday universe (ISS-scored)
CREATE TABLE IF NOT EXISTS intraday_universe (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    date                DATE NOT NULL,
    symbol              TEXT NOT NULL,
    iss_score           REAL NOT NULL,
    liquidity_score     REAL,
    atr_pct_15m         REAL,
    momentum_score      REAL,
    todvol_score        REAL,
    level_setup_score   REAL,
    news_score          REAL,
    gap_type            TEXT,
    iep_price           REAL,
    selected_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, symbol)
);

-- Current signal status (derived view, never mutated directly)
CREATE VIEW IF NOT EXISTS v_signal_status AS
SELECT
    s.id,
    s.symbol,
    s.strategy_id,
    s.mode,
    s.signal_type,
    s.entry_price,
    s.sl_price,
    s.target_1,
    s.target_2,
    s.reward_risk,
    s.regime,
    s.rationale,
    s.confidence_score,
    s.todvol_ratio,
    s.vwap_at_signal,
    s.atr_at_signal,
    s.created_at,
    COALESCE(last_e.event_type, 'PENDING') AS current_status,
    last_e.net_pnl_r,
    last_e.mfe_r,
    last_e.mae_r,
    last_e.price AS exit_price
FROM intraday_signals s
LEFT JOIN signal_events last_e ON last_e.id = (
    SELECT id FROM signal_events WHERE signal_id = s.id
    ORDER BY created_at DESC LIMIT 1
);
"""


def run_intraday_migration(conn: Any) -> None:
    """
    Create all IIM tables and views if they do not already exist.
    Safe to run multiple times (idempotent).
    """
    try:
        for statement in INTRADAY_SCHEMA_SQL.strip().split(";"):
            stmt = statement.strip()
            if stmt:
                conn.execute(stmt)
        conn.commit()
        logger.info("IIM database schema migration complete.")
    except Exception as exc:
        logger.exception("IIM migration failed: %s", exc)
        raise


# ---------------------------------------------------------------------------
# Write signal (append-only)
# ---------------------------------------------------------------------------

def persist_signal(
    conn: Any,
    signal_dict: dict[str, Any],
) -> int:
    """
    Insert a new signal into intraday_signals.

    Args:
        conn: Database connection.
        signal_dict: Fully validated signal dict (fields match table schema).

    Returns:
        The new signal's row ID.
    """
    sql = """
    INSERT INTO intraday_signals (
        strategy_id, strategy_ver, mode, symbol, exchange, signal_type,
        signal_candle_time, entry_time, timeframe, entry_price,
        sl_price, target_1, target_2, sl_distance, reward_risk,
        atr_at_signal, confidence_score, pillars_met, regime,
        vwap_at_signal, pivot_at_signal, pdh, pdl, todvol_ratio,
        rationale, feature_snapshot, feasibility_ok
    ) VALUES (
        :strategy_id, :strategy_ver, :mode, :symbol, :exchange, :signal_type,
        :signal_candle_time, :entry_time, :timeframe, :entry_price,
        :sl_price, :target_1, :target_2, :sl_distance, :reward_risk,
        :atr_at_signal, :confidence_score, :pillars_met, :regime,
        :vwap_at_signal, :pivot_at_signal, :pdh, :pdl, :todvol_ratio,
        :rationale, :feature_snapshot, :feasibility_ok
    )
    """
    cur = conn.execute(sql, signal_dict)
    conn.commit()
    signal_id = cur.lastrowid
    logger.info("Signal persisted: id=%d %s %s %s", signal_id,
                signal_dict["symbol"], signal_dict["signal_type"], signal_dict["strategy_id"])
    return signal_id


# ---------------------------------------------------------------------------
# Write event (append-only)
# ---------------------------------------------------------------------------

_VALID_EVENT_TYPES = {
    "ENTRY_FILLED", "T1_HIT", "T2_HIT", "SL_HIT",
    "TRAILING_STOP_HIT", "EXPIRED", "MANUAL_EXIT",
}


def persist_event(
    conn: Any,
    signal_id: int,
    event_type: str,
    event_time: datetime,
    price: float | None = None,
    shares: int | None = None,
    gross_pnl_r: float | None = None,
    fees_r: float | None = None,
    net_pnl_r: float | None = None,
    mfe_r: float | None = None,
    mae_r: float | None = None,
    note: str | None = None,
) -> int:
    """
    Append a new event to signal_events.

    Args:
        conn: Database connection.
        signal_id: ID of the parent signal.
        event_type: One of the defined event types.

    Returns:
        New event row ID.
    """
    if event_type not in _VALID_EVENT_TYPES:
        raise ValueError(f"Unknown event_type: {event_type}. Valid: {_VALID_EVENT_TYPES}")

    cur = conn.execute(
        """
        INSERT INTO signal_events (
            signal_id, event_type, event_time, price, shares,
            gross_pnl_r, fees_r, net_pnl_r, mfe_r, mae_r, note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (signal_id, event_type, event_time.isoformat(), price, shares,
         gross_pnl_r, fees_r, net_pnl_r, mfe_r, mae_r, note),
    )
    conn.commit()
    event_id = cur.lastrowid
    logger.info("Event persisted: signal_id=%d type=%s price=%s net_pnl_r=%s",
                signal_id, event_type, price, net_pnl_r)
    return event_id


# ---------------------------------------------------------------------------
# Read active signals
# ---------------------------------------------------------------------------

_TERMINAL_STATUSES = {"T1_HIT", "T2_HIT", "SL_HIT", "TRAILING_STOP_HIT", "EXPIRED", "MANUAL_EXIT"}


def get_active_signals(conn: Any, mode: str = "live") -> list[dict[str, Any]]:
    """
    Return all signals with non-terminal status (PENDING or ENTRY_FILLED).
    Uses v_signal_status view.
    """
    cur = conn.cursor()
    placeholders = ",".join(f"'{s}'" for s in _TERMINAL_STATUSES)
    cur.execute(
        f"""
        SELECT * FROM v_signal_status
        WHERE mode = ?
          AND current_status NOT IN ({placeholders})
        ORDER BY created_at DESC
        """,
        (mode,),
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_today_signals(conn: Any, mode: str = "live") -> list[dict[str, Any]]:
    """Return all signals created today."""
    cur = conn.cursor()
    today = datetime.now().date().isoformat()
    cur.execute(
        """
        SELECT * FROM v_signal_status
        WHERE mode = ? AND DATE(created_at) = ?
        ORDER BY created_at DESC
        """,
        (mode, today),
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_signal_history(
    conn: Any,
    strategy_id: str | None = None,
    mode: str = "live",
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Return historical signals with their final outcome for accuracy tracking."""
    cur = conn.cursor()
    where = "WHERE s.mode = ?"
    params: list[Any] = [mode]
    if strategy_id:
        where += " AND s.strategy_id = ?"
        params.append(strategy_id)
    cur.execute(
        f"""
        SELECT s.id, s.symbol, s.strategy_id, s.signal_type,
               s.entry_price, s.sl_price, s.target_1, s.sl_distance,
               s.reward_risk, s.regime, s.created_at,
               v.current_status, v.net_pnl_r, v.mfe_r, v.mae_r
        FROM intraday_signals s
        JOIN v_signal_status v ON v.id = s.id
        {where}
        ORDER BY s.created_at DESC
        LIMIT ?
        """,
        params + [limit],
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def upsert_candle(conn: Any, candle: dict[str, Any]) -> None:
    """
    Upsert a 15m candle with pre-computed indicators into intraday_candles.
    Uses INSERT OR REPLACE (SQLite).
    """
    conn.execute(
        """
        INSERT OR REPLACE INTO intraday_candles (
            symbol, timeframe, candle_time,
            open, high, low, close, volume,
            ema21, supertrend, supertrend_dir,
            atr14, adx14_nifty, vwap, obv, todvol_ratio, is_warmup
        ) VALUES (
            :symbol, :timeframe, :candle_time,
            :open, :high, :low, :close, :volume,
            :ema21, :supertrend, :supertrend_dir,
            :atr14, :adx14_nifty, :vwap, :obv, :todvol_ratio, :is_warmup
        )
        """,
        candle,
    )
