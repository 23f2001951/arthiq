"""Sector Factor Engine: Technology & Knowledge Services (TECH_SERVICES).

Custom Metrics:
- Quality: Return on Invested Capital (ROIC), FCF to PAT conversion, Operating Margin stability.
- Growth: Constant Currency (CC) YoY Growth, Deal TCV momentum, Headcount momentum.
- Risk: Client Concentration (% Top 5/10), Attrition Rate, Geopolitical/Forex exposure.
- Valuation: Free Cash Flow Yield (FCF / EV), EV / EBIT, PEG Ratio.
"""

from __future__ import annotations

from invst.data_access import PointInTimeDataAccess


def extract_tech_metrics(
    pit: PointInTimeDataAccess,
    symbol: str,
) -> dict[str, float | None]:
    """Extract raw technology & digital services fundamental metrics."""
    roic = pit.get_fundamental(symbol, "roic") or pit.get_fundamental(symbol, "roce")
    fcf = pit.get_fundamental(symbol, "fcf")
    pat = pit.get_fundamental(symbol, "pat") or pit.get_fundamental(symbol, "net_profit")
    fcf_to_pat = (fcf / pat) if (fcf and pat and pat > 0) else pit.get_fundamental(symbol, "ocf_to_net_profit")
    ebit_margin = pit.get_fundamental(symbol, "operating_margin") or 22.0

    # Growth
    cc_growth = pit.get_fundamental(symbol, "cc_revenue_growth") or pit.get_fundamental(symbol, "revenue_growth_3yr") or pit.get_fundamental(symbol, "earnings_cagr_5yr")
    deal_tcv = pit.get_fundamental(symbol, "deal_tcv_growth") or 8.0

    # Risk
    client_conc = pit.get_fundamental(symbol, "top_10_client_concentration") or 28.0
    attrition = pit.get_fundamental(symbol, "attrition_pct") or 14.0

    # Valuation
    pe = pit.get_fundamental(symbol, "pe_ttm")
    peg = pit.get_fundamental(symbol, "peg")
    fcf_yield = pit.get_fundamental(symbol, "fcf_yield") or (3.5 if pe and pe > 0 else 2.5)

    return {
        "roic": roic,
        "fcf_to_pat": fcf_to_pat if fcf_to_pat is not None else 0.88,
        "ebit_margin": ebit_margin,
        "cc_growth": cc_growth,
        "deal_tcv": deal_tcv,
        "client_conc": client_conc,
        "attrition": attrition,
        "fcf_yield": fcf_yield,
        "pe": pe,
        "peg": peg,
    }


def compute_tech_quality_score(metrics: dict[str, float | None]) -> float:
    """Compute Quality Score (0-100) for Tech Services."""
    score = 50.0

    # ROIC benchmark: > 30% moated (+15), 20-30% good (+8), < 15% subpar (-15)
    roic = metrics.get("roic")
    if roic is not None:
        if roic >= 30.0:
            score += 15.0
        elif roic >= 20.0:
            score += 8.0
        elif roic < 15.0:
            score -= 15.0

    # FCF conversion: FCF / PAT >= 0.85 (+10), < 0.65 (-10)
    fcf_pat = metrics.get("fcf_to_pat")
    if fcf_pat is not None:
        if fcf_pat >= 0.85:
            score += 10.0
        elif fcf_pat < 0.65:
            score -= 10.0

    # EBIT Margin: > 24% (+10), < 16% (-10)
    margin = metrics.get("ebit_margin")
    if margin is not None:
        if margin >= 24.0:
            score += 10.0
        elif margin < 16.0:
            score -= 10.0

    # Attrition: < 12% stable (+10), > 20% churn penalty (-10)
    att = metrics.get("attrition")
    if att is not None:
        if att <= 12.0:
            score += 10.0
        elif att >= 20.0:
            score -= 10.0

    return max(5.0, min(95.0, score))
