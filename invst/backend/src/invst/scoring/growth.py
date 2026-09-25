"""Standalone Growth Engine for Arth IQ V0.2.

Computes:
1. Historical Growth (3-5 yr Revenue & Earnings CAGR)
2. Growth Acceleration (Sequential YoY Growth inflection)
3. Operating Margin Expansion
4. Incremental Capital Efficiency (ROIIC)

Returns:
- Growth Score (0–100)
- Growth Confidence (0–100%)
- Growth Drivers & Risks
"""

from __future__ import annotations

from dataclasses import dataclass

from invst.data_access import PointInTimeDataAccess


@dataclass
class GrowthResult:
    symbol: str
    growth_score: float
    growth_confidence: float
    historical_growth_cagr: float
    growth_acceleration_delta: float
    margin_expansion_delta: float
    drivers: list[str]
    risks: list[str]


def evaluate_growth(
    pit: PointInTimeDataAccess,
    symbol: str,
    growth_cagr_override: float | None = None,
    is_etf: bool = False,
) -> GrowthResult:
    """Evaluate company growth engine independent of valuation and quality."""
    if is_etf:
        cagr = growth_cagr_override or 13.0
        return GrowthResult(
            symbol=symbol,
            growth_score=72.0,
            growth_confidence=85.0,
            historical_growth_cagr=cagr,
            growth_acceleration_delta=0.0,
            margin_expansion_delta=0.0,
            drivers=[
                "Benchmark index aggregate earnings expansion (~12-14% CAGR)",
                "Systemic Indian corporate revenue and economic expansion",
            ],
            risks=["Macro cyclical slowdown in aggregate index earnings"],
        )

    # 1. Historical CAGR
    rev_cagr = pit.get_fundamental(symbol, "revenue_growth_3yr")
    earn_cagr = pit.get_fundamental(symbol, "earnings_cagr_5yr")
    hist_growth = (
        growth_cagr_override
        if growth_cagr_override is not None
        else (earn_cagr if earn_cagr is not None else (rev_cagr if rev_cagr is not None else 12.0))
    )

    # 2. Sequential Acceleration
    growth_accel = pit.get_fundamental(symbol, "revenue_growth_acceleration") or 0.0

    # 3. Margin Expansion
    margin_exp = pit.get_fundamental(symbol, "margin_expansion_pct") or 0.0

    # 4. Incremental Capital Efficiency (ROIIC)
    roiic = pit.get_fundamental(symbol, "roiic") or 14.0

    drivers = []
    risks = []

    # Score calculation baseline
    score = 50.0

    # Historical growth impact
    if hist_growth >= 25.0:
        score += 20.0
        drivers.append(f"Hyper-compounding historical growth ({hist_growth:.1f}% CAGR)")
    elif hist_growth >= 15.0:
        score += 12.0
        drivers.append(f"Robust steady historical growth ({hist_growth:.1f}% CAGR)")
    elif hist_growth <= 0.0:
        score -= 20.0
        risks.append(f"Negative multi-year growth ({hist_growth:.1f}% CAGR)")
    elif hist_growth < 7.0:
        score -= 10.0
        risks.append("Sub-GDP top-line stagnation")

    # Acceleration impact
    if growth_accel > 5.0:
        score += 12.0
        drivers.append(f"Sequential growth inflection (+{growth_accel:.1f}% YoY acceleration)")
    elif growth_accel < -5.0:
        score -= 12.0
        risks.append(f"Growth deceleration headwind ({growth_accel:.1f}% deceleration)")

    # Margin Expansion impact
    if margin_exp > 1.5:
        score += 8.0
        drivers.append(f"Operating margin expansion (+{margin_exp:.1f}%)")
    elif margin_exp < -2.0:
        score -= 8.0
        risks.append(f"Operating margin compression ({margin_exp:.1f}%)")

    # ROIIC impact
    if roiic >= 25.0:
        score += 10.0
        drivers.append(f"High incremental capital return ({roiic:.1f}% ROIIC)")
    elif roiic < 8.0:
        score -= 10.0
        risks.append("Low return on incremental invested capital")

    growth_score = max(5.0, min(95.0, score))

    # Growth Confidence calculation (variance / stability based)
    confidence = 75.0
    if len(risks) >= 2:
        confidence -= 25.0
    if abs(growth_accel) > 15.0:
        confidence -= 10.0  # High volatility in growth rates lowers confidence
    if hist_growth > 20.0 and len(risks) == 0:
        confidence += 15.0

    growth_confidence = max(20.0, min(95.0, confidence))

    return GrowthResult(
        symbol=symbol,
        growth_score=round(growth_score, 2),
        growth_confidence=round(growth_confidence, 2),
        historical_growth_cagr=round(hist_growth, 2),
        growth_acceleration_delta=round(growth_accel, 2),
        margin_expansion_delta=round(margin_exp, 2),
        drivers=drivers,
        risks=risks,
    )
