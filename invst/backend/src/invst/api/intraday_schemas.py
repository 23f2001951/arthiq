"""IIM — Pydantic response schemas for all intraday API endpoints."""
from __future__ import annotations
from datetime import datetime
from typing import Any
from pydantic import BaseModel


class IntradayStockItem(BaseModel):
    symbol: str
    iss_score: float
    liquidity_score: float | None
    atr_pct_15m: float | None
    momentum_score: float | None
    todvol_score: float | None
    level_setup_score: float | None
    news_score: float | None
    gap_type: str | None
    iep_price: float | None
    selected_at: str | None


class IntradayUniverseResponse(BaseModel):
    date: str
    count: int
    stocks: list[IntradayStockItem]


class SignalSizingSchema(BaseModel):
    shares: int
    capital_at_risk: float
    risk_pct: float
    max_loss_inr: float


class IntradaySignalSchema(BaseModel):
    id: int
    symbol: str
    strategy_id: str
    mode: str
    signal_type: str
    entry_price: float | None
    sl_price: float
    target_1: float
    target_2: float | None
    sl_distance: float
    reward_risk: float
    atr_at_signal: float
    confidence_score: int | None
    pillars_met: str
    regime: str
    vwap_at_signal: float | None
    todvol_ratio: float | None
    rationale: str | None
    current_status: str
    net_pnl_r: float | None
    mfe_r: float | None
    mae_r: float | None
    created_at: str


class IntradaySignalsResponse(BaseModel):
    count: int
    signals: list[IntradaySignalSchema]
    mode: str


class CandleSchema(BaseModel):
    candle_time: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    ema21: float | None = None
    supertrend: float | None = None
    supertrend_dir: int | None = None
    atr14: float | None = None
    vwap: float | None = None
    todvol_ratio: float | None = None


class IntradayChartResponse(BaseModel):
    symbol: str
    timeframe: str
    candles: list[CandleSchema]
    pivot_levels: dict[str, float]
    orb_high: float | None
    orb_low: float | None
    prev_day_high: float | None
    prev_day_low: float | None


class RegimeResponse(BaseModel):
    regime: str
    adx: float
    india_vix: float
    nifty_ema21_slope: float
    sl_atr_adjustment: float
    reason: str
    timestamp: str


class AccuracyBreakdownItem(BaseModel):
    count: int
    win_rate: float
    expectancy: float


class AccuracyReportResponse(BaseModel):
    strategy_id: str
    mode: str
    total_trades: int
    win_rate: float
    avg_win_r: float
    avg_loss_r: float
    expectancy_net: float
    profit_factor: float
    max_drawdown_r: float
    ci_lower: float
    ci_upper: float
    rolling_50_expectancy: float
    auto_disabled: bool
    regime_breakdown: dict[str, AccuracyBreakdownItem]
    data_source_note: str
    computed_at: str


class SignalOutcomeFeedbackRequest(BaseModel):
    signal_id: int
    event_type: str   # T1_HIT, T2_HIT, SL_HIT, MANUAL_EXIT
    price: float | None = None
    shares: int | None = None
    note: str | None = None
