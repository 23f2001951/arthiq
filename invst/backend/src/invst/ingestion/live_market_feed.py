"""Live Market Feed Ingestion Engine for Indian Equities.

Provides real-time / on-demand live quotes, macro pulse (India VIX),
financial statements, and news headlines via yfinance and RSS feeds,
with full offline fallback resilience.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import date
from typing import Any

from invst.ingestion.news_rss import fetch_google_news_rss, ingest_news_records
from invst.ingestion.yfinance_prices import normalize_symbol_for_yf

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
except ImportError:
    yf = None


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Safely convert value to float, handling None, NaN, and TypeError."""
    if val is None:
        return default
    try:
        f = float(val)
        import math
        return default if math.isnan(f) else f
    except (ValueError, TypeError):
        return default


def fetch_live_macro_pulse(
    timeout: float = 5.0,
    fetch_live: bool = True,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Fetch macroeconomic regime indicators (India VIX, Nifty 50, USD/INR).

    Attempts live quote via yfinance, falling back gracefully to local benchmarks or safe defaults.
    """
    pulse = {
        "asof_date": date.today().isoformat(),
        "india_vix": 14.5,
        "nifty_50": 24500.0,
        "usd_inr": 83.5,
        "regime": "NEUTRAL",
        "regime_description": "Normal market volatility. Standard scenario weights apply.",
        "is_live": False,
    }

    if conn is not None:
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT close, trade_date
                FROM daily_prices
                WHERE symbol IN ('NIFTY500', 'NIFTY50', '^NSEI')
                ORDER BY trade_date DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()
            if row and row[0]:
                pulse["nifty_50"] = round(float(row[0]), 2)
                pulse["asof_date"] = str(row[1] or pulse["asof_date"])
        except Exception:
            pass

    if fetch_live and yf is not None:
        try:
            # Fetch India VIX
            vix_ticker = yf.Ticker("^INDIAVIX")
            vix_fast = getattr(vix_ticker, "fast_info", None)
            if vix_fast:
                v_p = _safe_float(getattr(vix_fast, "last_price", None), 0.0)
                if v_p > 0:
                    pulse["india_vix"] = round(v_p, 2)
                    pulse["is_live"] = True
        except Exception as e:
            logger.debug(f"Could not fetch live India VIX ({e}). Using default.")

        try:
            # Fetch Nifty 50
            nifty_ticker = yf.Ticker("^NSEI")
            nifty_fast = getattr(nifty_ticker, "fast_info", None)
            if nifty_fast:
                n_p = _safe_float(getattr(nifty_fast, "last_price", None), 0.0)
                if n_p > 0:
                    pulse["nifty_50"] = round(n_p, 2)
                    pulse["is_live"] = True
        except Exception as e:
            logger.debug(f"Could not fetch live Nifty 50 ({e}). Using default.")

    # Determine regime based on VIX
    vix = pulse["india_vix"]
    if vix >= 20.0:
        pulse["regime"] = "HIGH_VOLATILITY"
        pulse["regime_description"] = (
            f"Elevated market fear (India VIX {vix:.1f} >= 20.0). Bear scenario probability expanded to 35%."
        )
    elif vix <= 12.5:
        pulse["regime"] = "EXPANSIONARY"
        pulse["regime_description"] = (
            f"Complacent / expansionary market (India VIX {vix:.1f} <= 12.5). Bull scenario probability expanded to 30%."
        )
    else:
        pulse["regime"] = "NEUTRAL"
        pulse["regime_description"] = (
            f"Balanced market volatility (India VIX {vix:.1f}). Standard baseline probabilities apply."
        )

    return pulse


def is_etf_ticker(symbol: str) -> bool:
    """Identify if ticker is an Exchange Traded Fund or Index product."""
    clean = symbol.upper().replace(".NS", "").replace(".BO", "")
    if clean.endswith("BEES") or clean.endswith("ETF") or clean.endswith("INDEX") or clean.startswith("SETF"):
        return True
    known_etfs = {
        "NIFTYBEES", "BANKBEES", "GOLDBEES", "SILVERBEES", "ITBEES", "JUNIORBEES",
        "MON100", "CPSEETF", "BHARAT22", "HDFCBKETF", "AUTOBEES", "PHARMABEES",
        "MID150BEES", "MAFANG", "MOM50", "NV20BEES", "SETFNIF50", "SETFNN50",
    }
    return clean in known_etfs


def fetch_live_ticker_snapshot(
    symbol: str,
    timeout: float = 6.0,
    conn: sqlite3.Connection | None = None,
    fetch_live: bool = True,
) -> dict[str, Any]:
    """Fetch live market quote, technicals, key ratios, and news for any stock symbol.

    Supports universal NSE/BSE tickers (e.g. 'TCS', 'RELIANCE', 'ZOMATO', 'NIFTYBEES').
    If offline or ticker unavailable, falls back gracefully to latest database records or baseline estimates.
    """
    clean_sym = symbol.strip().upper().replace(".NS", "").replace(".BO", "")
    today_str = date.today().isoformat()
    is_etf = is_etf_ticker(clean_sym)

    default_name = clean_sym
    default_sec = "index_etf" if is_etf else "diversified"
    if clean_sym in ("GOLDBEES", "SILVERBEES", "GOLDIETF", "SILVERIETF"):
        default_sec = "commodity_etf"
        default_name = f"Nippon India ETF {clean_sym.replace('BEES', ' BeES').replace('IETF', ' ETF')}"
    elif is_etf and "NIFTY" in clean_sym:
        default_name = "Nippon India Nifty 50 BeES ETF"
    elif is_etf and "BANK" in clean_sym:
        default_name = "Nippon India ETF Bank BeES"

    snapshot: dict[str, Any] = {
        "symbol": clean_sym,
        "asof_date": today_str,
        "company_name": default_name,
        "sector": default_sec,
        "current_price": 0.0,
        "change_pct": 0.0,
        "prev_close": 0.0,
        "open": 0.0,
        "high": 0.0,
        "low": 0.0,
        "volume": 0,
        "high_52w": 0.0,
        "low_52w": 0.0,
        "dma_20": 0.0,
        "dma_50": 0.0,
        "dma_200": 0.0,
        "rsi_14": 52.0,
        "trend_phase": "NEUTRAL_RANGE",
        "market_cap_cr": 0.0,
        "pe_ratio": 22.0 if not is_etf else 22.5,
        "pb_ratio": 3.0,
        "roe": 15.0 if not is_etf else 15.5,
        "roce": 16.0 if not is_etf else 16.5,
        "debt_to_equity": 0.3 if not is_etf else 0.0,
        "cfo_pat_ratio": 0.85 if not is_etf else 1.0,
        "promoter_pledge_pct": 0.0,
        "altman_z": 3.2 if not is_etf else 8.5,
        "growth_cagr_3y": 12.0 if not is_etf else 13.0,
        "is_etf": is_etf,
        "is_live": False,
        "found": False,
        "headlines": [],
    }

    # 1. Try fetching live data via yfinance if fetch_live is True
    yf_succeeded = False
    if fetch_live and yf is not None:
        try:
            ticker_ns = normalize_symbol_for_yf(clean_sym)
            ticker = yf.Ticker(ticker_ns)
            fast_info = getattr(ticker, "fast_info", None)

            price = _safe_float(getattr(fast_info, "last_price", None), 0.0) if fast_info else 0.0
            if price > 0:
                snapshot["current_price"] = round(price, 2)
                prev = _safe_float(getattr(fast_info, "previous_close", None), price)
                snapshot["prev_close"] = round(prev, 2)
                if snapshot["prev_close"] > 0:
                    snapshot["change_pct"] = round(
                        ((price - snapshot["prev_close"]) / snapshot["prev_close"]) * 100.0, 2
                    )
                snapshot["high_52w"] = round(_safe_float(getattr(fast_info, "year_high", None), price * 1.2), 2)
                snapshot["low_52w"] = round(_safe_float(getattr(fast_info, "year_low", None), price * 0.8), 2)
                snapshot["market_cap_cr"] = round(_safe_float(getattr(fast_info, "market_cap", None), 0.0) / 1e7, 1)
                snapshot["open"] = round(_safe_float(getattr(fast_info, "open", None), price), 2)
                snapshot["high"] = round(_safe_float(getattr(fast_info, "day_high", None), price), 2)
                snapshot["low"] = round(_safe_float(getattr(fast_info, "day_low", None), price), 2)
                snapshot["volume"] = int(_safe_float(getattr(fast_info, "last_volume", None), 0.0))
                yf_succeeded = True

            # If fast_info didn't have price, try history
            if snapshot["current_price"] == 0.0:
                h_short = ticker.history(period="5d")
                if not h_short.empty and "Close" in h_short:
                    closes_s = h_short["Close"].dropna()
                    if len(closes_s) > 0:
                        p_val = float(closes_s.iloc[-1])
                        snapshot["current_price"] = round(p_val, 2)
                        snapshot["prev_close"] = round(float(closes_s.iloc[-2]) if len(closes_s) > 1 else p_val, 2)
                        if snapshot["prev_close"] > 0:
                            snapshot["change_pct"] = round(
                                ((p_val - snapshot["prev_close"]) / snapshot["prev_close"]) * 100.0, 2
                            )
                        yf_succeeded = True

            # Attempt historical technicals for moving averages & RSI
            hist = ticker.history(period="1y")
            if not hist.empty and "Close" in hist:
                closes = hist["Close"].dropna()
                if len(closes) >= 20:
                    snapshot["dma_20"] = round(float(closes.iloc[-20:].mean()), 2)
                if len(closes) >= 50:
                    snapshot["dma_50"] = round(float(closes.iloc[-50:].mean()), 2)
                if len(closes) >= 200:
                    snapshot["dma_200"] = round(float(closes.iloc[-200:].mean()), 2)
                if snapshot["current_price"] == 0.0 and len(closes) > 0:
                    snapshot["current_price"] = round(float(closes.iloc[-1]), 2)
                    yf_succeeded = True

                # RSI 14 calculation
                if len(closes) >= 15:
                    delta = closes.diff().dropna()
                    gain = delta.clip(lower=0)
                    loss = -delta.clip(upper=0)
                    avg_g = gain.iloc[-14:].mean()
                    avg_l = loss.iloc[-14:].mean()
                    if avg_l == 0:
                        snapshot["rsi_14"] = 100.0
                    else:
                        rs = avg_g / avg_l
                        snapshot["rsi_14"] = round(100.0 - (100.0 / (1.0 + rs)), 1)

            # Classify Trend Phase
            p = snapshot["current_price"]
            d50 = snapshot["dma_50"]
            d200 = snapshot["dma_200"]
            if d50 > 0 and d200 > 0:
                if p >= d50 and d50 >= d200:
                    snapshot["trend_phase"] = "BULLISH_MARKUP"
                elif p < d50 and p >= d200:
                    snapshot["trend_phase"] = "PULLBACK_IN_UPTREND"
                elif p >= d50 and d50 < d200:
                    snapshot["trend_phase"] = "ACCUMULATION_BASE"
                elif p < d50 and d50 < d200:
                    snapshot["trend_phase"] = "BEARISH_MARKDOWN"
                else:
                    snapshot["trend_phase"] = "NEUTRAL_RANGE"

            # Extract info metrics if available
            info = getattr(ticker, "info", {}) or {}
            if isinstance(info, dict) and info:
                qtype = str(info.get("quoteType", "")).upper()
                if qtype in ("ETF", "MUTUALFUND"):
                    snapshot["is_etf"] = True
                    is_etf = True
                    if snapshot["sector"] == "diversified":
                        snapshot["sector"] = "index_etf"

                snapshot["company_name"] = info.get("shortName") or info.get("longName") or snapshot["company_name"]
                if not is_etf and info.get("sector"):
                    snapshot["sector"] = (info.get("sector")).lower().replace(" ", "_")

                pe = info.get("trailingPE") or info.get("forwardPE")
                if pe and float(pe) > 0:
                    snapshot["pe_ratio"] = round(float(pe), 1)
                pb = info.get("priceToBook")
                if pb and float(pb) > 0:
                    snapshot["pb_ratio"] = round(float(pb), 2)
                roe = info.get("returnOnEquity")
                if roe and float(roe) > 0:
                    snapshot["roe"] = round(float(roe) * 100.0, 1)
                de = info.get("debtToEquity")
                if de is not None:
                    snapshot["debt_to_equity"] = round(float(de) / 100.0, 2)

            snapshot["is_live"] = yf_succeeded
        except Exception as e:
            logger.debug(f"Live yfinance snapshot error for {clean_sym}: {e}")

    # Upsert into DB if live data was successfully obtained
    if yf_succeeded and snapshot["current_price"] > 0 and conn is not None:
        try:
            ingest_live_ticker_to_db(conn, clean_sym, snapshot=snapshot)
        except Exception as e:
            logger.debug(f"Auto-ingest live price to DB failed for {clean_sym}: {e}")

    # 2. If offline or missing price, fallback to database records
    if conn and (not yf_succeeded or snapshot["current_price"] == 0.0):
        cur = conn.cursor()
        cur.execute(
            """
            SELECT close, open, high, low, volume, trade_date
            FROM daily_prices
            WHERE symbol = ?
            ORDER BY trade_date DESC
            LIMIT 1
            """,
            (clean_sym,),
        )
        row = cur.fetchone()
        if row:
            snapshot["current_price"] = float(row[0])
            snapshot["open"] = float(row[1] or row[0])
            snapshot["high"] = float(row[2] or row[0])
            snapshot["low"] = float(row[3] or row[0])
            snapshot["volume"] = int(row[4] or 0)
            snapshot["asof_date"] = row[5]

        # Check fundamentals in DB
        cur.execute(
            """
            SELECT metric, value
            FROM fundamentals_quarterly
            WHERE symbol = ?
            ORDER BY period_end DESC
            LIMIT 30
            """,
            (clean_sym,),
        )
        fund_rows = cur.fetchall()
        for m_name, m_val in fund_rows:
            if m_name == "roe":
                snapshot["roe"] = float(m_val)
            elif m_name == "roce":
                snapshot["roce"] = float(m_val)
            elif m_name == "pe":
                snapshot["pe_ratio"] = float(m_val)
            elif m_name == "pb":
                snapshot["pb_ratio"] = float(m_val)
            elif m_name == "debt_to_equity":
                snapshot["debt_to_equity"] = float(m_val)
            elif m_name == "cagr":
                snapshot["growth_cagr_3y"] = float(m_val)

    # 3. Fetch latest live or DB news headlines
    if fetch_live:
        try:
            news_items = fetch_google_news_rss(clean_sym)
            if news_items:
                snapshot["headlines"] = news_items[:5]
        except Exception as e:
            logger.debug(f"Could not fetch news headlines for {clean_sym}: {e}")

    if not snapshot["headlines"] and conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT headline, sentiment_score, source, published_at
            FROM news_sentiment
            WHERE symbol = ?
            ORDER BY published_at DESC
            LIMIT 5
            """,
            (clean_sym,),
        )
        snapshot["headlines"] = [
            {
                "headline": r[0],
                "sentiment_score": r[1] or 0.0,
                "source": r[2] or "Archive",
                "published_at": r[3],
            }
            for r in cur.fetchall()
        ]

    # Mark whether ticker was actually found (live feed or database records)
    snapshot["found"] = bool(yf_succeeded or (snapshot["current_price"] > 0.0))

    return snapshot


def ingest_live_ticker_to_db(
    conn: sqlite3.Connection,
    symbol: str,
    snapshot: dict[str, Any] | None = None,
) -> bool:
    """Upsert live market snapshot data for a symbol into local database."""
    if snapshot is None:
        snapshot = fetch_live_ticker_snapshot(symbol, conn=conn)

    clean_sym = snapshot["symbol"]
    trade_date = snapshot.get("asof_date") or date.today().isoformat()
    price = snapshot["current_price"]

    # 1. Upsert into daily_prices
    conn.execute(
        """
        INSERT OR REPLACE INTO daily_prices (
            symbol, trade_date, open, high, low, close, adj_close, volume, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            clean_sym,
            trade_date,
            snapshot.get("open") or price,
            snapshot.get("high") or price,
            snapshot.get("low") or price,
            price,
            price,
            snapshot.get("volume", 10000),
            "live_feed" if snapshot.get("is_live") else "cached",
        ),
    )

    # 2. Ingest any new headlines into news_sentiment
    if snapshot.get("headlines"):
        records_to_ingest = [
            {
                "headline_id": h.get("headline_id") or f"live_{clean_sym}_{abs(hash(h['headline']))}",
                "symbol": clean_sym,
                "published_at": h.get("published_at") or trade_date,
                "headline": h["headline"],
                "source": h.get("source", "Google News"),
                "sentiment_score": h.get("sentiment_score", 0.0),
                "model_version": "live_v1",
            }
            for h in snapshot["headlines"]
        ]
        ingest_news_records(conn, records_to_ingest)

    # 3. Upsert live fundamental metrics if present
    fund_metrics = [
        ("pe_ttm", snapshot.get("pe_ratio")),
        ("pb", snapshot.get("pb_ratio")),
        ("roe", snapshot.get("roe")),
        ("roce", snapshot.get("roce")),
        ("debt_to_equity", snapshot.get("debt_to_equity")),
        ("cfo_pat_ratio", snapshot.get("cfo_pat_ratio")),
        ("promoter_pledge_pct", snapshot.get("promoter_pledge_pct")),
        ("altman_z", snapshot.get("altman_z")),
        ("revenue_growth_3yr", snapshot.get("growth_cagr_3y")),
    ]
    for m_name, m_val in fund_metrics:
        if m_val is not None:
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO fundamentals_quarterly (
                        symbol, period_end, disclosed_at, metric, value, unit, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (clean_sym, trade_date, trade_date, m_name, float(m_val), "ratio", "live_feed"),
                )
            except Exception as ex:
                logger.debug(f"Could not persist fundamental {m_name} for {clean_sym}: {ex}")

    conn.commit()
    logger.info(f"Successfully ingested live snapshot for {clean_sym} (Price: ₹{price:.2f})")
    return True
