"""NSE Bhavcopy downloader and parser.

Downloads and parses the daily official NSE Bhavcopy (CM / EQ segment),
extracting equity symbols and EOD OHLCV records, and upserting them into
the daily_prices table idempotently.
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


def build_bhavcopy_url(trade_date: date) -> str:
    """Build the official NSE Bhavcopy download URL for a given trade date.

    Uses the standard NSE Archives format:
    https://archives.nseindia.com/content/historical/EQUITIES/{YEAR}/{MON}/cm{DD}{MON}{YEAR}bhav.csv.zip
    """
    year = trade_date.strftime("%Y")
    month_upper = trade_date.strftime("%b").upper()
    day = trade_date.strftime("%d")
    filename = f"cm{day}{month_upper}{year}bhav.csv.zip"
    return (
        f"https://archives.nseindia.com/content/historical/EQUITIES/{year}/{month_upper}/{filename}"
    )


def parse_nse_bhavcopy_csv(csv_content: str | io.StringIO) -> list[dict[str, Any]]:
    """Parse NSE Bhavcopy CSV content into structured OHLCV dictionaries.

    Filters for Series == 'EQ' (Equity cash segment) to ignore derivatives,
    bonds, or preference shares.
    """
    if isinstance(csv_content, str):
        reader = csv.DictReader(io.StringIO(csv_content))
    else:
        reader = csv.DictReader(csv_content)

    records: list[dict[str, Any]] = []

    for row in reader:
        # Standard column names can vary slightly by date format (e.g. SYMBOL or TckrSymb)
        symbol = row.get("SYMBOL") or row.get("Symbol") or row.get("TckrSymb")
        series = row.get("SERIES") or row.get("Series") or row.get("SctySrs")

        if not symbol or series != "EQ":
            continue

        raw_date = row.get("TIMESTAMP") or row.get("TradDt") or row.get("DATE1")
        trade_date_str = None
        if raw_date:
            try:
                # Often in format '02-JAN-2024' or '2024-01-02'
                if "-" in raw_date and len(raw_date.split("-")[0]) == 4:
                    trade_date_str = raw_date[:10]
                else:
                    parsed_dt = datetime.strptime(raw_date.strip(), "%d-%b-%Y")
                    trade_date_str = parsed_dt.strftime("%Y-%m-%d")
            except Exception:
                trade_date_str = raw_date.strip()

        try:
            open_p = float(row.get("OPEN") or row.get("OpnPric") or 0.0)
            high_p = float(row.get("HIGH") or row.get("HghPric") or 0.0)
            low_p = float(row.get("LOW") or row.get("LwPric") or 0.0)
            close_p = float(row.get("CLOSE") or row.get("ClsPric") or 0.0)
            volume = int(float(row.get("TOTTRDQTY") or row.get("TtlTradgVol") or 0))
        except (ValueError, TypeError) as e:
            logger.debug(f"Skipping row for {symbol}: invalid numeric data ({e})")
            continue

        records.append(
            {
                "symbol": symbol.strip(),
                "trade_date": trade_date_str,
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
                "adj_close": close_p,  # Bhavcopy is unadjusted, adj_close defaults to close
                "volume": volume,
                "source": "nse_bhavcopy",
            }
        )

    return records


def ingest_nse_bhavcopy(
    conn: sqlite3.Connection,
    trade_date: date | None = None,
    csv_file_path: str | Path | None = None,
    csv_content: str | None = None,
) -> int:
    """Ingest NSE Bhavcopy records into the daily_prices table.

    Either csv_file_path or csv_content can be passed. If neither is provided,
    attempting to download requires network access.
    """
    records: list[dict[str, Any]] = []

    if csv_content:
        records = parse_nse_bhavcopy_csv(csv_content)
    elif csv_file_path:
        path = Path(csv_file_path)
        if path.suffix == ".zip":
            with zipfile.ZipFile(path, "r") as z:
                # Usually contains one CSV
                for name in z.namelist():
                    if name.endswith(".csv"):
                        with z.open(name) as f:
                            content = f.read().decode("utf-8", errors="ignore")
                            records = parse_nse_bhavcopy_csv(content)
                            break
        else:
            with open(path, encoding="utf-8", errors="ignore") as f:
                records = parse_nse_bhavcopy_csv(f.read())
    else:
        # Download mode if network is available
        if trade_date is None:
            raise ValueError("Must provide either trade_date, csv_file_path, or csv_content")
        import urllib.request

        url = build_bhavcopy_url(trade_date)
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            },
        )
        with urllib.request.urlopen(req) as resp:
            zip_bytes = resp.read()
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                for name in z.namelist():
                    if name.endswith(".csv"):
                        with z.open(name) as f:
                            content = f.read().decode("utf-8", errors="ignore")
                            records = parse_nse_bhavcopy_csv(content)
                            break

    if not records:
        logger.warning("No records found to ingest for NSE Bhavcopy")
        return 0

    # Ensure trade_date is filled if missing in row
    default_date_str = trade_date.isoformat() if trade_date else None

    query = """
    INSERT OR REPLACE INTO daily_prices (
        symbol, trade_date, open, high, low, close, adj_close, volume, source
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    params = []
    for r in records:
        t_date = r["trade_date"] or default_date_str
        if not t_date:
            continue
        params.append(
            (
                r["symbol"],
                t_date,
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
    logger.info(f"Ingested {len(params)} NSE Bhavcopy records")
    return len(params)
