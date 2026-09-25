"""Stage 2: Valuation Scoring.

Evaluates valuation multiples against sector averages:
- P/E (TTM) — 30% (lower better)
- P/B — 20% (lower better)
- EV/EBITDA — 30% (lower better)
- Dividend yield — 10% (higher better)
- PEG (P/E / 5-yr growth) — 10% (lower better)

Scores are z-scored within sector and normalized to a 0–100 scale.
"""

from __future__ import annotations

import logging
from typing import Any

from invst.data_access import PointInTimeDataAccess
from invst.scoring.quality import z_score_metrics

logger = logging.getLogger(__name__)

DEFAULT_VALUATION_WEIGHTS = {
    "pe_ttm": 0.30,
    "pb": 0.20,
    "ev_ebitda": 0.30,
    "dividend_yield": 0.10,
    "peg": 0.10,
}

# Metrics where lower is cheaper/better
INVERTED_VALUATION_METRICS = {"pe_ttm", "pb", "ev_ebitda", "peg"}


def extract_valuation_metrics(
    pit: PointInTimeDataAccess,
    symbol: str,
) -> dict[str, float | None]:
    """Extract raw valuation metrics for a given symbol."""
    pe = pit.get_fundamental(symbol, "pe_ttm")
    pb = pit.get_fundamental(symbol, "pb")
    ev_ebitda = pit.get_fundamental(symbol, "ev_ebitda")
    div_yield = pit.get_fundamental(symbol, "dividend_yield")
    peg = pit.get_fundamental(symbol, "peg")

    # If PEG is not directly available, attempt calculation if growth and PE exist
    if peg is None and pe is not None and pe > 0:
        cagr = pit.get_fundamental(symbol, "earnings_cagr_5yr")
        if cagr and cagr > 0:
            peg = round(pe / cagr, 2)

    return {
        "pe_ttm": pe,
        "pb": pb,
        "ev_ebitda": ev_ebitda,
        "dividend_yield": div_yield,
        "peg": peg,
    }


def score_valuation_universe(
    pit: PointInTimeDataAccess,
    symbols: list[str],
    weights: dict[str, float] | None = None,
) -> dict[str, dict[str, Any]]:
    """Compute Valuation scores for all given symbols, z-scored within sector."""
    w = weights or DEFAULT_VALUATION_WEIGHTS

    sectors_map = pit.get_universe_with_sectors()
    by_sector: dict[str, list[str]] = {}
    for sym in symbols:
        sec = sectors_map.get(sym) or pit.get_sector(sym) or "diversified"
        by_sector.setdefault(sec, []).append(sym)

    results: dict[str, dict[str, Any]] = {}

    for sec, sec_symbols in by_sector.items():
        raw_data = {sym: extract_valuation_metrics(pit, sym) for sym in sec_symbols}

        metric_z_scores: dict[str, dict[str, float]] = {}
        for metric_name in w:
            metric_vals = {sym: raw_data[sym].get(metric_name) for sym in sec_symbols}
            invert = metric_name in INVERTED_VALUATION_METRICS
            metric_z_scores[metric_name] = z_score_metrics(metric_vals, invert=invert)

        for sym in sec_symbols:
            comp_z = 0.0
            for metric_name, weight in w.items():
                comp_z += weight * metric_z_scores[metric_name].get(sym, 0.0)

            scaled_score = max(0.0, min(100.0, 50.0 + comp_z * 16.667))

            results[sym] = {
                "valuation_score": round(scaled_score, 2),
                "valuation_z": round(comp_z, 3),
                "sector": sec,
                "metrics": raw_data[sym],
            }

    return results
