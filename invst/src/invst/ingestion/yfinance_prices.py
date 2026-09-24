"""yfinance price ingestor.

Fetches historical and daily OHLCV prices using yfinance for NSE/BSE tickers,
with rate-limiting safeguards, retry backoff, and idempotent database insertion.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from datetime import date, datetime
from typing import Any

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
except ImportError:
    yf = None


def normalize_symbol_for_yf(symbol: str, exchange: str = "NS") -> str:
    """Ensure the ticker symbol has the proper Yahoo Finance exchange suffix.

    e.g. 'RELIANCE' -> 'RELIANCE.NS'
    """
    symbol = symbol.strip().upper()
    if symbol.endswith(".NS") or symbol.endswith(".BO"):
        return symbol
    if symbol.startswith("^"):
        return symbol  # Indices like ^INDIAVIX
    return f"{symbol}.{exchange.upper()}"


def fetch_yfinance_ohlcv(
    symbol: str,
    start_date: str | date,
    end_date: str | date | None = None,
    max_retries: int = 3,
    backoff_factor: float = 1.5,
) -> list[dict[str, Any]]:
    """Fetch OHLCV historical dataframe for a symbol and convert to records list."""
    if yf is None:
        logger.warning("yfinance is not installed; returning empty records")
        return []

    ticker_sym = normalize_symbol_for_yf(symbol)
    start_str = (
        start_date.isoformat() if isinstance(start_date, (date, datetime)) else str(start_date)
    )
    end_str = (
        end_date.isoformat()
        if isinstance(end_date, (date, datetime))
        else (str(end_date) if end_date else None)
    )

    retries = 0
    df = None
    while retries < max_retries:
        try:
            ticker = yf.Ticker(ticker_sym)
            df = ticker.history(start=start_str, end=end_str, auto_adjust=False)
            break
        except Exception as e:
            retries += 1
            wait_time = backoff_factor**retries
            logger.warning(
                f"Error fetching {ticker_sym} (attempt {retries}/{max_retries}): {e}. Retrying in {wait_time:.1f}s"
            )
            time.sleep(wait_time)

    if df is None or df.empty:
        logger.info(f"No yfinance price data returned for {ticker_sym}")
        return []

    records: list[dict[str, Any]] = []
    # Strip exchange suffix for clean internal symbol storage (e.g. RELIANCE.NS -> RELIANCE)
    clean_sym = symbol.replace(".NS", "").replace(".BO", "")

    for idx, row in df.iterrows():
        trade_date_str = idx.strftime("%Y-%m-%d")
        try:
            open_p = float(row.get("Open", 0.0))
            high_p = float(row.get("High", 0.0))
            low_p = float(row.get("Low", 0.0))
            close_p = float(row.get("Close", 0.0))
            adj_close = float(row.get("Adj Close", close_p))
            volume = int(float(row.get("Volume", 0)))
        except (ValueError, TypeError):
            continue

        records.append(
            {
                "symbol": clean_sym,
                "trade_date": trade_date_str,
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
                "adj_close": adj_close,
                "volume": volume,
                "source": "yfinance",
            }
        )

    return records


def ingest_yfinance_prices(
    conn: sqlite3.Connection,
    symbols: list[str],
    start_date: str | date,
    end_date: str | date | None = None,
    delay_between_requests: float = 0.2,
) -> int:
    """Ingest daily OHLCV from yfinance for a list of symbols into daily_prices."""
    query = """
    INSERT OR REPLACE INTO daily_prices (
        symbol, trade_date, open, high, low, close, adj_close, volume, source
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    total_inserted = 0

    for symbol in symbols:
        records = fetch_yfinance_ohlcv(symbol, start_date=start_date, end_date=end_date)
        if not records:
            continue

        params = [
            (
                r["symbol"],
                r["trade_date"],
                r["open"],
                r["high"],
                r["low"],
                r["close"],
                r["adj_close"],
                r["volume"],
                r["source"],
            )
            for r in records
        ]

        conn.executemany(query, params)
        conn.commit()
        total_inserted += len(params)
        if delay_between_requests > 0:
            time.sleep(delay_between_requests)

    logger.info(f"Ingested {total_inserted} price rows from yfinance across {len(symbols)} symbols")
    return total_inserted
