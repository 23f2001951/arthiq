"""Stock Card UI Component for Streamlit."""

from __future__ import annotations

from typing import Any
import streamlit as st


def render_stock_card(
    symbol: str,
    sector: str,
    action: str,
    target_weight: float,
    current_weight: float,
    rationale: str,
    scorecard: dict[str, Any],
) -> None:
    """Render a comprehensive, evidence-backed recommendation card for a stock."""
    comp_score = scorecard.get("composite_score", 0.0)
    q_score = scorecard.get("quality_score", 0.0)
    v_score = scorecard.get("valuation_score", 0.0)
    r_score = scorecard.get("risk_score", 0.0)
    s_pts = scorecard.get("sentiment_overlay_points", 0.0)

    q_m = scorecard.get("quality_details", {}).get("metrics", {})
    v_m = scorecard.get("valuation_details", {}).get("metrics", {})
    r_m = scorecard.get("risk_details", {}).get("metrics", {})

    with st.container(border=True):
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.subheader(f"{symbol} — {sector.replace('_', ' ').title()}")
        with col2:
            badge_color = "green" if action == "BUY" else ("orange" if action == "HOLD" else "red")
            st.markdown(f"**Action:** :{badge_color}[{action}]")
        with col3:
            st.markdown(f"**Target:** {target_weight*100:.1f}%")

        # Plain-English Rationale Box
        st.info(f"**Why we like it:**\n\n{rationale}")

        # Metrics breakdown
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Composite Score", f"{comp_score:.1f} / 100")
        c2.metric("Quality Score", f"{q_score:.1f}")
        c3.metric("Valuation Score", f"{v_score:.1f}")
        c4.metric("Risk Score", f"{r_score:.1f}")
        c5.metric("Sentiment Overlay", f"{s_pts:+.1f} pts")

        # Detailed metrics expander
        with st.expander("Underlying Factor Numbers & Signals"):
            m_col1, m_col2, m_col3 = st.columns(3)
            with m_col1:
                st.markdown("**Fundamentals (Quality)**")
                st.write(f"- 5-yr Avg ROE: `{q_m.get('roe_5yr_avg', 'N/A')}%`")
                st.write(f"- 5-yr Avg ROCE: `{q_m.get('roce_5yr_avg', 'N/A')}%`")
                st.write(f"- Debt/Equity: `{q_m.get('debt_equity', 'N/A')}`")
                st.write(f"- Interest Coverage: `{q_m.get('interest_coverage', 'N/A')}x`")
                st.write(f"- Earnings CAGR 5yr: `{q_m.get('earnings_cagr_5yr', 'N/A')}%`")
            with m_col2:
                st.markdown("**Valuation Multiples**")
                st.write(f"- P/E (TTM): `{v_m.get('pe_ttm', 'N/A')}x`")
                st.write(f"- P/B: `{v_m.get('pb', 'N/A')}x`")
                st.write(f"- EV/EBITDA: `{v_m.get('ev_ebitda', 'N/A')}x`")
                st.write(f"- Dividend Yield: `{v_m.get('dividend_yield', 'N/A')}%`")
            with m_col3:
                st.markdown("**Risk & Volatility**")
                st.write(f"- 252d Volatility: `{r_m.get('annualised_vol_252d', 'N/A')}`")
                st.write(f"- Beta vs Nifty 500: `{r_m.get('beta_nifty500_2yr', 'N/A')}`")
                st.write(f"- Max Drawdown 3yr: `{r_m.get('max_drawdown_3yr', 'N/A')}`")
