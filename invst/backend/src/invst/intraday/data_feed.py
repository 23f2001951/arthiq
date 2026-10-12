"""
IIM — Live Data Feed.

Provides a unified adapter interface for real-time 15m candle data.
Two implementations:
  1. KiteConnectFeed  — real-time tick data via Zerodha Kite Connect WebSocket
                        (requires official API key + daily OAuth token)
  2. YFinanceFeed     — 15-min delayed data via yfinance (study/paper mode only)

Both implement the BaseDataFeed interface. The signal engine receives
closed 15m candles from whichever feed is active.

Mode labelling (never mutable at runtime):
  KiteConnectFeed  → mode = 'live'
  YFinanceFeed     → mode = 'paper'   (displayed with "STUDY" badge in UI)

Kite Connect daily re-auth:
  Access tokens expire daily at midnight. The scheduler calls
  refresh_kite_token() once per morning before market open.
  Session-token injection (Kite web session) is NOT supported —
  it violates Zerodha TOS and causes daily account risk.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import pandas as pd

logger = logging.getLogger("invst.intraday.data_feed")

IST = timezone(timedelta(hours=5, minutes=30))
_15M_SECONDS = 900


# ---------------------------------------------------------------------------
# Candle data model
# ---------------------------------------------------------------------------

class Candle:
    """A single 15m OHLCV candle — always represents a CLOSED bar."""
    __slots__ = ("symbol", "candle_time", "open", "high", "low", "close", "volume", "is_closed")

    def __init__(
        self,
        symbol: str,
        candle_time: datetime,
        open: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        is_closed: bool = True,
    ) -> None:
        self.symbol = symbol
        self.candle_time = candle_time
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.is_closed = is_closed

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "candle_time": self.candle_time.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "is_closed": self.is_closed,
        }


# ---------------------------------------------------------------------------
# Base interface
# ---------------------------------------------------------------------------

class BaseDataFeed(ABC):
    """Abstract base for all data feed implementations."""

    @property
    @abstractmethod
    def mode(self) -> str:
        """Return 'live' or 'paper'."""

    @abstractmethod
    def start(self, symbols: list[str]) -> None:
        """Begin streaming/polling for the given symbols."""

    @abstractmethod
    def stop(self) -> None:
        """Stop the feed gracefully."""

    @abstractmethod
    def get_candles(self, symbol: str, n: int = 100) -> pd.DataFrame:
        """
        Return the last n CLOSED 15m candles for a symbol.
        The current (incomplete) candle is NEVER included.
        """

    @abstractmethod
    def is_live(self) -> bool:
        """Return True if feed is actively receiving data."""


# ---------------------------------------------------------------------------
# Candle aggregator (shared by both feed implementations)
# ---------------------------------------------------------------------------

class CandleAggregator:
    """
    Aggregates tick-level (or per-bar) updates into 15m OHLCV candles.

    A candle is considered CLOSED when the current time ≥ candle_end_time.
    The incomplete candle is held in _open_candle and is NEVER returned
    from get_closed_candles().
    """

    def __init__(self) -> None:
        # symbol → list of closed Candle objects (chronological)
        self._closed: dict[str, list[Candle]] = defaultdict(list)
        # symbol → current open (incomplete) candle dict
        self._open: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _candle_start(ts: datetime) -> datetime:
        """Floor a timestamp to the nearest 15m boundary."""
        minute = (ts.minute // 15) * 15
        return ts.replace(minute=minute, second=0, microsecond=0)

    def on_tick(self, symbol: str, price: float, volume: int, ts: datetime) -> Candle | None:
        """
        Process a single tick. Returns a closed Candle if a 15m bar just closed.

        Args:
            symbol: NSE symbol.
            price: Last traded price.
            volume: Tick volume (traded quantity).
            ts: Tick timestamp (IST, tz-aware).

        Returns:
            Closed Candle if a bar boundary was crossed, else None.
        """
        bar_start = self._candle_start(ts)

        if symbol not in self._open:
            self._open[symbol] = {
                "start": bar_start,
                "open": price, "high": price, "low": price, "close": price,
                "volume": volume,
            }
            return None

        current = self._open[symbol]

        if bar_start > current["start"]:
            # Bar boundary crossed → close the previous candle
            closed = Candle(
                symbol=symbol,
                candle_time=current["start"],
                open=current["open"],
                high=current["high"],
                low=current["low"],
                close=current["close"],
                volume=current["volume"],
                is_closed=True,
            )
            self._closed[symbol].append(closed)

            # Start new open candle
            self._open[symbol] = {
                "start": bar_start,
                "open": price, "high": price, "low": price, "close": price,
                "volume": volume,
            }
            return closed

        # Update current candle
        current["high"] = max(current["high"], price)
        current["low"] = min(current["low"], price)
        current["close"] = price
        current["volume"] += volume
        return None

    def on_bar(self, symbol: str, candle: Candle) -> None:
        """Directly ingest a closed bar (used by yfinance poll feed)."""
        self._closed[symbol].append(candle)

    def get_closed_candles(self, symbol: str, n: int = 200) -> list[Candle]:
        """Return last n closed candles for a symbol."""
        return self._closed[symbol][-n:]

    def to_dataframe(self, symbol: str, n: int = 200) -> pd.DataFrame:
        """Return closed candles as a pd.DataFrame with DatetimeIndex (IST)."""
        candles = self.get_closed_candles(symbol, n)
        if not candles:
            return pd.DataFrame()
        rows = [
            {"candle_time": c.candle_time, "open": c.open, "high": c.high,
             "low": c.low, "close": c.close, "volume": c.volume}
            for c in candles
        ]
        df = pd.DataFrame(rows).set_index("candle_time")
        df.index = pd.DatetimeIndex(df.index)
        return df


# ---------------------------------------------------------------------------
# yfinance feed (paper/study mode)
# ---------------------------------------------------------------------------

class YFinanceFeed(BaseDataFeed):
    """
    15-minute delayed data feed via yfinance.

    Mode: 'paper' — all signals generated from this feed are labelled
    STUDY/PAPER ONLY. Never presented as live entry signals.

    Polls yfinance every 5 minutes and aggregates the last complete 15m bar.
    yfinance 15m history is limited to approximately 60 days.
    Bid/ask spread (Gate 8) is NOT computed on this feed.
    """

    def __init__(self) -> None:
        self._aggregator = CandleAggregator()
        self._symbols: list[str] = []
        self._running = False
        self._last_poll: dict[str, datetime] = {}

    @property
    def mode(self) -> str:
        return "paper"

    def start(self, symbols: list[str]) -> None:
        self._symbols = symbols
        self._running = True
        logger.info("YFinanceFeed started (paper mode) for %d symbols.", len(symbols))

    def stop(self) -> None:
        self._running = False
        logger.info("YFinanceFeed stopped.")

    def is_live(self) -> bool:
        return self._running

    def poll(self, symbol: str | None = None) -> list[Candle]:
        """
        Poll yfinance for new closed 15m bars.
        Call this method from the scheduler every 5 minutes.

        Returns:
            List of new closed Candle objects.
        """
        try:
            import yfinance as yf
        except ImportError:
            logger.error("yfinance not installed.")
            return []

        targets = [symbol] if symbol else self._symbols
        new_candles: list[Candle] = []

        for sym in targets:
            try:
                ticker = yf.Ticker(f"{sym}.NS")
                # Fetch last 5 days of 15m bars (yfinance max for 15m is ~60d)
                df = ticker.history(period="5d", interval="15m")
                if df is None or df.empty:
                    continue

                df.index = pd.DatetimeIndex(df.index).tz_convert(IST)
                df.columns = [c.lower() for c in df.columns]

                now_ist = datetime.now(IST)

                for ts, row in df.iterrows():
                    bar_end = ts + timedelta(minutes=15)
                    # Only process bars that are fully closed
                    if bar_end > now_ist:
                        continue
                    candle = Candle(
                        symbol=sym,
                        candle_time=ts.to_pydatetime(),
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=int(row["volume"]),
                        is_closed=True,
                    )
                    self._aggregator.on_bar(sym, candle)
                    new_candles.append(candle)

                self._last_poll[sym] = now_ist
            except Exception as exc:
                logger.warning("[%s] yfinance poll error: %s", sym, exc)

        return new_candles

    def get_candles(self, symbol: str, n: int = 100) -> pd.DataFrame:
        return self._aggregator.to_dataframe(symbol, n)

    def load_warmup_bars(self, symbol: str, n_prior_sessions: int = 3) -> pd.DataFrame:
        """
        Load warmup bars from prior sessions to seed EMA50 and other indicators.
        Returns a DataFrame with is_warmup=True marking.
        """
        try:
            import yfinance as yf
            ticker = yf.Ticker(f"{symbol}.NS")
            df = ticker.history(period="7d", interval="15m")
            if df is None or df.empty:
                return pd.DataFrame()
            df.index = pd.DatetimeIndex(df.index).tz_convert(IST)
            df.columns = [c.lower() for c in df.columns]

            today = datetime.now(IST).date()
            # Mark prior-session bars as warmup
            df["is_warmup"] = df.index.map(lambda t: t.date() < today).astype(int)
            return df
        except Exception as exc:
            logger.warning("[%s] warmup load error: %s", symbol, exc)
            return pd.DataFrame()


# ---------------------------------------------------------------------------
# Kite Connect feed (live mode)
# ---------------------------------------------------------------------------

class KiteConnectFeed(BaseDataFeed):
    """
    Real-time tick data via Zerodha Kite Connect WebSocket.

    Requires:
      - KITE_API_KEY environment variable
      - KITE_ACCESS_TOKEN environment variable (refreshed daily via OAuth)

    Access tokens expire daily. Use refresh_kite_token() in the morning
    scheduler to obtain a fresh token via the official OAuth flow.

    This implementation is a scaffold — KiteTicker callbacks are wired here.
    Full Kite Connect setup requires the kiteconnect package:
      pip install kiteconnect
    """

    def __init__(self, api_key: str, access_token: str) -> None:
        self._api_key = api_key
        self._access_token = access_token
        self._aggregator = CandleAggregator()
        self._symbols: list[str] = []
        self._instrument_tokens: dict[str, int] = {}
        self._running = False
        self._kws: Any = None  # KiteTicker instance
        self._on_closed_candle: Callable[[Candle], None] | None = None

    @property
    def mode(self) -> str:
        return "live"

    def set_candle_callback(self, callback: Callable[[Candle], None]) -> None:
        """Register a callback that fires whenever a 15m candle closes."""
        self._on_closed_candle = callback

    def _resolve_tokens(self, symbols: list[str]) -> None:
        """Resolve NSE symbols to Kite instrument tokens."""
        try:
            from kiteconnect import KiteConnect
            kite = KiteConnect(api_key=self._api_key)
            kite.set_access_token(self._access_token)
            instruments = kite.instruments("NSE")
            token_map = {i["tradingsymbol"]: i["instrument_token"] for i in instruments}
            self._instrument_tokens = {
                sym: token_map[sym]
                for sym in symbols
                if sym in token_map
            }
            if len(self._instrument_tokens) < len(symbols):
                missing = [s for s in symbols if s not in self._instrument_tokens]
                logger.warning("Kite token resolution missing: %s", missing)
        except Exception as exc:
            logger.error("Kite instrument token resolution failed: %s", exc)

    def start(self, symbols: list[str]) -> None:
        """Start KiteTicker WebSocket stream."""
        try:
            from kiteconnect import KiteTicker
        except ImportError:
            logger.error("kiteconnect package not installed. Run: pip install kiteconnect")
            return

        self._symbols = symbols
        self._resolve_tokens(symbols)

        if not self._instrument_tokens:
            logger.error("No instrument tokens resolved. Kite feed cannot start.")
            return

        self._kws = KiteTicker(self._api_key, self._access_token)

        def on_ticks(ws: Any, ticks: list[dict]) -> None:
            """Process incoming ticks from KiteTicker."""
            now = datetime.now(IST)
            token_to_sym = {v: k for k, v in self._instrument_tokens.items()}
            for tick in ticks:
                token = tick.get("instrument_token")
                sym = token_to_sym.get(token)
                if not sym:
                    continue
                ltp = float(tick.get("last_price", 0))
                vol = int(tick.get("volume_traded", 0))
                closed_candle = self._aggregator.on_tick(sym, ltp, vol, now)
                if closed_candle and self._on_closed_candle:
                    self._on_closed_candle(closed_candle)

        def on_connect(ws: Any, response: Any) -> None:
            tokens = list(self._instrument_tokens.values())
            ws.subscribe(tokens)
            ws.set_mode(ws.MODE_FULL, tokens)
            self._running = True
            logger.info("Kite WebSocket connected. Subscribed to %d tokens.", len(tokens))

        def on_close(ws: Any, code: Any, reason: Any) -> None:
            self._running = False
            logger.warning("Kite WebSocket closed: code=%s reason=%s", code, reason)

        def on_error(ws: Any, code: Any, reason: Any) -> None:
            logger.error("Kite WebSocket error: code=%s reason=%s", code, reason)

        self._kws.on_ticks = on_ticks
        self._kws.on_connect = on_connect
        self._kws.on_close = on_close
        self._kws.on_error = on_error
        self._kws.connect(threaded=True)
        logger.info("KiteConnectFeed started for %d symbols.", len(symbols))

    def stop(self) -> None:
        if self._kws:
            self._kws.close()
        self._running = False
        logger.info("KiteConnectFeed stopped.")

    def is_live(self) -> bool:
        return self._running

    def get_candles(self, symbol: str, n: int = 100) -> pd.DataFrame:
        return self._aggregator.to_dataframe(symbol, n)


# ---------------------------------------------------------------------------
# Feed factory
# ---------------------------------------------------------------------------

def create_feed(
    kite_api_key: str | None = None,
    kite_access_token: str | None = None,
) -> BaseDataFeed:
    """
    Create the appropriate data feed based on available credentials.

    If Kite credentials are present → KiteConnectFeed (live mode).
    Otherwise → YFinanceFeed (paper mode, 15-min delayed).
    """
    if kite_api_key and kite_access_token:
        logger.info("Creating KiteConnectFeed (live mode).")
        return KiteConnectFeed(kite_api_key, kite_access_token)

    logger.info(
        "Kite credentials not found. Creating YFinanceFeed (paper/study mode). "
        "Signals will be labelled STUDY ONLY."
    )
    return YFinanceFeed()


def refresh_kite_token(api_key: str, request_token: str, api_secret: str) -> str:
    """
    Exchange a Kite request_token for an access_token via official OAuth.

    This must be called once per day, typically via the morning scheduler.
    The request_token is obtained by redirecting the user to Kite's login URL
    and extracting the token from the callback URL.

    Returns:
        The new access_token string.

    Raises:
        RuntimeError if the exchange fails.
    """
    try:
        from kiteconnect import KiteConnect
        kite = KiteConnect(api_key=api_key)
        data = kite.generate_session(request_token, api_secret=api_secret)
        access_token = data["access_token"]
        logger.info("Kite access token refreshed successfully.")
        return access_token
    except Exception as exc:
        raise RuntimeError(f"Kite token refresh failed: {exc}") from exc
