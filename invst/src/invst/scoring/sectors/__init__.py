"""Sector-aware factor modules for Arth IQ V0.2."""

from __future__ import annotations

from typing import Any

from invst.data_access import PointInTimeDataAccess
from invst.scoring.sectors.archetypes import SectorArchetype, get_sector_archetype
from invst.scoring.sectors.consumer import compute_consumer_quality_score, extract_consumer_metrics
from invst.scoring.sectors.financials import (
    compute_financials_quality_score,
    extract_financials_metrics,
)
from invst.scoring.sectors.healthcare import (
    compute_healthcare_quality_score,
    extract_healthcare_metrics,
)
from invst.scoring.sectors.industrials import (
    compute_industrials_quality_score,
    extract_industrials_metrics,
)
from invst.scoring.sectors.tech_services import compute_tech_quality_score, extract_tech_metrics


def extract_sector_metrics(
    pit: PointInTimeDataAccess,
    symbol: str,
    sector: str | None = None,
) -> tuple[SectorArchetype, dict[str, float | None]]:
    """Extract appropriate sector-specialized metrics based on sector archetype."""
    sec = sector or pit.get_sector(symbol)
    archetype = get_sector_archetype(sec)

    if archetype == SectorArchetype.FINANCIALS:
        metrics = extract_financials_metrics(pit, symbol)
    elif archetype == SectorArchetype.TECH_SERVICES:
        metrics = extract_tech_metrics(pit, symbol)
    elif archetype == SectorArchetype.INDUSTRIALS_CAPEX:
        metrics = extract_industrials_metrics(pit, symbol)
    elif archetype == SectorArchetype.CONSUMER_MOATS:
        metrics = extract_consumer_metrics(pit, symbol)
    elif archetype == SectorArchetype.HEALTHCARE_PHARMA:
        metrics = extract_healthcare_metrics(pit, symbol)
    elif archetype in (SectorArchetype.INDEX_ETF, SectorArchetype.COMMODITY_ETF):
        metrics = {"is_etf": 1.0, "expense_ratio": 0.2, "tracking_error": 0.05}
    else:
        # Diversified default to industrials/broad
        metrics = extract_industrials_metrics(pit, symbol)

    return archetype, metrics


def score_sector_quality(
    archetype: SectorArchetype,
    metrics: dict[str, float | None],
) -> float:
    """Compute Quality score using archetype-specific rules."""
    if archetype == SectorArchetype.FINANCIALS:
        return compute_financials_quality_score(metrics)
    elif archetype == SectorArchetype.TECH_SERVICES:
        return compute_tech_quality_score(metrics)
    elif archetype == SectorArchetype.INDUSTRIALS_CAPEX:
        return compute_industrials_quality_score(metrics)
    elif archetype == SectorArchetype.CONSUMER_MOATS:
        return compute_consumer_quality_score(metrics)
    elif archetype == SectorArchetype.HEALTHCARE_PHARMA:
        return compute_healthcare_quality_score(metrics)
    elif archetype in (SectorArchetype.INDEX_ETF, SectorArchetype.COMMODITY_ETF):
        # Index ETFs have institutional durability, broad diversification, and zero single-stock default risk
        return 86.0
    else:
        return compute_industrials_quality_score(metrics)


from invst.scoring.sectors.normalization import normalize_cross_sectional_features_by_sector

__all__ = [
    "SectorArchetype",
    "get_sector_archetype",
    "extract_sector_metrics",
    "score_sector_quality",
    "normalize_cross_sectional_features_by_sector",
]
