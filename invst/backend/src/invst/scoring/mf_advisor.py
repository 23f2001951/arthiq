"""Mutual Fund Advisory & Goal Profiling Recommendation Engine.

Analyzes user investor profile (risk capacity, time horizon, goal type, and budget)
to generate optimal category asset allocation and curated fund recommendations
with suggested SIP distributions and quant rationales.
"""

from __future__ import annotations

import logging
from typing import Any

from invst.db.engine import get_db_connection
from invst.scoring.mf_metrics import calculate_sip_projection

logger = logging.getLogger(__name__)


def generate_mf_recommendation(
    risk_profile: str,
    horizon_years: int,
    goal_type: str,
    monthly_budget: float = 20000.0,
    step_up_pct: float = 10.0,
) -> dict[str, Any]:
    """Generate risk-profiled mutual fund basket and asset allocation.

    Args:
        risk_profile: 'CONSERVATIVE', 'MODERATE', 'GROWTH', 'AGGRESSIVE'
        horizon_years: Duration in years (1 to 30)
        goal_type: 'WEALTH_CREATION', 'TAX_SAVING', 'RETIREMENT', 'EMERGENCY_FUND', 'CHILD_FUTURE'
        monthly_budget: Total monthly investment budget in INR
        step_up_pct: Annual top-up percentage

    Returns:
        Structured recommendation payload including category breakdown,
        specific fund allocations, SIP amounts, and 5/10/15 year wealth projections.
    """
    risk_norm = risk_profile.strip().upper()
    goal_norm = goal_type.strip().upper()

    # 1. Determine Target Asset Allocation
    # Short horizon (< 3 years) mandates capital protection regardless of risk
    if horizon_years < 3 or goal_norm == "EMERGENCY_FUND":
        allocation = {
            "Debt: Liquid": 50.0,
            "Hybrid: Balanced Advantage": 50.0,
        }
        expected_cagr = 7.5
        risk_label = "Conservative (Capital Protection Focus)"
    elif goal_norm == "TAX_SAVING":
        # 80C ELSS focused
        allocation = {
            "Equity: ELSS": 60.0,
            "Equity: Flexi Cap": 40.0,
        }
        expected_cagr = 13.5
        risk_label = "Tax-Advantaged Wealth Creation"
    elif risk_norm == "CONSERVATIVE":
        allocation = {
            "Hybrid: Balanced Advantage": 50.0,
            "Equity: Large Cap": 30.0,
            "Equity: Index / Passive": 20.0,
        }
        expected_cagr = 10.5
        risk_label = "Conservative / Balanced"
    elif risk_norm == "MODERATE":
        allocation = {
            "Equity: Flexi Cap": 40.0,
            "Equity: Large Cap": 30.0,
            "Hybrid: Balanced Advantage": 20.0,
            "Equity: Mid Cap": 10.0,
        }
        expected_cagr = 12.5
        risk_label = "Balanced Growth"
    elif risk_norm in ("GROWTH", "AGGRESSIVE"):
        if horizon_years >= 7:
            allocation = {
                "Equity: Flexi Cap": 35.0,
                "Equity: Mid Cap": 30.0,
                "Equity: Small Cap": 20.0,
                "Equity: Index / Passive": 15.0,
            }
            expected_cagr = 14.5
            risk_label = "Aggressive Multi-Cap Alpha"
        else:
            allocation = {
                "Equity: Flexi Cap": 40.0,
                "Equity: Large Cap": 25.0,
                "Equity: Mid Cap": 25.0,
                "Hybrid: Balanced Advantage": 10.0,
            }
            expected_cagr = 13.0
            risk_label = "Growth Focused"
    else:  # Default balanced
        allocation = {
            "Equity: Flexi Cap": 40.0,
            "Equity: Large Cap": 30.0,
            "Equity: Mid Cap": 20.0,
            "Equity: Small Cap": 10.0,
        }
        expected_cagr = 13.0
        risk_label = "Balanced Wealth Creation"

    # 2. Match Top Funds from Database for each category
    conn = get_db_connection()
    recommended_funds: list[dict[str, Any]] = []
    total_assigned_sip = 0.0

    try:
        cur = conn.cursor()
        for cat, weight_pct in allocation.items():
            cur.execute(
                """
                SELECT scheme_code, scheme_name, fund_house, category,
                       expense_ratio, aum_cr, crisil_rating, risk_level, fund_manager
                FROM mf_schemes
                WHERE category = ?
                ORDER BY crisil_rating DESC, aum_cr DESC
                LIMIT 1;
                """,
                (cat,),
            )
            row = cur.fetchone()
            if not row:
                # Fallback to any scheme in category or flexi
                cur.execute(
                    """
                    SELECT scheme_code, scheme_name, fund_house, category,
                           expense_ratio, aum_cr, crisil_rating, risk_level, fund_manager
                    FROM mf_schemes
                    LIMIT 1;
                    """
                )
                row = cur.fetchone()

            if row:
                fund_sip = round((monthly_budget * weight_pct / 100.0) / 500.0) * 500.0  # round to nearest 500
                fund_sip = max(fund_sip, 500.0)
                total_assigned_sip += fund_sip

                # Generate quant rationale
                rationale = f"Top-rated {cat} with proven risk-adjusted alpha, {row[4] or 0.65}% expense ratio, and institutional AUM stability."
                if "Flexi" in cat:
                    rationale = "Core portfolio anchor with unconstrained market-cap mobility and international diversification."
                elif "Mid" in cat:
                    rationale = "High-growth engine capitalizing on India's manufacturing, healthcare, and consumer expansion."
                elif "Small" in cat:
                    rationale = "Aggressive alpha generator for multi-bagger small-cap opportunities with long holding horizon."
                elif "Balanced" in cat:
                    rationale = "Dynamic equity-debt hedging to cushion downside drawdowns during market corrections."

                cat_rank = None
                try:
                    from invst.portfolio.mf_portfolio_service import get_scheme_category_rank
                    cat_rank = get_scheme_category_rank(row[0], row[3], conn=conn)
                except Exception:
                    pass

                recommended_funds.append({
                    "scheme_code": row[0],
                    "scheme_name": row[1],
                    "fund_house": row[2],
                    "category": row[3],
                    "allocation_pct": weight_pct,
                    "monthly_sip": fund_sip,
                    "expense_ratio": row[4],
                    "aum_cr": row[5],
                    "crisil_rating": row[6] or 5,
                    "risk_level": row[7] or "Very High",
                    "fund_manager": row[8],
                    "rationale": rationale,
                    "category_rank": cat_rank,
                })
    finally:
        conn.close()

    # 3. Compute Wealth Projection with Step-Up across Multi-Scenarios
    clamped_years = min(max(horizon_years, 3), 25)
    bull_cagr = round(expected_cagr + 3.0, 1)
    bear_cagr = round(max(expected_cagr - 3.5, 4.5), 1)

    base_projection = calculate_sip_projection(
        monthly_sip=monthly_budget,
        expected_cagr_pct=expected_cagr,
        years=clamped_years,
        step_up_pct=step_up_pct,
        inflation_pct=6.0,
    )
    bull_projection = calculate_sip_projection(
        monthly_sip=monthly_budget,
        expected_cagr_pct=bull_cagr,
        years=clamped_years,
        step_up_pct=step_up_pct,
        inflation_pct=6.0,
    )
    bear_projection = calculate_sip_projection(
        monthly_sip=monthly_budget,
        expected_cagr_pct=bear_cagr,
        years=clamped_years,
        step_up_pct=step_up_pct,
        inflation_pct=6.0,
    )

    # Build unified trajectory merging all scenarios for clean frontend charting
    unified_trajectory = []
    base_traj = base_projection.get("trajectory", [])
    bull_traj = bull_projection.get("trajectory", [])
    bear_traj = bear_projection.get("trajectory", [])

    for i in range(len(base_traj)):
        y = base_traj[i]["year"]
        b_corp = base_traj[i]["estimated_corpus"]
        invested = base_traj[i]["total_invested"]
        real_pwr = base_traj[i]["real_purchasing_power"]
        bull_corp = bull_traj[i]["estimated_corpus"] if i < len(bull_traj) else b_corp
        bear_corp = bear_traj[i]["estimated_corpus"] if i < len(bear_traj) else b_corp

        unified_trajectory.append({
            "year": y,
            "monthly_sip": base_traj[i]["monthly_sip"],
            "total_invested": invested,
            "corpus_base": b_corp,
            "corpus_bull": bull_corp,
            "corpus_bear": bear_corp,
            "real_purchasing_power": real_pwr,
        })

    # Seasoned Analyst Narrative Rationale
    if risk_norm == "CONSERVATIVE" or horizon_years < 3:
        advisory_rationale = (
            f"Given your {horizon_years}-year horizon and capital preservation objective, this architecture "
            "prioritizes low volatility and downside cushioning. Over 50% is ring-fenced in dynamic hybrid or "
            "short-duration debt instruments to protect nominal capital, while a selective 30% large-cap core "
            "captures steady compounding with institutional balance-sheet security."
        )
    elif goal_norm == "TAX_SAVING":
        advisory_rationale = (
            "Optimized for dual-engine efficiency: Section 80C tax deduction up to ₹1.50 Lakh with a disciplined "
            "3-year lock-in that prevents behavioral panic-selling during cyclical dips. Complementary Flexi-Cap "
            "allocation provides unconstrained alpha without lock-in constraints."
        )
    elif risk_norm in ("GROWTH", "AGGRESSIVE"):
        advisory_rationale = (
            f"Engineered for high-conviction wealth compounding over your {horizon_years}-year runway. The core "
            "allocation harnesses Flexi-Cap mobility alongside high-growth Mid & Small-Cap engines. Historical "
            "rolling returns indicate that equity drawdowns over 7+ year holding windows have a <1% probability "
            "of negative outcomes in Indian equities, maximizing your equity compounding coefficient."
        )
    else:
        advisory_rationale = (
            f"A balanced core-and-satellite portfolio designed for a {horizon_years}-year wealth creation goal. "
            "Anchor allocations in large and flexi-cap schemes provide portfolio resilience, complemented by a "
            "tactical 30% mid/small-cap growth booster to generate superior risk-adjusted alpha over the benchmark."
        )

    # Institutional Tax Optimization Memo
    tax_optimization_memo = {
        "regime": "Budget 2024 LTCG & STCG Framework",
        "equity_ltcg_rate": "12.5% on gains exceeding ₹1.25 Lakh per financial year (exemption raised from ₹1.0L).",
        "equity_stcg_rate": "20% on units redeemed within 12 months (raised from 15%).",
        "tax_harvesting_strategy": "Harvest ₹1.25 Lakh of long-term capital gains tax-free every March by redeeming and reinvesting.",
        "debt_taxation": "Taxed at marginal personal slab rate for non-equity funds (funds with <65% domestic equity).",
        "elss_lockin": "Mandatory 3-year statutory lock-in from the date of each monthly SIP installment.",
    }

    # Tactical Portfolio Rebalancing Protocol
    rebalancing_protocol = {
        "tolerance_band_pct": 5.0,
        "review_cadence": "Semi-annual or annual allocation review",
        "execution_strategy": "Rebalance via fresh monthly SIP redirection rather than redeeming units to avoid unnecessary STCG/LTCG tax drag and exit loads.",
        "glide_path": f"Commence systematic STP to liquid/arbitrage funds {min(horizon_years, 3)} years prior to goal maturity to lock in compounding gains and eliminate sequencing risk.",
    }

    # Market Context & Compounding Multiplier Note
    market_context = (
        f"Rupee-cost averaging mitigates market volatility. With a {step_up_pct}% annual SIP step-up, "
        f"your expected terminal corpus reaches ₹{(base_projection['estimated_corpus'] / 100000):.2f} Lakhs "
        f"({base_projection['wealth_multiplier']}x wealth multiplier), significantly accelerating compounding "
        "compared to a flat static investment."
    )

    return {
        "user_profile": {
            "risk_profile": risk_norm,
            "horizon_years": horizon_years,
            "goal_type": goal_norm,
            "monthly_budget": monthly_budget,
            "step_up_pct": step_up_pct,
            "risk_label": risk_label,
            "expected_cagr_pct": expected_cagr,
        },
        "asset_allocation": allocation,
        "recommended_funds": recommended_funds,
        "total_monthly_sip": sum(f["monthly_sip"] for f in recommended_funds),
        "wealth_projection": base_projection,
        "advisory_rationale": advisory_rationale,
        "market_context": market_context,
        "tax_optimization_memo": tax_optimization_memo,
        "rebalancing_protocol": rebalancing_protocol,
        "multi_scenario_projections": {
            "expected_cagr": expected_cagr,
            "bull_cagr": bull_cagr,
            "bear_cagr": bear_cagr,
            "terminal_base": base_projection["estimated_corpus"],
            "terminal_bull": bull_projection["estimated_corpus"],
            "terminal_bear": bear_projection["estimated_corpus"],
            "total_invested": base_projection["total_invested"],
            "unified_trajectory": unified_trajectory,
        },
    }
