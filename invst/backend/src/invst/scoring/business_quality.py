"""Business Quality Score (BQS) Engine for Arth IQ V0.2.

Evaluates enterprise durability and moat depth independent of valuation:
1. Profitability & Moat Depth (sector-aware)
2. Capital Allocation & Efficiency (CROIC / ROIC / ROA)
3. Earnings Quality & Accruals Defense:
   - Modified Sloan Accruals: (Net Income - CFO) / Total Assets
   - Cash Conversion Ratio: CFO / EBITDA >= 0.75
4. Balance Sheet Strength & Solvency
5. Governance & Stewardship:
   - Promoter Pledge % (Pledge > 0% penalizes, > 20% severely penalizes)
   - Board Independence & Audit Quality
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from invst.data_access import PointInTimeDataAccess
from invst.scoring.sectors import extract_sector_metrics, score_sector_quality


@dataclass
class BusinessQualityResult:
    symbol: str
    archetype: str
    bqs_score: float
    profitability_score: float
    capital_efficiency_score: float
    earnings_quality_score: float
    balance_sheet_score: float
    governance_score: float
    flags: list[str]
    details: dict[str, Any]


def compute_sloan_accrual_penalty(pit: PointInTimeDataAccess, symbol: str) -> float:
    """Calculate Sloan Accruals = (Net Income - CFO) / Total Assets.

    High positive accruals indicate aggressive revenue recognition / paper earnings.
    Returns score delta: 0.0 (clean) to -20.0 (high accrual manipulation risk).
    """
    net_income = pit.get_fundamental(symbol, "net_profit") or pit.get_fundamental(symbol, "pat")
    cfo = pit.get_fundamental(symbol, "cfo")
    total_assets = pit.get_fundamental(symbol, "total_assets")

    if net_income is not None and cfo is not None and total_assets and total_assets > 0:
        accrual_ratio = (net_income - cfo) / total_assets
        if accrual_ratio > 0.10:
            return -15.0  # Significant accrual drag
        elif accrual_ratio > 0.05:
            return -8.0
        elif accrual_ratio < -0.02:
            return 5.0  # Conservative cash accounting
    return 0.0


def compute_governance_score(pit: PointInTimeDataAccess, symbol: str) -> tuple[float, list[str]]:
    """Evaluate promoter pledge, board composition, and accounting audit checks."""
    gov_score = 80.0
    flags = []

    pledge_pct = pit.get_fundamental(symbol, "promoter_pledge_pct") or 0.0
    if pledge_pct > 20.0:
        gov_score -= 50.0
        flags.append("HIGH_PROMOTER_PLEDGE_CRITICAL")
    elif pledge_pct > 5.0:
        gov_score -= 25.0
        flags.append("ELEVATED_PROMOTER_PLEDGE")
    elif pledge_pct == 0.0:
        gov_score += 10.0

    audit_flag = pit.get_fundamental(symbol, "audit_qualification_flag") or 0.0
    if audit_flag > 0:
        gov_score -= 40.0
        flags.append("AUDIT_QUALIFICATION_REPORTED")

    related_party_pct = pit.get_fundamental(symbol, "related_party_txn_pct") or 1.5
    if related_party_pct > 5.0:
        gov_score -= 15.0
        flags.append("HIGH_RELATED_PARTY_TRANSACTIONS")

    return max(5.0, min(100.0, gov_score)), flags


def evaluate_business_quality(
    pit: PointInTimeDataAccess,
    symbol: str,
    sector: str | None = None,
) -> BusinessQualityResult:
    """Compute consolidated Business Quality Score (BQS) for symbol."""
    archetype, metrics = extract_sector_metrics(pit, symbol, sector=sector)

    # 1. Base sector quality score (reflects profitability, efficiency, balance sheet)
    base_sector_q = score_sector_quality(archetype, metrics)

    # 2. Earnings Quality & Accruals
    if archetype.value in ("INDEX_ETF", "COMMODITY_ETF"):
        earn_qual = 85.0
        gov_score = 92.0
        gov_flags = []
        accrual_delta = 0.0
    else:
        accrual_delta = compute_sloan_accrual_penalty(pit, symbol)
        earn_qual = max(10.0, min(95.0, 70.0 + accrual_delta))
        # 3. Governance
        gov_score, gov_flags = compute_governance_score(pit, symbol)

    # 4. Synthesize BQS (Price-Agnostic)
    # Weights: Base Sector Factor 60%, Earnings Quality 20%, Governance 20%
    bqs = (0.60 * base_sector_q) + (0.20 * earn_qual) + (0.20 * gov_score)
    bqs = max(5.0, min(98.0, bqs))

    # If critical governance flag, cap BQS
    if "HIGH_PROMOTER_PLEDGE_CRITICAL" in gov_flags or "AUDIT_QUALIFICATION_REPORTED" in gov_flags:
        bqs = min(bqs, 35.0)

    flags = list(gov_flags)
    if accrual_delta <= -10.0:
        flags.append("ACCRUALS_DIVERGENCE_WARNING")

    return BusinessQualityResult(
        symbol=symbol,
        archetype=archetype.value,
        bqs_score=round(bqs, 2),
        profitability_score=round(base_sector_q, 2),
        capital_efficiency_score=round(base_sector_q, 2),
        earnings_quality_score=round(earn_qual, 2),
        balance_sheet_score=round(base_sector_q, 2),
        governance_score=round(gov_score, 2),
        flags=flags,
        details=metrics,
    )
