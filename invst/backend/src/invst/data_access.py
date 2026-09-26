"""invst — Point-in-Time Data Access Layer.

The ONLY blessed way to read fundamentals, prices, index constituents,
and news sentiment from the database for backtesting and live scoring.

Any code that reads the DB without going through this class is a
code-review red flag.  Every query is parameterised by an ``asof`` date
that represents the simulated "today" — no row with a timestamp after
``asof`` is ever returned.

Design invariants
-----------------
* Fundamentals are filtered by ``disclosed_at <= asof`` (never restated
  numbers that appeared after the decision date).
* Prices are filtered by ``trade_date <= asof``.
* Universe membership is determined by the most recent
  ``index_constituents_history`` snapshot on or before ``asof``.
* All date comparisons use ISO-8601 strings (``YYYY-MM-DD``) which sort
  lexicographically in SQLite.

See PROJECT_PLAN.md §3.3, §5.2, §5.4 for rationale.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class PriceRow:
    """A single daily price observation."""

    trade_date: str
    close: float
    adj_close: float | None
    volume: int | None


@dataclass(frozen=True)
class FundamentalRow:
    """A single fundamental metric observation with its disclosure date."""

    symbol: str
    value: float | None
    period_end: str
    disclosed_at: str


@dataclass(frozen=True)
class SentimentRow:
    """A single news-sentiment observation."""

    headline_id: str
    published_at: str
    headline: str
    source: str | None
    sentiment_score: float | None


@dataclass(frozen=True)
class BiTemporalFundamentalRow:
    """A bi-temporal fundamental metric observation."""

    symbol: str
    metric: str
    value: float | None
    raw_value: float | None
    restated_value: float | None
    period_end: str
    effective_date: str
    filing_timestamp: str
    revision_seq: int
    valid_from: str
    valid_to: str
    source: str


@dataclass(frozen=True)
class CorporateActionRow:
    """A single corporate action observation."""

    symbol: str
    action_type: str
    ex_date: str
    record_date: str | None
    ratio_numerator: float | None
    ratio_denominator: float | None
    dividend_amount: float | None
    effective_date: str
    source: str


@dataclass(frozen=True)
class CorporateEventRow:
    """A structured corporate event observation."""

    event_id: str
    symbol: str
    event_type: str
    headline: str
    direction: str
    materiality_score: float
    confidence_score: float
    affected_factors: list[str]
    effective_date: str
    source: str


class PointInTimeDataAccess:
    """Anti-lookahead data accessor for backtesting and live scoring.

    Every query is bounded by ``self.asof`` — the simulated "today".
    Instantiate one per rebalance date in a walk-forward backtest::

        pit = PointInTimeDataAccess(conn, asof=date(2020, 3, 31))
        roe = pit.get_fundamental("RELIANCE", "roe")
        # Returns the most recently *disclosed* ROE on or before 2020-03-31.

    Parameters
    ----------
    conn : sqlite3.Connection
        Open database connection (row_factory is NOT modified).
    asof : date
        The simulated current date.  No data disclosed, traded, or
        published after this date will ever be returned.
    """

    def __init__(self, conn: sqlite3.Connection, asof: date) -> None:
        self._conn = conn
        self._asof = asof

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def asof(self) -> date:
        """Return the point-in-time date this accessor is bound to."""
        return self._asof

    @property
    def conn(self) -> sqlite3.Connection:
        """Return the underlying database connection."""
        return self._conn

    # ------------------------------------------------------------------
    # Prices
    # ------------------------------------------------------------------

    def get_price(self, symbol: str, on_or_before: date | None = None) -> float | None:
        """Return the most recent closing price on or before the given date.

        Parameters
        ----------
        symbol : str
            Ticker symbol (e.g. ``"RELIANCE"``).
        on_or_before : date, optional
            Defaults to ``self.asof``.  Clamped to ``self.asof`` if it
            exceeds the point-in-time boundary.

        Returns
        -------
        float or None
            The closing price, or ``None`` if no price exists.
        """
        effective = min(on_or_before, self._asof) if on_or_before else self._asof
        row = self._conn.execute(
            """
            SELECT close FROM daily_prices
            WHERE symbol = ? AND trade_date <= ?
            ORDER BY trade_date DESC
            LIMIT 1
            """,
            (symbol, effective.isoformat()),
        ).fetchone()
        return row[0] if row else None

    def get_price_series(
        self,
        symbol: str,
        start: date,
        end: date | None = None,
    ) -> list[PriceRow]:
        """Return daily prices between ``start`` and ``end`` (inclusive).

        Parameters
        ----------
        symbol : str
            Ticker symbol.
        start : date
            First trading date (inclusive).
        end : date, optional
            Last trading date (inclusive).  Defaults to ``self.asof``.
            Clamped to ``self.asof`` if it exceeds the boundary.

        Returns
        -------
        list[PriceRow]
            Chronologically ordered price rows.
        """
        effective_end = min(end, self._asof) if end else self._asof
        rows = self._conn.execute(
            """
            SELECT trade_date, close, adj_close, volume
            FROM daily_prices
            WHERE symbol = ? AND trade_date BETWEEN ? AND ?
            ORDER BY trade_date
            """,
            (symbol, start.isoformat(), effective_end.isoformat()),
        ).fetchall()
        return [PriceRow(trade_date=r[0], close=r[1], adj_close=r[2], volume=r[3]) for r in rows]

    def get_prices_multi(
        self,
        symbols: list[str],
        on_or_before: date | None = None,
    ) -> dict[str, float]:
        """Return the most recent closing price for multiple symbols.

        Parameters
        ----------
        symbols : list[str]
            Ticker symbols.
        on_or_before : date, optional
            Defaults to ``self.asof``.

        Returns
        -------
        dict[str, float]
            Mapping of symbol → closing price.  Symbols with no price
            data are omitted.
        """
        if not symbols:
            return {}
        effective = min(on_or_before, self._asof) if on_or_before else self._asof
        placeholders = ",".join("?" * len(symbols))
        rows = self._conn.execute(
            f"""
            SELECT dp.symbol, dp.close
            FROM daily_prices dp
            JOIN (
                SELECT symbol, MAX(trade_date) AS max_td
                FROM daily_prices
                WHERE trade_date <= ?
                  AND symbol IN ({placeholders})
                GROUP BY symbol
            ) latest
              ON dp.symbol = latest.symbol
             AND dp.trade_date = latest.max_td
            """,
            [effective.isoformat(), *symbols],
        ).fetchall()
        return {r[0]: r[1] for r in rows}

    # ------------------------------------------------------------------
    # Fundamentals (point-in-time — bi-temporal with legacy fallback)
    # ------------------------------------------------------------------

    def get_fundamental(self, symbol: str, metric: str) -> float | None:
        """Return the latest disclosed value of ``metric`` for ``symbol``.

        Queries ``fundamentals_pit`` bi-temporal table first using
        effective_date <= asof, valid_from <= asof, valid_to > asof.
        Falls back to ``fundamentals_quarterly`` if no bi-temporal row exists.
        """
        asof_str = self._asof.isoformat()
        try:
            pit_row = self._conn.execute(
                """
                SELECT raw_value, restated_value FROM fundamentals_pit
                WHERE symbol = ? AND metric = ?
                  AND effective_date <= ?
                  AND valid_from <= ?
                  AND valid_to > ?
                ORDER BY effective_date DESC, period_end DESC, revision_seq DESC
                LIMIT 1
                """,
                (symbol, metric, asof_str, asof_str, asof_str),
            ).fetchone()
            if pit_row is not None:
                return pit_row[1] if pit_row[1] is not None else pit_row[0]
        except sqlite3.OperationalError:
            pass

        row = self._conn.execute(
            """
            SELECT value FROM fundamentals_quarterly
            WHERE symbol = ? AND metric = ?
              AND disclosed_at <= ?
            ORDER BY disclosed_at DESC, period_end DESC
            LIMIT 1
            """,
            (symbol, metric, asof_str),
        ).fetchone()
        return row[0] if row else None

    def get_fundamental_detail(self, symbol: str, metric: str) -> FundamentalRow | None:
        """Like :meth:`get_fundamental` but returns the full row metadata."""
        asof_str = self._asof.isoformat()
        try:
            pit_row = self._conn.execute(
                """
                SELECT symbol, raw_value, restated_value, period_end, effective_date
                FROM fundamentals_pit
                WHERE symbol = ? AND metric = ?
                  AND effective_date <= ?
                  AND valid_from <= ?
                  AND valid_to > ?
                ORDER BY effective_date DESC, period_end DESC, revision_seq DESC
                LIMIT 1
                """,
                (symbol, metric, asof_str, asof_str, asof_str),
            ).fetchone()
            if pit_row is not None:
                val = pit_row[2] if pit_row[2] is not None else pit_row[1]
                return FundamentalRow(symbol=pit_row[0], value=val, period_end=pit_row[3], disclosed_at=pit_row[4])
        except sqlite3.OperationalError:
            pass

        row = self._conn.execute(
            """
            SELECT symbol, value, period_end, disclosed_at
            FROM fundamentals_quarterly
            WHERE symbol = ? AND metric = ?
              AND disclosed_at <= ?
            ORDER BY disclosed_at DESC, period_end DESC
            LIMIT 1
            """,
            (symbol, metric, asof_str),
        ).fetchone()
        if row is None:
            return None
        return FundamentalRow(symbol=row[0], value=row[1], period_end=row[2], disclosed_at=row[3])

    def get_fundamentals_panel(
        self,
        metric: str,
        symbols: list[str],
    ) -> dict[str, float]:
        """Return the latest disclosed value of ``metric`` for many symbols.

        Vectorised version of :meth:`get_fundamental` used for
        cross-sectional ranking at each rebalance.
        """
        if not symbols:
            return {}
        placeholders = ",".join("?" * len(symbols))
        asof_str = self._asof.isoformat()
        results: dict[str, float] = {}

        # 1. Try fundamentals_pit first
        try:
            pit_rows = self._conn.execute(
                f"""
                SELECT fp.symbol, fp.raw_value, fp.restated_value
                FROM fundamentals_pit fp
                JOIN (
                    SELECT symbol, MAX(effective_date) AS max_eff
                    FROM fundamentals_pit
                    WHERE metric = ? AND effective_date <= ?
                      AND valid_from <= ? AND valid_to > ?
                      AND symbol IN ({placeholders})
                    GROUP BY symbol
                ) latest
                  ON fp.symbol = latest.symbol
                 AND fp.effective_date = latest.max_eff
                WHERE fp.metric = ?
                  AND fp.valid_from <= ? AND fp.valid_to > ?
                """,
                [metric, asof_str, asof_str, asof_str, *symbols, metric, asof_str, asof_str],
            ).fetchall()
            for r in pit_rows:
                v = r[2] if r[2] is not None else r[1]
                if v is not None:
                    results[r[0]] = v
        except sqlite3.OperationalError:
            pass

        # 2. For remaining symbols without a PIT record, query fundamentals_quarterly
        missing_symbols = [s for s in symbols if s not in results]
        if missing_symbols:
            m_placeholders = ",".join("?" * len(missing_symbols))
            rows = self._conn.execute(
                f"""
                SELECT f.symbol, f.value
                FROM fundamentals_quarterly f
                JOIN (
                    SELECT symbol, MAX(disclosed_at) AS max_disc
                    FROM fundamentals_quarterly
                    WHERE metric = ? AND disclosed_at <= ?
                      AND symbol IN ({m_placeholders})
                    GROUP BY symbol
                ) latest
                  ON f.symbol = latest.symbol
                 AND f.disclosed_at = latest.max_disc
                WHERE f.metric = ?
                """,
                [metric, asof_str, *missing_symbols, metric],
            ).fetchall()
            for r in rows:
                if r[1] is not None:
                    results[r[0]] = r[1]

        return results

    def get_fundamental_history(
        self,
        symbol: str,
        metric: str,
        n_quarters: int = 12,
    ) -> list[FundamentalRow]:
        """Return the last ``n_quarters`` disclosed values of a metric."""
        asof_str = self._asof.isoformat()
        try:
            pit_rows = self._conn.execute(
                """
                SELECT symbol, raw_value, restated_value, period_end, effective_date
                FROM fundamentals_pit
                WHERE symbol = ? AND metric = ?
                  AND effective_date <= ?
                  AND valid_from <= ?
                  AND valid_to > ?
                ORDER BY effective_date DESC, period_end DESC, revision_seq DESC
                LIMIT ?
                """,
                (symbol, metric, asof_str, asof_str, asof_str, n_quarters),
            ).fetchall()
            if pit_rows:
                return [
                    FundamentalRow(
                        symbol=r[0],
                        value=r[2] if r[2] is not None else r[1],
                        period_end=r[3],
                        disclosed_at=r[4],
                    )
                    for r in pit_rows
                ]
        except sqlite3.OperationalError:
            pass

        rows = self._conn.execute(
            """
            SELECT symbol, value, period_end, disclosed_at
            FROM fundamentals_quarterly
            WHERE symbol = ? AND metric = ?
              AND disclosed_at <= ?
            ORDER BY disclosed_at DESC, period_end DESC
            LIMIT ?
            """,
            (symbol, metric, asof_str, n_quarters),
        ).fetchall()
        return [
            FundamentalRow(symbol=r[0], value=r[1], period_end=r[2], disclosed_at=r[3])
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Corporate Actions & Corporate Events (Point-in-Time)
    # ------------------------------------------------------------------

    def get_corporate_actions(
        self,
        symbol: str,
        start: date | None = None,
        end: date | None = None,
    ) -> list[CorporateActionRow]:
        """Return corporate actions for symbol effective on or before self.asof."""
        effective_end = min(end, self._asof) if end else self._asof
        start_str = start.isoformat() if start else "1900-01-01"
        try:
            rows = self._conn.execute(
                """
                SELECT symbol, action_type, ex_date, record_date, ratio_numerator,
                       ratio_denominator, dividend_amount, effective_date, source
                FROM corporate_actions_pit
                WHERE symbol = ? AND effective_date <= ? AND ex_date BETWEEN ? AND ?
                ORDER BY ex_date
                """,
                (symbol, self._asof.isoformat(), start_str, effective_end.isoformat()),
            ).fetchall()
            return [
                CorporateActionRow(
                    symbol=r[0],
                    action_type=r[1],
                    ex_date=r[2],
                    record_date=r[3],
                    ratio_numerator=r[4],
                    ratio_denominator=r[5],
                    dividend_amount=r[6],
                    effective_date=r[7],
                    source=r[8],
                )
                for r in rows
            ]
        except sqlite3.OperationalError:
            return []

    def get_corporate_events(
        self,
        symbol: str,
        lookback_days: int = 180,
    ) -> list[CorporateEventRow]:
        """Return structured corporate events up to self.asof."""
        import json

        asof_str = self._asof.isoformat()
        start_date = date.fromordinal(max(1, self._asof.toordinal() - lookback_days)).isoformat()
        try:
            rows = self._conn.execute(
                """
                SELECT event_id, symbol, event_type, headline, direction,
                       materiality_score, confidence_score, affected_factors,
                       effective_date, source
                FROM corporate_events_pit
                WHERE symbol = ? AND effective_date <= ? AND effective_date >= ?
                ORDER BY effective_date DESC
                """,
                (symbol, asof_str, start_date),
            ).fetchall()
            res = []
            for r in rows:
                try:
                    factors = json.loads(r[7]) if isinstance(r[7], str) else []
                except Exception:
                    factors = []
                res.append(
                    CorporateEventRow(
                        event_id=r[0],
                        symbol=r[1],
                        event_type=r[2],
                        headline=r[3],
                        direction=r[4],
                        materiality_score=float(r[5]),
                        confidence_score=float(r[6]),
                        affected_factors=factors,
                        effective_date=r[8],
                        source=r[9],
                    )
                )
            return res
        except sqlite3.OperationalError:
            return []

    # ------------------------------------------------------------------
    # Universe (index constituents, point-in-time)
    # ------------------------------------------------------------------

    def get_universe(self) -> list[str]:
        """Return the Nifty 500 constituent symbols as of ``self.asof``.

        Uses the most recent ``index_constituents_history`` snapshot on or
        before ``self.asof``.  This correctly handles additions and removals:
        a stock is in the universe only if it appears in the latest snapshot.

        Returns
        -------
        list[str]
            Sorted list of ticker symbols.
        """
        # Find the most recent rebalance/snapshot date on or before asof
        latest_row = self._conn.execute(
            """
            SELECT MAX(effective_date) FROM index_constituents_history
            WHERE effective_date <= ?
            """,
            (self._asof.isoformat(),),
        ).fetchone()

        if latest_row is None or latest_row[0] is None:
            return []

        latest_date = latest_row[0]

        rows = self._conn.execute(
            """
            SELECT DISTINCT symbol FROM index_constituents_history
            WHERE effective_date = ?
            ORDER BY symbol
            """,
            (latest_date,),
        ).fetchall()
        return [r[0] for r in rows]

    def get_universe_with_sectors(self) -> dict[str, str]:
        """Return a mapping of symbol → sector for the current universe.

        Returns
        -------
        dict[str, str]
            Mapping of symbol → sector code.
        """
        latest_row = self._conn.execute(
            """
            SELECT MAX(effective_date) FROM index_constituents_history
            WHERE effective_date <= ?
            """,
            (self._asof.isoformat(),),
        ).fetchone()

        if latest_row is None or latest_row[0] is None:
            return {}

        latest_date = latest_row[0]

        rows = self._conn.execute(
            """
            SELECT symbol, sector FROM index_constituents_history
            WHERE effective_date = ?
            ORDER BY symbol
            """,
            (latest_date,),
        ).fetchall()
        return {r[0]: r[1] for r in rows}

    def get_sector(self, symbol: str) -> str | None:
        """Return the sector classification for a symbol as of ``self.asof``.

        Parameters
        ----------
        symbol : str
            Ticker symbol.

        Returns
        -------
        str or None
            Sector code, or ``None`` if the symbol is not in the universe.
        """
        row = self._conn.execute(
            """
            SELECT sector FROM index_constituents_history
            WHERE symbol = ? AND effective_date <= ?
            ORDER BY effective_date DESC
            LIMIT 1
            """,
            (symbol, self._asof.isoformat()),
        ).fetchone()
        return row[0] if row else None

    # ------------------------------------------------------------------
    # News sentiment (point-in-time — filtered by published_at)
    # ------------------------------------------------------------------

    def get_sentiment(
        self,
        symbol: str,
        lookback_days: int = 90,
    ) -> list[SentimentRow]:
        """Return news-sentiment rows for ``symbol`` within a lookback window.

        Parameters
        ----------
        symbol : str
            Ticker symbol.
        lookback_days : int
            Number of calendar days to look back from ``self.asof``.

        Returns
        -------
        list[SentimentRow]
            Ordered newest-first by ``published_at``.
        """
        lookback_date = (self._asof - timedelta(days=lookback_days)).isoformat()
        rows = self._conn.execute(
            """
            SELECT headline_id, published_at, headline, source, sentiment_score
            FROM news_sentiment
            WHERE symbol = ?
              AND published_at <= ?
              AND published_at >= ?
            ORDER BY published_at DESC
            """,
            (symbol, self._asof.isoformat(), lookback_date),
        ).fetchall()
        return [
            SentimentRow(
                headline_id=r[0],
                published_at=r[1],
                headline=r[2],
                source=r[3],
                sentiment_score=r[4],
            )
            for r in rows
        ]

    def get_avg_sentiment(self, symbol: str, lookback_days: int = 90) -> float | None:
        """Return the mean sentiment score over the lookback window.

        Parameters
        ----------
        symbol : str
            Ticker symbol.
        lookback_days : int
            Number of calendar days to look back from ``self.asof``.

        Returns
        -------
        float or None
            Average sentiment in ``[-1, +1]``, or ``None`` if no data.
        """
        lookback_date = (self._asof - timedelta(days=lookback_days)).isoformat()
        try:
            row = self._conn.execute(
                """
                SELECT AVG(sentiment_score)
                FROM news_sentiment
                WHERE symbol = ?
                  AND published_at <= ?
                  AND published_at >= ?
                  AND sentiment_score IS NOT NULL
                """,
                (symbol, self._asof.isoformat(), lookback_date),
            ).fetchone()
            return row[0] if row and row[0] is not None else None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"PointInTimeDataAccess(asof={self._asof.isoformat()})"
