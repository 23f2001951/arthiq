"""Sector Factor Engine: Banking & Financial Services (FINANCIALS).

Custom Metrics:
- Quality: Return on Assets (ROA, 3-yr avg), Net Interest Margin (NIM),
           Cost-to-Income, Provision Coverage Ratio (PCR), Capital Adequacy (CRAR).
- Growth: Advances Growth (3-yr CAGR), CASA Ratio Growth, NII Growth.
- Risk: Gross NPA %, Net NPA %, Slippage Ratio.
- Valuation: Price to Adjusted Book Value (P/ABV), P/E.

Key Invariant: Never penalize Debt/Equity or compute industrial ROCE for banks.
"""

from __future__ import annotations

from invst.data_access import PointInTimeDataAccess


def extract_financials_metrics(
    pit: PointInTimeDataAccess,
    symbol: str,
) -> dict[str, float | None]:
    """Extract raw banking & NBFC fundamental metrics."""
    # ROA & ROE
    roa = pit.get_fundamental(symbol, "roa")
    roe = pit.get_fundamental(symbol, "roe")
    nim = pit.get_fundamental(symbol, "nim")
    cost_to_income = pit.get_fundamental(symbol, "cost_to_income")
    pcr = pit.get_fundamental(symbol, "pcr")
    crar = pit.get_fundamental(symbol, "crar")

    # Growth
    advances_growth = pit.get_fundamental(symbol, "advances_growth_3yr") or pit.get_fundamental(symbol, "earnings_cagr_5yr")
    casa_growth = pit.get_fundamental(symbol, "casa_growth") or pit.get_fundamental(symbol, "revenue_growth_3yr")
    nii_growth = pit.get_fundamental(symbol, "nii_growth") or pit.get_fundamental(symbol, "earnings_cagr_5yr")

    # Asset Quality & Risk
    gnpa = pit.get_fundamental(symbol, "gnpa_pct")
    nnpa = pit.get_fundamental(symbol, "nnpa_pct")
    slippage = pit.get_fundamental(symbol, "slippage_ratio")

    # Valuation
    p_abv = pit.get_fundamental(symbol, "p_abv") or pit.get_fundamental(symbol, "pb")
    pe = pit.get_fundamental(symbol, "pe_ttm")

    return {
        "roa": roa if roa is not None else (roe / 8.0 if roe is not None else None),
        "nim": nim if nim is not None else 3.5,
        "cost_to_income": cost_to_income if cost_to_income is not None else 48.0,
        "pcr": pcr if pcr is not None else 72.0,
        "crar": crar if crar is not None else 16.5,
        "advances_growth": advances_growth,
        "casa_growth": casa_growth,
        "nii_growth": nii_growth,
        "gnpa": gnpa if gnpa is not None else 2.5,
        "nnpa": nnpa if nnpa is not None else 0.8,
        "slippage": slippage if slippage is not None else 1.5,
        "p_abv": p_abv,
        "pe": pe,
    }


def compute_financials_quality_score(metrics: dict[str, float | None]) -> float:
    """Compute Quality Score (0-100) for Banking/NBFCs."""
    score = 50.0

    # ROA benchmark: > 1.8% excellent (100), 1.2-1.8% good, < 0.8% poor
    roa = metrics.get("roa")
    if roa is not None:
        if roa >= 2.0:
            score += 15.0
        elif roa >= 1.4:
            score += 8.0
        elif roa < 0.8:
            score -= 15.0

    # NIM benchmark: > 4.0% excellent (+10), < 2.8% compressed (-10)
    nim = metrics.get("nim")
    if nim is not None:
        if nim >= 4.0:
            score += 10.0
        elif nim < 2.8:
            score -= 10.0

    # Cost to Income: < 45% efficient (+10), > 60% inefficient (-10)
    c2i = metrics.get("cost_to_income")
    if c2i is not None:
        if c2i <= 45.0:
            score += 10.0
        elif c2i >= 58.0:
            score -= 10.0

    # Provision Coverage Ratio (PCR): > 75% safe (+10), < 60% risky (-15)
    pcr = metrics.get("pcr")
    if pcr is not None:
        if pcr >= 75.0:
            score += 10.0
        elif pcr < 60.0:
            score -= 15.0

    # CRAR (Capital Adequacy): > 16% strong (+10), < 12% regulatory concern (-15)
    crar = metrics.get("crar")
    if crar is not None:
        if crar >= 16.0:
            score += 10.0
        elif crar < 12.0:
            score -= 15.0

    return max(5.0, min(95.0, score))
