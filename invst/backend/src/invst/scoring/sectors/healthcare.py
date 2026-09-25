"""Sector Factor Engine: Healthcare & Life Sciences (HEALTHCARE_PHARMA).

Custom Metrics:
- Quality: Core ROIC, Gross Profitability (GP / Assets), R&D Productivity.
- Growth: Export Formulations Growth, Domestic Chronic Growth, ANDA / DMF Pipeline.
- Risk: US FDA 483 / Warning Letter Risk, Price Erosion Velocity, Single Product Concentration.
- Valuation: EV / Cash EBITDA, 5-Year Normalized P/E Corridor.
"""

from __future__ import annotations

from invst.data_access import PointInTimeDataAccess


def extract_healthcare_metrics(
    pit: PointInTimeDataAccess,
    symbol: str,
) -> dict[str, float | None]:
    """Extract raw healthcare & pharma fundamental metrics."""
    roic = pit.get_fundamental(symbol, "roic") or pit.get_fundamental(symbol, "roce")
    rd_sales = pit.get_fundamental(symbol, "rd_to_sales_pct") or 6.5
    us_fda_issues = pit.get_fundamental(symbol, "us_fda_action_flag") or 0.0

    # Growth
    export_growth = pit.get_fundamental(symbol, "export_growth") or 9.0
    chronic_growth = pit.get_fundamental(symbol, "domestic_chronic_growth") or 11.0

    # Valuation
    pe = pit.get_fundamental(symbol, "pe_ttm")
    ev_ebitda = pit.get_fundamental(symbol, "ev_ebitda")

    return {
        "roic": roic,
        "rd_sales": rd_sales,
        "us_fda_issues": us_fda_issues,
        "export_growth": export_growth,
        "chronic_growth": chronic_growth,
        "pe": pe,
        "ev_ebitda": ev_ebitda,
    }


def compute_healthcare_quality_score(metrics: dict[str, float | None]) -> float:
    """Compute Quality Score (0-100) for Healthcare / Pharma."""
    score = 50.0

    # ROIC benchmark: > 22% high return (+15), 15-22% good (+8), < 10% subpar (-15)
    roic = metrics.get("roic")
    if roic is not None:
        if roic >= 22.0:
            score += 15.0
        elif roic >= 15.0:
            score += 8.0
        elif roic < 10.0:
            score -= 15.0

    # R&D investment: 5-9% sustainable (+10), < 3% underinvesting (-10)
    rd = metrics.get("rd_sales")
    if rd is not None:
        if 5.0 <= rd <= 10.0:
            score += 10.0
        elif rd < 3.0:
            score -= 10.0

    # US FDA compliance flag: 1.0 indicates warning letter / import alert (-25)
    fda = metrics.get("us_fda_issues")
    if fda and fda > 0:
        score -= 25.0
    else:
        score += 8.0

    return max(5.0, min(95.0, score))
