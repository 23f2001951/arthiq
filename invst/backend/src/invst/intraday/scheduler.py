"""
IIM — Background Scheduler.

Market-hours job scheduler using APScheduler.

CRITICAL CONSTRAINT: This scheduler MUST run in a single-worker process.
Start the server with: uvicorn app:app --workers 1

If you ever scale to multiple workers, migrate to Celery Beat + Redis.
A startup warning is logged if worker count > 1 is detected.

Schedule (all times IST):
  08:45 AM  → run_morning_universe_scan()    (select today's stocks)
  09:15 AM  → load_warmup_bars()             (seed EMA50 from prior session)
  09:30 AM  → start_live_feed()              (begin data collection)
  Every 1m  → update_candles_and_check()     (core signal loop, market hours only)
  03:00 PM  → disable_new_signals()          (no new entries in last 30 min)
  03:35 PM  → expire_active_signals()        (EOD expire all pending)
  03:45 PM  → run_eod_accuracy_report()      (compute day metrics)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger("invst.intraday.scheduler")

IST = timezone(timedelta(hours=5, minutes=30))

# Module-level state (single-worker safe)
_feed: Any = None           # BaseDataFeed instance
_signal_enabled: bool = False
_conn_factory: Any = None   # callable returning a DB connection
_universe: list[str] = []   # today's selected symbols

# Suspend table (strategy_id → bool)
_suspended_strategies: dict[str, bool] = {}


def _now_ist() -> datetime:
    return datetime.now(IST)


def _is_market_hours() -> bool:
    """Return True if current IST time is within NSE trading hours."""
    now = _now_ist().time()
    from datetime import time
    return time(9, 15) <= now <= time(15, 30)


def get_feed_status() -> dict[str, Any]:
    """Expose the configured feed mode so clients never label delayed data as live."""
    mode = getattr(_feed, "mode", None) if _feed is not None else None
    try:
        receiving = bool(_feed and _feed.is_live())
    except Exception:
        receiving = False
    return {
        "mode": mode,
        "receiving": receiving,
        "signal_generation_enabled": _signal_enabled,
        "market_hours": _is_market_hours(),
        "universe_size": len(_universe),
    }


# ---------------------------------------------------------------------------
# Job functions
# ---------------------------------------------------------------------------

def job_morning_scan() -> None:
    """8:45 AM: Score and select today's intraday universe."""
    global _universe
    from invst.intraday.universe_scanner import run_morning_scan
    try:
        conn = _conn_factory()
        selected = run_morning_scan(conn)
        _universe = [s["symbol"] for s in selected]
        conn.close()
        logger.info("Morning scan done: %d stocks selected: %s", len(_universe), _universe)
    except Exception as exc:
        logger.exception("Morning scan job failed: %s", exc)


def job_load_warmup_bars() -> None:
    """9:15 AM: Load prior-session bars to seed indicators (EMA50 etc.)."""
    global _feed
    if _feed is None or not _universe:
        return
    try:
        if hasattr(_feed, "load_warmup_bars"):
            for sym in _universe:
                _feed.load_warmup_bars(sym)
            logger.info("Warmup bars loaded for %d symbols.", len(_universe))
        # Also load Nifty50 for regime detection
        if hasattr(_feed, "load_warmup_bars"):
            _feed.load_warmup_bars("^NSEI")
    except Exception as exc:
        logger.exception("Warmup bar load failed: %s", exc)


def job_start_feed() -> None:
    """9:30 AM: Start the live data feed for today's universe."""
    global _feed, _signal_enabled
    if _feed is None or not _universe:
        logger.warning("Feed not initialised or universe empty — cannot start feed.")
        return
    try:
        # Add Nifty50 to subscription for regime detection
        symbols_to_stream = list(set(_universe + ["NIFTY50", "^NSEI"]))
        _feed.start(symbols_to_stream)
        logger.info("Live feed started for %d symbols.", len(symbols_to_stream))
    except Exception as exc:
        logger.exception("Feed start failed: %s", exc)


def job_enable_signals() -> None:
    """9:45 AM: Open signal generation window (after opening range is locked)."""
    global _signal_enabled
    _signal_enabled = True
    logger.info("Signal generation ENABLED (9:45 AM IST).")


def job_signal_loop() -> None:
    """
    Every 1 minute during market hours: check for new closed 15m bars
    and run signal engine. Core real-time loop.
    """
    if not _signal_enabled or _feed is None or not _universe:
        return
    if not _is_market_hours():
        return

    from invst.intraday.indicators import (
        apply_all_indicators, compute_pivot_levels, classify_gap,
    )
    from invst.intraday.regime_detector import classify_regime, Regime
    from invst.intraday.signal_engine import check_trend_pullback, check_intraday_breakout
    from invst.intraday.sl_target_engine import compute_sl_target, estimate_remaining_range
    from invst.intraday.signal_validator import validate_signal, compute_position_size
    from invst.intraday.signal_store import (
        get_active_signals, persist_signal, persist_event,
    )
    from invst.intraday.accuracy_tracker import is_strategy_suspended
    from invst.intraday.todvol import get_todvol_ratio
    from invst.intraday.universe_scanner import NSE_SECTOR_MAP
    from invst.intraday.indicators import resample_to_1h

    now = _now_ist()
    conn = _conn_factory()

    try:
        active_signals = get_active_signals(conn, mode=_feed.mode)

        # Get Nifty50 candles for regime detection
        nifty_df_raw = _feed.get_candles("^NSEI", n=120)
        if nifty_df_raw.empty:
            return

        # Fetch India VIX (from ticker tape cache or yfinance)
        india_vix = _fetch_india_vix()

        # Apply indicators to Nifty50
        nifty_df = apply_all_indicators(nifty_df_raw)
        regime_state = classify_regime(nifty_df, india_vix)

        if regime_state.regime in (Regime.AVOID, Regime.AMBIGUOUS, Regime.RANGING):
            logger.debug("Regime %s — skipping signal check.", regime_state.regime)
            return

        for sym in _universe:
            try:
                # Check if this strategy is auto-suspended
                if _suspended_strategies.get("TREND_PULLBACK_v1") or \
                   _suspended_strategies.get("INTRADAY_BREAKOUT_v1"):
                    logger.warning("Strategy suspended — skipping %s.", sym)
                    continue

                df_raw = _feed.get_candles(sym, n=120)
                if len(df_raw) < 30:
                    continue

                # Apply indicators
                df = apply_all_indicators(df_raw)
                df_1h = resample_to_1h(df)

                cur_bar = df.iloc[-1]
                slot = cur_bar.name.strftime("%H:%M")

                todvol = get_todvol_ratio(conn, sym, slot, float(cur_bar["volume"]))
                vwap = float(cur_bar.get("vwap", 0.0) or 0.0)
                atr14 = float(cur_bar.get("atr14", 0.0) or 0.0)

                # Previous day levels (from DB or candle history)
                pdh, pdl, pdclose = _get_prev_day_levels(df_raw)
                pivot_levels = compute_pivot_levels(pdh, pdl, pdclose)

                # ORB levels (bars from 9:15–9:44)
                orb_high, orb_low = _get_orb_levels(df_raw)

                remaining_range = estimate_remaining_range(df, now.replace(tzinfo=None))
                daily_atr_approx = atr14 * 26

                # Try TREND_PULLBACK
                for strategy_fn, strategy_id in [
                    (check_trend_pullback, "TREND_PULLBACK_v1"),
                    (check_intraday_breakout, "INTRADAY_BREAKOUT_v1"),
                ]:
                    if is_strategy_suspended(conn, strategy_id, mode=_feed.mode):
                        _suspended_strategies[strategy_id] = True
                        continue

                    kwargs: dict[str, Any] = dict(
                        symbol=sym, df_15m=df, df_1h=df_1h,
                        regime_state=regime_state, vwap=vwap,
                        pivot_levels=pivot_levels, todvol_ratio=todvol,
                        prev_day_high=pdh, prev_day_low=pdl,
                    )
                    if strategy_id == "INTRADAY_BREAKOUT_v1":
                        kwargs["orb_high"] = orb_high
                        kwargs["orb_low"] = orb_low

                    signal = strategy_fn(**kwargs)
                    if signal is None:
                        continue

                    # Compute SL/Target
                    next_open = float(df.iloc[-1]["close"])  # approximation; real = next bar open
                    sl_result = compute_sl_target(
                        entry_price=next_open,
                        direction=signal.signal_type,
                        atr_15m=atr14,
                        sl_atr_adjustment=regime_state.sl_atr_adjustment,
                        now=now.replace(tzinfo=None),
                        expected_remaining_range=remaining_range,
                        daily_atr=daily_atr_approx,
                    )

                    # Full validation pipeline
                    account_capital = _get_account_capital()
                    valid, reasons = validate_signal(
                        signal=signal,
                        sl_result=sl_result,
                        df_15m=df,
                        active_signals=active_signals,
                        sector_map=NSE_SECTOR_MAP,
                        account_capital=account_capital,
                        current_day_pnl_r=_get_day_pnl_r(active_signals),
                    )

                    if not valid:
                        logger.debug("[%s] Signal rejected: %s", sym, reasons)
                        continue

                    # Sizing
                    sizing = compute_position_size(
                        account_capital=account_capital,
                        sl_distance=sl_result.sl_distance,
                    )

                    import json
                    signal_dict = {
                        "strategy_id": strategy_id,
                        "strategy_ver": "1.0.0",
                        "mode": _feed.mode,
                        "symbol": sym,
                        "exchange": "NSE",
                        "signal_type": signal.signal_type,
                        "signal_candle_time": cur_bar.name.isoformat(),
                        "entry_time": now.isoformat(),
                        "timeframe": "15m",
                        "entry_price": sl_result.entry_price,
                        "sl_price": sl_result.sl_price,
                        "target_1": sl_result.target_1,
                        "target_2": sl_result.target_2,
                        "sl_distance": sl_result.sl_distance,
                        "reward_risk": sl_result.reward_risk,
                        "atr_at_signal": sl_result.atr_at_signal,
                        "confidence_score": signal.confidence_score,
                        "pillars_met": json.dumps(signal.pillars_met),
                        "regime": signal.regime,
                        "vwap_at_signal": signal.vwap_at_signal,
                        "pivot_at_signal": signal.pivot_at_signal,
                        "pdh": signal.pdh,
                        "pdl": signal.pdl,
                        "todvol_ratio": signal.todvol_ratio,
                        "rationale": signal.rationale,
                        "feature_snapshot": json.dumps(signal.feature_snapshot),
                        "feasibility_ok": 1,
                    }
                    signal_id = persist_signal(conn, signal_dict)
                    conn.commit()

                    logger.info(
                        "🟢 SIGNAL FIRED: id=%d %s %s %s entry=%.2f SL=%.2f T1=%.2f "
                        "shares=%d capital_at_risk=₹%.0f",
                        signal_id, sym, signal.signal_type, strategy_id,
                        sl_result.entry_price, sl_result.sl_price, sl_result.target_1,
                        sizing["shares"], sizing["capital_at_risk"],
                    )

                    # Broadcast to SSE clients
                    _broadcast_event({
                        "type": "SIGNAL_NEW",
                        "data": {**signal_dict, "id": signal_id, "sizing": sizing},
                    })

            except Exception as exc:
                logger.exception("[%s] Signal loop error: %s", sym, exc)

    finally:
        conn.close()


def job_disable_signals() -> None:
    """3:00 PM: No new signal entries in the last 30 min before close."""
    global _signal_enabled
    _signal_enabled = False
    logger.info("Signal generation DISABLED (3:00 PM IST — last 30 min window).")


def job_expire_signals() -> None:
    """3:35 PM: Auto-expire all signals still in PENDING/ENTRY_FILLED state."""
    from invst.intraday.signal_store import get_active_signals, persist_event
    conn = _conn_factory()
    try:
        active = get_active_signals(conn, mode=_feed.mode if _feed else "paper")
        for sig in active:
            persist_event(
                conn, signal_id=sig["id"],
                event_type="EXPIRED",
                event_time=_now_ist().replace(tzinfo=None),
                note="Auto-expired at EOD (3:35 PM IST).",
            )
        conn.commit()
        logger.info("EOD: expired %d active signals.", len(active))
    except Exception as exc:
        logger.exception("Signal expiry job failed: %s", exc)
    finally:
        conn.close()


def job_eod_accuracy() -> None:
    """3:45 PM: Compute and log end-of-day accuracy report."""
    from invst.intraday.accuracy_tracker import run_eod_accuracy_report
    conn = _conn_factory()
    try:
        mode = _feed.mode if _feed else "paper"
        reports = run_eod_accuracy_report(conn, mode=mode)
        for sid, report in reports.items():
            if report.auto_disabled:
                _suspended_strategies[sid] = True
                logger.warning("Strategy %s auto-disabled after EOD review.", sid)
    except Exception as exc:
        logger.exception("EOD accuracy job failed: %s", exc)
    finally:
        conn.close()


def job_daily_market_data() -> None:
    """18:00 IST: ingest the official NSE end-of-day equity bhavcopy."""
    if _conn_factory is None:
        return
    conn = None
    try:
        from invst.ingestion.nse_bhavcopy import ingest_nse_bhavcopy

        trade_date = _now_ist().date()
        conn = _conn_factory()
        existing = conn.execute(
            "SELECT 1 FROM daily_prices WHERE trade_date = ? AND source = 'nse_bhavcopy' LIMIT 1",
            (trade_date.isoformat(),),
        ).fetchone()
        if existing:
            logger.info("NSE EOD prices already ingested for %s.", trade_date.isoformat())
            return

        count = ingest_nse_bhavcopy(conn, trade_date=trade_date)
        if count:
            logger.info("NSE EOD price refresh stored %d rows for %s.", count, trade_date.isoformat())
        else:
            logger.warning("NSE EOD price refresh returned no rows for %s.", trade_date.isoformat())
    except Exception as exc:
        logger.exception("NSE EOD price refresh failed: %s", exc)
    finally:
        if conn is not None:
            conn.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch_india_vix() -> float:
    """Fetch current India VIX from yfinance (cached in ticker tape)."""
    try:
        import yfinance as yf
        t = yf.Ticker("^INDIAVIX")
        fi = getattr(t, "fast_info", None)
        if fi:
            lp = getattr(fi, "last_price", None)
            if lp:
                return float(lp)
    except Exception:
        pass
    return 14.0  # Safe default


def _get_prev_day_levels(df: Any) -> tuple[float, float, float]:
    """Extract prev-day H/L/C from the loaded candle history."""
    if df is None or len(df) < 2:
        return 0.0, 0.0, 0.0
    import pandas as pd
    if hasattr(df.index, "date"):
        today = df.index[-1].date()
        prev = df[df.index.map(lambda t: t.date()) < today]
        if prev.empty:
            return 0.0, 0.0, 0.0
        return float(prev["high"].max()), float(prev["low"].min()), float(prev["close"].iloc[-1])
    return 0.0, 0.0, 0.0


def _get_orb_levels(df: Any) -> tuple[float | None, float | None]:
    """Extract Opening Range High/Low from 9:15–9:44 AM bars."""
    try:
        from datetime import time
        orb = df[df.index.map(lambda t: t.time() < time(9, 45))]
        if orb.empty:
            return None, None
        return float(orb["high"].max()), float(orb["low"].min())
    except Exception:
        return None, None


def _get_account_capital() -> float:
    """Return configured account capital (₹). Default 5,00,000."""
    try:
        return float(os.environ.get("IIM_ACCOUNT_CAPITAL", "500000"))
    except (TypeError, ValueError):
        return 500000.0


def _get_day_pnl_r(active_signals: list[dict]) -> float:
    """Sum net_pnl_r across active signals for daily halt check."""
    return sum(float(s.get("net_pnl_r") or 0.0) for s in active_signals)


# ---------------------------------------------------------------------------
# SSE event broadcast
# ---------------------------------------------------------------------------

_sse_queue: list[dict] = []


def _broadcast_event(event: dict) -> None:
    """Queue an SSE event for delivery to connected clients."""
    _sse_queue.append(event)
    if len(_sse_queue) > 500:
        _sse_queue.pop(0)


def pop_pending_events() -> list[dict]:
    """Drain and return all pending SSE events."""
    events = list(_sse_queue)
    _sse_queue.clear()
    return events


# ---------------------------------------------------------------------------
# Scheduler setup (APScheduler, single-worker)
# ---------------------------------------------------------------------------

def create_scheduler(conn_factory: Any, feed: Any) -> Any:
    """
    Create and configure the APScheduler instance.

    Args:
        conn_factory: Callable returning a DB connection.
        feed: BaseDataFeed instance.

    Returns:
        Configured BackgroundScheduler (not yet started).
    """
    global _conn_factory, _feed

    # Warn if multiple workers detected
    worker_count = int(os.environ.get("WEB_CONCURRENCY", "1"))
    if worker_count > 1:
        logger.critical(
            "⚠️  IIM Scheduler WARNING: WEB_CONCURRENCY=%d > 1. "
            "APScheduler will run duplicate jobs. "
            "Start with --workers 1 or migrate to Celery Beat.",
            worker_count,
        )

    _conn_factory = conn_factory
    _feed = feed

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.interval import IntervalTrigger
    except ImportError:
        logger.error("apscheduler not installed. Run: pip install apscheduler")
        return None

    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

    # Morning scan: 8:45 AM Mon–Fri
    scheduler.add_job(job_morning_scan, CronTrigger(
        day_of_week="mon-fri", hour=8, minute=45,
    ), id="morning_scan", name="Morning Universe Scan")

    # Load warmup bars: 9:15 AM
    scheduler.add_job(job_load_warmup_bars, CronTrigger(
        day_of_week="mon-fri", hour=9, minute=15,
    ), id="warmup_bars", name="Load Warmup Bars")

    # Start feed: 9:30 AM
    scheduler.add_job(job_start_feed, CronTrigger(
        day_of_week="mon-fri", hour=9, minute=30,
    ), id="start_feed", name="Start Live Feed")

    # Enable signals: 9:45 AM (after ORB is locked)
    scheduler.add_job(job_enable_signals, CronTrigger(
        day_of_week="mon-fri", hour=9, minute=45,
    ), id="enable_signals", name="Enable Signal Generation")

    # Core signal loop: every 1 minute, Mon–Fri
    scheduler.add_job(job_signal_loop, IntervalTrigger(
        seconds=60,
    ), id="signal_loop", name="Signal Check Loop")

    # Disable new signals: 3:00 PM
    scheduler.add_job(job_disable_signals, CronTrigger(
        day_of_week="mon-fri", hour=15, minute=0,
    ), id="disable_signals", name="Disable New Signals")

    # Expire EOD: 3:35 PM
    scheduler.add_job(job_expire_signals, CronTrigger(
        day_of_week="mon-fri", hour=15, minute=35,
    ), id="expire_signals", name="EOD Signal Expiry")

    # EOD accuracy report: 3:45 PM
    scheduler.add_job(job_eod_accuracy, CronTrigger(
        day_of_week="mon-fri", hour=15, minute=45,
    ), id="eod_accuracy", name="EOD Accuracy Report")

    # Daily official closing prices after exchange archive publication, with one retry.
    scheduler.add_job(job_daily_market_data, CronTrigger(
        day_of_week="mon-fri", hour=18, minute=0,
    ), id="daily_market_data", name="Daily NSE Closing Prices")
    scheduler.add_job(job_daily_market_data, CronTrigger(
        day_of_week="mon-fri", hour=19, minute=30,
    ), id="daily_market_data_retry", name="Retry NSE Closing Prices")

    logger.info("IIM Scheduler configured with %d jobs.", len(scheduler.get_jobs()))
    return scheduler
