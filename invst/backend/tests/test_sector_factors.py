"""Unit tests for Sector-Aware Factor Engines (Arth IQ V0.2)."""


from invst.scoring.sectors import (
    SectorArchetype,
    get_sector_archetype,
)
from invst.scoring.sectors.consumer import compute_consumer_quality_score
from invst.scoring.sectors.financials import compute_financials_quality_score
from invst.scoring.sectors.healthcare import compute_healthcare_quality_score
from invst.scoring.sectors.industrials import compute_industrials_quality_score
from invst.scoring.sectors.tech_services import compute_tech_quality_score


def test_sector_archetype_mapping():
    assert get_sector_archetype("banks") == SectorArchetype.FINANCIALS
    assert get_sector_archetype("financial_services") == SectorArchetype.FINANCIALS
    assert get_sector_archetype("it") == SectorArchetype.TECH_SERVICES
    assert get_sector_archetype("industrials") == SectorArchetype.INDUSTRIALS_CAPEX
    assert get_sector_archetype("fmcg") == SectorArchetype.CONSUMER_MOATS
    assert get_sector_archetype("pharma") == SectorArchetype.HEALTHCARE_PHARMA
    assert get_sector_archetype("unknown_sector") == SectorArchetype.DIVERSIFIED


def test_financials_quality_scoring():
    # Strong bank: ROA 2.1%, NIM 4.2%, C2I 42%, PCR 80%, CRAR 18%
    strong_bank = {
        "roa": 2.1,
        "nim": 4.2,
        "cost_to_income": 42.0,
        "pcr": 80.0,
        "crar": 18.0,
    }
    score_strong = compute_financials_quality_score(strong_bank)
    assert score_strong >= 80.0

    # Weak bank: ROA 0.5%, NIM 2.4%, C2I 65%, PCR 52%, CRAR 11%
    weak_bank = {
        "roa": 0.5,
        "nim": 2.4,
        "cost_to_income": 65.0,
        "pcr": 52.0,
        "crar": 11.0,
    }
    score_weak = compute_financials_quality_score(weak_bank)
    assert score_weak <= 35.0


def test_industrials_quality_scoring():
    # Strong industrial: ROCE 24%, CFO/EBITDA 0.85, Int Coverage 10x, Net Debt/EBITDA 0.5x
    strong_ind = {
        "roce": 24.0,
        "cfo_ebitda": 0.85,
        "interest_coverage": 10.0,
        "net_debt_ebitda": 0.5,
    }
    score_strong = compute_industrials_quality_score(strong_ind)
    assert score_strong >= 80.0

    # Distressed industrial: ROCE 6%, CFO/EBITDA 0.35, Int Coverage 1.8x, Net Debt/EBITDA 4.2x
    weak_ind = {
        "roce": 6.0,
        "cfo_ebitda": 0.35,
        "interest_coverage": 1.8,
        "net_debt_ebitda": 4.2,
    }
    score_weak = compute_industrials_quality_score(weak_ind)
    assert score_weak <= 25.0


def test_tech_quality_scoring():
    # Pristine tech: ROIC 35%, FCF/PAT 0.95, EBIT Margin 26%, Attrition 11%
    strong_tech = {
        "roic": 35.0,
        "fcf_to_pat": 0.95,
        "ebit_margin": 26.0,
        "attrition": 11.0,
    }
    score_strong = compute_tech_quality_score(strong_tech)
    assert score_strong >= 85.0


def test_consumer_quality_scoring():
    # Compounding consumer titan: ROCE 42%, WC Days -12, Gross Margin 52%, Pledge 0%
    strong_consumer = {
        "roce": 42.0,
        "working_cap_days": -12.0,
        "gross_margin": 52.0,
        "pledge_pct": 0.0,
    }
    score_strong = compute_consumer_quality_score(strong_consumer)
    assert score_strong >= 85.0


def test_healthcare_fda_warning_penalty():
    # Healthcare with US FDA warning
    fda_issue = {
        "roic": 25.0,
        "rd_sales": 7.5,
        "us_fda_issues": 1.0,  # Warning letter
    }
    score = compute_healthcare_quality_score(fda_issue)
    # The 25 point FDA penalty reduces score significantly
    assert score <= 60.0
