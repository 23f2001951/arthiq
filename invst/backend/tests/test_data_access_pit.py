"""Comprehensive point-in-time data access tests.

This is the single most critical test file in the project.  It verifies
that ``PointInTimeDataAccess`` NEVER leaks future data — the fundamental
anti-cheating guarantee that the entire backtest rests upon.

Test categories
---------------
1. **Fundamentals PIT** — disclosed_at filtering, ordering, panel queries.
2. **Prices PIT** — trade_date clamping, series boundaries.
3. **Universe PIT** — constituent snapshots, additions, removals.
4. **Sentiment PIT** — published_at filtering, lookback windows.
5. **Edge cases** — empty DB, missing symbols, boundary dates.

See PROJECT_PLAN.md §3.3, §5.2, §5.4.
"""

import sqlite3
from datetime import date

import pytest

from invst.data_access import FundamentalRow, PointInTimeDataAccess, PriceRow

# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture
def pit_db(tmp_db: sqlite3.Connection) -> sqlite3.Connection:
    """Populate the tmp_db with a rich, realistic test dataset.

    Timeline
    --------
    Universe snapshots:
      2020-03-31: RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK
      2021-03-31: RELIANCE, TCS, INFY, HDFCBANK (ICICIBANK removed, WIPRO added)
      2021-03-31: WIPRO added in same snapshot

    Prices (RELIANCE):
      2020-03-30: 1100  (before Q4 rebalance)
      2020-03-31: 1120  (rebalance day)
      2020-04-01: 1135  (day after rebalance)
      2020-06-30: 1250  (Q1 end)
      2021-03-31: 1950  (next year rebalance)

    Fundamentals (RELIANCE):
      Q3 FY20 results (period_end=2019-12-31, disclosed_at=2020-01-20)  roe=12.5
      Q4 FY20 results (period_end=2020-03-31, disclosed_at=2020-05-15)  roe=13.8
      Q1 FY21 results (period_end=2020-06-30, disclosed_at=2020-08-10)  roe=14.2
      Restated Q3 (period_end=2019-12-31, disclosed_at=2020-06-01)      roe=12.1  (restatement)

    Fundamentals (TCS):
      Q4 FY20 results (period_end=2020-03-31, disclosed_at=2020-04-15)  roe=38.5

    News sentiment:
      RELIANCE 2020-03-25: "Reliance announces rights issue" score=+0.3
      RELIANCE 2020-04-10: "Reliance JioMart launch" score=+0.6
      RELIANCE 2020-07-15: "Facebook invests in Jio" score=+0.8
    """
    c = tmp_db

    # ── Universe snapshots ──
    constituents = [
        (
            "2020-03-31",
            "RELIANCE",
            "INE002A01018",
            "oil_gas_consumable_fuels",
            "nse_index_rebalance",
        ),
        ("2020-03-31", "TCS", "INE467B01029", "information_technology", "nse_index_rebalance"),
        ("2020-03-31", "INFY", "INE009A01021", "information_technology", "nse_index_rebalance"),
        ("2020-03-31", "HDFCBANK", "INE040A01034", "financial_services", "nse_index_rebalance"),
        ("2020-03-31", "ICICIBANK", "INE090A01021", "financial_services", "nse_index_rebalance"),
        # 2021 rebalance — ICICIBANK removed, WIPRO added
        (
            "2021-03-31",
            "RELIANCE",
            "INE002A01018",
            "oil_gas_consumable_fuels",
            "nse_index_rebalance",
        ),
        ("2021-03-31", "TCS", "INE467B01029", "information_technology", "nse_index_rebalance"),
        ("2021-03-31", "INFY", "INE009A01021", "information_technology", "nse_index_rebalance"),
        ("2021-03-31", "HDFCBANK", "INE040A01034", "financial_services", "nse_index_rebalance"),
        ("2021-03-31", "WIPRO", "INE075A01022", "information_technology", "nse_index_rebalance"),
    ]
    c.executemany(
        "INSERT INTO index_constituents_history (effective_date, symbol, isin, sector, source) VALUES (?,?,?,?,?)",
        constituents,
    )

    # ── Prices ──
    prices = [
        # RELIANCE
        ("RELIANCE", "2020-03-30", 1095.0, 1110.0, 1085.0, 1100.0, 1100.0, 5000000, "nse_bhavcopy"),
        ("RELIANCE", "2020-03-31", 1105.0, 1125.0, 1100.0, 1120.0, 1120.0, 6000000, "nse_bhavcopy"),
        ("RELIANCE", "2020-04-01", 1125.0, 1140.0, 1115.0, 1135.0, 1135.0, 5500000, "nse_bhavcopy"),
        ("RELIANCE", "2020-06-30", 1240.0, 1260.0, 1230.0, 1250.0, 1250.0, 7000000, "nse_bhavcopy"),
        ("RELIANCE", "2021-03-31", 1930.0, 1960.0, 1920.0, 1950.0, 1950.0, 8000000, "nse_bhavcopy"),
        # TCS
        ("TCS", "2020-03-30", 1800.0, 1820.0, 1780.0, 1810.0, 1810.0, 3000000, "nse_bhavcopy"),
        ("TCS", "2020-03-31", 1820.0, 1840.0, 1800.0, 1830.0, 1830.0, 3500000, "nse_bhavcopy"),
        ("TCS", "2020-04-01", 1835.0, 1860.0, 1825.0, 1850.0, 1850.0, 3200000, "nse_bhavcopy"),
        # INFY (only one date — tests missing-data edge case)
        ("INFY", "2020-03-31", 680.0, 695.0, 675.0, 690.0, 690.0, 4000000, "nse_bhavcopy"),
    ]
    c.executemany(
        "INSERT INTO daily_prices (symbol, trade_date, open, high, low, close, adj_close, volume, source) VALUES (?,?,?,?,?,?,?,?,?)",
        prices,
    )

    # ── Fundamentals ──
    fundamentals = [
        # RELIANCE Q3 FY20 — original disclosure
        ("RELIANCE", "2019-12-31", "2020-01-20", "roe", 12.5, "pct", "nse_filing"),
        # RELIANCE Q4 FY20 — disclosed AFTER March 31 rebalance
        ("RELIANCE", "2020-03-31", "2020-05-15", "roe", 13.8, "pct", "nse_filing"),
        # RELIANCE Q1 FY21
        ("RELIANCE", "2020-06-30", "2020-08-10", "roe", 14.2, "pct", "nse_filing"),
        # RELIANCE Q3 FY20 — RESTATEMENT disclosed later (replaces 12.5 with 12.1)
        ("RELIANCE", "2019-12-31", "2020-06-01", "roe", 12.1, "pct", "paid_api"),
        # RELIANCE revenue
        ("RELIANCE", "2019-12-31", "2020-01-20", "revenue", 156789.0, "INR_cr", "nse_filing"),
        ("RELIANCE", "2020-03-31", "2020-05-15", "revenue", 148230.0, "INR_cr", "nse_filing"),
        # TCS Q4 FY20 — disclosed BEFORE March 31 is NOT possible, set to April 15
        ("TCS", "2020-03-31", "2020-04-15", "roe", 38.5, "pct", "nse_filing"),
        # TCS revenue
        ("TCS", "2019-12-31", "2020-01-15", "revenue", 39854.0, "INR_cr", "nse_filing"),
    ]
    c.executemany(
        "INSERT INTO fundamentals_quarterly (symbol, period_end, disclosed_at, metric, value, unit, source) VALUES (?,?,?,?,?,?,?)",
        fundamentals,
    )

    # ── News sentiment ──
    sentiment = [
        (
            "hash_rel_1",
            "RELIANCE",
            "2020-03-25",
            "Reliance announces rights issue",
            "livemint",
            0.3,
            "finbert-v1",
        ),
        (
            "hash_rel_2",
            "RELIANCE",
            "2020-04-10",
            "Reliance JioMart launch success",
            "moneycontrol",
            0.6,
            "finbert-v1",
        ),
        (
            "hash_rel_3",
            "RELIANCE",
            "2020-07-15",
            "Facebook invests $5.7B in Jio",
            "livemint",
            0.8,
            "finbert-v1",
        ),
    ]
    c.executemany(
        "INSERT INTO news_sentiment (headline_id, symbol, published_at, headline, source, sentiment_score, model_version) VALUES (?,?,?,?,?,?,?)",
        sentiment,
    )

    c.commit()
    return c


# ══════════════════════════════════════════════════════════════════════
# 1. FUNDAMENTALS — Point-in-Time Tests
# ══════════════════════════════════════════════════════════════════════


class TestFundamentalsPIT:
    """Verify that fundamentals are NEVER leaked across the asof boundary."""

    def test_returns_latest_disclosed_before_asof(self, pit_db: sqlite3.Connection) -> None:
        """On 2020-03-31, only Q3 FY20 (disclosed 2020-01-20) is visible."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 3, 31))
        roe = pit.get_fundamental("RELIANCE", "roe")
        assert roe == 12.5  # Q3 FY20, not Q4 which was disclosed 2020-05-15

    def test_does_not_return_undisclosed_quarter(self, pit_db: sqlite3.Connection) -> None:
        """On 2020-04-01, Q4 FY20 (disclosed 2020-05-15) is still invisible."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 4, 1))
        roe = pit.get_fundamental("RELIANCE", "roe")
        assert roe == 12.5  # Still Q3 FY20

    def test_returns_newly_disclosed_quarter(self, pit_db: sqlite3.Connection) -> None:
        """On 2020-05-16, Q4 FY20 (disclosed 2020-05-15) becomes visible."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 5, 16))
        roe = pit.get_fundamental("RELIANCE", "roe")
        assert roe == 13.8  # Q4 FY20 now visible

    def test_restatement_not_visible_before_disclosure(self, pit_db: sqlite3.Connection) -> None:
        """On 2020-05-20, the restatement (disclosed 2020-06-01) is still invisible."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 5, 20))
        # The latest disclosed value should be Q4 FY20 (13.8), not the restatement
        roe = pit.get_fundamental("RELIANCE", "roe")
        assert roe == 13.8

    def test_restatement_visible_after_disclosure(self, pit_db: sqlite3.Connection) -> None:
        """On 2020-06-02, the restatement (disclosed 2020-06-01) is now visible.

        The restatement has disclosed_at=2020-06-01 which is the MOST RECENT
        disclosure, so it should be returned even though its period_end is older.
        """
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 6, 2))
        roe = pit.get_fundamental("RELIANCE", "roe")
        # The query orders by disclosed_at DESC, period_end DESC.
        # Restatement: disclosed_at=2020-06-01, period_end=2019-12-31
        # Q4 FY20: disclosed_at=2020-05-15, period_end=2020-03-31
        # So restatement wins on disclosed_at.
        assert roe == 12.1

    def test_returns_none_when_no_data(self, pit_db: sqlite3.Connection) -> None:
        """A symbol with no fundamentals returns None."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 3, 31))
        assert pit.get_fundamental("HDFCBANK", "roe") is None

    def test_returns_none_before_any_disclosure(self, pit_db: sqlite3.Connection) -> None:
        """Before any disclosure date, returns None."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2019, 12, 31))
        assert pit.get_fundamental("RELIANCE", "roe") is None

    def test_fundamental_detail_returns_metadata(self, pit_db: sqlite3.Connection) -> None:
        """get_fundamental_detail returns the full FundamentalRow."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 3, 31))
        detail = pit.get_fundamental_detail("RELIANCE", "roe")
        assert detail is not None
        assert isinstance(detail, FundamentalRow)
        assert detail.value == 12.5
        assert detail.period_end == "2019-12-31"
        assert detail.disclosed_at == "2020-01-20"

    def test_fundamental_history_respects_asof(self, pit_db: sqlite3.Connection) -> None:
        """get_fundamental_history only returns rows disclosed on or before asof."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 5, 16))
        history = pit.get_fundamental_history("RELIANCE", "roe", n_quarters=10)
        # At asof=2020-05-16: Q3 (disclosed 2020-01-20) and Q4 (disclosed 2020-05-15) visible
        # Restatement (disclosed 2020-06-01) NOT visible
        assert len(history) == 2
        assert history[0].value == 13.8  # Q4 FY20 (most recent disclosed_at)
        assert history[1].value == 12.5  # Q3 FY20

    def test_fundamentals_panel_vectorised(self, pit_db: sqlite3.Connection) -> None:
        """Panel query returns values for multiple symbols, respecting asof."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 3, 31))
        panel = pit.get_fundamentals_panel("roe", ["RELIANCE", "TCS", "HDFCBANK"])
        # RELIANCE has ROE 12.5 (Q3), TCS ROE disclosed 2020-04-15 so NOT visible
        assert panel["RELIANCE"] == 12.5
        assert "TCS" not in panel  # TCS Q4 not yet disclosed
        assert "HDFCBANK" not in panel  # no data at all

    def test_fundamentals_panel_after_tcs_disclosure(self, pit_db: sqlite3.Connection) -> None:
        """After TCS Q4 disclosure, both RELIANCE and TCS appear."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 4, 20))
        panel = pit.get_fundamentals_panel("roe", ["RELIANCE", "TCS"])
        assert panel["RELIANCE"] == 12.5
        assert panel["TCS"] == 38.5

    def test_fundamentals_panel_empty_symbols(self, pit_db: sqlite3.Connection) -> None:
        """Panel with empty symbol list returns empty dict."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 3, 31))
        assert pit.get_fundamentals_panel("roe", []) == {}


# ══════════════════════════════════════════════════════════════════════
# 2. PRICES — Point-in-Time Tests
# ══════════════════════════════════════════════════════════════════════


class TestPricesPIT:
    """Verify that prices never leak beyond the asof date."""

    def test_get_price_on_exact_date(self, pit_db: sqlite3.Connection) -> None:
        """Price on a date that exists should return that day's close."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 3, 31))
        price = pit.get_price("RELIANCE")
        assert price == 1120.0

    def test_get_price_clamped_to_asof(self, pit_db: sqlite3.Connection) -> None:
        """Requesting a price after asof should clamp to asof."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 3, 31))
        # Ask for April 1 price — should be clamped to March 31
        price = pit.get_price("RELIANCE", on_or_before=date(2020, 4, 1))
        assert price == 1120.0  # March 31 close, not April 1

    def test_get_price_on_or_before_non_trading_day(self, pit_db: sqlite3.Connection) -> None:
        """Price on a non-trading day should return the most recent prior close."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 6, 30))
        # Ask for April 5 (weekend/holiday) — should get April 1 close
        price = pit.get_price("RELIANCE", on_or_before=date(2020, 4, 5))
        assert price == 1135.0  # April 1 is the latest before April 5

    def test_get_price_returns_none_before_history(self, pit_db: sqlite3.Connection) -> None:
        """No price before any trading data exists."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2019, 1, 1))
        assert pit.get_price("RELIANCE") is None

    def test_get_price_series_clamped(self, pit_db: sqlite3.Connection) -> None:
        """Price series end is clamped to asof."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 3, 31))
        series = pit.get_price_series("RELIANCE", start=date(2020, 3, 29), end=date(2020, 4, 5))
        # Should only get March 30 and March 31 (April 1 is after asof)
        assert len(series) == 2
        assert all(isinstance(row, PriceRow) for row in series)
        assert series[0].trade_date == "2020-03-30"
        assert series[0].close == 1100.0
        assert series[1].trade_date == "2020-03-31"
        assert series[1].close == 1120.0

    def test_get_price_series_default_end(self, pit_db: sqlite3.Connection) -> None:
        """Without explicit end, series goes up to asof."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 4, 1))
        series = pit.get_price_series("RELIANCE", start=date(2020, 3, 29))
        assert len(series) == 3  # March 30, 31, April 1

    def test_get_prices_multi(self, pit_db: sqlite3.Connection) -> None:
        """Multi-symbol price fetch respects asof."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 3, 31))
        prices = pit.get_prices_multi(["RELIANCE", "TCS", "WIPRO"])
        assert prices["RELIANCE"] == 1120.0
        assert prices["TCS"] == 1830.0
        assert "WIPRO" not in prices  # no price data for WIPRO

    def test_get_prices_multi_empty(self, pit_db: sqlite3.Connection) -> None:
        """Empty symbol list returns empty dict."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 3, 31))
        assert pit.get_prices_multi([]) == {}

    def test_future_prices_invisible(self, pit_db: sqlite3.Connection) -> None:
        """Prices traded after asof must NEVER be returned."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 3, 31))
        series = pit.get_price_series("RELIANCE", start=date(2020, 1, 1))
        dates = [row.trade_date for row in series]
        assert "2020-04-01" not in dates
        assert "2020-06-30" not in dates
        assert "2021-03-31" not in dates


# ══════════════════════════════════════════════════════════════════════
# 3. UNIVERSE — Point-in-Time Tests
# ══════════════════════════════════════════════════════════════════════


class TestUniversePIT:
    """Verify that universe membership respects point-in-time snapshots."""

    def test_universe_at_2020_rebalance(self, pit_db: sqlite3.Connection) -> None:
        """At 2020-03-31, universe should be the 5 original members."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 3, 31))
        universe = pit.get_universe()
        assert set(universe) == {"RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"}

    def test_universe_between_rebalances(self, pit_db: sqlite3.Connection) -> None:
        """Between rebalances, universe is the last known snapshot."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 9, 15))
        universe = pit.get_universe()
        # Still using 2020-03-31 snapshot
        assert set(universe) == {"RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"}

    def test_universe_at_2021_rebalance(self, pit_db: sqlite3.Connection) -> None:
        """At 2021-03-31, ICICIBANK removed and WIPRO added."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2021, 3, 31))
        universe = pit.get_universe()
        assert "ICICIBANK" not in universe
        assert "WIPRO" in universe
        assert set(universe) == {"RELIANCE", "TCS", "INFY", "HDFCBANK", "WIPRO"}

    def test_future_rebalance_invisible(self, pit_db: sqlite3.Connection) -> None:
        """Before the 2021 rebalance, WIPRO is NOT in the universe."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2021, 3, 30))
        universe = pit.get_universe()
        assert "WIPRO" not in universe
        assert "ICICIBANK" in universe  # still in 2020 snapshot

    def test_universe_before_any_snapshot(self, pit_db: sqlite3.Connection) -> None:
        """Before any snapshot, universe is empty."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2019, 1, 1))
        assert pit.get_universe() == []

    def test_universe_is_sorted(self, pit_db: sqlite3.Connection) -> None:
        """Universe should be returned in alphabetical order."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 3, 31))
        universe = pit.get_universe()
        assert universe == sorted(universe)

    def test_universe_with_sectors(self, pit_db: sqlite3.Connection) -> None:
        """get_universe_with_sectors returns symbol→sector mapping."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 3, 31))
        mapping = pit.get_universe_with_sectors()
        assert mapping["RELIANCE"] == "oil_gas_consumable_fuels"
        assert mapping["TCS"] == "information_technology"
        assert mapping["HDFCBANK"] == "financial_services"

    def test_get_sector_for_symbol(self, pit_db: sqlite3.Connection) -> None:
        """get_sector returns the correct sector for a symbol."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 3, 31))
        assert pit.get_sector("RELIANCE") == "oil_gas_consumable_fuels"
        assert pit.get_sector("NONEXISTENT") is None


# ══════════════════════════════════════════════════════════════════════
# 4. SENTIMENT — Point-in-Time Tests
# ══════════════════════════════════════════════════════════════════════


class TestSentimentPIT:
    """Verify that sentiment data never leaks beyond published_at."""

    def test_sentiment_respects_asof(self, pit_db: sqlite3.Connection) -> None:
        """Only headlines published on or before asof are returned."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 3, 31))
        rows = pit.get_sentiment("RELIANCE", lookback_days=90)
        # Only the March 25 headline is on or before March 31
        assert len(rows) == 1
        assert rows[0].sentiment_score == 0.3

    def test_sentiment_includes_later_headline(self, pit_db: sqlite3.Connection) -> None:
        """At asof=2020-04-15, both March and April headlines visible."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 4, 15))
        rows = pit.get_sentiment("RELIANCE", lookback_days=90)
        assert len(rows) == 2
        # Newest first
        assert rows[0].sentiment_score == 0.6  # April 10
        assert rows[1].sentiment_score == 0.3  # March 25

    def test_sentiment_future_invisible(self, pit_db: sqlite3.Connection) -> None:
        """July 15 headline should not appear when asof is June 30."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 6, 30))
        rows = pit.get_sentiment("RELIANCE", lookback_days=180)
        headlines = [r.headline for r in rows]
        assert not any("Facebook" in h for h in headlines)

    def test_avg_sentiment(self, pit_db: sqlite3.Connection) -> None:
        """Average sentiment should be computed correctly."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 4, 15))
        avg = pit.get_avg_sentiment("RELIANCE", lookback_days=90)
        assert avg is not None
        assert abs(avg - 0.45) < 0.01  # (0.3 + 0.6) / 2

    def test_avg_sentiment_no_data(self, pit_db: sqlite3.Connection) -> None:
        """Average sentiment for a symbol with no data returns None."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 3, 31))
        assert pit.get_avg_sentiment("TCS") is None

    def test_lookback_window_excludes_old_headlines(self, pit_db: sqlite3.Connection) -> None:
        """Headlines outside the lookback window are excluded."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 7, 20))
        # 7-day lookback from July 20 = July 13..July 20
        rows = pit.get_sentiment("RELIANCE", lookback_days=7)
        assert len(rows) == 1
        assert rows[0].sentiment_score == 0.8  # July 15 is within 7-day window


# ══════════════════════════════════════════════════════════════════════
# 5. EDGE CASES
# ══════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Boundary conditions and empty-state behaviour."""

    def test_repr(self, pit_db: sqlite3.Connection) -> None:
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 3, 31))
        assert "2020-03-31" in repr(pit)

    def test_asof_property(self, pit_db: sqlite3.Connection) -> None:
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 3, 31))
        assert pit.asof == date(2020, 3, 31)

    def test_empty_db_returns_none(self, tmp_db: sqlite3.Connection) -> None:
        """On an empty (but schema-present) database, all queries return None/empty."""
        pit = PointInTimeDataAccess(tmp_db, asof=date(2020, 3, 31))
        assert pit.get_price("ANYTHING") is None
        assert pit.get_fundamental("ANYTHING", "roe") is None
        assert pit.get_universe() == []
        assert pit.get_prices_multi(["A", "B"]) == {}
        assert pit.get_fundamentals_panel("roe", ["A"]) == {}
        assert pit.get_sentiment("ANYTHING") == []
        assert pit.get_avg_sentiment("ANYTHING") is None

    def test_different_asof_same_db(self, pit_db: sqlite3.Connection) -> None:
        """Two PIT accessors on the same connection but different dates see different data."""
        pit_early = PointInTimeDataAccess(pit_db, asof=date(2020, 3, 31))
        pit_late = PointInTimeDataAccess(pit_db, asof=date(2020, 8, 15))

        # Early: only Q3 FY20 ROE visible
        assert pit_early.get_fundamental("RELIANCE", "roe") == 12.5
        # Late: Q1 FY21 visible (disclosed 2020-08-10)
        assert pit_late.get_fundamental("RELIANCE", "roe") == 14.2

        # Early: 2 prices (March 30, 31)
        early_series = pit_early.get_price_series("RELIANCE", start=date(2020, 1, 1))
        assert len(early_series) == 2
        # Late: 4 prices (up to June 30)
        late_series = pit_late.get_price_series("RELIANCE", start=date(2020, 1, 1))
        assert len(late_series) == 4

    def test_metrics_are_independent(self, pit_db: sqlite3.Connection) -> None:
        """Different metrics for the same symbol are queried independently."""
        pit = PointInTimeDataAccess(pit_db, asof=date(2020, 3, 31))
        roe = pit.get_fundamental("RELIANCE", "roe")
        revenue = pit.get_fundamental("RELIANCE", "revenue")
        assert roe == 12.5
        assert revenue == 156789.0
