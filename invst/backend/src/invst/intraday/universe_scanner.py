"""
IIM — Intraday Universe Scanner.

Runs at 8:45 AM IST before market open. Scores every candidate from NSE
F&O and Nifty100 universe using the Intraday Suitability Score (ISS).

ISS Dimensions (0–100):
  Liquidity (25%):      20-day avg traded value ≥ ₹100 Cr (F&O stocks)
  ATR Suitability (20%): 15m ATR as % of price in 0.3%–1.5% sweet spot
  Momentum (15%):        5-day return vs Nifty50 (relative strength)
  TODVOL Surge (20%):    Pre-market / prior-day TODVOL deviation
  Level Setup (10%):     Distance to nearest key level ≤ 0.5%
  News/Events (10%):     NSE announcements, block deals, earnings

Minimum ISS ≥ 65 to be included in today's universe (top 10–15 stocks).

Pre-open data (9:00–9:08 AM):
  - NSE indicative equilibrium price (IEP) from pre-open session
  - Gap classification vs prev-day close
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
import yfinance as yf

from invst.intraday.indicators import classify_gap, compute_pivot_levels

logger = logging.getLogger("invst.intraday.universe_scanner")

# NSE F&O stocks (top liquid subset) — used as primary candidate universe
# This list is the starting point; it should be updated from NSE F&O lot file
NSE_FNO_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "BHARTIARTL",
    "SBIN", "KOTAKBANK", "LT", "HINDUNILVR", "BAJFINANCE", "AXISBANK",
    "ASIANPAINT", "MARUTI", "SUNPHARMA", "TATAMOTORS", "WIPRO",
    "HCLTECH", "NTPC", "POWERGRID", "ONGC", "COALINDIA", "BPCL",
    "IOC", "GRASIM", "TITAN", "ULTRACEMCO", "NESTLEIND", "TECHM",
    "JSWSTEEL", "TATASTEEL", "HINDALCO", "VEDL", "ADANIPORTS",
    "ADANIENT", "DRREDDY", "CIPLA", "DIVISLAB", "APOLLOHOSP",
    "BAJAJFINSV", "BAJAJ-AUTO", "EICHERMOT", "HEROMOTOCO",
    "M&M", "TATACONSUM", "BRITANNIA", "UPL", "SHREECEM",
]

# NSE sector mapping (simplified — extend as needed)
NSE_SECTOR_MAP: dict[str, str] = {
    "RELIANCE": "OIL_GAS",
    "TCS": "IT", "INFY": "IT", "HCLTECH": "IT", "WIPRO": "IT", "TECHM": "IT",
    "HDFCBANK": "BANKING", "ICICIBANK": "BANKING", "AXISBANK": "BANKING",
    "KOTAKBANK": "BANKING", "SBIN": "BANKING",
    "LT": "INFRA", "NTPC": "POWER", "POWERGRID": "POWER",
    "BHARTIARTL": "TELECOM", "SUNPHARMA": "PHARMA",
    "DRREDDY": "PHARMA", "CIPLA": "PHARMA", "DIVISLAB": "PHARMA",
    "MARUTI": "AUTO", "TATAMOTORS": "AUTO", "M&M": "AUTO",
    "BAJAJ-AUTO": "AUTO", "HEROMOTOCO": "AUTO", "EICHERMOT": "AUTO",
    "BAJFINANCE": "NBFC", "BAJAJFINSV": "NBFC",
    "TATASTEEL": "METALS", "JSWSTEEL": "METALS", "HINDALCO": "METALS",
    "VEDL": "METALS", "COALINDIA": "MINING", "ONGC": "OIL_GAS",
    "BPCL": "OIL_GAS", "IOC": "OIL_GAS", "ADANIPORTS": "INFRA",
}


def _yf_symbol(nse_symbol: str) -> str:
    """Convert NSE symbol to yfinance format."""
    return f"{nse_symbol}.NS"


def _fetch_historical(
    symbol: str,
    period_days: int = 30,
) -> pd.DataFrame | None:
    """
    Fetch historical daily OHLCV for ISS scoring.

    Returns None on failure. Never raises — scanner must be robust.
    """
    try:
        ticker = yf.Ticker(_yf_symbol(symbol))
        end = datetime.now()
        start = end - timedelta(days=period_days + 5)
        df = ticker.history(start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))
        if df.empty or len(df) < 5:
            return None
        df.columns = [c.lower() for c in df.columns]
        return df
    except Exception as exc:
        logger.debug("Failed to fetch history for %s: %s", symbol, exc)
        return None


def _score_liquidity(df: pd.DataFrame) -> float:
    """
    Liquidity score 0–100.
    20-day avg traded value (close × volume) in ₹.
    ₹100 Cr = 100, ₹200 Cr = 100, ₹50 Cr = 50, ₹10 Cr = 10.
    """
    if df is None or len(df) < 5:
        return 0.0
    avg_traded = float((df["close"] * df["volume"]).tail(20).mean())
    cr = avg_traded / 1e7  # convert to crores
    if cr >= 200:
        return 100.0
    if cr >= 100:
        return 100.0
    if cr >= 50:
        return 50.0
    if cr >= 10:
        return 25.0
    return 0.0


def _score_atr_suitability(df: pd.DataFrame) -> float:
    """
    ATR suitability score 0–100.
    Sweet spot: daily ATR as % of price between 1.0% and 4.0%.
    We approximate 15m ATR from daily ATR / sqrt(26) bars.
    """
    if df is None or len(df) < 15:
        return 0.0
    close = float(df["close"].iloc[-1])
    high = df["high"].tail(14)
    low = df["low"].tail(14)
    prev_close = df["close"].tail(14).shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    atr14 = float(tr.mean())
    atr_pct = atr14 / close * 100.0 if close > 0 else 0.0
    # Ideal range for intraday: 1.5% – 4% daily ATR
    if 1.5 <= atr_pct <= 4.0:
        return 100.0
    if 1.0 <= atr_pct < 1.5 or 4.0 < atr_pct <= 5.0:
        return 60.0
    if 0.5 <= atr_pct < 1.0:
        return 30.0
    return 0.0


def _score_momentum(df: pd.DataFrame, nifty_df: pd.DataFrame | None) -> float:
    """
    Momentum score 0–100. 5-day return relative to Nifty50.
    Stock outperforms Nifty by ≥1% → 100. Underperforms by ≥1% → 0.
    """
    if df is None or len(df) < 6:
        return 50.0
    stock_ret = (float(df["close"].iloc[-1]) - float(df["close"].iloc[-6])) / float(df["close"].iloc[-6])
    nifty_ret = 0.0
    if nifty_df is not None and len(nifty_df) >= 6:
        nifty_ret = (float(nifty_df["close"].iloc[-1]) - float(nifty_df["close"].iloc[-6])) / float(nifty_df["close"].iloc[-6])
    rel = stock_ret - nifty_ret
    if rel >= 0.02:
        return 100.0
    if rel >= 0.01:
        return 80.0
    if rel >= 0.0:
        return 60.0
    if rel >= -0.01:
        return 40.0
    return 10.0


def _score_volume_surge(df: pd.DataFrame) -> float:
    """
    Volume surge score 0–100. Yesterday's volume vs 20-day avg.
    Ratio ≥ 2.0 → 100, ratio ≥ 1.5 → 80, ratio < 0.8 → 10.
    """
    if df is None or len(df) < 21:
        return 50.0
    avg_20 = float(df["volume"].iloc[-21:-1].mean())
    yesterday_vol = float(df["volume"].iloc[-1])
    if avg_20 <= 0:
        return 50.0
    ratio = yesterday_vol / avg_20
    if ratio >= 2.0:
        return 100.0
    if ratio >= 1.5:
        return 80.0
    if ratio >= 1.2:
        return 60.0
    if ratio >= 0.8:
        return 40.0
    return 10.0


def _score_level_setup(df: pd.DataFrame) -> float:
    """
    Level setup score 0–100. Is today's open near a key level?
    Checks proximity to PDH, PDL, and daily pivot.
    """
    if df is None or len(df) < 3:
        return 50.0
    pdh = float(df["high"].iloc[-2])
    pdl = float(df["low"].iloc[-2])
    pdclose = float(df["close"].iloc[-2])
    levels = compute_pivot_levels(pdh, pdl, pdclose)
    today_close = float(df["close"].iloc[-1])

    all_levels = [pdh, pdl, levels["pivot"], levels["r1"], levels["s1"]]
    min_dist_pct = min(abs(today_close - lvl) / today_close for lvl in all_levels if lvl > 0)
    if min_dist_pct <= 0.003:
        return 100.0
    if min_dist_pct <= 0.005:
        return 80.0
    if min_dist_pct <= 0.01:
        return 60.0
    return 30.0


def compute_iss(
    symbol: str,
    df: pd.DataFrame | None,
    nifty_df: pd.DataFrame | None,
) -> dict[str, float]:
    """
    Compute the Intraday Suitability Score (ISS) for a symbol.

    Returns:
        Dict with iss_score and all sub-scores.
    """
    liq = _score_liquidity(df)
    atr = _score_atr_suitability(df)
    mom = _score_momentum(df, nifty_df)
    vol = _score_volume_surge(df)
    lvl = _score_level_setup(df)
    # News score: default 50 (no live news data in scanner currently)
    news = 50.0

    iss = (
        0.25 * liq +
        0.20 * atr +
        0.15 * mom +
        0.20 * vol +
        0.10 * lvl +
        0.10 * news
    )

    return {
        "iss_score": round(iss, 2),
        "liquidity_score": round(liq, 2),
        "atr_pct_15m": round(atr, 2),
        "momentum_score": round(mom, 2),
        "todvol_score": round(vol, 2),
        "level_setup_score": round(lvl, 2),
        "news_score": round(news, 2),
    }


def run_morning_scan(
    conn: Any,
    top_n: int = 15,
    min_iss: float = 65.0,
    symbols: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Run the morning universe scan. Called at 8:45 AM IST.

    Scores all NSE F&O candidates and persists top-N into intraday_universe.

    Args:
        conn: Database connection.
        top_n: Max number of stocks to select.
        min_iss: Minimum ISS to qualify.
        symbols: Override candidate list (for testing).

    Returns:
        List of selected stock dicts with ISS scores.
    """
    candidates = symbols or NSE_FNO_SYMBOLS
    today = date.today().isoformat()

    logger.info("Morning scan starting: %d candidates, min_iss=%.0f", len(candidates), min_iss)

    # Fetch Nifty50 for relative momentum
    nifty_df = _fetch_historical("^NSEI", period_days=30)

    scored: list[dict[str, Any]] = []
    for sym in candidates:
        try:
            df = _fetch_historical(sym, period_days=30)
            scores = compute_iss(sym, df, nifty_df)

            if scores["iss_score"] < min_iss:
                logger.debug("[%s] ISS=%.1f < %.0f — excluded", sym, scores["iss_score"], min_iss)
                continue

            gap_type = "FLAT"
            iep_price = None
            if df is not None and len(df) >= 2:
                prev_close = float(df["close"].iloc[-2])
                today_open = float(df["close"].iloc[-1])
                gap_type = classify_gap(today_open, prev_close)

            row = {
                "date": today,
                "symbol": sym,
                "gap_type": gap_type,
                "iep_price": iep_price,
                **scores,
            }
            scored.append(row)
        except Exception as exc:
            logger.warning("[%s] Scan error: %s", sym, exc)
            continue

    # Sort by ISS descending, take top_n
    scored.sort(key=lambda x: x["iss_score"], reverse=True)
    selected = scored[:top_n]

    # Persist to DB
    for row in selected:
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO intraday_universe (
                    date, symbol, iss_score, liquidity_score, atr_pct_15m,
                    momentum_score, todvol_score, level_setup_score, news_score,
                    gap_type, iep_price
                ) VALUES (
                    :date, :symbol, :iss_score, :liquidity_score, :atr_pct_15m,
                    :momentum_score, :todvol_score, :level_setup_score, :news_score,
                    :gap_type, :iep_price
                )
                """,
                row,
            )
        except Exception as exc:
            logger.warning("[%s] DB persist error: %s", row["symbol"], exc)
    conn.commit()

    logger.info(
        "Morning scan complete: %d stocks selected (of %d scored)",
        len(selected), len(scored)
    )
    return selected


def get_today_universe(conn: Any) -> list[dict[str, Any]]:
    """Return today's selected intraday universe from the database."""
    today = date.today().isoformat()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM intraday_universe WHERE date = ? ORDER BY iss_score DESC",
        (today,),
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]
