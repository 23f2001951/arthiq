"""Sector Archetypes and Classification for Arth IQ V0.2.

Maps diverse Indian industry sectors into 5 fundamental Economic Archetypes:
1. FINANCIALS: Banks, NBFCs, Housing Finance (HDFCBANK, ICICIBANK, BAJFINANCE)
2. TECH_SERVICES: IT Services, SaaS, Digital Platforms (TCS, INFY, HCLTECH)
3. INDUSTRIALS_CAPEX: Infra, Capital Goods, Energy, Metals, Utilities (LT, RELIANCE, NTPC)
4. CONSUMER_MOATS: FMCG, Retail, Auto OEMs, Durables (HINDUNILVR, TITAN, MARUTI)
5. HEALTHCARE_PHARMA: Formulations, API, Hospitals, Diagnostics (SUNPHARMA, CIPLA, APOLLOHOSP)
"""

from __future__ import annotations

from enum import Enum


class SectorArchetype(str, Enum):
    FINANCIALS = "FINANCIALS"
    TECH_SERVICES = "TECH_SERVICES"
    INDUSTRIALS_CAPEX = "INDUSTRIALS_CAPEX"
    CONSUMER_MOATS = "CONSUMER_MOATS"
    HEALTHCARE_PHARMA = "HEALTHCARE_PHARMA"
    INDEX_ETF = "INDEX_ETF"
    COMMODITY_ETF = "COMMODITY_ETF"
    DIVERSIFIED = "DIVERSIFIED"


# Comprehensive mapping from NSE sectors to Archetypes
SECTOR_TO_ARCHETYPE: dict[str, SectorArchetype] = {
    # Financials
    "financial_services": SectorArchetype.FINANCIALS,
    "financials": SectorArchetype.FINANCIALS,
    "banks": SectorArchetype.FINANCIALS,
    "banking": SectorArchetype.FINANCIALS,
    "nbfc": SectorArchetype.FINANCIALS,
    "insurance": SectorArchetype.FINANCIALS,
    "housing_finance": SectorArchetype.FINANCIALS,

    # Tech & Knowledge
    "information_technology": SectorArchetype.TECH_SERVICES,
    "it": SectorArchetype.TECH_SERVICES,
    "technology": SectorArchetype.TECH_SERVICES,
    "software": SectorArchetype.TECH_SERVICES,
    "telecom": SectorArchetype.TECH_SERVICES,

    # Heavy Assets & Industrials
    "industrials": SectorArchetype.INDUSTRIALS_CAPEX,
    "capital_goods": SectorArchetype.INDUSTRIALS_CAPEX,
    "infrastructure": SectorArchetype.INDUSTRIALS_CAPEX,
    "construction": SectorArchetype.INDUSTRIALS_CAPEX,
    "energy": SectorArchetype.INDUSTRIALS_CAPEX,
    "oil_and_gas": SectorArchetype.INDUSTRIALS_CAPEX,
    "power": SectorArchetype.INDUSTRIALS_CAPEX,
    "utilities": SectorArchetype.INDUSTRIALS_CAPEX,
    "metals": SectorArchetype.INDUSTRIALS_CAPEX,
    "metals_and_mining": SectorArchetype.INDUSTRIALS_CAPEX,
    "cement": SectorArchetype.INDUSTRIALS_CAPEX,
    "chemicals": SectorArchetype.INDUSTRIALS_CAPEX,
    "real_estate": SectorArchetype.INDUSTRIALS_CAPEX,
    "realty": SectorArchetype.INDUSTRIALS_CAPEX,

    # Consumer & Retail
    "consumer": SectorArchetype.CONSUMER_MOATS,
    "consumer_goods": SectorArchetype.CONSUMER_MOATS,
    "consumer_durables": SectorArchetype.CONSUMER_MOATS,
    "fmcg": SectorArchetype.CONSUMER_MOATS,
    "automobile": SectorArchetype.CONSUMER_MOATS,
    "auto": SectorArchetype.CONSUMER_MOATS,
    "retail": SectorArchetype.CONSUMER_MOATS,
    "textiles": SectorArchetype.CONSUMER_MOATS,

    # Healthcare & Life Sciences
    "healthcare": SectorArchetype.HEALTHCARE_PHARMA,
    "pharma": SectorArchetype.HEALTHCARE_PHARMA,
    "pharmaceuticals": SectorArchetype.HEALTHCARE_PHARMA,
    "life_sciences": SectorArchetype.HEALTHCARE_PHARMA,
    "hospitals": SectorArchetype.HEALTHCARE_PHARMA,
    "diagnostics": SectorArchetype.HEALTHCARE_PHARMA,

    # ETFs & Index Funds
    "etf": SectorArchetype.INDEX_ETF,
    "index_etf": SectorArchetype.INDEX_ETF,
    "index_fund": SectorArchetype.INDEX_ETF,
    "mutual_fund": SectorArchetype.INDEX_ETF,
    "commodity_etf": SectorArchetype.COMMODITY_ETF,
    "gold_etf": SectorArchetype.COMMODITY_ETF,
    "silver_etf": SectorArchetype.COMMODITY_ETF,
}


def get_sector_archetype(sector: str | None) -> SectorArchetype:
    """Resolve raw sector name to a standard SectorArchetype."""
    if not sector:
        return SectorArchetype.DIVERSIFIED
    norm = sector.strip().lower().replace(" ", "_").replace("-", "_")
    return SECTOR_TO_ARCHETYPE.get(norm, SectorArchetype.DIVERSIFIED)
