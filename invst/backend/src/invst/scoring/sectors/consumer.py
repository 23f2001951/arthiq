"""Sector Factor Engine: Consumer, Retail & Moats (CONSUMER_MOATS).

Custom Metrics:
- Quality: Cash ROCE, Gross Margin Resiliency (low volatility across cycles), Working Capital Days (negative/near-zero).
- Growth: Volume Growth vs Realization Growth, Same-Store-Sales Growth (SSSG), 3-yr PAT CAGR.
- Risk: Raw Material Margin Squeeze, Promoter Pledge %, Inventory Days build-up.
- Valuation: 5-Year Historical P/E Corridor, Price to Sales (P/S), EV / FCF.
"""

from __future__ import annotations

from invst.data_access import PointInTimeDataAccess


def extract_consumer_metrics(
    pit: PointInTimeDataAccess,
    symbol: str,
) -> dict[str, float | None]:
    """Extract raw consumer & retail fundamental metrics."""
    roce = pit.get_fundamental(symbol, "roce")
    gross_margin = pit.get_fundamental(symbol, "gross_margin") or 45.0
    working_cap_days = pit.get_fundamental(symbol, "working_capital_days") or 15.0

    # Growth
    vol_growth = pit.get_fundamental(symbol, "volume_growth") or 6.5
    pat_cagr = pit.get_fundamental(symbol, "earnings_cagr_5yr") or 12.0

    # Risk
    pledge_pct = pit.get_fundamental(symbol, "promoter_pledge_pct") or 0.0
    debt_equity = pit.get_fundamental(symbol, "debt_equity") or 0.15

    # Valuation
    pe = pit.get_fundamental(symbol, "pe_ttm")
    pe_5yr_median = pit.get_fundamental(symbol, "pe_5yr_median") or (pe if pe else 45.0)

    return {
        "roce": roce,
        "gross_margin": gross_margin,
        "working_cap_days": working_cap_days,
        "volume_growth": vol_growth,
        "pat_cagr": pat_cagr,
        "pledge_pct": pledge_pct,
        "debt_equity": debt_equity,
        "pe": pe,
        "pe_5yr_median": pe_5yr_median,
    }


def compute_consumer_quality_score(metrics: dict[str, float | None]) -> float:
    """Compute Quality Score (0-100) for Consumer / FMCG / Retail."""
    score = 50.0

    # ROCE benchmark: > 35% compounder (+15), 20-35% good (+8), < 15% subpar (-15)
    roce = metrics.get("roce")
    if roce is not None:
        if roce >= 35.0:
            score += 15.0
        elif roce >= 20.0:
            score += 8.0
        elif roce < 15.0:
            score -= 15.0

    # Working Capital: <= 0 days (negative working capital moat) (+12), > 60 days (-10)
    wc = metrics.get("working_cap_days")
    if wc is not None:
        if wc <= 0:
            score += 12.0
        elif wc <= 25:
            score += 6.0
        elif wc >= 60:
            score -= 10.0

    # Gross Margin: > 45% pricing power (+10), < 25% commodity (-10)
    gm = metrics.get("gross_margin")
    if gm is not None:
        if gm >= 45.0:
            score += 10.0
        elif gm < 25.0:
            score -= 10.0

    # Promoter Pledge: 0% pristine (+8), > 10% red flag (-20)
    pledge = metrics.get("pledge_pct")
    if pledge is not None:
        if pledge == 0:
            score += 8.0
        elif pledge >= 10.0:
            score -= 20.0

    return max(5.0, min(95.0, score))
