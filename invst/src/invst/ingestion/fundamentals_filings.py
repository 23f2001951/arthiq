"""Quarterly fundamentals ingestor.

Parses and ingests quarterly financial metrics with strict disclosure date
tracking (disclosed_at) to uphold point-in-time integrity.
"""

from __future__ import annotations

import csv
import io
import logging
import sqlite3
from collections.abc import Sequence
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def ingest_fundamentals_records(
    conn: sqlite3.Connection,
    records: Sequence[dict[str, Any]],
) -> int:
    """Ingest a sequence of fundamental metric records into fundamentals_quarterly.

    Each record must have:
      - symbol: str
      - period_end: str (YYYY-MM-DD)
      - disclosed_at: str (YYYY-MM-DD)
      - metric: str
      - value: float or None
      - unit: str (optional, defaults to 'ratio')
      - source: str (optional, defaults to 'nse_filing')
    """
    if not records:
        return 0

    query = """
    INSERT OR REPLACE INTO fundamentals_quarterly (
        symbol, period_end, disclosed_at, metric, value, unit, source
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """

    params = []
    for r in records:
        sym = r.get("symbol")
        p_end = r.get("period_end")
        disc = r.get("disclosed_at")
        met = r.get("metric")
        if not (sym and p_end and disc and met):
            continue

        val = r.get("value")
        if val is not None:
            try:
                val = float(val)
            except (ValueError, TypeError):
                continue

        unit = r.get("unit", "ratio")
        src = r.get("source", "nse_filing")

        params.append(
            (
                sym.strip().upper(),
                str(p_end).strip(),
                str(disc).strip(),
                str(met).strip().lower(),
                val,
                unit,
                src,
            )
        )

    conn.executemany(query, params)
    conn.commit()
    logger.info(f"Ingested {len(params)} fundamentals records into fundamentals_quarterly")
    return len(params)


def ingest_fundamentals_csv(
    conn: sqlite3.Connection,
    csv_path_or_content: str | Path | io.StringIO,
) -> int:
    """Parse a CSV containing fundamentals data and ingest into the database."""
    if isinstance(csv_path_or_content, (str, Path)) and Path(csv_path_or_content).is_file():
        with open(csv_path_or_content, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            records = list(reader)
    elif isinstance(csv_path_or_content, io.StringIO):
        reader = csv.DictReader(csv_path_or_content)
        records = list(reader)
    elif isinstance(csv_path_or_content, str):
        reader = csv.DictReader(io.StringIO(csv_path_or_content))
        records = list(reader)
    else:
        raise ValueError("Invalid csv_path_or_content argument")

    return ingest_fundamentals_records(conn, records)
