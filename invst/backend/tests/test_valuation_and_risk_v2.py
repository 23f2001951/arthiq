"""Unit tests for Valuation V0.2, Reverse DCF, and Multi-Dimensional Risk Engine."""

import sqlite3
from datetime import date

import pytest

from invst.data_access import PointInTimeDataAccess
from invst.scoring.risk_v2 import evaluate_risk_v2
from invst.scoring.valuation_v2 import (
    compute_earnings_yield,
    evaluate_valuation_v2,
    solve_reverse_dcf_implied_growth,
)


@pytest.fixture
def test_db():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute(
        """
        CREATE TABLE daily_prices (
            symbol TEXT, trade_date DATE, open REAL, high REAL, low REAL,
            close REAL, adj_close REAL, volume INTEGER, source TEXT,
            PRIMARY KEY (symbol, trade_date, source)
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE fundamentals_quarterly (
            symbol TEXT, period_end DATE, disclosed_at DATE, metric TEXT,
            value REAL, unit TEXT, source TEXT,
            PRIMARY KEY (symbol, period_end, metric, source)
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE fundamentals_pit (
            id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT, period_end DATE,
            metric TEXT, raw_value REAL, restated_value REAL, unit TEXT,
            filing_timestamp DATETIME, effective_date DATE, revision_seq INTEGER,
            valid_from DATE, valid_to DATE, source TEXT, source_url TEXT, created_at DATETIME
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE index_constituents_history (
            effective_date DATE, symbol TEXT, isin TEXT, sector TEXT, source TEXT,
            PRIMARY KEY (effective_date, symbol)
        );
        """
    )

    # Seed constituent
    conn.execute("INSERT INTO index_constituents_history VALUES ('2023-01-01', 'TITAN', 'INE280A01028', 'consumer', 'NSE');")
    conn.execute("INSERT INTO index_constituents_history VALUES ('2023-01-01', 'LOSER', 'INE999A01028', 'industrials', 'NSE');")
    conn.execute("INSERT INTO index_constituents_history VALUES ('2023-01-01', 'PLEDGED', 'INE888A01028', 'industrials', 'NSE');")

    # Seed fundamentals
    conn.execute("INSERT INTO fundamentals_quarterly VALUES ('TITAN', '2023-03-31', '2023-05-10', 'pe_ttm', 48.0, 'RATIO', 'NSE');")
    conn.execute("INSERT INTO fundamentals_quarterly VALUES ('TITAN', '2023-03-31', '2023-05-10', 'roce', 32.0, 'PCT', 'NSE');")

    # Loss maker with negative PE
    conn.execute("INSERT INTO fundamentals_quarterly VALUES ('LOSER', '2023-03-31', '2023-05-10', 'pe_ttm', -8.0, 'RATIO', 'NSE');")
    conn.execute("INSERT INTO fundamentals_quarterly VALUES ('LOSER', '2023-03-31', '2023-05-10', 'roce', -4.0, 'PCT', 'NSE');")

    # Company with extreme promoter pledge
    conn.execute("INSERT INTO fundamentals_quarterly VALUES ('PLEDGED', '2023-03-31', '2023-05-10', 'pe_ttm', 15.0, 'RATIO', 'NSE');")
    conn.execute("INSERT INTO fundamentals_quarterly VALUES ('PLEDGED', '2023-03-31', '2023-05-10', 'promoter_pledge_pct', 42.0, 'PCT', 'NSE');")

    # Seed daily prices for 100 days
    for d in range(100):
        dt = f"2023-05-{10+d//4:02d}" if d < 80 else f"2023-06-{d-70:02d}"
        conn.execute(f"INSERT OR IGNORE INTO daily_prices VALUES ('TITAN', '{dt}', 2500, 2550, 2480, {2500 + d*2}, 2500, 100000, 'NSE');")
        conn.execute(f"INSERT OR IGNORE INTO daily_prices VALUES ('LOSER', '{dt}', 100, 105, 95, {100 - d*0.5}, 100, 50000, 'NSE');")
        conn.execute(f"INSERT OR IGNORE INTO daily_prices VALUES ('PLEDGED', '{dt}', 300, 310, 290, 300, 300, 50000, 'NSE');")

    conn.commit()
    return conn


def test_earnings_yield_transformation():
    # Positive PE
    assert compute_earnings_yield(20.0) == 5.0  # 5% yield
    assert compute_earnings_yield(10.0) == 10.0 # 10% yield

    # Negative PE -> becomes negative yield, NOT artificially high cheapness
    ey_neg = compute_earnings_yield(-5.0)
    assert ey_neg == -20.0  # -20% yield, ranked strictly worse than all positive yields


def test_reverse_dcf_solver():
    # Stock price = 100, FCF per share = 5.0, WACC = 11.5%
    g = solve_reverse_dcf_implied_growth(price=100.0, fcf_per_share=5.0, wacc=0.115, terminal_growth=0.05)
    assert g is not None
    # Expected implied growth should be around 7-10%
    assert 5.0 <= g <= 15.0


def test_valuation_negative_earnings_safety(test_db):
    pit = PointInTimeDataAccess(test_db, asof=date(2023, 6, 20))
    val_res = evaluate_valuation_v2(pit, "LOSER", sector="industrials")

    # Must detect negative earnings run rate and assign low score
    assert "NEGATIVE_EARNINGS_RUN_RATE" in val_res.risks
    assert val_res.valuation_score <= 35.0


def test_risk_contagion_redline_trigger(test_db):
    pit = PointInTimeDataAccess(test_db, asof=date(2023, 6, 20))
    risk_res = evaluate_risk_v2(pit, "PLEDGED", sector="industrials")

    # High promoter pledge (42%) MUST trigger redline
    assert len(risk_res.redlines_triggered) > 0
    assert any("CRITICAL_PROMOTER_PLEDGE" in r for r in risk_res.redlines_triggered)
    # Contagion gate MUST cap score at <= 30.0
    assert risk_res.risk_score <= 30.0
