"""
ArthIQ Intraday Intelligence Module (IIM) V2.

Provides high-accuracy intraday trading signals for NSE equities using a
4-pillar confluence engine with ATR-based dynamic SL/Target computation.

Strategies (V1):
  - TREND_PULLBACK: Pullback entry to EMA21 / VWAP in an established trend.
  - INTRADAY_BREAKOUT: Breakout of key levels (ORB, prev-day high/low, pivots).

All signals are generated on fully closed 15m candles only.
Entry is modelled at the open of the next candle (no lookahead).
"""

__version__ = "2.0.0"
