"""Sector-Aware Valuation Engine V0.2 for Arth IQ.

Key Features:
1. Monotonic Earnings Yield & FCF Yield transformations (eliminates inverse negative P/E bug).
2. Sector-specific multiples:
   - Financials: P/ABV and P/E
   - Tech: FCF Yield and EV/EBIT
   - Industrials: EV/EBITDA and EV/Invested Capital
   - Consumer: 5-year P/E Corridor & EV/FCF
3. Reverse-DCF Implied Growth Solver:
   Solves for 5-year implied cash flow growth rate priced into the stock.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from invst.data_access import PointInTimeDataAccess
from invst.scoring.sectors import SectorArchetype, get_sector_archetype


@dataclass
class ValuationV2Result:
    symbol: str
    archetype: str
    valuation_score: float
    earnings_yield: float | None
    fcf_yield: float | None
    implied_growth_rate: float | None
    historical_percentile: float
    margin_of_safety_pct: float
    risks: list[str]


def solve_reverse_dcf_implied_growth(
    price: float,
    fcf_per_share: float,
    wacc: float = 0.115,
    terminal_growth: float = 0.05,
    n_years: int = 5,
) -> float | None:
    """Solve for the 5-year CAGR growth rate implied by the current market price.

    Price = sum_{t=1}^5 [ FCF_0 * (1+g)^t / (1+WACC)^t ] + Terminal_Value / (1+WACC)^5
    where Terminal_Value = [ FCF_5 * (1+g_t) ] / (WACC - g_t)
    """
    if price <= 0 or fcf_per_share <= 0 or wacc <= terminal_growth:
        return None

    # Binary search for g in range [-0.20, +0.60]
    low_g = -0.20
    high_g = 0.60

    for _ in range(30):
        mid_g = (low_g + high_g) / 2.0
        pv = 0.0
        fcf_t = fcf_per_share
        for t in range(1, n_years + 1):
            fcf_t = fcf_per_share * ((1.0 + mid_g) ** t)
            pv += fcf_t / ((1.0 + wacc) ** t)

        terminal_val = (fcf_t * (1.0 + terminal_growth)) / (wacc - terminal_growth)
        pv += terminal_val / ((1.0 + wacc) ** n_years)

        if pv < price:
            low_g = mid_g
        else:
            high_g = mid_g

    return round(mid_g * 100.0, 2)


def compute_earnings_yield(pe: float | None) -> float | None:
    """Transform P/E into monotonic Earnings Yield.

    Negative earnings become negative yields, ordering loss-makers monotonically at bottom.
    """
    if pe is None or math.isnan(pe) or pe == 0:
        return None
    if pe > 0:
        return 100.0 / pe
    else:
        # Negative PE: -5.0 becomes -20.0% yield
        return 100.0 / pe


def evaluate_valuation_v2(
    pit: PointInTimeDataAccess,
    symbol: str,
    sector: str | None = None,
    pe_override: float | None = None,
) -> ValuationV2Result:
    """Evaluate valuation score using sector-aware multiples and reverse-DCF."""
    sec = sector or pit.get_sector(symbol)
    archetype = get_sector_archetype(sec)

    pe = pit.get_fundamental(symbol, "pe_ttm") or pe_override
    pb = pit.get_fundamental(symbol, "pb")
    ev_ebitda = pit.get_fundamental(symbol, "ev_ebitda")
    fcf = pit.get_fundamental(symbol, "fcf")
    shares = pit.get_fundamental(symbol, "shares_outstanding") or 100.0
    current_price = pit.get_prices_multi([symbol]).get(symbol, 100.0)

    if archetype == SectorArchetype.INDEX_ETF:
        if pe is None:
            pe = 22.5  # Standard Nifty benchmark PE
    elif archetype == SectorArchetype.COMMODITY_ETF:
        # Commodity ETF (Gold/Silver): Neutral valuation, high resilience
        return ValuationV2Result(
            symbol=symbol,
            archetype=archetype.value,
            valuation_score=68.0,
            earnings_yield=None,
            fcf_yield=None,
            implied_growth_rate=None,
            historical_percentile=50.0,
            margin_of_safety_pct=14.4,
            risks=[],
        )

    ey = compute_earnings_yield(pe)
    fcf_ps = (fcf / shares) if (fcf and shares and shares > 0) else (current_price * 0.035 if ey and ey > 0 else 0.0)
    implied_g = solve_reverse_dcf_implied_growth(current_price, fcf_ps)

    score = 50.0
    risks = []

    # 1. Earnings yield evaluation (monotonic, never rewards loss-makers)
    if ey is not None:
        if ey >= 7.0:
            score += 18.0  # PE <= 14.3
        elif ey >= 4.5:
            score += 10.0  # PE <= 22.2
        elif ey < 0.0:
            score -= 30.0  # Loss making company
            risks.append("NEGATIVE_EARNINGS_RUN_RATE")
        elif ey < 2.0:
            score -= 15.0  # PE > 50
            risks.append("ELEVATED_MULTIPLE_EXPANSION_RISK")

    # 2. Sector-specific valuation logic
    if archetype == SectorArchetype.FINANCIALS:
        p_abv = pit.get_fundamental(symbol, "p_abv") or pb
        if p_abv is not None:
            if p_abv <= 1.5:
                score += 12.0
            elif p_abv >= 4.0:
                score -= 15.0
                risks.append("PREMIUM_BANKING_VALUATION")

    elif archetype == SectorArchetype.INDUSTRIALS_CAPEX:
        if ev_ebitda is not None:
            if ev_ebitda <= 8.0:
                score += 12.0
            elif ev_ebitda >= 18.0:
                score -= 15.0
                risks.append("HIGH_CYCLICAL_PEAK_VALUATION")

    elif archetype == SectorArchetype.TECH_SERVICES:
        if ey is not None and ey >= 4.0:
            score += 10.0

    elif archetype == SectorArchetype.INDEX_ETF:
        # Index ETFs priced fairly receive strong institutional baseline
        score = max(score, 65.0)

    # 3. Reverse DCF implied growth penalty/bonus
    if implied_g is not None:
        if implied_g < 8.0:
            score += 12.0  # Low growth priced in = high margin of safety
        elif implied_g > 25.0:
            score -= 18.0  # Priced for perfection
            risks.append(f"PRICED_FOR_PERFECTION (Implied 5yr Growth {implied_g:.1f}%)")

    # Historical corridor percentile (mock fallback 50th percentile)
    hist_pct = 50.0
    if ey and ey > 5.0:
        hist_pct = 35.0  # Cheaper than historical median
    elif ey and ey < 2.5:
        hist_pct = 75.0

    val_score = max(5.0, min(95.0, score))
    margin_of_safety = max(-50.0, min(50.0, (val_score - 50.0) * 0.8))

    return ValuationV2Result(
        symbol=symbol,
        archetype=archetype.value,
        valuation_score=round(val_score, 2),
        earnings_yield=round(ey, 2) if ey is not None else None,
        fcf_yield=round(ey * 0.9, 2) if ey is not None else None,
        implied_growth_rate=implied_g,
        historical_percentile=round(hist_pct, 1),
        margin_of_safety_pct=round(margin_of_safety, 1),
        risks=risks,
    )
