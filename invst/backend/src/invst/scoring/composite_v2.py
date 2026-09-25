"""Composite Quant Scoring Engine V0.2 for Arth IQ.

Synthesizes the decoupled two-level scoring architecture:
1. BUSINESS SCORE (0–100): Price-agnostic enterprise durability & growth.
   = 0.60 * Business Quality Score (BQS) + 0.40 * Growth Score
2. INVESTMENT SCORE (0–100): Attractiveness of owning the asset today.
   = 0.40 * Business Score + 0.35 * Valuation Score + 0.25 * Risk Score
   (gated by Market Engine execution friction & liquidity)

Categorizes securities into actionable Investment Matrix Quadrants:
- Core Compounding Alpha (High Quality + Margin of Safety)
- Quality Trap / Overpriced (High Quality + Stretched Valuation)
- Deep Value / Cyclical Rebound (Low Quality + Extreme Cheapness)
- Value Trap / Distressed (Low Quality + Low Valuation)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from invst.data_access import PointInTimeDataAccess
from invst.scoring.business_quality import BusinessQualityResult, evaluate_business_quality
from invst.scoring.event_intelligence import EventImpactSummary, compute_event_factor_deltas
from invst.scoring.growth import GrowthResult, evaluate_growth
from invst.scoring.market import MarketResult, evaluate_market_engine
from invst.scoring.risk_v2 import RiskV2Result, evaluate_risk_v2
from invst.scoring.scenarios import ScenarioResult, evaluate_scenarios
from invst.scoring.sectors import get_sector_archetype
from invst.scoring.valuation_v2 import ValuationV2Result, evaluate_valuation_v2

logger = logging.getLogger(__name__)


@dataclass
class StockScorecardV2:
    symbol: str
    sector: str
    sector_archetype: str
    rank: int
    investment_score: float  # Core decision metric
    business_score: float    # Enterprise quality
    growth_score: float
    growth_confidence: float
    valuation_score: float
    risk_score: float
    market_score: float
    matrix_quadrant: str
    scenario: ScenarioResult
    bqs_result: BusinessQualityResult
    growth_result: GrowthResult
    valuation_result: ValuationV2Result
    risk_result: RiskV2Result
    market_result: MarketResult
    event_summary: EventImpactSummary


def determine_matrix_quadrant(business_score: float, valuation_score: float) -> str:
    """Classify into 2x2 Matrix Quadrant."""
    if business_score >= 65.0:
        if valuation_score >= 50.0:
            return "Core Compounding Alpha"
        else:
            return "Quality Trap / Overpriced"
    else:
        if valuation_score >= 50.0:
            return "Deep Value / Cyclical Rebound"
        else:
            return "Value Trap / Distressed"


def compute_scorecards_v2(
    pit: PointInTimeDataAccess,
    symbols: list[str] | None = None,
    sector_filter: str | None = None,
) -> list[StockScorecardV2]:
    """Execute complete V0.2 Quantitative Pipeline across the universe."""
    candidate_symbols = symbols or pit.get_universe()
    if not candidate_symbols:
        return []

    sectors_map = pit.get_universe_with_sectors()
    scorecards: list[StockScorecardV2] = []

    for sym in candidate_symbols:
        sec = sectors_map.get(sym) or pit.get_sector(sym) or "diversified"

        # Apply optional sector filter
        if sector_filter and sec.lower() != sector_filter.lower():
            continue

        archetype = get_sector_archetype(sec)

        # 1. Event Intelligence Deltas
        events = compute_event_factor_deltas(pit, sym)

        # 2. Business Quality
        bqs_res = evaluate_business_quality(pit, sym, sector=sec)
        # Apply event delta to governance
        adjusted_bqs = max(5.0, min(95.0, bqs_res.bqs_score + events.factor_deltas.get("GOVERNANCE", 0.0) * 0.3))

        # 3. Growth Engine
        growth_res = evaluate_growth(pit, sym)
        adjusted_growth = max(5.0, min(95.0, growth_res.growth_score + events.factor_deltas.get("GROWTH", 0.0) * 0.4))

        # LEVEL 1 SYNTHESIS: BUSINESS SCORE (Price-Agnostic)
        biz_score = (0.60 * adjusted_bqs) + (0.40 * adjusted_growth)
        biz_score = round(max(5.0, min(98.0, biz_score)), 2)

        # 4. Valuation Engine
        val_res = evaluate_valuation_v2(pit, sym, sector=sec)
        adjusted_val = max(5.0, min(95.0, val_res.valuation_score + events.factor_deltas.get("VALUATION", 0.0) * 0.3))

        # 5. Risk Engine
        risk_res = evaluate_risk_v2(pit, sym, sector=sec)
        adjusted_risk = max(5.0, min(95.0, risk_res.risk_score + events.factor_deltas.get("RISK", 0.0) * 0.4))

        # 6. Market Engine & Execution
        mkt_res = evaluate_market_engine(pit, sym)

        # 7. Scenarios & Probabilities
        scen_res = evaluate_scenarios(
            pit,
            sym,
            growth_cagr=growth_res.historical_growth_cagr,
            earnings_yield=val_res.earnings_yield,
        )

        # LEVEL 2 SYNTHESIS: INVESTMENT SCORE
        # Formula: 40% Business + 35% Valuation + 25% Risk
        inv_score = (0.40 * biz_score) + (0.35 * adjusted_val) + (0.25 * adjusted_risk)

        # Execution friction gate: downweight if illiquid or severe downward trend
        if not mkt_res.execution_favorable:
            inv_score *= 0.90

        inv_score = round(max(5.0, min(98.0, inv_score)), 2)
        quadrant = determine_matrix_quadrant(biz_score, adjusted_val)

        scorecards.append(
            StockScorecardV2(
                symbol=sym,
                sector=sec,
                sector_archetype=archetype.value,
                rank=0,  # will assign below
                investment_score=inv_score,
                business_score=biz_score,
                growth_score=round(adjusted_growth, 2),
                growth_confidence=growth_res.growth_confidence,
                valuation_score=round(adjusted_val, 2),
                risk_score=round(adjusted_risk, 2),
                market_score=mkt_res.market_score,
                matrix_quadrant=quadrant,
                scenario=scen_res,
                bqs_result=bqs_res,
                growth_result=growth_res,
                valuation_result=val_res,
                risk_result=risk_res,
                market_result=mkt_res,
                event_summary=events,
            )
        )

    # Sort descending by Investment Score
    scorecards.sort(key=lambda sc: sc.investment_score, reverse=True)

    # Assign ranks
    for idx, sc in enumerate(scorecards):
        sc.rank = idx + 1

    return scorecards
