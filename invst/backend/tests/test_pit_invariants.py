"""Comprehensive Point-in-Time Anti-Lookahead Test Harness for Arth IQ V0.2.

Validates that:
1. Future fundamentals and earnings filings are strictly invisible before effective date.
2. Restatements are isolated: as-of date prior to restatement returns original value;
   as-of date after restatement returns restated value.
3. Late filings (after market close) receive next trading day effective date and cannot leak.
4. Corporate actions (splits/bonuses) and corporate events strictly obey effective date fences.
5. Bi-temporal valid_from and valid_to filters eliminate historical rewriting.
"""

from __future__ import annotations

import sqlite3
from datetime import date

import pytest

from invst.data_access import PointInTimeDataAccess


@pytest.fixture
def pit_db():
    """Set up an in-memory SQLite database with V0.1 and V0.2 PIT schemas."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")

    # V0.1 tables
    conn.execute(
        """
        CREATE TABLE index_constituents_history (
            effective_date   DATE    NOT NULL,
            symbol           TEXT    NOT NULL,
            isin             TEXT,
            sector           TEXT    NOT NULL,
            source           TEXT    NOT NULL,
            PRIMARY KEY (effective_date, symbol)
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE daily_prices (
            symbol           TEXT    NOT NULL,
            trade_date       DATE    NOT NULL,
            open             REAL,
            high             REAL,
            low              REAL,
            close            REAL    NOT NULL,
            adj_close        REAL,
            volume           INTEGER,
            source           TEXT    NOT NULL,
            PRIMARY KEY (symbol, trade_date, source)
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE fundamentals_quarterly (
            symbol           TEXT    NOT NULL,
            period_end       DATE    NOT NULL,
            disclosed_at     DATE    NOT NULL,
            metric           TEXT    NOT NULL,
            value            REAL,
            unit             TEXT,
            source           TEXT    NOT NULL,
            PRIMARY KEY (symbol, period_end, metric, source)
        );
        """
    )

    # V0.2 Bi-temporal tables
    conn.execute(
        """
        CREATE TABLE fundamentals_pit (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol              TEXT    NOT NULL,
            period_end          DATE    NOT NULL,
            metric              TEXT    NOT NULL,
            raw_value           REAL,
            restated_value      REAL,
            unit                TEXT    DEFAULT 'INR_CR',
            filing_timestamp    DATETIME NOT NULL,
            effective_date      DATE    NOT NULL,
            revision_seq        INTEGER DEFAULT 0,
            valid_from          DATE    NOT NULL,
            valid_to            DATE    DEFAULT '9999-12-31',
            source              TEXT    NOT NULL,
            source_url          TEXT,
            created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE corporate_actions_pit (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol              TEXT    NOT NULL,
            action_type         TEXT    NOT NULL,
            ex_date             DATE    NOT NULL,
            record_date         DATE,
            ratio_numerator     REAL,
            ratio_denominator   REAL,
            dividend_amount     REAL,
            filing_timestamp    DATETIME NOT NULL,
            effective_date      DATE    NOT NULL,
            source              TEXT    NOT NULL
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE corporate_events_pit (
            event_id            TEXT    PRIMARY KEY,
            symbol              TEXT    NOT NULL,
            event_type          TEXT    NOT NULL,
            headline            TEXT    NOT NULL,
            direction           TEXT    NOT NULL,
            materiality_score   REAL    NOT NULL,
            confidence_score    REAL    NOT NULL,
            affected_factors    TEXT    NOT NULL,
            event_timestamp     DATETIME NOT NULL,
            effective_date      DATE    NOT NULL,
            source              TEXT    NOT NULL
        );
        """
    )

    conn.commit()
    return conn


def test_fundamental_effective_date_isolation(pit_db):
    """Q4 FY23 (ended 2023-03-31) filed after-hours on 2023-05-10 with effective_date 2023-05-11."""
    pit_db.execute(
        """
        INSERT INTO fundamentals_pit (
            symbol, period_end, metric, raw_value, filing_timestamp,
            effective_date, revision_seq, valid_from, valid_to, source
        ) VALUES (
            'RELIANCE', '2023-03-31', 'revenue', 215000.0, '2023-05-10 18:30:00',
            '2023-05-11', 0, '2023-05-11', '9999-12-31', 'NSE'
        )
        """
    )
    pit_db.commit()

    # Query as of 2023-03-31 (period end) -> must NOT be visible
    pit_mar = PointInTimeDataAccess(pit_db, asof=date(2023, 3, 31))
    assert pit_mar.get_fundamental("RELIANCE", "revenue") is None

    # Query as of 2023-05-10 (filing evening, market closed) -> must NOT be visible
    pit_may10 = PointInTimeDataAccess(pit_db, asof=date(2023, 5, 10))
    assert pit_may10.get_fundamental("RELIANCE", "revenue") is None

    # Query as of 2023-05-11 (effective date at market open) -> MUST be visible
    pit_may11 = PointInTimeDataAccess(pit_db, asof=date(2023, 5, 11))
    assert pit_may11.get_fundamental("RELIANCE", "revenue") == 215000.0


def test_restatement_bi_temporal_isolation(pit_db):
    """Company originally reports Net Profit 1000 Cr on 2022-05-15.
    Restates to 850 Cr in next annual report effective 2023-05-15.
    """
    # Original filing
    pit_db.execute(
        """
        INSERT INTO fundamentals_pit (
            symbol, period_end, metric, raw_value, restated_value,
            filing_timestamp, effective_date, revision_seq, valid_from, valid_to, source
        ) VALUES (
            'TCS', '2022-03-31', 'net_profit', 1000.0, NULL,
            '2022-05-14 10:00:00', '2022-05-15', 0, '2022-05-15', '2023-05-15', 'NSE'
        )
        """
    )
    # Restatement filing superseding the original
    pit_db.execute(
        """
        INSERT INTO fundamentals_pit (
            symbol, period_end, metric, raw_value, restated_value,
            filing_timestamp, effective_date, revision_seq, valid_from, valid_to, source
        ) VALUES (
            'TCS', '2022-03-31', 'net_profit', 1000.0, 850.0,
            '2023-05-14 10:00:00', '2023-05-15', 1, '2023-05-15', '9999-12-31', 'NSE'
        )
        """
    )
    pit_db.commit()

    # In December 2022, only the original 1000 Cr is known
    pit_2022 = PointInTimeDataAccess(pit_db, asof=date(2022, 12, 31))
    assert pit_2022.get_fundamental("TCS", "net_profit") == 1000.0

    # In June 2023, the restated 850 Cr is active
    pit_2023 = PointInTimeDataAccess(pit_db, asof=date(2023, 6, 30))
    assert pit_2023.get_fundamental("TCS", "net_profit") == 850.0


def test_corporate_actions_isolation(pit_db):
    """Stock Split 1:2 on 2023-08-20."""
    pit_db.execute(
        """
        INSERT INTO corporate_actions_pit (
            symbol, action_type, ex_date, record_date, ratio_numerator,
            ratio_denominator, filing_timestamp, effective_date, source
        ) VALUES (
            'INFY', 'SPLIT', '2023-08-20', '2023-08-21', 2.0, 1.0,
            '2023-08-01 12:00:00', '2023-08-20', 'NSE'
        )
        """
    )
    pit_db.commit()

    # Before ex_date
    pit_before = PointInTimeDataAccess(pit_db, asof=date(2023, 8, 15))
    actions_before = pit_before.get_corporate_actions("INFY")
    assert len(actions_before) == 0

    # On or after ex_date
    pit_after = PointInTimeDataAccess(pit_db, asof=date(2023, 8, 25))
    actions_after = pit_after.get_corporate_actions("INFY")
    assert len(actions_after) == 1
    assert actions_after[0].action_type == "SPLIT"
    assert actions_after[0].ratio_numerator == 2.0


def test_corporate_events_isolation(pit_db):
    """Regulatory event on 2023-09-10."""
    pit_db.execute(
        """
        INSERT INTO corporate_events_pit (
            event_id, symbol, event_type, headline, direction,
            materiality_score, confidence_score, affected_factors,
            event_timestamp, effective_date, source
        ) VALUES (
            'EV001', 'HDFCBANK', 'REGULATORY_ACTION', 'RBI issues advisory on tech compliance',
            'NEGATIVE', 0.75, 0.95, '["GOVERNANCE", "RISK"]',
            '2023-09-10 14:00:00', '2023-09-10', 'BSE'
        )
        """
    )
    pit_db.commit()

    # Before event
    pit_before = PointInTimeDataAccess(pit_db, asof=date(2023, 9, 5))
    assert len(pit_before.get_corporate_events("HDFCBANK")) == 0

    # On or after event
    pit_after = PointInTimeDataAccess(pit_db, asof=date(2023, 9, 15))
    events = pit_after.get_corporate_events("HDFCBANK")
    assert len(events) == 1
    assert events[0].event_type == "REGULATORY_ACTION"
    assert "GOVERNANCE" in events[0].affected_factors
    assert events[0].materiality_score == 0.75
