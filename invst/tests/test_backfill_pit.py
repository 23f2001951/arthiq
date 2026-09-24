"""Unit tests for PIT backfill ingestion engine."""

import sqlite3
from datetime import date
from pathlib import Path

import pytest

from invst.data_access import PointInTimeDataAccess
from invst.ingestion.backfill_pit import (
    run_historical_backfill,
)


@pytest.fixture
def pit_test_db(tmp_path: Path, project_root: Path) -> sqlite3.Connection:
    """Create in-memory/temp database with 0001_init.sql and 0002_pit_v2.sql applied."""
    db_file = tmp_path / "backfill_test.db"
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")

    init_sql = (project_root / "db" / "migrations" / "0001_init.sql").read_text(encoding="utf-8")
    conn.executescript(init_sql)

    pit_sql = (project_root / "db" / "migrations" / "0002_pit_v2.sql").read_text(encoding="utf-8")
    conn.executescript(pit_sql)
    conn.commit()

    try:
        yield conn
    finally:
        conn.close()


def test_backfill_execution(pit_test_db: sqlite3.Connection):
    """Verify that run_historical_backfill populates all required tables."""
    conn = pit_test_db
    # Run backfill for small test window 2022-2024
    summary = run_historical_backfill(conn, start_year=2022, end_year=2024)

    assert summary["fundamentals_pit_records"] > 0
    assert summary["corporate_actions_records"] > 0
    assert summary["corporate_events_records"] > 0
    assert summary["index_constituents_records"] > 0
    assert summary["daily_prices_records"] > 0

    # Point-in-time access verification as of 2023-06-30
    asof = date(2023, 6, 30)
    pit = PointInTimeDataAccess(conn, asof=asof)

    # 1. Fundamentals PIT check
    tcs_roe = pit.get_fundamental("TCS", "roe")
    assert tcs_roe is not None
    assert tcs_roe > 20.0

    # 2. Corporate Actions PIT check
    ca = pit.get_corporate_actions("TCS")
    assert isinstance(ca, list)

    # 3. Corporate Events PIT check
    events = pit.get_corporate_events("ICICIBANK", lookback_days=365 * 3)
    assert isinstance(events, list)

    # 4. Universe PIT check
    univ = pit.get_universe()
    assert "TCS" in univ
    assert "RELIANCE" in univ
    assert "HDFCBANK" in univ

    # 5. Prices PIT check
    px = pit.get_price("RELIANCE", on_or_before=asof)
    assert px is not None
    assert px > 10.0
