"""Point-in-time ML Feature Extraction & Forward Target Labeling.

Constructs institutional feature matrices for walk-forward model training and inference
as of each rebalance date, strictly enforcing zero look-ahead data leakage.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import numpy as np

from invst.data_access import PointInTimeDataAccess
from invst.scoring.quality import extract_quality_metrics
from invst.scoring.risk import compute_price_risk_metrics
from invst.scoring.sentiment_overlay import compute_price_momentum_6_12_1
from invst.scoring.valuation import extract_valuation_metrics

logger = logging.getLogger(__name__)


def compute_dist_from_52w_high(pit: PointInTimeDataAccess, symbol: str) -> float:
    """Compute percentage distance from 52-week high (<= 0.0)."""
    asof = pit.asof
    start_1yr = date.fromordinal(max(1, asof.toordinal() - 365))
    prices = pit.get_price_series(symbol, start=start_1yr, end=asof)
    if not prices:
        return 0.0

    high_52w = max(p.close for p in prices)
    curr_close = prices[-1].close

    if high_52w > 0:
        return (curr_close - high_52w) / high_52w
    return 0.0


def compute_downside_semivariance(pit: PointInTimeDataAccess, symbol: str, lookback_days: int = 180) -> float:
    """Compute annualized downside semivariance below zero daily return."""
    asof = pit.asof
    start_dt = date.fromordinal(max(1, asof.toordinal() - lookback_days))
    prices = pit.get_price_series(symbol, start=start_dt, end=asof)
    if len(prices) < 20:
        return 0.15

    closes = np.array([p.close for p in prices])
    rets = (closes[1:] - closes[:-1]) / closes[:-1]
    downside_rets = rets[rets < 0.0]
    if len(downside_rets) == 0:
        return 0.05
    semi_var = float(np.sqrt(np.mean(downside_rets ** 2)) * np.sqrt(252.0))
    return round(semi_var, 4)


def extract_symbol_ml_features(
    pit: PointInTimeDataAccess,
    symbol: str,
    composite_score: float = 50.0,
    investment_score: float = 50.0,
    business_score: float = 50.0,
    growth_score: float = 50.0,
) -> dict[str, float]:
    """Extract a 24-dimensional flat vector of point-in-time numeric features for a stock."""
    # 1. Quality & Fundamentals
    q = extract_quality_metrics(pit, symbol)
    v = extract_valuation_metrics(pit, symbol)

    # 2. Risk & Price Distribution
    r = compute_price_risk_metrics(pit, symbol)
    downside_semi = compute_downside_semivariance(pit, symbol)

    # 3. Momentum & Relative High
    mom = compute_price_momentum_6_12_1(pit, symbol)
    dist_52w = compute_dist_from_52w_high(pit, symbol)

    # 4. News Sentiment
    sent = pit.get_avg_sentiment(symbol, lookback_days=90) or 0.0

    # 5. Macro State Variables
    vix = pit.get_price("INDIA_VIX") or 15.0
    vix_30d_prior = pit.get_price("INDIA_VIX", on_or_before=date.fromordinal(max(1, pit.asof.toordinal() - 30))) or vix
    vix_change = (vix - vix_30d_prior) / max(1.0, vix_30d_prior)

    usd_inr = pit.get_price("USD_INR") or 83.0

    # 6. Additional fundamental momentum signals
    roe = float(q.get("roe_5yr_avg") or 15.0)
    roce = float(q.get("roce_5yr_avg") or 15.0)
    debt_eq = float(q.get("debt_equity") or 0.5)
    pe = float(v.get("pe_ttm") or 20.0)
    pb = float(v.get("pb") or 3.0)
    ev_ebitda = float(v.get("ev_ebitda") or 14.0)

    return {
        "composite_score": float(composite_score),
        "investment_score": float(investment_score),
        "business_score": float(business_score),
        "growth_score": float(growth_score),
        "roe_5yr": roe,
        "roce_5yr": roce,
        "debt_equity": debt_eq,
        "pe_ttm": pe,
        "pb": pb,
        "ev_ebitda": ev_ebitda,
        "annualised_vol": float(r.get("annualised_vol_252d") or 0.25),
        "beta": float(r.get("beta_nifty500_2yr") or 1.0),
        "max_drawdown": float(r.get("max_drawdown_3yr") or -0.20),
        "downside_semivariance": downside_semi,
        "momentum_6_12_1": float(mom),
        "dist_from_52w_high": float(dist_52w),
        "news_sentiment": float(sent),
        "macro_vix": float(vix),
        "macro_vix_change_30d": float(vix_change),
        "macro_usd_inr": float(usd_inr),
        "quality_to_valuation_ratio": float(roce / max(5.0, pe)),
        "risk_adjusted_momentum": float(mom / max(0.10, float(r.get("annualised_vol_252d") or 0.25))),
    }


def compute_forward_return(
    conn: Any,
    symbol: str,
    asof_date: date,
    horizon_days: int = 90,
) -> float | None:
    """Compute forward holding period return strictly for training labels (offline)."""
    end_date = date.fromordinal(asof_date.toordinal() + horizon_days)

    cur = conn.execute(
        """
        SELECT close FROM daily_prices
        WHERE symbol = ? AND trade_date >= ?
        ORDER BY trade_date ASC LIMIT 1
        """,
        (symbol, asof_date.isoformat()),
    )
    r_start = cur.fetchone()
    if not r_start or r_start[0] is None or r_start[0] <= 0:
        return None

    cur = conn.execute(
        """
        SELECT close FROM daily_prices
        WHERE symbol = ? AND trade_date <= ?
        ORDER BY trade_date DESC LIMIT 1
        """,
        (symbol, end_date.isoformat()),
    )
    r_end = cur.fetchone()
    if not r_end or r_end[0] is None or r_end[0] <= 0:
        return None

    p0 = float(r_start[0])
    p1 = float(r_end[0])
    return (p1 - p0) / p0


def compute_forward_excess_label(
    conn: Any,
    symbol: str,
    benchmark_symbol: str,
    asof_date: date,
    horizon_days: int = 90,
) -> tuple[int, float] | None:
    """Compute forward excess return and binary label: 1 if symbol beats benchmark, 0 otherwise."""
    stock_ret = compute_forward_return(conn, symbol, asof_date, horizon_days)
    bench_ret = compute_forward_return(conn, benchmark_symbol, asof_date, horizon_days)

    if stock_ret is None or bench_ret is None:
        return None

    excess = stock_ret - bench_ret
    label = 1 if excess > 0.0 else 0
    return label, excess


def build_ml_feature_dataset(
    pit: PointInTimeDataAccess,
    symbols: list[str],
    composite_scores_map: dict[str, float],
    investment_scores_map: dict[str, float] | None = None,
    business_scores_map: dict[str, float] | None = None,
    growth_scores_map: dict[str, float] | None = None,
) -> tuple[np.ndarray, list[str], list[str]]:
    """Build feature matrix X, symbol list, and feature names list as of pit.asof."""
    X_rows = []
    valid_symbols = []
    feature_names = []

    inv_map = investment_scores_map or {}
    bus_map = business_scores_map or {}
    gro_map = growth_scores_map or {}

    for sym in symbols:
        comp_score = composite_scores_map.get(sym, 50.0)
        inv_score = inv_map.get(sym, comp_score)
        bus_score = bus_map.get(sym, comp_score)
        gro_score = gro_map.get(sym, 50.0)

        feats = extract_symbol_ml_features(
            pit,
            sym,
            composite_score=comp_score,
            investment_score=inv_score,
            business_score=bus_score,
            growth_score=gro_score,
        )
        if not feature_names:
            feature_names = sorted(feats.keys())

        row = [feats[name] for name in feature_names]
        X_rows.append(row)
        valid_symbols.append(sym)

    X = np.array(X_rows, dtype=np.float32) if X_rows else np.empty((0, 0))
    return X, valid_symbols, feature_names
