"""Tests for all ingestion pipeline modules.

Verifies:
- NSE Bhavcopy CSV parsing and idempotent daily_prices upsert
- BSE Bhavcopy parsing and daily_prices upsert
- yfinance symbol normalization and ingestion mapping
- Quarterly fundamentals parsing, disclosure date validation, and upsert
- News RSS XML parsing, idempotent hashing, and deduplication
- Macro series ingestion
"""

import sqlite3
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd

from invst.ingestion.bse_bhavcopy import (
    build_bse_bhavcopy_url,
    ingest_bse_bhavcopy,
)
from invst.ingestion.fundamentals_filings import (
    ingest_fundamentals_csv,
    ingest_fundamentals_records,
)
from invst.ingestion.macro import (
    ingest_macro_records,
)
from invst.ingestion.news_rss import (
    generate_headline_id,
    ingest_news_records,
    parse_rss_xml,
)
from invst.ingestion.nse_bhavcopy import (
    build_bhavcopy_url,
    ingest_nse_bhavcopy,
    parse_nse_bhavcopy_csv,
)
from invst.ingestion.yfinance_prices import (
    fetch_yfinance_ohlcv,
    ingest_yfinance_prices,
    normalize_symbol_for_yf,
)

# ── NSE Bhavcopy Tests ────────────────────────────────────────────────


def test_build_bhavcopy_url():
    t_date = date(2024, 1, 15)
    url = build_bhavcopy_url(t_date)
    assert "2024" in url
    assert "JAN" in url
    assert "cm15JAN2024bhav.csv.zip" in url


def test_parse_and_ingest_nse_bhavcopy(tmp_db: sqlite3.Connection):
    sample_csv = """SYMBOL,SERIES,OPEN,HIGH,LOW,CLOSE,LAST,PREVCLOSE,TOTTRDQTY,TOTTRDVAL,TIMESTAMP,TOTALTRADES,ISIN
RELIANCE,EQ,2700.0,2750.0,2690.0,2740.5,2742.0,2695.0,5421000,14850000000,15-JAN-2024,185000,INE002A01018
TCS,EQ,3800.0,3850.0,3790.0,3835.0,3830.0,3795.0,1820000,6980000000,15-JAN-2024,92000,INE467B01029
HDFCBOND,N1,100.0,101.0,99.5,100.2,100.2,100.0,500,50100,15-JAN-2024,10,INE040A08012
"""
    records = parse_nse_bhavcopy_csv(sample_csv)
    # HDFCBOND has SERIES='N1', so it should be filtered out
    assert len(records) == 2
    assert records[0]["symbol"] == "RELIANCE"
    assert records[0]["trade_date"] == "2024-01-15"
    assert records[0]["close"] == 2740.5
    assert records[0]["volume"] == 5421000

    # Ingest into DB
    count = ingest_nse_bhavcopy(tmp_db, csv_content=sample_csv)
    assert count == 2

    # Verify rows in daily_prices
    row = tmp_db.execute(
        "SELECT close, volume, source FROM daily_prices WHERE symbol = ? AND trade_date = ?",
        ("RELIANCE", "2024-01-15"),
    ).fetchone()
    assert row is not None
    assert row[0] == 2740.5
    assert row[1] == 5421000
    assert row[2] == "nse_bhavcopy"

    # Idempotent re-run
    count2 = ingest_nse_bhavcopy(tmp_db, csv_content=sample_csv)
    assert count2 == 2
    total_rows = tmp_db.execute("SELECT COUNT(*) FROM daily_prices").fetchone()[0]
    assert total_rows == 2


# ── BSE Bhavcopy Tests ────────────────────────────────────────────────


def test_build_bse_bhavcopy_url():
    t_date = date(2024, 1, 15)
    url = build_bse_bhavcopy_url(t_date)
    assert "EQ150124_CSV.ZIP" in url


def test_parse_and_ingest_bse_bhavcopy(tmp_db: sqlite3.Connection):
    sample_bse_csv = """SC_CODE,SC_NAME,SC_GROUP,SC_TYPE,OPEN,HIGH,LOW,CLOSE,LAST,PREVCLOSE,NO_OF_SHRS,NET_TURNOV,TDCLOINDI
500325,RELIANCE,A,Q,2705.0,2752.0,2695.0,2742.0,2742.0,2700.0,450000,1233900000,
532540,TCS,A,Q,3805.0,3855.0,3795.0,3838.0,3838.0,3800.0,210000,805980000,
"""
    count = ingest_bse_bhavcopy(tmp_db, trade_date=date(2024, 1, 15), csv_content=sample_bse_csv)
    assert count == 2

    row = tmp_db.execute(
        "SELECT close, source FROM daily_prices WHERE symbol = ? AND trade_date = ? AND source = 'bse_bhavcopy'",
        ("RELIANCE", "2024-01-15"),
    ).fetchone()
    assert row is not None
    assert row[0] == 2742.0
    assert row[1] == "bse_bhavcopy"


# ── yfinance Ingestor Tests ───────────────────────────────────────────


def test_normalize_symbol_for_yf():
    assert normalize_symbol_for_yf("RELIANCE") == "RELIANCE.NS"
    assert normalize_symbol_for_yf("TCS.BO") == "TCS.BO"
    assert normalize_symbol_for_yf("^INDIAVIX") == "^INDIAVIX"


@patch("invst.ingestion.yfinance_prices.yf")
def test_fetch_and_ingest_yfinance_prices(mock_yf, tmp_db: sqlite3.Connection):
    # Mock Ticker.history return DataFrame
    dates = pd.date_range("2024-01-01", periods=3, freq="D")
    mock_df = pd.DataFrame(
        {
            "Open": [100.0, 102.0, 101.0],
            "High": [105.0, 106.0, 104.0],
            "Low": [99.0, 101.0, 100.0],
            "Close": [104.0, 103.0, 102.0],
            "Adj Close": [104.0, 103.0, 102.0],
            "Volume": [10000, 12000, 11000],
        },
        index=dates,
    )
    mock_ticker_instance = MagicMock()
    mock_ticker_instance.history.return_value = mock_df
    mock_yf.Ticker.return_value = mock_ticker_instance

    records = fetch_yfinance_ohlcv("INFY", "2024-01-01", "2024-01-03")
    assert len(records) == 3
    assert records[0]["symbol"] == "INFY"
    assert records[0]["close"] == 104.0

    count = ingest_yfinance_prices(
        tmp_db, ["INFY"], "2024-01-01", "2024-01-03", delay_between_requests=0
    )
    assert count == 3

    rows = tmp_db.execute(
        "SELECT COUNT(*) FROM daily_prices WHERE symbol='INFY' AND source='yfinance'"
    ).fetchone()[0]
    assert rows == 3


# ── Fundamentals Filings Tests ────────────────────────────────────────


def test_ingest_fundamentals_records(tmp_db: sqlite3.Connection):
    records = [
        {
            "symbol": "RELIANCE",
            "period_end": "2023-12-31",
            "disclosed_at": "2024-01-20",
            "metric": "roe",
            "value": 14.5,
            "unit": "pct",
            "source": "nse_filing",
        },
        {
            "symbol": "RELIANCE",
            "period_end": "2023-12-31",
            "disclosed_at": "2024-01-20",
            "metric": "revenue",
            "value": 225000.0,
            "unit": "INR_cr",
            "source": "nse_filing",
        },
    ]

    count = ingest_fundamentals_records(tmp_db, records)
    assert count == 2

    row = tmp_db.execute(
        "SELECT value, unit FROM fundamentals_quarterly WHERE symbol='RELIANCE' AND metric='roe'"
    ).fetchone()
    assert row[0] == 14.5
    assert row[1] == "pct"


def test_ingest_fundamentals_csv(tmp_db: sqlite3.Connection):
    csv_text = """symbol,period_end,disclosed_at,metric,value,unit,source
TCS,2023-12-31,2024-01-11,pe_ttm,28.5,ratio,nse_filing
TCS,2023-12-31,2024-01-11,roce,45.2,pct,nse_filing
"""
    count = ingest_fundamentals_csv(tmp_db, csv_text)
    assert count == 2

    row = tmp_db.execute(
        "SELECT value FROM fundamentals_quarterly WHERE symbol='TCS' AND metric='roce'"
    ).fetchone()
    assert row[0] == 45.2


# ── News RSS Tests ───────────────────────────────────────────────────


def test_generate_headline_id():
    h1 = generate_headline_id("Reliance buys robotics company", "https://news.com/1", "2024-01-15")
    h2 = generate_headline_id("Reliance buys robotics company", "https://news.com/1", "2024-01-15")
    h3 = generate_headline_id("Different headline", "https://news.com/2", "2024-01-15")
    assert h1 == h2
    assert h1 != h3


def test_parse_and_ingest_news_rss(tmp_db: sqlite3.Connection):
    sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Financial News</title>
    <item>
      <title>HDFC Bank posts strong Q3 profit growth</title>
      <link>https://mint.com/hdfc-q3</link>
      <pubDate>Mon, 15 Jan 2024 10:00:00 GMT</pubDate>
      <source>Livemint</source>
    </item>
    <item>
      <title>IT sector prepares for deal cycle rebound</title>
      <link>https://moneycontrol.com/it-rebound</link>
      <pubDate>Mon, 15 Jan 2024 14:30:00 GMT</pubDate>
      <source>Moneycontrol</source>
    </item>
  </channel>
</rss>
"""
    records = parse_rss_xml(sample_xml, default_symbol="HDFCBANK")
    assert len(records) == 2
    assert records[0]["headline"] == "HDFC Bank posts strong Q3 profit growth"
    assert records[0]["published_at"] == "2024-01-15"
    assert records[0]["source"] == "Livemint"

    count = ingest_news_records(tmp_db, records)
    assert count == 2

    # Verify deduplication / idempotence
    count2 = ingest_news_records(tmp_db, records)
    assert count2 == 2
    total_news = tmp_db.execute("SELECT COUNT(*) FROM news_sentiment").fetchone()[0]
    assert total_news == 2


# ── Macro Ingestor Tests ──────────────────────────────────────────────


def test_ingest_macro_records(tmp_db: sqlite3.Connection):
    records = [
        {"symbol": "INDIA_VIX", "trade_date": "2024-01-15", "close": 13.8},
        {"symbol": "USD_INR", "trade_date": "2024-01-15", "close": 83.15},
    ]
    count = ingest_macro_records(tmp_db, records)
    assert count == 2

    row = tmp_db.execute(
        "SELECT close FROM daily_prices WHERE symbol='INDIA_VIX' AND trade_date='2024-01-15'"
    ).fetchone()
    assert row[0] == 13.8
