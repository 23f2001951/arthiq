"""Sector Factor Engine: Industrials, Infra, Energy, Metals & Cyclicals (INDUSTRIALS_CAPEX).

Custom Metrics:
- Quality: ROCE (3-yr avg), Fixed Asset Turnover, Cash Flow Conversion (CFO / EBITDA),
           Interest Coverage Ratio.
- Growth: Order Book to Billing, Capex Execution / Capacity Utilization, 3-yr Revenue CAGR.
- Risk: Net Debt / EBITDA, Working Capital Days extension, Debt-to-Equity.
- Valuation: EV / Invested Capital, EV / EBITDA (cyclically normalized), P/E.
"""

from __future__ import annotations

from invst.data_access import PointInTimeDataAccess


def extract_industrials_metrics(
    pit: PointInTimeDataAccess,
    symbol: str,
) -> dict[str, float | None]:
    """Extract raw industrial & capex fundamental metrics."""
    roce = pit.get_fundamental(symbol, "roce")
    asset_turnover = pit.get_fundamental(symbol, "asset_turnover") or 1.2
    cfo = pit.get_fundamental(symbol, "cfo")
    ebitda = pit.get_fundamental(symbol, "ebitda")
    cfo_ebitda = (cfo / ebitda) if (cfo and ebitda and ebitda > 0) else pit.get_fundamental(symbol, "ocf_to_net_profit")
    interest_coverage = pit.get_fundamental(symbol, "interest_coverage")

    # Growth & Capex
    order_book_ratio = pit.get_fundamental(symbol, "order_book_to_billing") or 2.2
    rev_cagr = pit.get_fundamental(symbol, "revenue_growth_3yr") or pit.get_fundamental(symbol, "earnings_cagr_5yr")
    capex_growth = pit.get_fundamental(symbol, "capex_growth") or 10.0

    # Risk & Balance Sheet
    net_debt_ebitda = pit.get_fundamental(symbol, "net_debt_ebitda")
    debt_equity = pit.get_fundamental(symbol, "debt_equity")
    working_cap_days = pit.get_fundamental(symbol, "working_capital_days") or 75.0

    # Valuation
    ev_ebitda = pit.get_fundamental(symbol, "ev_ebitda")
    pe = pit.get_fundamental(symbol, "pe_ttm")

    return {
        "roce": roce,
        "asset_turnover": asset_turnover,
        "cfo_ebitda": cfo_ebitda if cfo_ebitda is not None else 0.75,
        "interest_coverage": interest_coverage,
        "order_book_ratio": order_book_ratio,
        "rev_cagr": rev_cagr,
        "capex_growth": capex_growth,
        "net_debt_ebitda": net_debt_ebitda if net_debt_ebitda is not None else (debt_equity * 1.5 if debt_equity else 1.2),
        "debt_equity": debt_equity,
        "working_cap_days": working_cap_days,
        "ev_ebitda": ev_ebitda,
        "pe": pe,
    }


def compute_industrials_quality_score(metrics: dict[str, float | None]) -> float:
    """Compute Quality Score (0-100) for Industrials / Capex."""
    score = 50.0

    # ROCE benchmark: > 20% compounding (+15), 14-20% good (+8), < 10% poor (-15)
    roce = metrics.get("roce")
    if roce is not None:
        if roce >= 20.0:
            score += 15.0
        elif roce >= 14.0:
            score += 8.0
        elif roce < 10.0:
            score -= 15.0

    # Cash conversion: CFO / EBITDA >= 0.75 (+10), < 0.50 cash drag (-10)
    conv = metrics.get("cfo_ebitda")
    if conv is not None:
        if conv >= 0.75:
            score += 10.0
        elif conv < 0.50:
            score -= 10.0

    # Interest coverage: > 5x safe (+10), < 2.5x distressed (-15)
    ic = metrics.get("interest_coverage")
    if ic is not None:
        if ic >= 5.0:
            score += 10.0
        elif ic < 2.5:
            score -= 15.0

    # Net Debt / EBITDA: < 1.0x pristine (+10), > 3.0x excessive leverage (-15)
    nd_ebitda = metrics.get("net_debt_ebitda")
    if nd_ebitda is not None:
        if nd_ebitda <= 1.0:
            score += 10.0
        elif nd_ebitda >= 3.0:
            score -= 15.0

    return max(5.0, min(95.0, score))
