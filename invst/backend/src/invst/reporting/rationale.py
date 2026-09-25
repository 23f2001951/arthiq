"""Plain-English investment rationale generator.

Translates complex quantitative signals, fundamental ratios, valuation metrics,
and sentiment indicators into cohesive, human-readable commentary per stock.
"""

from __future__ import annotations

from typing import Any


def generate_plain_english_rationale(
    symbol: str,
    company_name: str,
    sector: str,
    action: str,  # 'BUY', 'HOLD', 'SELL'
    target_weight: float,
    current_weight: float,
    scorecard: dict[str, Any],
) -> str:
    """Generate a coherent, evidence-backed narrative explaining the recommendation."""
    q_metrics = scorecard.get("quality_details", {}).get("metrics", {})
    v_metrics = scorecard.get("valuation_details", {}).get("metrics", {})
    r_metrics = scorecard.get("risk_details", {}).get("metrics", {})
    s_metrics = scorecard.get("sentiment_details", {})

    roe = q_metrics.get("roe_5yr_avg")
    roce = q_metrics.get("roce_5yr_avg")
    de = q_metrics.get("debt_equity")
    ic = q_metrics.get("interest_coverage")
    cagr = q_metrics.get("earnings_cagr_5yr")

    pe = v_metrics.get("pe_ttm")
    pb = v_metrics.get("pb")
    ev_ebitda = v_metrics.get("ev_ebitda")

    vol = r_metrics.get("annualised_vol_252d")
    beta = r_metrics.get("beta_nifty500_2yr")
    dd = r_metrics.get("max_drawdown_3yr")

    mom = s_metrics.get("momentum_return")
    sent = s_metrics.get("sentiment_score")

    # 1. Opening summary
    weight_pct = target_weight * 100
    if action == "BUY":
        if current_weight > 0:
            headline = f"Increasing target allocation in {symbol} to {weight_pct:.1f}%."
        else:
            headline = f"Initiating a new BUY position in {symbol} with a target allocation of {weight_pct:.1f}%."
    elif action == "SELL":
        headline = f"Trimming or closing position in {symbol} (target weight {weight_pct:.1f}%)."
    else:
        headline = f"Maintaining HOLD on {symbol} at {weight_pct:.1f}% target allocation."

    # 2. Fundamentals narrative
    fund_points = []
    if roe is not None and roce is not None:
        fund_points.append(
            f"shows consistent capital efficiency with a 5-year average ROE of {roe:.1f}% and ROCE of {roce:.1f}%"
        )
    if de is not None:
        if de <= 0.5:
            fund_points.append(
                f"maintains a conservative balance sheet with a low debt-to-equity ratio of {de:.2f}"
            )
        elif de <= 1.0:
            fund_points.append(f"operates with manageable leverage (D/E of {de:.2f})")
        else:
            fund_points.append(
                f"bears elevated leverage with a D/E of {de:.2f}, partially offset by interest coverage of {ic or 1.0:.1f}x"
            )
    if cagr is not None and cagr > 10.0:
        fund_points.append(f"has delivered robust 5-year earnings growth CAGR of {cagr:.1f}%")

    fund_sentence = (
        f"{company_name or symbol} " + ", and ".join(fund_points) + "." if fund_points else ""
    )

    # 3. Valuation narrative
    val_points = []
    if pe is not None and pe > 0:
        val_points.append(f"TTM P/E is trading at {pe:.1f}x")
    if ev_ebitda is not None and ev_ebitda > 0:
        val_points.append(f"EV/EBITDA stands at {ev_ebitda:.1f}x")
    if pb is not None and pb > 0:
        val_points.append(f"P/B is {pb:.1f}x")

    val_sentence = (
        "On valuation, "
        + " with ".join(val_points)
        + ", presenting an attractive entry within the "
        f"{sector.replace('_', ' ').title()} sector."
        if val_points
        else ""
    )

    # 4. Momentum and Sentiment
    tech_points = []
    if mom is not None:
        mom_pct = mom * 100
        if mom_pct > 15:
            tech_points.append(f"positive 6-12-1 price momentum of +{mom_pct:.1f}%")
        elif mom_pct < -15:
            tech_points.append(f"subdued price momentum ({mom_pct:.1f}%)")
        else:
            tech_points.append(f"steady price momentum of {mom_pct:.1f}%")

    if sent is not None:
        if sent > 0.2:
            tech_points.append("positive press and institutional sentiment")
        elif sent < -0.2:
            tech_points.append("cautious headline sentiment")
        else:
            tech_points.append("neutral media coverage")

    tech_sentence = (
        "Technical and market sentiment overlays confirm " + " alongside ".join(tech_points) + "."
        if tech_points
        else ""
    )

    # 5. Risk caveats
    risk_notes = []
    if vol is not None and vol > 0.35:
        risk_notes.append(f"elevated annualized volatility ({vol * 100:.1f}%)")
    if beta is not None and beta > 1.3:
        risk_notes.append(f"market beta of {beta:.2f}")
    if dd is not None and abs(dd) > 0.35:
        risk_notes.append(f"a 3-year maximum drawdown of {dd * 100:.1f}%")

    risk_sentence = (
        "Key monitoring risk: position sized with regard to " + " and ".join(risk_notes) + "."
        if risk_notes
        else ""
    )

    narrative_paragraphs = [
        headline,
        fund_sentence,
        val_sentence,
        tech_sentence,
        risk_sentence,
    ]

    return " ".join(p for p in narrative_paragraphs if p)
