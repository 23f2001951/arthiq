"""Unit and integration tests for live_market_feed and live news ingestion."""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock, patch

from invst.ingestion.live_market_feed import (
    fetch_live_macro_pulse,
    fetch_live_ticker_snapshot,
    ingest_live_ticker_to_db,
)
from invst.ingestion.news_rss import fetch_google_news_rss, parse_rss_xml


def test_fetch_live_macro_pulse_fallback():
    """Verify macro pulse returns well-formed dict and correct regime even if offline."""
    pulse = fetch_live_macro_pulse()
    assert "india_vix" in pulse
    assert "regime" in pulse
    assert pulse["regime"] in ["HIGH_VOLATILITY", "EXPANSIONARY", "NEUTRAL"]
    assert "asof_date" in pulse


def test_fetch_live_macro_pulse_regime_thresholds():
    """Verify regime switches based on India VIX level."""
    with patch("invst.ingestion.live_market_feed.yf") as mock_yf:
        # High volatility
        mock_ticker = MagicMock()
        mock_fast = MagicMock()
        mock_fast.last_price = 22.5
        mock_ticker.fast_info = mock_fast
        mock_yf.Ticker.return_value = mock_ticker

        pulse_high = fetch_live_macro_pulse()
        assert pulse_high["regime"] == "HIGH_VOLATILITY"
        assert pulse_high["india_vix"] == 22.5

        # Expansionary
        mock_fast.last_price = 11.2
        pulse_low = fetch_live_macro_pulse()
        assert pulse_low["regime"] == "EXPANSIONARY"
        assert pulse_low["india_vix"] == 11.2


def test_fetch_live_ticker_snapshot_db_fallback():
    """Verify snapshot falls back smoothly to DB when offline."""
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE daily_prices (
            symbol TEXT, trade_date DATE, open REAL, high REAL, low REAL, close REAL, adj_close REAL, volume INTEGER, source TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE fundamentals_quarterly (
            symbol TEXT, period_end DATE, metric TEXT, value REAL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE news_sentiment (
            headline_id TEXT, symbol TEXT, published_at DATE, headline TEXT, source TEXT, sentiment_score REAL, model_version TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO daily_prices VALUES ('TCS', '2026-09-20', 1400.0, 1420.0, 1390.0, 1410.0, 1410.0, 50000, 'test')"
    )
    conn.execute(
        "INSERT INTO fundamentals_quarterly VALUES ('TCS', '2026-06-30', 'roe', 38.5)"
    )
    conn.execute(
        "INSERT INTO news_sentiment VALUES ('h1', 'TCS', '2026-09-20', 'TCS wins massive cloud transformation deal', 'Reuters', 0.8, 'test')"
    )
    conn.commit()

    with patch("invst.ingestion.live_market_feed.yf", None):
        snapshot = fetch_live_ticker_snapshot("TCS", conn=conn)
        assert snapshot["symbol"] == "TCS"
        assert snapshot["current_price"] == 1410.0
        assert snapshot["roe"] == 38.5
        assert len(snapshot["headlines"]) == 1
        assert snapshot["headlines"][0]["headline"] == "TCS wins massive cloud transformation deal"
        assert snapshot["is_live"] is False


def test_ingest_live_ticker_to_db():
    """Verify upserting live snapshot records into daily_prices and news_sentiment."""
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE daily_prices (
            symbol TEXT, trade_date DATE, open REAL, high REAL, low REAL, close REAL, adj_close REAL, volume INTEGER, source TEXT,
            PRIMARY KEY(symbol, trade_date)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE news_sentiment (
            headline_id TEXT PRIMARY KEY, symbol TEXT, published_at DATE, headline TEXT, source TEXT, sentiment_score REAL, model_version TEXT,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    mock_snapshot = {
        "symbol": "INFY",
        "asof_date": "2026-09-21",
        "current_price": 1950.0,
        "open": 1940.0,
        "high": 1960.0,
        "low": 1935.0,
        "volume": 120000,
        "is_live": True,
        "headlines": [
            {
                "headline_id": "infy_live_1",
                "headline": "Infosys expands AI partnership with global enterprise",
                "source": "Google News",
                "published_at": "2026-09-21",
                "sentiment_score": 0.65,
            }
        ],
    }

    res = ingest_live_ticker_to_db(conn, "INFY", snapshot=mock_snapshot)
    assert res is True

    # Verify price inserted
    p_row = conn.execute("SELECT close, source FROM daily_prices WHERE symbol = 'INFY'").fetchone()
    assert p_row is not None
    assert p_row[0] == 1950.0
    assert p_row[1] == "live_feed"

    # Verify news inserted
    n_row = conn.execute("SELECT headline, sentiment_score FROM news_sentiment WHERE symbol = 'INFY'").fetchone()
    assert n_row is not None
    assert n_row[0] == "Infosys expands AI partnership with global enterprise"
    assert n_row[1] == 0.65


def test_fetch_google_news_rss_network_fallback():
    """Verify news RSS gracefully returns empty list if network call fails."""
    with patch("urllib.request.urlopen", side_effect=OSError("Network unreachable")):
        records = fetch_google_news_rss("RELIANCE")
        assert records == []


def test_parse_rss_xml_sentiment():
    """Verify RSS XML parses titles and applies sentiment correctly."""
    sample_xml = """<rss version="2.0">
        <channel>
            <item>
                <title>HDFC Bank posts strong quarterly profit surge and robust growth</title>
                <link>https://example.com/hdfc-q1</link>
                <pubDate>Mon, 21 Sep 2026 10:00:00 GMT</pubDate>
            </item>
            <item>
                <title>Company faces regulatory probe and penalty risk</title>
                <link>https://example.com/hdfc-risk</link>
                <pubDate>Mon, 21 Sep 2026 09:00:00 GMT</pubDate>
            </item>
        </channel>
    </rss>"""
    from invst.ml.sentiment import rule_based_financial_sentiment

    records = parse_rss_xml(sample_xml, default_symbol="HDFCBANK")
    assert len(records) == 2
    assert "strong" in records[0]["headline"]

    score1 = rule_based_financial_sentiment(records[0]["headline"])
    score2 = rule_based_financial_sentiment(records[1]["headline"])
    assert score1 > 0.0  # profit surge, strong, growth
    assert score2 < 0.0  # probe, penalty, risk
