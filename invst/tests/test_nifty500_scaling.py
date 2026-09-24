"""Unit tests for Arth IQ V0.3 Track 1: Nifty 500 Universe Expansion and Sector Scaling."""

import sqlite3
from datetime import date

from invst.data_access import PointInTimeDataAccess
from invst.ingestion.backfill_pit import run_historical_backfill
from invst.ingestion.nifty500_universe import (
    CORE_20_STOCKS,
    build_full_nifty500_roster,
)
from invst.scoring.sectors.archetypes import SectorArchetype


def test_core_20_stocks_preserved():
    """Verify that the 20 audited baseline stocks are completely intact with valid attributes."""
    assert len(CORE_20_STOCKS) == 20
    symbols = {s.symbol for s in CORE_20_STOCKS}
    expected_anchors = {"HDFCBANK", "ICICIBANK", "TCS", "INFY", "LT", "RELIANCE", "HINDUNILVR", "ITC"}
    assert expected_anchors.issubset(symbols)

    for s in CORE_20_STOCKS:
        assert s.base_mcap > 0
        assert s.base_pe > 0
        assert s.annual_drift > 0
        assert s.volatility > 0


def test_full_nifty500_roster_generation():
    """Verify that build_full_nifty500_roster generates exactly 500 distinct symbols across sectors."""
    roster = build_full_nifty500_roster()
    assert len(roster) == 500

    symbols = [s.symbol for s in roster]
    assert len(set(symbols)) == 500, "Duplicate symbols detected in Nifty 500 roster"

    # Verify sector distribution
    sectors = {s.sector for s in roster}
    assert len(sectors) >= 10, f"Expected at least 10 sectors, got {len(sectors)}"
    assert "financial_services" in sectors
    assert "information_technology" in sectors
    assert "capital_goods" in sectors
    assert "healthcare" in sectors
    assert "automobile_and_auto_components" in sectors

    # Verify archetypes
    archetypes = {s.archetype for s in roster}
    assert SectorArchetype.FINANCIALS in archetypes
    assert SectorArchetype.TECH_SERVICES in archetypes
    assert SectorArchetype.INDUSTRIALS_CAPEX in archetypes
    assert SectorArchetype.CONSUMER_MOATS in archetypes
    assert SectorArchetype.HEALTHCARE_PHARMA in archetypes


def test_nifty500_database_backfill_and_pit_query():
    """Verify fast backfill and point-in-time retrieval of constituents for nifty500 mode."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS daily_prices (
        symbol TEXT NOT NULL, trade_date DATE NOT NULL,
        open REAL, high REAL, low REAL, close REAL, adj_close REAL, volume INTEGER, source TEXT,
        PRIMARY KEY (symbol, trade_date)
    );
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS index_constituents_history (
        effective_date DATE NOT NULL, symbol TEXT NOT NULL,
        isin TEXT, sector TEXT, source TEXT,
        PRIMARY KEY (effective_date, symbol)
    );
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS fundamentals_pit (
        id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL, period_end DATE NOT NULL,
        metric TEXT NOT NULL, raw_value REAL, restated_value REAL, unit TEXT,
        filing_timestamp DATETIME, effective_date DATE NOT NULL, revision_seq INTEGER,
        valid_from DATE, valid_to DATE, source TEXT, source_url TEXT
    );
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS fundamentals_quarterly (
        symbol TEXT NOT NULL, period_end DATE NOT NULL, disclosed_at DATE NOT NULL,
        metric TEXT NOT NULL, value REAL, unit TEXT, source TEXT,
        PRIMARY KEY (symbol, period_end, metric)
    );
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS corporate_actions_pit (
        id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT, action_type TEXT,
        ex_date DATE, record_date DATE, ratio_numerator REAL, ratio_denominator REAL,
        dividend_amount REAL, filing_timestamp DATETIME, effective_date DATE, source TEXT
    );
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS corporate_events_pit (
        event_id TEXT PRIMARY KEY, symbol TEXT, event_type TEXT, headline TEXT,
        direction TEXT, materiality_score REAL, confidence_score REAL,
        affected_factors TEXT, event_timestamp DATETIME, effective_date DATE, source TEXT
    );
    """)

    # Backfill with universe_mode="nifty500" for a narrow 1-year window
    res = run_historical_backfill(conn, start_year=2022, end_year=2023, universe_mode="nifty500")
    assert res["index_constituents_records"] > 0
    assert res["daily_prices_records"] > 0

    pit = PointInTimeDataAccess(conn, asof=date(2022, 12, 31))
    univ = pit.get_universe()
    assert len(univ) == 500

    univ_sec = pit.get_universe_with_sectors()
    assert len(univ_sec) == 500

    conn.close()
