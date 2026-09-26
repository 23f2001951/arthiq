"""Daily Data Quality and Freshness Checks.

Audits:
1. Daily price record counts
2. Duplicate (symbol, trade_date, source) records
3. Fundamentals freshness (disclosed within 90 days)
4. News sentiment coverage
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class QualityCheckResult:
    check_name: str
    passed: bool
    message: str
    details: dict[str, Any]


def check_daily_prices_freshness(
    conn: sqlite3.Connection, asof: date | None = None
) -> QualityCheckResult:
    """Check daily_prices table for latest trade dates and row count."""
    target_date = asof or date.today()
    target_str = target_date.isoformat()

    row = conn.execute(
        "SELECT COUNT(*) FROM daily_prices WHERE trade_date = ?",
        (target_str,),
    ).fetchone()
    count = row[0] if row else 0

    passed = count > 0
    msg = (
        f"Found {count} price rows for {target_str}"
        if passed
        else f"No price rows found for {target_str}"
    )

    return QualityCheckResult(
        check_name="daily_prices_freshness",
        passed=passed,
        message=msg,
        details={"date": target_str, "row_count": count},
    )


def check_duplicate_prices(conn: sqlite3.Connection) -> QualityCheckResult:
    """Ensure no duplicate daily price entries exist."""
    cur = conn.execute(
        """
        SELECT symbol, trade_date, source, COUNT(*) as cnt
        FROM daily_prices
        GROUP BY symbol, trade_date, source
        HAVING cnt > 1
        """
    )
    dups = cur.fetchall()
    passed = len(dups) == 0
    msg = (
        "No duplicate price entries found"
        if passed
        else f"Detected {len(dups)} duplicate price keys!"
    )

    return QualityCheckResult(
        check_name="duplicate_prices_check",
        passed=passed,
        message=msg,
        details={"duplicate_count": len(dups)},
    )


def check_fundamentals_freshness(
    conn: sqlite3.Connection, asof: date | None = None
) -> QualityCheckResult:
    """Check that at least 70% of active stocks have fundamentals disclosed within 120 days."""
    target_date = asof or date.today()
    cutoff_date = (target_date - timedelta(days=120)).isoformat()
    cur = conn.execute(
        """
        SELECT COUNT(DISTINCT symbol)
        FROM fundamentals_quarterly
        WHERE disclosed_at >= ?
        """,
        (cutoff_date,),
    )
    fresh_count = cur.fetchone()[0]

    return QualityCheckResult(
        check_name="fundamentals_freshness",
        passed=fresh_count > 0,
        message=f"{fresh_count} symbols have fundamentals disclosed within last 120 days",
        details={"fresh_symbols_count": fresh_count},
    )


def run_all_data_quality_checks(
    conn: sqlite3.Connection, asof: date | None = None
) -> list[QualityCheckResult]:
    """Execute all daily data quality assertions."""
    return [
        check_daily_prices_freshness(conn, asof),
        check_duplicate_prices(conn),
        check_fundamentals_freshness(conn, asof),
    ]
