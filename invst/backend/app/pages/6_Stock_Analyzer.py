import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import sqlite3
import streamlit as st

from invst.config import get_config
from invst.ingestion.live_market_feed import fetch_live_macro_pulse
from invst.scoring.stock_analyzer import analyze_stock_on_demand
from app.components.kpi_tile import render_kpi_tile

st.set_page_config(page_title="Stock Analyzer — invst", page_icon="🔍", layout="wide")
st.title("🔍 On-Demand Single Stock Quantitative Analyzer")
st.caption("Live Market Intelligence, Decoupled Factor Scoring, Redline Audits & Multi-Horizon Return Forecasts")

cfg = get_config()
conn = sqlite3.connect(str(cfg.database.path))

# --- Macro Pulse Sidebar ---
fetch_live = st.sidebar.checkbox(
    "Fetch Live Quotes (yfinance)",
    value=False,
    help="When enabled, pulls latest live prices from yfinance. Keep unchecked for fast offline evaluation using local database.",
)
pulse = fetch_live_macro_pulse(conn=conn, fetch_live=fetch_live)
st.sidebar.subheader("🌐 Macro Market Pulse")
vix_color = "🔴" if pulse["regime"] == "HIGH_VOLATILITY" else ("🟢" if pulse["regime"] == "EXPANSIONARY" else "🟡")
st.sidebar.metric("India VIX", f"{pulse['india_vix']:.2f}", delta=f"{pulse['regime']}")
st.sidebar.metric("Nifty 50", f"{pulse['nifty_50']:,.2f}")
st.sidebar.info(pulse["regime_description"])

# --- Symbol Input ---
col_in1, col_in2 = st.columns([3, 1])
with col_in1:
    symbol_input = st.text_input(
        "Enter NSE Stock Symbol (e.g. TCS, RELIANCE, INFY, HDFCBANK, ZOMATO):",
        value="TCS",
        help="Type any NSE equity symbol. Offline evaluation reads directly from local database.",
    ).strip().upper()

with col_in2:
    st.write("")
    st.write("")
    run_analysis = st.button("🚀 Analyze Stock", type="primary", use_container_width=True)

# Quick picks row
quick_symbols = ["TCS", "INFY", "RELIANCE", "HDFCBANK", "BAJFINANCE", "LT", "TITAN", "CIPLA"]
st.write("Quick select:")
q_cols = st.columns(len(quick_symbols))
selected_sym = symbol_input
for idx, q_sym in enumerate(quick_symbols):
    if q_cols[idx].button(q_sym, key=f"q_{q_sym}", use_container_width=True):
        selected_sym = q_sym
        st.session_state["active_sym"] = q_sym

if "active_sym" in st.session_state:
    selected_sym = st.session_state["active_sym"]

if selected_sym:
    with st.spinner(f"Running full quantitative models for {selected_sym}..."):
        try:
            res = analyze_stock_on_demand(conn, selected_sym, fetch_live=fetch_live)
        except ValueError as e:
            st.warning(f"🔍 {e}")
            res = None
        except Exception as e:
            st.error(f"Analysis failed for {selected_sym}: {e}")
            res = None

    if res:
        st.markdown("---")
        # --- Top Header ---
        h_col1, h_col2, h_col3, h_col4 = st.columns([3, 2, 2, 2])
        with h_col1:
            st.subheader(f"{res.company_name} ({res.symbol})")
            feed_badge = "🟢 Live Feed" if res.is_live_data else "📁 Database / PIT"
            st.caption(f"Sector: **{res.sector.title()}** ({res.sector_archetype}) | {feed_badge}")

        with h_col2:
            chg_sign = "+" if res.change_pct >= 0 else ""
            st.metric(
                label="Current Price",
                value=f"₹{res.current_price:,.2f}",
                delta=f"{chg_sign}{res.change_pct:.2f}% (1D)",
            )

        with h_col3:
            st.metric(
                label="52-Week Range",
                value=f"₹{res.high_52w:,.0f}",
                delta=f"Low: ₹{res.low_52w:,.0f}",
                delta_color="off",
            )

        with h_col4:
            if res.dma_50 > 0 and res.dma_200 > 0:
                trend_status = "Bullish" if res.current_price > res.dma_50 > res.dma_200 else "Neutral/Bearish"
                st.metric(label="50-DMA / 200-DMA", value=f"₹{res.dma_50:,.0f}", delta=trend_status)
            else:
                st.metric(label="50-DMA", value="Tracking")

        # --- Decision Verdict Banner ---
        st.markdown("---")
        v_col1, v_col2 = st.columns([1, 2])
        with v_col1:
            st.markdown(f"### Verdict: {res.verdict_badge}")
            st.write(f"**Matrix Quadrant:** `{res.matrix_quadrant}`")
            if res.is_investment_worthy:
                st.success("✅ **Approved for Portfolio Allocation** (High conviction compounder / value)")
            else:
                st.warning("⚠️ **Exercise Caution / Avoid Allocation** (Quality trap, value trap, or redline alert)")

        with v_col2:
            st.write("**Core Factor Scores:**")
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                render_kpi_tile("Investment Score", f"{res.investment_score:.1f}/100", "Core Decision")
            with k2:
                render_kpi_tile("Business Score", f"{res.business_score:.1f}/100", "Quality + Growth")
            with k3:
                render_kpi_tile("Valuation Score", f"{res.valuation_score:.1f}/100", "Margin of Safety")
            with k4:
                render_kpi_tile("Risk Score", f"{res.risk_score:.1f}/100", "Balance Sheet")

        # --- Redline Safety Banner ---
        if res.redlines_triggered:
            st.error(f"🚨 **REDLINE ALERTS TRIGGERED ({len(res.redlines_triggered)}):**")
            for r in res.redlines_triggered:
                st.write(f"• {r}")
        else:
            st.success("🛡️ **Redline Safety Audit Passed:** Zero corporate governance, debt distress, or pledging redlines detected.")

        # --- Multi-Horizon Expected Return Table ---
        st.markdown("---")
        st.subheader("📈 Multi-Horizon Expected Return Projections")
        st.caption("Deterministic 3-scenario projections dynamically calibrated against India VIX macro regime.")

        horizons_data = []
        for h in [res.horizon_3m, res.horizon_6m, res.horizon_12m, res.horizon_3y]:
            cagr_text = f" ({h.cagr_pct:.1f}% p.a.)" if h.cagr_pct else ""
            horizons_data.append(
                {
                    "Horizon": f"{h.horizon} ({h.months} Mos)",
                    "Bear Case Price": f"₹{h.target_price_bear:,.2f}",
                    "Bear Ret %": f"{h.return_bear_pct:>+6.1f}%",
                    "Base Case Price": f"₹{h.target_price_base:,.2f}",
                    "Base Ret %": f"{h.return_base_pct:>+6.1f}%",
                    "Bull Case Price": f"₹{h.target_price_bull:,.2f}",
                    "Bull Ret %": f"{h.return_bull_pct:>+6.1f}%",
                    "Expected Return": f"{h.expected_return_pct:>+6.1f}%{cagr_text}",
                    "Downside/Upside": f"{h.downside_to_upside_ratio:.2f}x",
                }
            )
        st.dataframe(horizons_data, use_container_width=True)

        # --- Thesis & News Feeds ---
        st.markdown("---")
        t_col1, t_col2 = st.columns([3, 2])
        with t_col1:
            st.subheader("📝 Investment Thesis & Rationale")
            st.info(res.thesis_rationale)

            if res.growth_drivers:
                st.write("**Key Growth Drivers:**")
                for d in res.growth_drivers:
                    st.write(f"• {d}")

            if res.primary_risks:
                st.write("**Primary Identified Risks:**")
                for rsk in res.primary_risks:
                    st.write(f"• {rsk}")

        with t_col2:
            st.subheader("📰 Recent Disclosures & Sentiment")
            sent_str = f"Sentiment Score: {res.sentiment_score:+.2f}"
            st.caption(sent_str)
            if res.headlines:
                for h in res.headlines:
                    s_score = h.get("sentiment_score", 0.0)
                    s_badge = "🟢" if s_score > 0.1 else ("🔴" if s_score < -0.1 else "⚪")
                    st.write(f"{s_badge} **{h['headline']}**")
                    st.caption(f"Source: {h.get('source', 'News')} | Published: {h.get('published_at', '')}")
            else:
                st.info("No recent news headlines available for this symbol.")

conn.close()
