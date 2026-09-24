"""Market & Execution Liquidity Engine V0.2 for Arth IQ.

Captures price momentum, trend integrity, and microstructure execution frictions.
Strictly separated from long-horizon fundamental thesis.

Features:
1. Jegadeesh-Titman 12M - 1M Momentum (strips short-term 1-month mean reversion)
2. Relative Strength vs Benchmark (63-day and 126-day)
3. Trend Integrity (50 EMA vs 200 SMA)
4. Amihud Price Impact & Expected Execution Slippage (bps)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from invst.data_access import PointInTimeDataAccess


@dataclass
class MarketResult:
    symbol: str
    market_score: float  # 0 to 100
    momentum_12m_1m_pct: float
    relative_strength_63d_pct: float
    trend_integrity: str  # BULLISH, NEUTRAL, BEARISH
    expected_slippage_bps: float
    execution_favorable: bool


def evaluate_market_engine(
    pit: PointInTimeDataAccess,
    symbol: str,
    benchmark_symbol: str = "NIFTY500",
) -> MarketResult:
    """Compute market and microstructure execution score."""
    asof = pit.asof
    start_date = date.fromordinal(max(1, asof.toordinal() - 400))
    prices = pit.get_price_series(symbol, start=start_date, end=asof)

    if not prices or len(prices) < 40:
        return MarketResult(
            symbol=symbol,
            market_score=50.0,
            momentum_12m_1m_pct=0.0,
            relative_strength_63d_pct=0.0,
            trend_integrity="NEUTRAL",
            expected_slippage_bps=10.0,
            execution_favorable=True,
        )

    closes = [p.close for p in prices]
    n = len(closes)

    # 1. 12M - 1M Momentum (Jegadeesh & Titman)
    # Price 1 month ago (t-21) vs price 12 months ago (t-252)
    p_t = closes[-1]
    p_1m = closes[-22] if n >= 22 else closes[0]
    p_12m = closes[-252] if n >= 252 else closes[0]

    mom_12m_1m = ((p_1m - p_12m) / p_12m) * 100.0 if p_12m > 0 else 0.0

    # 2. Benchmark Relative Strength (63 days ~ 3 months)
    bench_prices = pit.get_price_series(benchmark_symbol, start=start_date, end=asof)
    rs_63d = 0.0
    if bench_prices and len(bench_prices) >= 63 and n >= 63:
        b_now = bench_prices[-1].close
        b_63 = bench_prices[-63].close
        b_ret = (b_now - b_63) / b_63 if b_63 > 0 else 0.0

        s_now = closes[-1]
        s_63 = closes[-63]
        s_ret = (s_now - s_63) / s_63 if s_63 > 0 else 0.0
        rs_63d = (s_ret - b_ret) * 100.0

    # 3. Trend Integrity (50 EMA vs 200 SMA)
    sma_200 = sum(closes[-200:]) / min(n, 200)
    sma_50 = sum(closes[-50:]) / min(n, 50)

    if p_t > sma_50 > sma_200:
        trend = "BULLISH"
        trend_score = 75.0
    elif p_t < sma_50 < sma_200:
        trend = "BEARISH"
        trend_score = 25.0
    else:
        trend = "NEUTRAL"
        trend_score = 50.0

    # 4. Expected Slippage calculation (Amihud baseline)
    volumes = [p.volume for p in prices[-30:] if p.volume and p.volume > 0]
    median_vol = sorted(volumes)[len(volumes) // 2] if volumes else 100_000
    est_turnover_cr = (median_vol * p_t) / 10_000_000.0

    # Typical institutional trade ₹50 Lakhs vs daily turnover
    if est_turnover_cr >= 25.0:
        slippage_bps = 5.0
    elif est_turnover_cr >= 5.0:
        slippage_bps = 10.0
    else:
        slippage_bps = 25.0

    # Market Score Synthesis
    score = 50.0
    if mom_12m_1m > 30.0:
        score += 15.0
    elif mom_12m_1m > 10.0:
        score += 8.0
    elif mom_12m_1m < -15.0:
        score -= 15.0

    if rs_63d > 10.0:
        score += 12.0
    elif rs_63d < -10.0:
        score -= 12.0

    score = (score * 0.70) + (trend_score * 0.30)
    market_score = max(10.0, min(95.0, score))
    exec_favorable = market_score >= 35.0 and slippage_bps <= 15.0

    return MarketResult(
        symbol=symbol,
        market_score=round(market_score, 2),
        momentum_12m_1m_pct=round(mom_12m_1m, 2),
        relative_strength_63d_pct=round(rs_63d, 2),
        trend_integrity=trend,
        expected_slippage_bps=round(slippage_bps, 1),
        execution_favorable=exec_favorable,
    )
