"""Pytest configuration and shared fixtures for the invst test suite.

Provides fixtures for:
  - project_root: Path to the repository root directory.
  - tmp_db: Temporary SQLite database with 0001_init.sql schema applied.
  - sample_config: Loaded and frozen Config instance.
"""

import sqlite3
from collections.abc import Generator
from pathlib import Path

import pytest

from invst.config import Config, get_config, get_project_root


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return the absolute path to the project root directory."""
    return get_project_root()


@pytest.fixture
def tmp_db(tmp_path: Path, project_root: Path) -> Generator[sqlite3.Connection, None, None]:
    """Create a temporary SQLite database with the schema from 0001_init.sql applied.

    Initializes all 7 core tables and the schema_version tracker from
    `db/migrations/0001_init.sql`.

    Yields:
        sqlite3.Connection: Connection to the populated test database.
    """
    db_file = tmp_path / "test_invst.db"
    conn = sqlite3.connect(str(db_file), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")

    migration_file = project_root / "db" / "migrations" / "0001_init.sql"
    if not migration_file.is_file():
        raise FileNotFoundError(f"Migration file not found at: {migration_file}")

    schema_sql = migration_file.read_text(encoding="utf-8")
    conn.executescript(schema_sql)
    conn.commit()

    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def sample_config(project_root: Path) -> Config:
    """Load and return the application Config instance for testing.

    Forces a reload to ensure a pristine configuration object.

    Returns:
        Config: Frozen, immutable configuration object.
    """
    return get_config(project_root=project_root, reload=True)


@pytest.fixture
def scoring_db(tmp_db: sqlite3.Connection) -> sqlite3.Connection:
    """Fixture with a rich set of stocks, metrics, and price history."""
    from datetime import date

    c = tmp_db
    asof_str = "2024-03-31"

    # Constituents
    constituents = [
        (asof_str, "STOCK_A", "ISIN_A", "information_technology", "nse"),
        (asof_str, "STOCK_B", "ISIN_B", "information_technology", "nse"),
        (asof_str, "STOCK_C", "ISIN_C", "financial_services", "nse"),
        (asof_str, "STOCK_D", "ISIN_D", "financial_services", "nse"),
        (asof_str, "PENNY_STOCK", "ISIN_E", "metals_mining", "nse"),
    ]
    c.executemany(
        "INSERT INTO index_constituents_history (effective_date, symbol, isin, sector, source) VALUES (?,?,?,?,?)",
        constituents,
    )

    # Prices (generate daily prices over 1200 days for STOCK_A: >3 years listing)
    prices = []
    prices.append(("PENNY_STOCK", asof_str, 5.0, 5.2, 4.8, 5.0, 5.0, 100000, "nse_bhavcopy"))

    for i in range(1200):
        t_d = date.fromordinal(date(2024, 3, 31).toordinal() - 1200 + i).isoformat()
        price = 100.0 + (i * 0.1)
        prices.append(
            ("STOCK_A", t_d, price, price + 1, price - 1, price, price, 500000, "nse_bhavcopy")
        )
        bench_p = 10000.0 + i * 2.0
        prices.append(
            (
                "NIFTY500",
                t_d,
                bench_p,
                bench_p + 10,
                bench_p - 10,
                bench_p,
                bench_p,
                1000000,
                "nse_bhavcopy",
            )
        )

    for i in range(400):
        t_d = date.fromordinal(date(2024, 3, 31).toordinal() - 400 + i).isoformat()
        price_b = 200.0 + (5.0 if i % 2 == 0 else -5.0)
        prices.append(
            (
                "STOCK_B",
                t_d,
                price_b,
                price_b + 2,
                price_b - 2,
                price_b,
                price_b,
                400000,
                "nse_bhavcopy",
            )
        )

    for i in range(100):
        t_d = date.fromordinal(date(2024, 3, 31).toordinal() - 100 + i).isoformat()
        prices.append(("STOCK_C", t_d, 500.0, 505.0, 495.0, 500.0, 500.0, 300000, "nse_bhavcopy"))
        prices.append(("STOCK_D", t_d, 800.0, 810.0, 790.0, 800.0, 800.0, 250000, "nse_bhavcopy"))

    c.executemany(
        "INSERT INTO daily_prices (symbol, trade_date, open, high, low, close, adj_close, volume, source) VALUES (?,?,?,?,?,?,?,?,?)",
        prices,
    )

    funds = []
    for q in range(12):
        p_end = date.fromordinal(date(2023, 12, 31).toordinal() - q * 91).isoformat()
        disc = date.fromordinal(date(2024, 1, 20).toordinal() - q * 91).isoformat()
        funds.append(("STOCK_A", p_end, disc, "roe", 24.0, "pct", "nse"))
        funds.append(("STOCK_A", p_end, disc, "roce", 28.0, "pct", "nse"))

    funds.extend(
        [
            ("STOCK_A", "2023-12-31", "2024-01-20", "debt_equity", 0.1, "ratio", "nse"),
            ("STOCK_A", "2023-12-31", "2024-01-20", "interest_coverage", 15.0, "ratio", "nse"),
            ("STOCK_A", "2023-12-31", "2024-01-20", "earnings_cagr_5yr", 18.0, "pct", "nse"),
            ("STOCK_A", "2023-12-31", "2024-01-20", "ocf_to_net_profit", 1.1, "ratio", "nse"),
            ("STOCK_A", "2023-12-31", "2024-01-20", "pe_ttm", 22.0, "ratio", "nse"),
            ("STOCK_A", "2023-12-31", "2024-01-20", "pb", 4.5, "ratio", "nse"),
            ("STOCK_A", "2023-12-31", "2024-01-20", "ev_ebitda", 14.0, "ratio", "nse"),
            ("STOCK_A", "2023-12-31", "2024-01-20", "dividend_yield", 1.5, "pct", "nse"),
            ("STOCK_A", "2023-12-31", "2024-01-20", "market_cap", 50000.0, "INR_cr", "nse"),
            ("STOCK_A", "2023-12-31", "2024-01-20", "promoter_holding_pct", 55.0, "pct", "nse"),
            ("STOCK_B", "2023-12-31", "2024-01-20", "roe", 10.0, "pct", "nse"),
            ("STOCK_B", "2023-12-31", "2024-01-20", "roce", 12.0, "pct", "nse"),
            ("STOCK_B", "2023-12-31", "2024-01-20", "debt_equity", 1.5, "ratio", "nse"),
            ("STOCK_B", "2023-12-31", "2024-01-20", "interest_coverage", 2.5, "ratio", "nse"),
            ("STOCK_B", "2023-12-31", "2024-01-20", "earnings_cagr_5yr", 6.0, "pct", "nse"),
            ("STOCK_B", "2023-12-31", "2024-01-20", "ocf_to_net_profit", 0.6, "ratio", "nse"),
            ("STOCK_B", "2023-12-31", "2024-01-20", "pe_ttm", 45.0, "ratio", "nse"),
            ("STOCK_B", "2023-12-31", "2024-01-20", "pb", 8.0, "ratio", "nse"),
            ("STOCK_B", "2023-12-31", "2024-01-20", "ev_ebitda", 26.0, "ratio", "nse"),
            ("STOCK_B", "2023-12-31", "2024-01-20", "dividend_yield", 0.5, "pct", "nse"),
            ("STOCK_B", "2023-12-31", "2024-01-20", "market_cap", 20000.0, "INR_cr", "nse"),
            ("STOCK_B", "2023-12-31", "2024-01-20", "promoter_holding_pct", 82.0, "pct", "nse"),
            ("PENNY_STOCK", "2023-12-31", "2024-01-20", "market_cap", 50.0, "INR_cr", "nse"),
        ]
    )
    c.executemany(
        "INSERT INTO fundamentals_quarterly (symbol, period_end, disclosed_at, metric, value, unit, source) VALUES (?,?,?,?,?,?,?)",
        funds,
    )

    news = [
        (
            "h_a1",
            "STOCK_A",
            "2024-03-10",
            "STOCK_A wins multi-million cloud contract",
            "reuters",
            0.7,
            "v1",
        ),
        (
            "h_b1",
            "STOCK_B",
            "2024-03-15",
            "STOCK_B reports margin compression",
            "bloomberg",
            -0.4,
            "v1",
        ),
    ]
    c.executemany(
        "INSERT INTO news_sentiment (headline_id, symbol, published_at, headline, source, sentiment_score, model_version) VALUES (?,?,?,?,?,?,?)",
        news,
    )

    c.commit()
    return c
