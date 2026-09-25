"""BSE Bhavcopy downloader and parser.

Parses daily BSE Equity Bhavcopy files and upserts records into
the daily_prices table with source='bse_bhavcopy'.
"""

from __future__ import annotations

import csv
import io
import logging
import sqlite3
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def build_bse_bhavcopy_url(trade_date: date) -> str:
    """Build the official BSE Bhavcopy download URL for a given trade date.

    Standard BSE Equity Bhavcopy URL format:
    https://www.bseindia.com/BSEDATA/gross/{YEAR}/EQ{DD}{MM}{YY}_CSV.ZIP
    """
    day = trade_date.strftime("%d")
    month = trade_date.strftime("%m")
    year_short = trade_date.strftime("%y")
    year_full = trade_date.strftime("%Y")
    filename = f"EQ{day}{month}{year_short}_CSV.ZIP"
    return f"https://www.bseindia.com/BSEDATA/gross/{year_full}/{filename}"


def parse_bse_bhavcopy_csv(
    csv_content: str | io.StringIO, default_trade_date: date | None = None
) -> list[dict[str, Any]]:
    """Parse BSE Bhavcopy CSV into structured OHLCV records."""
    if isinstance(csv_content, str):
        reader = csv.DictReader(io.StringIO(csv_content))
    else:
        reader = csv.DictReader(csv_content)

    records: list[dict[str, Any]] = []

    for row in reader:
        symbol = row.get("SC_NAME") or row.get("SC_CODE") or row.get("Security Name")
        if not symbol:
            continue

        raw_date = row.get("TRADING_DATE") or row.get("DATE") or row.get("TradDt")
        trade_date_str = None
        if raw_date:
            try:
                trade_date_str = datetime.strptime(raw_date.strip(), "%d/%m/%Y").strftime(
                    "%Y-%m-%d"
                )
            except Exception:
                trade_date_str = raw_date.strip()
        elif default_trade_date:
            trade_date_str = default_trade_date.isoformat()

        try:
            open_p = float(row.get("OPEN") or row.get("OPEN_PRICE") or 0.0)
            high_p = float(row.get("HIGH") or row.get("HIGH_PRICE") or 0.0)
            low_p = float(row.get("LOW") or row.get("LOW_PRICE") or 0.0)
            close_p = float(row.get("CLOSE") or row.get("CLOSE_PRICE") or 0.0)
            volume = int(float(row.get("NO_OF_SHRS") or row.get("NO_TRADES") or 0))
        except (ValueError, TypeError) as e:
            logger.debug(f"Skipping row for {symbol}: invalid numeric data ({e})")
            continue

        records.append(
            {
                "symbol": symbol.strip().upper(),
                "trade_date": trade_date_str,
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
                "adj_close": close_p,
                "volume": volume,
                "source": "bse_bhavcopy",
            }
        )

    return records


def ingest_bse_bhavcopy(
    conn: sqlite3.Connection,
    trade_date: date | None = None,
    csv_file_path: str | Path | None = None,
    csv_content: str | None = None,
) -> int:
    """Ingest BSE Bhavcopy records into daily_prices table."""
    records: list[dict[str, Any]] = []

    if csv_content:
        records = parse_bse_bhavcopy_csv(csv_content, default_trade_date=trade_date)
    elif csv_file_path:
        path = Path(csv_file_path)
        if path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path, "r") as z:
                for name in z.namelist():
                    if name.lower().endswith(".csv"):
                        with z.open(name) as f:
                            content = f.read().decode("utf-8", errors="ignore")
                            records = parse_bse_bhavcopy_csv(content, default_trade_date=trade_date)
                            break
        else:
            with open(path, encoding="utf-8", errors="ignore") as f:
                records = parse_bse_bhavcopy_csv(f.read(), default_trade_date=trade_date)
    else:
        if trade_date is None:
            raise ValueError("Must provide either trade_date, csv_file_path, or csv_content")
        import urllib.request

        url = build_bse_bhavcopy_url(trade_date)
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        )
        with urllib.request.urlopen(req) as resp:
            zip_bytes = resp.read()
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                for name in z.namelist():
                    if name.lower().endswith(".csv"):
                        with z.open(name) as f:
                            content = f.read().decode("utf-8", errors="ignore")
                            records = parse_bse_bhavcopy_csv(content, default_trade_date=trade_date)
                            break

    if not records:
        logger.warning("No records found to ingest for BSE Bhavcopy")
        return 0

    query = """
    INSERT OR REPLACE INTO daily_prices (
        symbol, trade_date, open, high, low, close, adj_close, volume, source
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    params = []
    for r in records:
        if not r["trade_date"]:
            continue
        params.append(
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
        )

    conn.executemany(query, params)
    conn.commit()
    logger.info(f"Ingested {len(params)} BSE Bhavcopy records")
    return len(params)
