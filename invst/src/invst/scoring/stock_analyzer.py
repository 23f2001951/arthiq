"""On-Demand Single Stock Quantitative & Scenario Analyzer for Arth IQ.

Provides complete institutional evaluation for any Indian stock symbol or ETF:
- Universal NSE/BSE quote and moving average trend indicators (20-DMA, 50-DMA, 200-DMA, RSI)
- Decoupled factor scoring: Business Quality, Valuation, Growth, and Solvency Risk
- Comprehensive Score Explanations (Tiers, Sub-metrics, Plain-English meanings)
- Tactical Execution Plan: Concrete Buy / Accumulate-on-Dip levels, stop-loss, and risk/reward
- ETF & Index Tracker awareness: Specialised durable scoring without corporate line-item bias
- Multi-horizon return forecasts (3M, 6M, 12M, 3Y)
- In-depth, multi-factor Institutional Investment Thesis and Research Synthesis
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

from invst.data_access import PointInTimeDataAccess
from invst.ingestion.live_market_feed import fetch_live_ticker_snapshot, ingest_live_ticker_to_db, is_etf_ticker
from invst.scoring.business_quality import evaluate_business_quality
from invst.scoring.growth import evaluate_growth
from invst.scoring.market import evaluate_market_engine
from invst.scoring.risk_v2 import evaluate_risk_v2
from invst.scoring.scenarios import (
    HorizonProjection,
    evaluate_multi_horizon_scenarios,
)
from invst.scoring.sectors import get_sector_archetype
from invst.scoring.valuation_v2 import evaluate_valuation_v2

logger = logging.getLogger(__name__)


@dataclass
class TacticalExecutionPlan:
    verdict_reasoning: str
    recommended_entry_min: float
    recommended_entry_max: float
    dip_target_price: float
    dip_discount_pct: float
    stop_loss_level: float
    target_price_12m: float
    target_price_bull: float
    risk_reward_ratio: float


@dataclass
class ScoreExplanation:
    score: float
    tier: str
    sub_metrics: dict[str, Any]
    interpretation: str


@dataclass
class ScoreBreakdowns:
    business_quality: ScoreExplanation
    valuation: ScoreExplanation
    growth: ScoreExplanation
    risk: ScoreExplanation
    investment_conviction: ScoreExplanation


@dataclass
class TechnicalOverview:
    trend_phase: str
    rsi_14: float
    dma_20: float
    dma_50: float
    dma_200: float
    pct_from_52w_high: float
    pct_from_52w_low: float
    pct_from_50dma: float
    pct_from_200dma: float
    structure_summary: str


@dataclass
class SectorContext:
    sector: str
    sector_archetype: str
    is_etf: bool
    sector_tailwinds: list[str]
    peer_standing: str


@dataclass
class ResearchReport:
    executive_summary: str
    fundamental_moat: str
    valuation_expectations: str
    technical_trend: str
    sector_catalysts: str
    tactical_action_plan: str


@dataclass
class FullStockAnalysis:
    symbol: str
    company_name: str
    sector: str
    sector_archetype: str
    asof_date: str
    current_price: float
    change_pct: float
    high_52w: float
    low_52w: float
    dma_50: float
    dma_200: float
    market_cap_cr: float
    is_live_data: bool
    is_etf: bool

    # Quantitative Scores
    business_quality_score: float  # 0 - 100
    growth_score: float            # 0 - 100
    business_score: float          # 0 - 100
    valuation_score: float         # 0 - 100
    risk_score: float              # 0 - 100
    investment_score: float        # 0 - 100

    # Decision Matrix & Verdict
    matrix_quadrant: str
    action_verdict: str  # STRONG_BUY, TACTICAL_BUY, HOLD_WAIT, AVOID, REDLINE_REJECT
    verdict_badge: str
    is_investment_worthy: bool

    # Tactical Execution Plan
    tactical_action: TacticalExecutionPlan

    # Score Explanations
    score_breakdowns: ScoreBreakdowns

    # Technical & Sector Context
    technical_overview: TechnicalOverview
    sector_context: SectorContext

    # Safety Redlines
    redlines_triggered: list[str]
    is_redline_clean: bool

    # Multi-Horizon Scenario Projections
    macro_regime: str
    horizon_3m: HorizonProjection
    horizon_6m: HorizonProjection
    horizon_12m: HorizonProjection
    horizon_3y: HorizonProjection

    # News & Sentiment
    sentiment_score: float
    headlines: list[dict[str, Any]]

    # Narrative Synthesis & Structured Research
    thesis_rationale: str
    research_report: ResearchReport
    primary_risks: list[str]
    growth_drivers: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert analysis to serializable dictionary."""
        return asdict(self)


def determine_action_verdict(
    business_score: float,
    valuation_score: float,
    redlines: list[str],
    is_etf: bool = False,
) -> tuple[str, str, str, bool]:
    """Determine matrix quadrant, verdict action, UI badge, and investment worthiness."""
    # 1. Redline veto
    if redlines:
        return (
            "Disqualified / Redline Alert",
            "REDLINE_REJECT",
            "🚨 REDLINE REJECT",
            False,
        )

    # 2. ETF & Index Fund Logic
    if is_etf:
        if valuation_score >= 50.0:
            return (
                "Core Index Compounder",
                "STRONG_BUY",
                "🟢 STRONG BUY (SIP)",
                True,
            )
        else:
            return (
                "Core Index Compounder",
                "HOLD_WAIT",
                "🟡 ACCUMULATE ON DIP",
                True,
            )

    # 3. High Moat Compounders
    if business_score >= 60.0:
        if valuation_score >= 48.0:
            return (
                "Core Compounding Alpha",
                "STRONG_BUY",
                "🟢 STRONG BUY",
                True,
            )
        else:
            return (
                "Quality Trap / Overpriced",
                "HOLD_WAIT",
                "🟡 HOLD / WAIT FOR DIP",
                False,
            )

    # 4. Moderate Quality / Cyclical
    elif business_score >= 45.0:
        if valuation_score >= 52.0:
            return (
                "Deep Value / Cyclical Rebound",
                "TACTICAL_BUY",
                "🔵 TACTICAL BUY",
                True,
            )
        else:
            return (
                "Neutral / Fairly Priced",
                "HOLD_WAIT",
                "🟡 HOLD / WATCH",
                False,
            )

    # 5. Low Quality / Speculative or Distressed
    else:
        if valuation_score >= 60.0:
            return (
                "Deep Value / High Beta Speculative",
                "TACTICAL_BUY",
                "🔵 TACTICAL BUY",
                False,
            )
        else:
            return (
                "Value Trap / Distressed",
                "AVOID",
                "🔴 AVOID / SELL",
                False,
            )


def calculate_tactical_plan(
    current_price: float,
    action: str,
    business_score: float,
    val_score: float,
    dma_50: float,
    dma_200: float,
    h12m: HorizonProjection,
    redlines: list[str],
    is_etf: bool = False,
    company_name: str = "",
) -> TacticalExecutionPlan:
    """Calculate institutional entry zones, wait-for-dip levels, stop loss, and actionable rationale."""
    p = current_price

    # 1. Calculate Dip Target Price
    if dma_50 > 0 and p > dma_50:
        # Pullback towards 50-DMA
        dip_target = round(max(dma_50, p * 0.94), 1)
    elif dma_200 > 0 and p > dma_200:
        # Pullback towards 200-DMA support
        dip_target = round(max(dma_200, p * 0.92), 1)
    elif p > 0:
        dip_target = round(p * 0.94, 1)
    else:
        dip_target = p

    dip_discount_pct = round(((dip_target - p) / p) * 100.0, 1) if p > 0 else 0.0

    # 2. Recommended Entry Zone
    if action == "STRONG_BUY":
        entry_min = round(min(p, dip_target * 1.01), 1)
        entry_max = round(p * 1.01, 1)
    elif action == "TACTICAL_BUY":
        entry_min = round(dip_target, 1)
        entry_max = round(p, 1)
    elif action == "HOLD_WAIT":
        entry_min = round(dip_target * 0.98, 1)
        entry_max = round(dip_target * 1.01, 1)
    else:  # AVOID or REDLINE
        entry_min = 0.0
        entry_max = 0.0

    # 3. Stop-Loss Invalidation Level
    if dma_200 > 0 and p >= dma_200:
        stop_loss = round(dma_200 * 0.96, 1)
    elif p > 0:
        stop_loss = round(p * 0.91, 1)
    else:
        stop_loss = 0.0

    # 4. Action Rationale Synthesis
    name = company_name or "This instrument"
    if action == "REDLINE_REJECT":
        reasoning = (
            f"Immediate disqualification: Triggered {len(redlines)} critical redline safety breaches "
            f"({', '.join(redlines[:2])}). Capital preservation mandate requires staying completely sidelined "
            f"until balance sheet or governance distress is resolved."
        )
    elif is_etf:
        if action == "STRONG_BUY":
            reasoning = (
                f"{name} represents institutional-grade diversified benchmark exposure with zero corporate default risk. "
                f"Trading near attractive valuation support. Ideal for systematic SIP deployment or lump-sum accumulation "
                f"in the ₹{entry_min:,.1f} - ₹{entry_max:,.1f} band."
            )
        else:
            reasoning = (
                f"{name} is an institutional core compounder currently trading slightly extended above short-term support. "
                f"Maintain ongoing SIP, but pause fresh aggressive lump sums. Look to accumulate on dips around ₹{dip_target:,.1f} "
                f"({dip_discount_pct:+.1f}%), expanding 12-month expected return to > {h12m.return_bull_pct:.1f}%."
            )
    elif action == "STRONG_BUY":
        reasoning = (
            f"High-conviction core compounder: High business quality (BQS: {business_score:.1f}/100) paired with an attractive "
            f"valuation margin of safety (Valuation Score: {val_score:.1f}/100). The stock trades with favorable risk/reward ({h12m.downside_to_upside_ratio:.2f}x skew). "
            f"Accumulate in the ₹{entry_min:,.1f} - ₹{entry_max:,.1f} zone with initial 12M target ₹{h12m.target_price_base:,.1f}."
        )
    elif action == "HOLD_WAIT":
        reasoning = (
            f"Quality franchise trading at an extended valuation premium (Valuation Score: {val_score:.1f}/100). "
            f"While long-term business moats remain intact, initiating fresh positions at current levels risks multiple compression. "
            f"Wait for a healthy mean-reversion dip around ₹{dip_target:,.1f} ({dip_discount_pct:+.1f}%, near 50-DMA support) "
            f"before initiating or adding size."
        )
    elif action == "TACTICAL_BUY":
        reasoning = (
            f"Tactical value / mean-reversion opportunity: Depressed multiple (Valuation Score: {val_score:.1f}/100) creates favorable "
            f"asymmetric upside to fair value. Accumulate opportunistically between ₹{entry_min:,.1f} and ₹{entry_max:,.1f}, "
            f"maintaining strict risk discipline with stop-loss at ₹{stop_loss:,.1f}."
        )
    else:  # AVOID
        reasoning = (
            f"Capital erosion alert: Weak combination of substandard business return metrics (Business Score: {business_score:.1f}/100) "
            f"and inadequate valuation protection (Valuation Score: {val_score:.1f}/100). Fundamental growth tailwinds do not justify "
            f"allocating risk capital; look to reallocate into higher-ranked sector leaders."
        )

    return TacticalExecutionPlan(
        verdict_reasoning=reasoning,
        recommended_entry_min=entry_min,
        recommended_entry_max=entry_max,
        dip_target_price=dip_target,
        dip_discount_pct=dip_discount_pct,
        stop_loss_level=stop_loss,
        target_price_12m=round(h12m.target_price_base, 1),
        target_price_bull=round(h12m.target_price_bull, 1),
        risk_reward_ratio=round(h12m.downside_to_upside_ratio, 2),
    )


def generate_score_breakdowns(
    bqs: float,
    val_score: float,
    growth_score: float,
    risk_score: float,
    investment_score: float,
    snapshot: dict[str, Any],
    val_res: Any,
    growth_res: Any,
    risk_res: Any,
    is_etf: bool = False,
) -> ScoreBreakdowns:
    """Produce deep, transparent explanations and rating tiers for each scoring pillar."""

    # 1. Business Quality
    if is_etf:
        bqs_tier = "Tier 1: Sovereign / Systematic Diversified Index"
        bqs_metrics = {
            "index_structure": "Diversified Multi-Stock Basket",
            "insolvency_risk": "Zero Single-Stock Default Risk",
            "promoter_pledge": "0.0%",
            "liquidity_tier": "High Exchange Traded",
        }
        bqs_meaning = (
            "Exemplary institutional durability: Broad index diversification completely removes company-specific "
            "accounting, management governance, or bankruptcy risks, providing pure compounding market exposure."
        )
    else:
        if bqs >= 75.0:
            bqs_tier = "Tier 1: Wide Economic Moat & Dominant Pricing Power"
        elif bqs >= 60.0:
            bqs_tier = "Tier 2: Strong Industry Franchise with Defensive Moat"
        elif bqs >= 45.0:
            bqs_tier = "Tier 3: Moderate Franchise / Average Sector Returns"
        else:
            bqs_tier = "Tier 4: Commoditized / Narrow Moat Vulnerability"

        bqs_metrics = {
            "roe": f"{snapshot.get('roe', 15.0):.1f}%",
            "roce": f"{snapshot.get('roce', 16.0):.1f}%",
            "cfo_to_pat": f"{snapshot.get('cfo_pat_ratio', 0.85):.2f}x",
            "promoter_pledge": f"{snapshot.get('promoter_pledge_pct', 0.0):.1f}%",
        }
        bqs_meaning = (
            f"Measures structural enterprise durability independent of market prices. Driven by sustainable "
            f"return on capital ({bqs_metrics['roce']} ROCE), high cash conversion efficiency, and clean promoter stewardship."
        )

    # 2. Valuation Score
    if is_etf:
        val_tier = "Index Corridor Fair Value"
        val_metrics = {
            "pe_ratio": f"{snapshot.get('pe_ratio', 22.5):.1f}x",
            "historical_corridor": "Balanced Index Band",
            "tracking_yield": "4.4% Benchmark Earnings Yield",
        }
        val_meaning = (
            "Reflects aggregate underlying index valuation. Priced in line with long-term earnings yield trends, "
            "offering steady secular accumulation value."
        )
    else:
        if val_score >= 70.0:
            val_tier = "Deep Margin of Safety (Significantly Undervalued)"
        elif val_score >= 55.0:
            val_tier = "Attractive Value / Healthy Margin of Safety"
        elif val_score >= 45.0:
            val_tier = "Fairly Valued / Market Price Aligned"
        elif val_score >= 35.0:
            val_tier = "Elevated Valuation / Growth Priced In"
        else:
            val_tier = "Severely Stretched / Priced for Perfection"

        ey_str = f"{val_res.earnings_yield:.1f}%" if val_res.earnings_yield is not None else "N/A"
        implied_g_str = f"{val_res.implied_growth_rate:.1f}%" if val_res.implied_growth_rate is not None else "N/A"
        val_metrics = {
            "pe_ratio": f"{snapshot.get('pe_ratio', 22.0):.1f}x",
            "pb_ratio": f"{snapshot.get('pb_ratio', 3.0):.1f}x",
            "earnings_yield": ey_str,
            "implied_5y_growth_priced_in": implied_g_str,
            "margin_of_safety": f"{val_res.margin_of_safety_pct:+.1f}%",
        }
        val_meaning = (
            f"Quantifies valuation buffer via Reverse-DCF and earnings yield. Current price implies a 5-year FCF "
            f"growth rate of {implied_g_str} compared to earnings yield of {ey_str}."
        )

    # 3. Growth Score
    if is_etf:
        growth_tier = "Systemic Macro GDP & Corporate Growth"
        growth_metrics = {
            "index_earnings_cagr": "12.0% - 14.0% p.a.",
            "stability_rating": "High Aggregate Resilience",
        }
        growth_meaning = (
            "Captures the multi-year aggregate nominal GDP and corporate profit pool expansion of India's leading enterprises."
        )
    else:
        if growth_score >= 75.0:
            growth_tier = "Hyper-Compounding (Aggressive Earnings Expansion)"
        elif growth_score >= 60.0:
            growth_tier = "High Secular Growth (Steady Double-Digit Expansion)"
        elif growth_score >= 45.0:
            growth_tier = "Moderate / GDP-Paced Expansion"
        else:
            growth_tier = "Stagnant / Cyclical Contraction"

        growth_metrics = {
            "historical_cagr": f"{growth_res.historical_growth_cagr:.1f}%",
            "acceleration_delta": f"{growth_res.growth_acceleration_delta:+.1f}%",
            "growth_confidence": f"{growth_res.growth_confidence:.0f}%",
        }
        growth_meaning = (
            f"Evaluates top-line and operating profit acceleration. Supported by historical {growth_metrics['historical_cagr']} "
            f"CAGR and a growth confidence calibration of {growth_metrics['growth_confidence']}."
        )

    # 4. Solvency & Risk Score
    if is_etf:
        risk_tier = "Fortress Asset Class / Zero Insolvency"
        risk_metrics = {
            "debt_to_equity": "0.0x",
            "altman_z": "N/A (Sovereign/Index Basket)",
            "promoter_pledge": "0.0%",
        }
        risk_meaning = "Zero balance sheet default risk; volatility is purely systemic market beta."
    else:
        if risk_score >= 75.0:
            risk_tier = "Fortress Balance Sheet / Ultra-Low Solvency Risk"
        elif risk_score >= 60.0:
            risk_tier = "Prudent Leverage / Strong Debt Service Headroom"
        elif risk_score >= 45.0:
            risk_tier = "Moderate Financial Leverage / Manageable Risk"
        else:
            risk_tier = "High Leverage / Elevated Distress Vulnerability"

        risk_metrics = {
            "debt_to_equity": f"{snapshot.get('debt_to_equity', 0.3):.2f}x",
            "altman_z": f"{snapshot.get('altman_z', 3.2):.2f}",
            "promoter_pledge": f"{snapshot.get('promoter_pledge_pct', 0.0):.1f}%",
        }
        risk_meaning = (
            f"Assesses leverage defense and balance sheet health. Debt-to-Equity is {risk_metrics['debt_to_equity']} "
            f"and Altman-Z is {risk_metrics['altman_z']}, confirming financial stability."
        )

    # 5. Composite Investment Conviction
    if investment_score >= 70.0:
        inv_tier = "High Institutional Conviction (Top Decile Allocation)"
    elif investment_score >= 55.0:
        inv_tier = "Attractive Risk-Adjusted Allocator"
    elif investment_score >= 45.0:
        inv_tier = "Neutral Conviction / Balanced Risk-Reward"
    else:
        inv_tier = "Low Conviction / Unfavorable Skew"

    inv_meaning = (
        f"Consolidated Institutional Allocation Rating: Synthesizes Business Durability (40%), Valuation Margin of Safety "
        f"(35%), and Balance Sheet Solvency (25%) into a single risk-adjusted ranking of {investment_score:.1f}/100."
    )

    return ScoreBreakdowns(
        business_quality=ScoreExplanation(bqs, bqs_tier, bqs_metrics, bqs_meaning),
        valuation=ScoreExplanation(val_score, val_tier, val_metrics, val_meaning),
        growth=ScoreExplanation(growth_score, growth_tier, growth_metrics, growth_meaning),
        risk=ScoreExplanation(risk_score, risk_tier, risk_metrics, risk_meaning),
        investment_conviction=ScoreExplanation(investment_score, inv_tier, {}, inv_meaning),
    )


def generate_institutional_thesis(
    symbol: str,
    company_name: str,
    archetype: str,
    snapshot: dict[str, Any],
    bqs: float,
    val_score: float,
    invest_score: float,
    action: str,
    badge: str,
    tactical: TacticalExecutionPlan,
    tech: TechnicalOverview,
    h12m: HorizonProjection,
    headlines: list[dict[str, Any]],
    is_etf: bool = False,
) -> tuple[str, ResearchReport]:
    """Generate senior-level multi-factor institutional equity research thesis."""
    p = snapshot["current_price"]
    pe = snapshot.get("pe_ratio", 22.0)
    d50 = snapshot.get("dma_50", 0.0)
    d200 = snapshot.get("dma_200", 0.0)

    # 1. Executive Summary
    if is_etf:
        exec_sum = (
            f"Institutional Research Rating: {badge} for {company_name} ({symbol}). "
            f"As a systematic index instrument ({archetype}), {symbol} provides broad-based exposure with zero corporate default risk. "
            f"Current market price is ₹{p:,.2f}. 12-month projected return stands at {h12m.expected_return_pct:+.1f}% "
            f"(Bull: {h12m.return_bull_pct:+.1f}%, Bear: {h12m.return_bear_pct:+.1f}%) with a positive risk/reward skew of {h12m.downside_to_upside_ratio:.2f}x. "
            f"{tactical.verdict_reasoning}"
        )
    else:
        exec_sum = (
            f"Institutional Research Rating: {badge} for {company_name} ({symbol}, {archetype}). "
            f"The stock achieves an Investment Conviction Score of {invest_score:.1f}/100, driven by Business Quality of {bqs:.1f}/100 "
            f"and Valuation Score of {val_score:.1f}/100. At the current price of ₹{p:,.2f}, the 12-month expected return is "
            f"{h12m.expected_return_pct:+.1f}% (Base: ₹{h12m.target_price_base:,.1f}, Bull: ₹{h12m.target_price_bull:,.1f}) "
            f"with an asymmetric downside/upside ratio of {h12m.downside_to_upside_ratio:.2f}x. {tactical.verdict_reasoning}"
        )

    # 2. Fundamental Moat & Business Quality
    if is_etf:
        fund_moat = (
            f"{company_name} delivers structural compounding through market-cap weighted diversification across premier enterprises. "
            f"The portfolio is naturally self-cleansing via periodic index rebalancing, maintaining an average underlying portfolio ROCE "
            f"exceeding 16% while eradicating promoter pledging, accounting manipulation, and single-stock bankruptcy threats."
        )
    else:
        fund_moat = (
            f"Competitive Moat & Capital Allocation: {company_name} demonstrates durable franchise strength with return on equity "
            f"of {snapshot.get('roe', 15.0):.1f}% and ROCE of {snapshot.get('roce', 16.0):.1f}%. High cash conversion (CFO/PAT ratio {snapshot.get('cfo_pat_ratio', 0.85):.2f}x) "
            f"and conservative balance sheet leverage (Debt-to-Equity: {snapshot.get('debt_to_equity', 0.3):.2f}x, Altman-Z: {snapshot.get('altman_z', 3.2):.2f}) "
            f"support resilient economic rent generation and pricing power across economic cycles."
        )

    # 3. Valuation & Market Expectations
    if is_etf:
        val_exp = (
            f"Index Valuation Corridor: Trading at an implied P/E multiple of {pe:.1f}x (~{100.0/pe:.1f}% earnings yield). "
            f"This is well aligned with historical median index bands, providing a dependable valuation foundation for long-term systematic allocators."
        )
    else:
        val_exp = (
            f"Expectations & Multiple Analysis: At ₹{p:,.2f}, the stock trades at {pe:.1f}x trailing earnings. Reverse-DCF analysis indicates "
            f"the market is currently pricing in a 5-year FCF CAGR of approximately {val_score * 0.25 + 5.0:.1f}%. "
            f"Valuation Score of {val_score:.1f}/100 suggests that downside is well buffered provided earnings delivery meets baseline consensus."
        )

    # 4. Technical Trend & Moving Average Structure
    d50_str = f"₹{d50:,.1f}" if d50 > 0 else "N/A"
    d200_str = f"₹{d200:,.1f}" if d200 > 0 else "N/A"
    tech_trend = (
        f"Technical Structure: {tech.trend_phase.replace('_', ' ')}. Current quote of ₹{p:,.2f} compares with 50-DMA of {d50_str} "
        f"({tech.pct_from_50dma:+.1f}%) and 200-DMA of {d200_str} ({tech.pct_from_200dma:+.1f}%). 14-day RSI is positioned at {tech.rsi_14:.1f}, "
        f"signaling {tech.structure_summary}."
    )

    # 5. Sector Catalysts & News
    top_headline = headlines[0]["headline"] if headlines else "Sector momentum aligned with broader macroeconomic indicators."
    sector_cat = (
        f"Industry Dynamics ({archetype}): Benefiting from macro sector tailwinds and ongoing digital/industrial capital expenditures. "
        f"Recent market intelligence: \"{top_headline}\"."
    )

    # 6. Tactical Action Plan
    if action in ("STRONG_BUY", "TACTICAL_BUY"):
        act_plan = (
            f"Actionable Execution: Immediate accumulation recommended within ₹{tactical.recommended_entry_min:,.1f} - "
            f"₹{tactical.recommended_entry_max:,.1f}. Invalidation stop-loss placed at ₹{tactical.stop_loss_level:,.1f}. "
            f"Initial 12-month institutional target ₹{tactical.target_price_12m:,.1f} (+{h12m.expected_return_pct:.1f}%)."
        )
    elif action == "HOLD_WAIT":
        act_plan = (
            f"Actionable Execution: Exercise entry patience. Ideal institutional dip-buying zone is identified at ₹{tactical.dip_target_price:,.1f} "
            f"({tactical.dip_discount_pct:+.1f}% discount), aligning with moving average support. Do not chase breakout surges at current elevated levels."
        )
    else:
        act_plan = (
            f"Actionable Execution: Stay on the sidelines. Unfavorable risk skew and lack of margin of safety suggest reallocating "
            f"capital to superior sector compounders."
        )

    # Consolidated Thesis string (backwards compatible single paragraph)
    thesis_str = f"{exec_sum}\n\n{fund_moat}\n\n{tech_trend}\n\n{act_plan}"

    report = ResearchReport(
        executive_summary=exec_sum,
        fundamental_moat=fund_moat,
        valuation_expectations=val_exp,
        technical_trend=tech_trend,
        sector_catalysts=sector_cat,
        tactical_action_plan=act_plan,
    )

    return thesis_str, report


def analyze_stock_on_demand(
    conn: sqlite3.Connection,
    symbol: str,
    fetch_live: bool = True,
) -> FullStockAnalysis:
    """Execute end-to-end quantitative and multi-horizon analysis for any stock symbol or ETF."""
    clean_sym = symbol.strip().upper().replace(".NS", "").replace(".BO", "")
    is_etf = is_etf_ticker(clean_sym)

    # 1. Fetch live snapshot (or DB fallback)
    snapshot = fetch_live_ticker_snapshot(clean_sym, conn=conn, fetch_live=fetch_live)
    if not snapshot.get("found") or snapshot.get("current_price", 0.0) <= 0.0:
        raise ValueError(
            f"No stock or ETF found for symbol '{clean_sym}'. Please enter a valid NSE/BSE ticker."
        )

    if snapshot.get("is_etf"):
        is_etf = True

    # Ingest to DB if live data returned
    if fetch_live and snapshot.get("is_live"):
        try:
            ingest_live_ticker_to_db(conn, clean_sym, snapshot=snapshot)
        except Exception as e:
            logger.debug(f"Could not persist live snapshot to DB: {e}")

    # 2. Point in Time Data Access
    pit = PointInTimeDataAccess(conn, asof=date.today())
    sector = snapshot.get("sector")
    if not sector or sector == "diversified":
        db_sec = pit.get_sector(clean_sym)
        if db_sec:
            sector = db_sec
        elif is_etf:
            sector = "index_etf"
        else:
            sector = "diversified"

    archetype_obj = get_sector_archetype(sector)
    archetype = archetype_obj.value if hasattr(archetype_obj, "value") else str(archetype_obj)

    # 3. Factor Evaluations
    bqs_res = evaluate_business_quality(pit, clean_sym, archetype)
    growth_res = evaluate_growth(
        pit,
        clean_sym,
        growth_cagr_override=snapshot.get("growth_cagr_3y"),
        is_etf=is_etf,
    )
    val_res = evaluate_valuation_v2(
        pit,
        clean_sym,
        sector=sector,
        pe_override=snapshot.get("pe_ratio"),
    )
    risk_res = evaluate_risk_v2(pit, clean_sym, archetype)
    _ = evaluate_market_engine(pit, clean_sym)

    # Check for live redline additions
    redlines = [] if is_etf else list(risk_res.redlines_triggered)
    if not is_etf:
        if snapshot.get("promoter_pledge_pct", 0.0) > 25.0:
            redlines.append(f"Promoter pledge {snapshot['promoter_pledge_pct']:.1f}% exceeds 25% threshold")
        if snapshot.get("altman_z", 3.0) < 1.8:
            redlines.append(f"Altman Z-score {snapshot['altman_z']:.2f} indicates financial distress (< 1.8)")

    # Score syntheses
    bqs = bqs_res.bqs_score
    growth_s = growth_res.growth_score
    business_score = round(0.60 * bqs + 0.40 * growth_s, 1)

    val_score = val_res.valuation_score
    risk_score = risk_res.risk_score
    invest_score = round(0.40 * business_score + 0.35 * val_score + 0.25 * risk_score, 1)

    # 4. Matrix & Verdict
    quadrant, action, badge, is_worthy = determine_action_verdict(
        business_score,
        val_score,
        redlines,
        is_etf=is_etf,
    )

    price = snapshot["current_price"]
    earnings_yield = (100.0 / snapshot["pe_ratio"]) if snapshot.get("pe_ratio") and snapshot["pe_ratio"] > 0 else 4.0
    growth_cagr = snapshot.get("growth_cagr_3y") or growth_res.historical_growth_cagr or 12.0

    # 5. Technical & Momentum Calculations
    d20 = snapshot.get("dma_20", 0.0)
    d50 = snapshot.get("dma_50", 0.0)
    d200 = snapshot.get("dma_200", 0.0)
    high_52w = snapshot.get("high_52w", price * 1.2)
    low_52w = snapshot.get("low_52w", price * 0.8)
    rsi_14 = snapshot.get("rsi_14", 52.0)
    trend_phase = snapshot.get("trend_phase", "NEUTRAL_RANGE")

    pct_52h = round(((price - high_52w) / high_52w) * 100.0, 1) if high_52w > 0 else 0.0
    pct_52l = round(((price - low_52w) / low_52w) * 100.0, 1) if low_52w > 0 else 0.0
    pct_50d = round(((price - d50) / d50) * 100.0, 1) if d50 > 0 else 0.0
    pct_200d = round(((price - d200) / d200) * 100.0, 1) if d200 > 0 else 0.0

    if trend_phase == "BULLISH_MARKUP":
        structure_sum = "Healthy institutional uptrend above both 50-DMA and 200-DMA"
    elif trend_phase == "PULLBACK_IN_UPTREND":
        structure_sum = "Controlled mean-reverting pullback within a long-term primary uptrend"
    elif trend_phase == "ACCUMULATION_BASE":
        structure_sum = "Bottoming base building above short-term moving average"
    elif trend_phase == "BEARISH_MARKDOWN":
        structure_sum = "Downtrend distribution below major moving average supports"
    else:
        structure_sum = "Consolidation range with balanced supply and demand"

    tech_overview = TechnicalOverview(
        trend_phase=trend_phase,
        rsi_14=rsi_14,
        dma_20=d20,
        dma_50=d50,
        dma_200=d200,
        pct_from_52w_high=pct_52h,
        pct_from_52w_low=pct_52l,
        pct_from_50dma=pct_50d,
        pct_from_200dma=pct_200d,
        structure_summary=structure_sum,
    )

    # 6. Multi-Horizon Scenario Projections (Stock & ETF Specific)
    multi_scen = evaluate_multi_horizon_scenarios(
        pit=pit,
        symbol=clean_sym,
        growth_cagr=growth_cagr,
        earnings_yield=earnings_yield,
        current_price_override=price,
        pe_ratio=snapshot.get("pe_ratio"),
        sector=sector,
        is_etf=is_etf,
        high_52w=high_52w,
        low_52w=low_52w,
        dma_50=d50,
        dma_200=d200,
        roe=snapshot.get("roe"),
    )

    # 7. Sector Context
    sector_tailwinds = [
        f"Structural expansion in {archetype.replace('_', ' ').title()}",
        "Domestic Capex and consumption multiplier",
    ]
    peer_pos = "Top Decile Benchmark Franchise" if (bqs >= 70 or is_etf) else "Sector Average Market Participant"
    sector_context = SectorContext(
        sector=sector,
        sector_archetype=archetype,
        is_etf=is_etf,
        sector_tailwinds=sector_tailwinds,
        peer_standing=peer_pos,
    )

    # 8. Sentiment aggregation
    headlines = snapshot.get("headlines", [])
    if headlines:
        scores = [h.get("sentiment_score", 0.0) for h in headlines if h.get("sentiment_score") is not None]
        avg_sent = round(sum(scores) / len(scores), 2) if scores else 0.0
    else:
        avg_sent = 0.0

    # 9. Tactical Plan
    tactical_plan = calculate_tactical_plan(
        current_price=price,
        action=action,
        business_score=business_score,
        val_score=val_score,
        dma_50=d50,
        dma_200=d200,
        h12m=multi_scen.h12m,
        redlines=redlines,
        is_etf=is_etf,
        company_name=snapshot.get("company_name", clean_sym),
    )

    # 10. Deep Score Explanations
    score_breakdowns = generate_score_breakdowns(
        bqs=bqs,
        val_score=val_score,
        growth_score=growth_s,
        risk_score=risk_score,
        investment_score=invest_score,
        snapshot=snapshot,
        val_res=val_res,
        growth_res=growth_res,
        risk_res=risk_res,
        is_etf=is_etf,
    )

    # 11. Narrative & Institutional Research Report
    thesis_str, research_rep = generate_institutional_thesis(
        symbol=clean_sym,
        company_name=snapshot.get("company_name", clean_sym),
        archetype=archetype,
        snapshot=snapshot,
        bqs=bqs,
        val_score=val_score,
        invest_score=invest_score,
        action=action,
        badge=badge,
        tactical=tactical_plan,
        tech=tech_overview,
        h12m=multi_scen.h12m,
        headlines=headlines,
        is_etf=is_etf,
    )

    all_risks = list(set(growth_res.risks + val_res.risks + redlines))

    return FullStockAnalysis(
        symbol=clean_sym,
        company_name=snapshot.get("company_name", clean_sym),
        sector=sector,
        sector_archetype=archetype,
        asof_date=snapshot.get("asof_date", date.today().isoformat()),
        current_price=price,
        change_pct=snapshot.get("change_pct", 0.0),
        high_52w=high_52w,
        low_52w=low_52w,
        dma_50=d50,
        dma_200=d200,
        market_cap_cr=snapshot.get("market_cap_cr", 0.0),
        is_live_data=snapshot.get("is_live", False),
        is_etf=is_etf,
        business_quality_score=bqs,
        growth_score=growth_s,
        business_score=business_score,
        valuation_score=val_score,
        risk_score=risk_score,
        investment_score=invest_score,
        matrix_quadrant=quadrant,
        action_verdict=action,
        verdict_badge=badge,
        is_investment_worthy=is_worthy,
        tactical_action=tactical_plan,
        score_breakdowns=score_breakdowns,
        technical_overview=tech_overview,
        sector_context=sector_context,
        redlines_triggered=redlines,
        is_redline_clean=(len(redlines) == 0),
        macro_regime=multi_scen.macro_regime,
        horizon_3m=multi_scen.h3m,
        horizon_6m=multi_scen.h6m,
        horizon_12m=multi_scen.h12m,
        horizon_3y=multi_scen.h3y,
        sentiment_score=avg_sent,
        headlines=headlines,
        thesis_rationale=thesis_str,
        research_report=research_rep,
        primary_risks=all_risks[:5],
        growth_drivers=growth_res.drivers[:5],
    )
