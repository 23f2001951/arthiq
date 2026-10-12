"""
IIM — FastAPI Route Handlers.

All intraday endpoints. SSE stream for live signal push.
Uses the same get_db() dependency as the existing routes.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from invst.api.intraday_schemas import (
    AccuracyReportResponse,
    CandleSchema,
    IntradayChartResponse,
    IntradaySignalSchema,
    IntradaySignalsResponse,
    IntradayStockItem,
    IntradayUniverseResponse,
    RegimeResponse,
    SignalOutcomeFeedbackRequest,
)
from invst.intraday.accuracy_tracker import compute_accuracy_report
from invst.intraday.indicators import compute_pivot_levels
from invst.intraday.regime_detector import classify_regime, Regime
from invst.intraday.signal_store import (
    get_active_signals,
    get_today_signals,
    get_signal_history,
    persist_event,
    run_intraday_migration,
)
from invst.intraday.universe_scanner import get_today_universe

logger = logging.getLogger("invst.api.intraday")
router = APIRouter(prefix="/api/v1/intraday", tags=["Intraday IIM"])


@router.get("/status")
def get_intraday_status():
    """Return scheduler mode and market-session availability without inventing quotes."""
    from invst.intraday.scheduler import get_feed_status
    return get_feed_status()


# ---------------------------------------------------------------------------
# DB dependency — reuse existing pattern
# ---------------------------------------------------------------------------

def _get_db_dep():
    """Import lazily to avoid circular imports at module load."""
    from invst.api.routes import get_db
    return get_db


# ---------------------------------------------------------------------------
# Ensure schema exists on first access
# ---------------------------------------------------------------------------

_migration_done = False


def _ensure_migration(conn) -> None:
    global _migration_done
    if not _migration_done:
        run_intraday_migration(conn)
        _migration_done = True


# ---------------------------------------------------------------------------
# GET /api/v1/intraday/universe
# ---------------------------------------------------------------------------

@router.get("/universe", response_model=IntradayUniverseResponse)
def get_intraday_universe(conn=Depends(_get_db_dep())):
    """Return today's ISS-scored intraday stock universe."""
    _ensure_migration(conn)
    stocks = get_today_universe(conn)
    today = date.today().isoformat()
    return IntradayUniverseResponse(
        date=today,
        count=len(stocks),
        stocks=[IntradayStockItem(**{k: s.get(k) for k in IntradayStockItem.model_fields}) for s in stocks],
    )


# ---------------------------------------------------------------------------
# GET /api/v1/intraday/signals
# ---------------------------------------------------------------------------

@router.get("/signals", response_model=IntradaySignalsResponse)
def get_intraday_signals(
    mode: str = "live",
    history: bool = False,
    conn=Depends(_get_db_dep()),
):
    """
    Return active live signals or today's full signal history.

    Query params:
      mode:    'live' | 'paper'
      history: if True, returns all signals today (including closed ones)
    """
    _ensure_migration(conn)
    raw = get_today_signals(conn, mode=mode) if history else get_active_signals(conn, mode=mode)
    signals = []
    for s in raw:
        try:
            signals.append(IntradaySignalSchema(**{
                k: s.get(k) for k in IntradaySignalSchema.model_fields
            }))
        except Exception:
            pass
    return IntradaySignalsResponse(count=len(signals), signals=signals, mode=mode)


# ---------------------------------------------------------------------------
# GET /api/v1/intraday/signals/{symbol}
# ---------------------------------------------------------------------------

@router.get("/signals/{symbol}", response_model=IntradaySignalsResponse)
def get_signals_for_symbol(
    symbol: str,
    mode: str = "live",
    conn=Depends(_get_db_dep()),
):
    """Return today's signals for a specific NSE symbol."""
    _ensure_migration(conn)
    all_today = get_today_signals(conn, mode=mode)
    filtered = [s for s in all_today if s.get("symbol", "").upper() == symbol.upper()]
    signals = []
    for s in filtered:
        try:
            signals.append(IntradaySignalSchema(**{
                k: s.get(k) for k in IntradaySignalSchema.model_fields
            }))
        except Exception:
            pass
    return IntradaySignalsResponse(count=len(signals), signals=signals, mode=mode)


# ---------------------------------------------------------------------------
# GET /api/v1/intraday/chart/{symbol}
# ---------------------------------------------------------------------------

@router.get("/chart/{symbol}", response_model=IntradayChartResponse)
def get_chart_data(
    symbol: str,
    n: int = 100,
    conn=Depends(_get_db_dep()),
):
    """
    Return OHLCV candles with pre-computed indicators for charting.
    Used by the IntradayChart.tsx component.
    """
    _ensure_migration(conn)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT candle_time, open, high, low, close, volume,
               ema21, supertrend, supertrend_dir, atr14, vwap, todvol_ratio
        FROM intraday_candles
        WHERE symbol = ? AND timeframe = '15m' AND is_warmup = 0
        ORDER BY candle_time DESC LIMIT ?
        """,
        (symbol.upper(), n),
    )
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    candles = []
    pdh, pdl, pdclose = 0.0, 0.0, 0.0
    for row in reversed(rows):  # chronological order
        d = dict(zip(cols, row))
        candles.append(CandleSchema(
            candle_time=str(d.get("candle_time", "")),
            open=float(d.get("open") or 0),
            high=float(d.get("high") or 0),
            low=float(d.get("low") or 0),
            close=float(d.get("close") or 0),
            volume=int(d.get("volume") or 0),
            ema21=d.get("ema21"),
            supertrend=d.get("supertrend"),
            supertrend_dir=d.get("supertrend_dir"),
            atr14=d.get("atr14"),
            vwap=d.get("vwap"),
            todvol_ratio=d.get("todvol_ratio"),
        ))

    # Prev-day levels from last 2 dates in candle history
    orb_high, orb_low = None, None
    if candles:
        # Approximate from candle data
        try:
            import pandas as pd
            from datetime import time as dtime
            from invst.intraday.indicators import classify_gap
            dates = sorted(set(c.candle_time[:10] for c in candles))
            if len(dates) >= 2:
                prev_date = dates[-2]
                prev_candles = [c for c in candles if c.candle_time.startswith(prev_date)]
                if prev_candles:
                    pdh = max(c.high for c in prev_candles)
                    pdl = min(c.low for c in prev_candles)
                    pdclose = prev_candles[-1].close

            today_date = dates[-1] if dates else ""
            today_candles = [c for c in candles if c.candle_time.startswith(today_date)]
            orb_candles = [c for c in today_candles if "09:1" in c.candle_time or
                           "09:2" in c.candle_time or "09:3" in c.candle_time or
                           "09:4" in c.candle_time and c.candle_time[11:16] < "09:45"]
            if orb_candles:
                orb_high = max(c.high for c in orb_candles)
                orb_low = min(c.low for c in orb_candles)
        except Exception:
            pass

    pivot_levels = compute_pivot_levels(pdh, pdl, pdclose) if pdh > 0 else {}

    return IntradayChartResponse(
        symbol=symbol.upper(),
        timeframe="15m",
        candles=candles,
        pivot_levels=pivot_levels,
        orb_high=orb_high,
        orb_low=orb_low,
        prev_day_high=pdh if pdh > 0 else None,
        prev_day_low=pdl if pdl > 0 else None,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/intraday/regime
# ---------------------------------------------------------------------------

@router.get("/regime", response_model=RegimeResponse)
def get_regime(conn=Depends(_get_db_dep())):
    """Return the current market regime classification."""
    _ensure_migration(conn)
    import yfinance as yf
    import pandas as pd
    from invst.intraday.indicators import apply_all_indicators

    # Try to get Nifty50 candles from DB first, then yfinance
    cur = conn.cursor()
    cur.execute(
        """
        SELECT candle_time, open, high, low, close, volume
        FROM intraday_candles
        WHERE symbol = 'NIFTY50' AND timeframe = '15m'
        ORDER BY candle_time DESC LIMIT 80
        """
    )
    rows = cur.fetchall()

    if rows:
        df = pd.DataFrame(rows, columns=["candle_time", "open", "high", "low", "close", "volume"])
        df.index = pd.DatetimeIndex(df["candle_time"])
        df = df.drop(columns=["candle_time"])
        nifty_df = apply_all_indicators(df.iloc[::-1])
    else:
        # Fallback: fetch from yfinance
        try:
            ticker = yf.Ticker("^NSEI")
            raw = ticker.history(period="3d", interval="15m")
            if raw is None or raw.empty:
                raise ValueError("No Nifty data")
            raw.columns = [c.lower() for c in raw.columns]
            nifty_df = apply_all_indicators(raw)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Could not fetch Nifty50 data: {exc}")

    # Get India VIX
    india_vix = 14.0
    try:
        t = yf.Ticker("^INDIAVIX")
        fi = getattr(t, "fast_info", None)
        if fi:
            lp = getattr(fi, "last_price", None)
            if lp:
                india_vix = float(lp)
    except Exception:
        pass

    regime_state = classify_regime(nifty_df, india_vix)
    return RegimeResponse(
        regime=regime_state.regime.value,
        adx=round(regime_state.adx, 2),
        india_vix=round(regime_state.india_vix, 2),
        nifty_ema21_slope=round(regime_state.nifty_ema21_slope, 4),
        sl_atr_adjustment=regime_state.sl_atr_adjustment,
        reason=regime_state.reason,
        timestamp=datetime.now().isoformat(),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/intraday/accuracy
# ---------------------------------------------------------------------------

@router.get("/accuracy", response_model=AccuracyReportResponse)
def get_accuracy(
    strategy_id: str | None = None,
    mode: str = "live",
    conn=Depends(_get_db_dep()),
):
    """Return rolling accuracy report for a strategy."""
    _ensure_migration(conn)
    report = compute_accuracy_report(conn, strategy_id=strategy_id, mode=mode)
    return AccuracyReportResponse(
        strategy_id=report.strategy_id,
        mode=report.mode,
        total_trades=report.total_trades,
        win_rate=report.win_rate,
        avg_win_r=report.avg_win_r,
        avg_loss_r=report.avg_loss_r,
        expectancy_net=report.expectancy_net,
        profit_factor=report.profit_factor,
        max_drawdown_r=report.max_drawdown_r,
        ci_lower=report.ci_lower,
        ci_upper=report.ci_upper,
        rolling_50_expectancy=report.rolling_50_expectancy,
        auto_disabled=report.auto_disabled,
        regime_breakdown={
            k: {"count": v["count"], "win_rate": v["win_rate"], "expectancy": v["expectancy"]}
            for k, v in report.regime_breakdown.items()
        },
        data_source_note=report.data_source_note,
        computed_at=report.computed_at,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/intraday/feedback
# ---------------------------------------------------------------------------

@router.post("/feedback")
def submit_signal_feedback(
    request: SignalOutcomeFeedbackRequest,
    conn=Depends(_get_db_dep()),
):
    """
    Mark a signal outcome (T1 hit, SL hit, manual exit).
    Used by the signal card's outcome-marking buttons.
    """
    _ensure_migration(conn)
    valid_types = {"T1_HIT", "T2_HIT", "SL_HIT", "MANUAL_EXIT"}
    if request.event_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event_type. Must be one of: {valid_types}",
        )

    try:
        event_id = persist_event(
            conn,
            signal_id=request.signal_id,
            event_type=request.event_type,
            event_time=datetime.now(),
            price=request.price,
            shares=request.shares,
            note=request.note or "Manual feedback from UI",
        )
        return {"success": True, "event_id": event_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /api/v1/intraday/stream  — SSE
# ---------------------------------------------------------------------------

@router.get("/stream")
async def intraday_sse_stream(request: Request):
    """
    Server-Sent Events stream for live signal and candle updates.

    Events emitted:
      {"type": "SIGNAL_NEW", "data": {...}}
      {"type": "CANDLE_UPDATE", "symbol": "...", "data": {...}}
      {"type": "SIGNAL_UPDATE", "signal_id": N, "status": "T1_HIT", ...}
      {"type": "HEARTBEAT", "ts": "..."}
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        from invst.intraday.scheduler import pop_pending_events
        heartbeat_interval = 0
        while True:
            if await request.is_disconnected():
                break

            events = pop_pending_events()
            for event in events:
                yield f"data: {json.dumps(event)}\n\n"

            # Heartbeat every 30 seconds to keep connection alive
            heartbeat_interval += 1
            if heartbeat_interval >= 30:
                yield f"data: {json.dumps({'type': 'HEARTBEAT', 'ts': datetime.now().isoformat()})}\n\n"
                heartbeat_interval = 0

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
