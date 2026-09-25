"""Macro indicators ingestor.

Ingests key Indian macroeconomic indicators into daily_prices with pseudo-symbols:
- ^INDIAVIX: India Volatility Index
- USDINR=X: USD/INR exchange rate
- BZ=F: Brent Crude oil futures
- IN10Y=RR: 10-Year Indian Government Bond yield
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import date
from typing import Any

from invst.ingestion.yfinance_prices import fetch_yfinance_ohlcv

logger = logging.getLogger(__name__)

MACRO_SYMBOLS = {
    "INDIA_VIX": "^INDIAVIX",
    "USD_INR": "INR=X",
    "BRENT_CRUDE": "BZ=F",
}


def ingest_macro_indicators(
    conn: sqlite3.Connection,
    start_date: str | date,
    end_date: str | date | None = None,
) -> int:
    """Ingest macroeconomic time series using yfinance into daily_prices."""
    query = """
    INSERT OR REPLACE INTO daily_prices (
        symbol, trade_date, open, high, low, close, adj_close, volume, source
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    total_inserted = 0

    for internal_sym, yf_sym in MACRO_SYMBOLS.items():
        records = fetch_yfinance_ohlcv(yf_sym, start_date=start_date, end_date=end_date)
        if not records:
            continue

        params = [
            (
                internal_sym,
                r["trade_date"],
                r["open"],
                r["high"],
                r["low"],
                r["close"],
                r["adj_close"],
                r["volume"],
                "macro_yfinance",
            )
            for r in records
        ]

        conn.executemany(query, params)
        conn.commit()
        total_inserted += len(params)

    logger.info(f"Ingested {total_inserted} macro records across {len(MACRO_SYMBOLS)} series")
    return total_inserted


def ingest_macro_records(
    conn: sqlite3.Connection,
    records: list[dict[str, Any]],
) -> int:
    """Directly ingest pre-formatted macro observation records into daily_prices."""
    query = """
    INSERT OR REPLACE INTO daily_prices (
        symbol, trade_date, open, high, low, close, adj_close, volume, source
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    params = [
        (
            r["symbol"],
            r["trade_date"],
            r.get("open", r["close"]),
            r.get("high", r["close"]),
            r.get("low", r["close"]),
            r["close"],
            r.get("adj_close", r["close"]),
            r.get("volume", 0),
            r.get("source", "macro_manual"),
        )
        for r in records
    ]

    conn.executemany(query, params)
    conn.commit()
    return len(params)
