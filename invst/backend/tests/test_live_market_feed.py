"""Unit and integration tests for live_market_feed and live news ingestion."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from unittest.mock import MagicMock, patch

from invst.api.routes import _resolve_market_asof
from invst.ingestion.live_market_feed import (
    TICKER_TAPE_CACHE,
    fetch_live_macro_pulse,
    fetch_live_ticker_snapshot,
    fetch_live_ticker_tape,
    ingest_live_ticker_to_db,
)
from invst.ingestion.news_rss import fetch_google_news_rss, parse_rss_xml
from invst.intraday.scheduler import job_daily_market_data


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


def test_fetch_live_ticker_tape_omits_unavailable_quotes():
    """Never substitute plausible-looking prices when neither live nor DB data exists."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE daily_prices (symbol TEXT, trade_date DATE, close REAL)")
    with patch("invst.ingestion.live_market_feed.yf", None), patch.dict(
        TICKER_TAPE_CACHE, {"timestamp": 0.0, "data": []}
    ):
        quotes = fetch_live_ticker_tape(conn=conn, fetch_live=False)
    assert quotes == []


def test_fetch_live_ticker_tape_marks_database_prices_as_snapshots():
    """Database close prices carry their actual trade date and source metadata."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE daily_prices (symbol TEXT, trade_date DATE, close REAL)")
    conn.execute("INSERT INTO daily_prices VALUES ('NIFTY50', '2026-10-09', 25123.4)")
    conn.execute("INSERT INTO daily_prices VALUES ('NIFTY50', '2026-10-08', 25000.0)")
    with patch("invst.ingestion.live_market_feed.yf", None), patch.dict(
        TICKER_TAPE_CACHE, {"timestamp": 0.0, "data": []}
    ):
        quotes = fetch_live_ticker_tape(conn=conn, fetch_live=False)
    nifty = next(item for item in quotes if item["symbol"] == "NIFTY 50")
    assert nifty["price_val"] == 25123.4
    assert nifty["last_updated"] == "2026-10-09"
    assert nifty["is_live"] is False
    assert nifty["price_source"] == "daily_close"


def test_resolve_market_asof_uses_latest_stored_session_and_preserves_explicit_cutoff():
    """Default recommendation dates follow stored sessions; explicit PIT dates remain fixed."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE daily_prices (symbol TEXT, trade_date DATE, close REAL)")
    conn.execute("INSERT INTO daily_prices VALUES ('NIFTY500', '2026-10-09', 100.0)")
    conn.execute("INSERT INTO daily_prices VALUES ('RELIANCE', '2026-10-12', 101.0)")
    assert _resolve_market_asof(conn).isoformat() == "2026-10-12"
    assert _resolve_market_asof(conn, "2024-03-31").isoformat() == "2024-03-31"


def test_daily_market_refresh_skips_an_already_ingested_session():
    """The scheduled close-price task is idempotent for an existing source date."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE daily_prices (trade_date DATE, source TEXT)")
    conn.execute("INSERT INTO daily_prices VALUES ('2026-10-12', 'nse_bhavcopy')")
    with (
        patch("invst.intraday.scheduler._conn_factory", return_value=conn),
        patch("invst.intraday.scheduler._now_ist") as now_ist,
        patch("invst.ingestion.nse_bhavcopy.ingest_nse_bhavcopy") as ingest,
    ):
        now_ist.return_value = datetime.fromisoformat("2026-10-12T18:00:00+05:30")
        job_daily_market_data()
        ingest.assert_not_called()


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
