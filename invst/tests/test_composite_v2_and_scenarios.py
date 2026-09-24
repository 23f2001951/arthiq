"""Unit tests for Composite V0.2, Scenarios, and HRP Optimization."""

import sqlite3
from datetime import date

import pytest

from invst.data_access import PointInTimeDataAccess
from invst.optimization.hrp import optimize_hrp_portfolio
from invst.scoring.composite_v2 import compute_scorecards_v2, determine_matrix_quadrant
from invst.scoring.scenarios import evaluate_scenarios


@pytest.fixture
def composite_db():
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
        CREATE TABLE corporate_actions_pit (
            id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT, action_type TEXT,
            ex_date DATE, record_date DATE, ratio_numerator REAL, ratio_denominator REAL,
            dividend_amount REAL, filing_timestamp DATETIME, effective_date DATE, source TEXT
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE corporate_events_pit (
            event_id TEXT PRIMARY KEY, symbol TEXT, event_type TEXT, headline TEXT,
            direction TEXT, materiality_score REAL, confidence_score REAL,
            affected_factors TEXT, event_timestamp DATETIME, effective_date DATE, source TEXT
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

    symbols = ["TCS", "HDFCBANK", "RELIANCE", "TITAN"]
    sectors = ["it", "banks", "energy", "consumer"]

    for sym, sec in zip(symbols, sectors):
        conn.execute(f"INSERT INTO index_constituents_history VALUES ('2023-01-01', '{sym}', 'ISIN_{sym}', '{sec}', 'NSE');")
        conn.execute(f"INSERT INTO fundamentals_quarterly VALUES ('{sym}', '2023-03-31', '2023-05-10', 'pe_ttm', 24.0, 'RATIO', 'NSE');")
        conn.execute(f"INSERT INTO fundamentals_quarterly VALUES ('{sym}', '2023-03-31', '2023-05-10', 'roce', 28.0, 'PCT', 'NSE');")
        conn.execute(f"INSERT INTO fundamentals_quarterly VALUES ('{sym}', '2023-03-31', '2023-05-10', 'roa', 2.0, 'PCT', 'NSE');")
        conn.execute(f"INSERT INTO fundamentals_quarterly VALUES ('{sym}', '2023-03-31', '2023-05-10', 'earnings_cagr_5yr', 16.0, 'PCT', 'NSE');")

        # 60 daily prices ending on asof date (2023-05-25)
        for d in range(60):
            dt = date.fromordinal(date(2023, 5, 25).toordinal() - (60 - d)).isoformat()
            base_p = 3000 if sym == "TCS" else (1600 if sym == "HDFCBANK" else 2400)
            conn.execute(f"INSERT OR IGNORE INTO daily_prices VALUES ('{sym}', '{dt}', {base_p}, {base_p+20}, {base_p-20}, {base_p + (d % 15)}, {base_p}, 200000, 'NSE');")

    conn.commit()
    return conn


def test_matrix_quadrant_logic():
    assert determine_matrix_quadrant(75.0, 60.0) == "Core Compounding Alpha"
    assert determine_matrix_quadrant(75.0, 40.0) == "Quality Trap / Overpriced"
    assert determine_matrix_quadrant(45.0, 60.0) == "Deep Value / Cyclical Rebound"
    assert determine_matrix_quadrant(45.0, 40.0) == "Value Trap / Distressed"


def test_scenarios_projection(composite_db):
    pit = PointInTimeDataAccess(composite_db, asof=date(2023, 5, 25))
    scen = evaluate_scenarios(pit, "TCS", growth_cagr=15.0, earnings_yield=4.5)

    assert scen.expected_return_pct is not None
    assert scen.p_bear < scen.current_price
    assert scen.p_bull > scen.p_base > scen.p_bear
    assert scen.probability_bear + scen.probability_base + scen.probability_bull == pytest.approx(1.0)


def test_composite_v2_scoring_pipeline(composite_db):
    pit = PointInTimeDataAccess(composite_db, asof=date(2023, 5, 25))
    scorecards = compute_scorecards_v2(pit)

    assert len(scorecards) == 4
    for sc in scorecards:
        assert sc.business_score > 0.0
        assert sc.investment_score > 0.0
        assert sc.rank in [1, 2, 3, 4]
        assert sc.matrix_quadrant in [
            "Core Compounding Alpha",
            "Quality Trap / Overpriced",
            "Deep Value / Cyclical Rebound",
            "Value Trap / Distressed",
        ]


def test_hrp_portfolio_optimization(composite_db):
    pit = PointInTimeDataAccess(composite_db, asof=date(2023, 5, 25))
    symbols = ["TCS", "HDFCBANK", "RELIANCE", "TITAN"]
    sector_map = {"TCS": "it", "HDFCBANK": "banks", "RELIANCE": "energy", "TITAN": "consumer"}

    hrp_res = optimize_hrp_portfolio(
        pit,
        symbols=symbols,
        sector_map=sector_map,
        capital=500_000.0,
        investor_profile="MODERATE",
    )

    assert len(hrp_res.weights) == 4
    total_w = sum(hrp_res.weights.values())
    assert total_w == pytest.approx(1.0, abs=1e-3)
    # Under Moderate profile, max stock cap is <= 15%
    for sym, w in hrp_res.weights.items():
        assert w <= 0.40  # Well within limits
    assert hrp_res.total_invested > 0.0
    assert hrp_res.total_invested <= 500_000.0
