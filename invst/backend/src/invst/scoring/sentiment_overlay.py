"""Stage 4: Sentiment and Momentum Overlay.

Additive overlay capped at ±10 points:
- Price momentum (6-12-1) — ±5 points
- News sentiment (90-day FinBERT/VADER mean) — ±5 points
- Promoter holding trend — ±3 points

Total points are clamped to [-10, +10] to ensure sentiment cannot
override fundamentals and risk.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from invst.data_access import PointInTimeDataAccess

logger = logging.getLogger(__name__)

MOMENTUM_MAX_PTS = 5.0
SENTIMENT_MAX_PTS = 5.0
PROMOTER_MAX_PTS = 3.0
TOTAL_OVERLAY_CAP = 10.0


def compute_price_momentum_6_12_1(
    pit: PointInTimeDataAccess,
    symbol: str,
) -> float:
    """Compute 6-12-1 price momentum: return between 12 months ago and 1 month ago.

    Excludes the most recent month to avoid short-term reversal effects.
    """
    asof = pit.asof
    t_minus_1m = date.fromordinal(asof.toordinal() - 30)
    t_minus_12m = date.fromordinal(asof.toordinal() - 365)

    p_1m = pit.get_price(symbol, on_or_before=t_minus_1m)
    p_12m = pit.get_price(symbol, on_or_before=t_minus_12m)

    if p_1m and p_12m and p_12m > 0:
        return (p_1m - p_12m) / p_12m
    return 0.0


def compute_promoter_trend(
    pit: PointInTimeDataAccess,
    symbol: str,
) -> float:
    """Compute change in promoter holding over the last 4 quarters."""
    history = pit.get_fundamental_history(symbol, "promoter_holding_pct", n_quarters=4)
    if len(history) >= 2 and history[0].value is not None and history[-1].value is not None:
        return history[0].value - history[-1].value
    return 0.0


def compute_sentiment_overlay(
    pit: PointInTimeDataAccess,
    symbol: str,
) -> dict[str, Any]:
    """Calculate the Stage 4 overlay points for a single symbol."""
    # 1. Price momentum
    mom_return = compute_price_momentum_6_12_1(pit, symbol)
    # Scale: -30% return gives -5 pts, +30% return gives +5 pts
    mom_pts = max(-MOMENTUM_MAX_PTS, min(MOMENTUM_MAX_PTS, (mom_return / 0.30) * MOMENTUM_MAX_PTS))

    # 2. News sentiment (last 90 days)
    avg_sentiment = pit.get_avg_sentiment(symbol, lookback_days=90)
    if avg_sentiment is not None:
        sent_pts = max(
            -SENTIMENT_MAX_PTS, min(SENTIMENT_MAX_PTS, avg_sentiment * SENTIMENT_MAX_PTS)
        )
    else:
        sent_pts = 0.0

    # 3. Promoter holding trend
    prom_change = compute_promoter_trend(pit, symbol)
    # Scale: +2% increase -> +3 pts, -2% decrease -> -3 pts
    prom_pts = max(-PROMOTER_MAX_PTS, min(PROMOTER_MAX_PTS, (prom_change / 2.0) * PROMOTER_MAX_PTS))

    raw_total = mom_pts + sent_pts + prom_pts
    capped_total = max(-TOTAL_OVERLAY_CAP, min(TOTAL_OVERLAY_CAP, raw_total))

    return {
        "overlay_points": round(capped_total, 2),
        "momentum_return": round(mom_return, 4),
        "momentum_points": round(mom_pts, 2),
        "sentiment_score": round(avg_sentiment, 3) if avg_sentiment is not None else None,
        "sentiment_points": round(sent_pts, 2),
        "promoter_change": round(prom_change, 2),
        "promoter_points": round(prom_pts, 2),
    }


def score_sentiment_universe(
    pit: PointInTimeDataAccess,
    symbols: list[str],
) -> dict[str, dict[str, Any]]:
    """Compute Stage 4 sentiment overlay for all given symbols."""
    return {sym: compute_sentiment_overlay(pit, sym) for sym in symbols}
