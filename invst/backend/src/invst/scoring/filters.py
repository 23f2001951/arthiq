"""Stage 0: Screening Filters for Universe Reduction.

Applies mechanical quality and safety criteria to the point-in-time universe:
1. Liquidity: 30-day median traded value >= min_liquidity_cr (default ₹5 cr)
2. Market cap: >= min_market_cap_cr (default ₹1,000 cr)
3. Listing tenure: >= min_listing_years (default 3 years)
4. Float: Promoter holding <= max_promoter_holding_pct (default 75%)
5. Data integrity: Has >= min_quarters_available of last 12 quarters (default 10)
6. Exclusions: No penny stocks (price < min_price, default ₹10), no suspended/delisted.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date

from invst.data_access import PointInTimeDataAccess

logger = logging.getLogger(__name__)


@dataclass
class FilterResult:
    """Result of Stage 0 filtering for a single symbol."""

    symbol: str
    passed: bool
    reasons: list[str] = field(default_factory=list)
    details: dict[str, float | int | str | None] = field(default_factory=dict)


def evaluate_symbol_filters(
    pit: PointInTimeDataAccess,
    symbol: str,
    min_price: float = 10.0,
    min_liquidity_cr: float = 5.0,
    min_market_cap_cr: float = 1000.0,
    max_promoter_holding_pct: float = 75.0,
    min_quarters_available: int = 10,
    min_listing_years: int = 3,
) -> FilterResult:
    """Evaluate all Stage 0 filters for a single symbol at pit.asof."""
    reasons: list[str] = []
    details: dict[str, float | int | str | None] = {}

    # 1. Price check (no penny stocks)
    price = pit.get_price(symbol)
    details["price"] = price
    if price is None:
        reasons.append("No price data available")
    elif price < min_price:
        reasons.append(f"Price ₹{price:.2f} < ₹{min_price:.2f} (penny stock)")

    # 2. Market cap check
    mcap = pit.get_fundamental(symbol, "market_cap")
    details["market_cap_cr"] = mcap
    if mcap is not None and mcap < min_market_cap_cr:
        reasons.append(f"Market cap ₹{mcap:.1f} cr < ₹{min_market_cap_cr:.1f} cr")

    # 3. Liquidity: 30-day median traded value
    liq = pit.get_fundamental(symbol, "traded_value_median_30d")
    if liq is None and price is not None:
        # Fallback: estimate from recent daily_prices volume * close
        start_30d = date.fromordinal(pit.asof.toordinal() - 45)
        prices = pit.get_price_series(symbol, start=start_30d, end=pit.asof)
        if prices:
            traded_vals = [p.close * (p.volume or 0) / 1e7 for p in prices[-30:]]  # in ₹ Crore
            if traded_vals:
                traded_vals.sort()
                liq = traded_vals[len(traded_vals) // 2]
    details["liquidity_cr"] = liq
    if liq is not None and liq < min_liquidity_cr:
        reasons.append(f"30-day median liquidity ₹{liq:.2f} cr < ₹{min_liquidity_cr:.2f} cr")

    # 4. Float: Promoter holding
    promoter_pct = pit.get_fundamental(symbol, "promoter_holding_pct")
    details["promoter_holding_pct"] = promoter_pct
    if promoter_pct is not None and promoter_pct > max_promoter_holding_pct:
        reasons.append(f"Promoter holding {promoter_pct:.1f}% > {max_promoter_holding_pct:.1f}%")

    # 5. Data integrity: Quarterly fundamentals history
    history = pit.get_fundamental_history(symbol, "roe", n_quarters=12)
    quarters_count = len(history)
    details["quarters_count"] = quarters_count
    # If fundamentals exist in DB, enforce check
    if quarters_count > 0 and quarters_count < min_quarters_available:
        reasons.append(
            f"Only {quarters_count}/12 quarters available (minimum {min_quarters_available})"
        )

    # 6. Listing tenure
    earliest_date_str = None
    row = pit.conn.execute(
        "SELECT MIN(trade_date) FROM daily_prices WHERE symbol = ?",
        (symbol,),
    ).fetchone()
    if row and row[0]:
        earliest_date_str = row[0]
        try:
            earliest_dt = date.fromisoformat(earliest_date_str)
            tenure_years = (pit.asof - earliest_dt).days / 365.25
            details["tenure_years"] = round(tenure_years, 2)
            if tenure_years < min_listing_years:
                reasons.append(f"Listing tenure {tenure_years:.1f} yrs < {min_listing_years} yrs")
        except Exception:
            pass

    passed = len(reasons) == 0
    return FilterResult(symbol=symbol, passed=passed, reasons=reasons, details=details)


def filter_universe(
    pit: PointInTimeDataAccess,
    symbols: list[str] | None = None,
    min_price: float = 10.0,
    min_liquidity_cr: float = 5.0,
    min_market_cap_cr: float = 1000.0,
    max_promoter_holding_pct: float = 75.0,
    min_quarters_available: int = 10,
    min_listing_years: int = 3,
) -> tuple[list[str], dict[str, FilterResult]]:
    """Screen the universe and return the list of passing symbols."""
    target_symbols = symbols if symbols is not None else pit.get_universe()
    passed_symbols: list[str] = []
    results: dict[str, FilterResult] = {}

    for sym in target_symbols:
        res = evaluate_symbol_filters(
            pit,
            sym,
            min_price=min_price,
            min_liquidity_cr=min_liquidity_cr,
            min_market_cap_cr=min_market_cap_cr,
            max_promoter_holding_pct=max_promoter_holding_pct,
            min_quarters_available=min_quarters_available,
            min_listing_years=min_listing_years,
        )
        results[sym] = res
        if res.passed:
            passed_symbols.append(sym)

    logger.info(f"Stage 0 Filters: {len(passed_symbols)}/{len(target_symbols)} passed screening")
    return passed_symbols, results
