"""Tests for tmp_db fixture and SQLite database schema."""

import sqlite3


def test_tmp_db_tables_exist(tmp_db: sqlite3.Connection) -> None:
    """Verify all 7 core tables and schema_version exist in the tmp_db fixture."""
    expected_tables = {
        "index_constituents_history",
        "daily_prices",
        "fundamentals_quarterly",
        "news_sentiment",
        "model_predictions",
        "portfolio_history",
        "backtest_runs",
        "schema_version",
    }

    cursor = tmp_db.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
    )
    actual_tables = {row[0] for row in cursor.fetchall()}

    assert expected_tables.issubset(actual_tables), (
        f"Missing tables: {expected_tables - actual_tables}"
    )


def test_tmp_db_crud_operations(tmp_db: sqlite3.Connection) -> None:
    """Test basic insert and point-in-time query on fundamentals_quarterly."""
    cursor = tmp_db.cursor()

    # Insert test data
    cursor.execute(
        """
        INSERT INTO fundamentals_quarterly
        (symbol, period_end, disclosed_at, metric, value, unit, source)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "RELIANCE",
            "2024-03-31",
            "2024-04-25",
            "roe",
            14.2,
            "pct",
            "nse_filing",
        ),
    )
    tmp_db.commit()

    # Query with point-in-time filter
    cursor.execute(
        """
        SELECT value FROM fundamentals_quarterly
        WHERE symbol = ? AND metric = ? AND disclosed_at <= ?
        ORDER BY disclosed_at DESC, period_end DESC
        LIMIT 1
        """,
        ("RELIANCE", "roe", "2024-05-01"),
    )
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == 14.2

    # Query with asof before disclosure date should return nothing
    cursor.execute(
        """
        SELECT value FROM fundamentals_quarterly
        WHERE symbol = ? AND metric = ? AND disclosed_at <= ?
        ORDER BY disclosed_at DESC, period_end DESC
        LIMIT 1
        """,
        ("RELIANCE", "roe", "2024-04-01"),
    )
    assert cursor.fetchone() is None
