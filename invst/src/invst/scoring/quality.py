"""Stage 1: Fundamentals & Quality Scoring.

Scores companies on five-year averages and balance-sheet health:
- ROE (5-yr avg) — 25%
- ROCE (5-yr avg) — 25%
- Debt / Equity — 15% (lower better)
- Interest coverage — 10% (higher better)
- Earnings growth CAGR (5-yr) — 15% (higher better)
- OCF / Net profit — 10% (higher better, >= 0.8 preferred)

Scores are z-scored within sector and normalized to a 0–100 scale.
"""

from __future__ import annotations

import logging
import math
from typing import Any

from invst.data_access import PointInTimeDataAccess

logger = logging.getLogger(__name__)

DEFAULT_QUALITY_WEIGHTS = {
    "roe_5yr_avg": 0.25,
    "roce_5yr_avg": 0.25,
    "debt_equity": 0.15,
    "interest_coverage": 0.10,
    "earnings_cagr_5yr": 0.15,
    "ocf_to_net_profit": 0.10,
}

INVERTED_METRICS = {"debt_equity"}


def compute_metric_avg(
    pit: PointInTimeDataAccess, symbol: str, metric: str, n_quarters: int = 20
) -> float | None:
    """Compute multi-year average for a metric from point-in-time quarterly history."""
    history = pit.get_fundamental_history(symbol, metric, n_quarters=n_quarters)
    if not history:
        # Fallback to single latest value
        return pit.get_fundamental(symbol, metric)
    vals = [h.value for h in history if h.value is not None]
    return sum(vals) / len(vals) if vals else None


def extract_quality_metrics(
    pit: PointInTimeDataAccess,
    symbol: str,
) -> dict[str, float | None]:
    """Extract all raw Quality metrics for a given symbol."""
    return {
        "roe_5yr_avg": compute_metric_avg(pit, symbol, "roe", n_quarters=20),
        "roce_5yr_avg": compute_metric_avg(pit, symbol, "roce", n_quarters=20),
        "debt_equity": pit.get_fundamental(symbol, "debt_equity"),
        "interest_coverage": pit.get_fundamental(symbol, "interest_coverage"),
        "earnings_cagr_5yr": pit.get_fundamental(symbol, "earnings_cagr_5yr"),
        "ocf_to_net_profit": pit.get_fundamental(symbol, "ocf_to_net_profit"),
    }


def z_score_metrics(
    values_by_symbol: dict[str, float | None],
    invert: bool = False,
    clip_range: tuple[float, float] = (-3.0, 3.0),
) -> dict[str, float]:
    """Standardize a single metric cross-sectionally using z-scores."""
    valid_vals = [v for v in values_by_symbol.values() if v is not None and not math.isnan(v)]
    if not valid_vals:
        return dict.fromkeys(values_by_symbol, 0.0)

    mean = sum(valid_vals) / len(valid_vals)
    variance = sum((x - mean) ** 2 for x in valid_vals) / max(len(valid_vals) - 1, 1)
    std = math.sqrt(variance) if variance > 1e-8 else 1.0

    z_scores = {}
    for sym, val in values_by_symbol.items():
        if val is None or math.isnan(val):
            z = 0.0
        else:
            z = (val - mean) / std
            if invert:
                z = -z
            z = max(clip_range[0], min(clip_range[1], z))
        z_scores[sym] = z

    return z_scores


def score_quality_universe(
    pit: PointInTimeDataAccess,
    symbols: list[str],
    weights: dict[str, float] | None = None,
) -> dict[str, dict[str, Any]]:
    """Compute Quality scores for all given symbols, z-scored within sector."""
    w = weights or DEFAULT_QUALITY_WEIGHTS

    # Group symbols by sector
    sectors_map = pit.get_universe_with_sectors()
    by_sector: dict[str, list[str]] = {}
    for sym in symbols:
        sec = sectors_map.get(sym) or pit.get_sector(sym) or "diversified"
        by_sector.setdefault(sec, []).append(sym)

    results: dict[str, dict[str, Any]] = {}

    for sec, sec_symbols in by_sector.items():
        # Extract raw metrics
        raw_data = {sym: extract_quality_metrics(pit, sym) for sym in sec_symbols}

        # Compute z-scores per metric within sector
        metric_z_scores: dict[str, dict[str, float]] = {}
        for metric_name in w:
            metric_vals = {sym: raw_data[sym].get(metric_name) for sym in sec_symbols}
            invert = metric_name in INVERTED_METRICS
            metric_z_scores[metric_name] = z_score_metrics(metric_vals, invert=invert)

        # Aggregate weighted z-scores into 0–100 score
        for sym in sec_symbols:
            comp_z = 0.0
            for metric_name, weight in w.items():
                comp_z += weight * metric_z_scores[metric_name].get(sym, 0.0)

            # Map z in [-3, +3] to [0, 100] with mean 50
            scaled_score = max(0.0, min(100.0, 50.0 + comp_z * 16.667))

            results[sym] = {
                "quality_score": round(scaled_score, 2),
                "quality_z": round(comp_z, 3),
                "sector": sec,
                "metrics": raw_data[sym],
            }

    return results
