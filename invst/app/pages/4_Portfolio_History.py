import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import csv
import io
import sqlite3
import pandas as pd
import streamlit as st

from invst.config import get_config
from invst.portfolio.health import (
    UserHolding,
    evaluate_portfolio_health,
    load_user_holdings,
    save_user_holdings,
)
from app.components.kpi_tile import render_kpi_tile
from app.components.chart_helpers import plot_sector_allocations

st.set_page_config(page_title="My Portfolio — invst", page_icon="💼", layout="wide")
st.title("💼 Personal Portfolio & Health Diagnostic Workspace")
st.caption("Add your holdings manually or via CSV to get instant portfolio health scoring, redline audits, and BUY/SELL/HOLD advice.")

cfg = get_config()
conn = sqlite3.connect(str(cfg.database.path))

tab1, tab2 = st.tabs(["💼 My Live Portfolio & Health", "📜 Model Rebalance Audit"])

with tab1:
    st.subheader("1. Your Current Stock Holdings")
    
    # Load existing holdings from DB
    existing_holdings = load_user_holdings(conn)
    if "custom_holdings" in st.session_state:
        existing_holdings = st.session_state["custom_holdings"]

    # Convert to DataFrame for st.data_editor
    holdings_df = pd.DataFrame(
        [
            {"Symbol": h.symbol, "Shares": float(h.shares), "Avg Buy Price (₹)": float(h.buy_price)}
            for h in existing_holdings
        ]
        if existing_holdings
        else [{"Symbol": "", "Shares": 0.0, "Avg Buy Price (₹)": 0.0}]
    )

    col_input1, col_input2 = st.columns([3, 2])
    with col_input1:
        st.write("Edit or add positions directly in the table below:")
        edited_df = st.data_editor(
            holdings_df,
            num_rows="dynamic",
            use_container_width=True,
            key="portfolio_editor",
        )
        sample_col1, sample_col2 = st.columns([1, 1])
        with sample_col1:
            if st.button("📥 Load Sample Compounders (Demo)", help="Load a 4-stock sample portfolio to test diagnostics"):
                st.session_state["custom_holdings"] = [
                    UserHolding(symbol="TCS", shares=15.0, buy_price=1380.0),
                    UserHolding(symbol="INFY", shares=20.0, buy_price=1850.0),
                    UserHolding(symbol="HDFCBANK", shares=25.0, buy_price=1250.0),
                    UserHolding(symbol="RELIANCE", shares=10.0, buy_price=2200.0),
                ]
                st.rerun()
        with sample_col2:
            if st.button("🗑️ Clear Portfolio", help="Clear all positions"):
                st.session_state["custom_holdings"] = []
                save_user_holdings(conn, [])
                st.rerun()

    with col_input2:
        st.write("Or import your holdings from CSV (Zerodha / Groww / CAS):")
        uploaded_file = st.file_uploader("Upload CSV", type=["csv"], help="CSV with columns: symbol, shares/qty, price")
        if uploaded_file is not None:
            try:
                csv_df = pd.read_csv(uploaded_file)
                # Map columns flexibly
                col_map = {}
                for c in csv_df.columns:
                    cl = c.strip().lower()
                    if "symbol" in cl or "ticker" in cl or "stock" in cl:
                        col_map[c] = "Symbol"
                    elif "share" in cl or "qty" in cl or "quantity" in cl:
                        col_map[c] = "Shares"
                    elif "buy" in cl or "price" in cl or "avg" in cl or "cost" in cl:
                        col_map[c] = "Avg Buy Price (₹)"
                
                if len(col_map) >= 3:
                    csv_df = csv_df[list(col_map.keys())].rename(columns=col_map)
                    csv_df["Symbol"] = csv_df["Symbol"].astype(str).str.upper()
                    csv_df["Shares"] = pd.to_numeric(csv_df["Shares"], errors="coerce").fillna(0.0)
                    csv_df["Avg Buy Price (₹)"] = pd.to_numeric(csv_df["Avg Buy Price (₹)"], errors="coerce").fillna(0.0)
                    st.success(f"Loaded {len(csv_df)} rows from CSV. Click Save & Analyze below.")
                    edited_df = csv_df
                else:
                    st.warning("CSV must contain columns for symbol, quantity/shares, and buy price.")
            except Exception as e:
                st.error(f"Failed to parse CSV: {e}")

    # Process Holdings
    active_holdings: list[UserHolding] = []
    if edited_df is not None and not edited_df.empty:
        for _, row in edited_df.iterrows():
            sym = str(row.get("Symbol", "")).strip().upper()
            try:
                sh = float(row.get("Shares", 0.0))
                bp = float(row.get("Avg Buy Price (₹)", 0.0))
                if sym and sh > 0 and bp > 0:
                    active_holdings.append(UserHolding(symbol=sym, shares=sh, buy_price=bp))
            except (ValueError, TypeError):
                continue

    btn_col1, btn_col2 = st.columns([2, 5])
    with btn_col1:
        diagnose_btn = st.button("⚡ Save & Run Health Diagnosis", type="primary", use_container_width=True)

    if diagnose_btn:
        if active_holdings:
            save_user_holdings(conn, active_holdings)
            if "custom_holdings" in st.session_state:
                del st.session_state["custom_holdings"]
            with st.spinner("Diagnosing portfolio health against live factor models and redlines..."):
                report = evaluate_portfolio_health(conn, active_holdings)

            st.markdown("---")
            st.subheader("2. Portfolio Health Scorecard")

            k1, k2, k3, k4 = st.columns(4)
            with k1:
                render_kpi_tile("Current Portfolio Value", f"₹{report.total_current_value:,.0f}", f"Invested: ₹{report.total_invested:,.0f}")
            with k2:
                pnl_sign = "+" if report.total_unrealized_pnl >= 0 else ""
                pnl_color = "normal" if report.total_unrealized_pnl >= 0 else "inverse"
                render_kpi_tile(
                    "Total Unrealized P&L",
                    f"{pnl_sign}₹{report.total_unrealized_pnl:,.0f}",
                    f"{pnl_sign}{report.total_unrealized_pnl_pct:.2f}% Return",
                    delta_color=pnl_color,
                )
            with k3:
                grade_color = "🟢" if report.overall_health_grade in ["EXCELLENT", "GOOD"] else "🔴"
                render_kpi_tile(
                    "Health Score",
                    f"{report.overall_health_score:.1f}/100",
                    f"Grade: {report.overall_health_grade} {grade_color}",
                )
            with k4:
                render_kpi_tile(
                    "Weighted Quality / Valuation",
                    f"{report.weighted_business_score:.0f} / {report.weighted_valuation_score:.0f}",
                    "Quality vs Margin of Safety",
                )

            # Alerts & Warnings
            if report.critical_redline_alerts:
                st.error("🚨 **CRITICAL REDLINE ALERTS ON ACTIVE HOLDINGS:**")
                for cra in report.critical_redline_alerts:
                    st.write(f"• **{cra}**")

            if report.sector_warnings:
                st.warning("⚠️ **SECTOR CONCENTRATION WARNINGS:**")
                for sw in report.sector_warnings:
                    st.write(f"• {sw}")

            # Position-by-Position Advisory Table
            st.markdown("---")
            st.subheader("3. Position-by-Position Actionable Guidance")
            st.caption(f"Action Summary: **{report.summary_action_plan}**")

            pos_data = []
            for p in report.positions:
                pnl_s = "+" if p.unrealized_pnl >= 0 else ""
                pos_data.append(
                    {
                        "Symbol": p.symbol,
                        "Shares": f"{p.shares:.0f}",
                        "Avg Price": f"₹{p.buy_price:,.2f}",
                        "Current Price": f"₹{p.current_price:,.2f}",
                        "Current Value": f"₹{p.current_value:,.0f}",
                        "Weight": f"{p.weight_pct:.1f}%",
                        "P&L %": f"{pnl_s}{p.unrealized_pnl_pct:.2f}%",
                        "12M Return Exp": f"{p.expected_return_12m:>+5.1f}%",
                        "Action Advice": p.action_badge,
                        "Action Rationale": p.action_rationale,
                    }
                )

            st.dataframe(pos_data, use_container_width=True)

            # Sector Breakdown & Replacement Ideas
            st.markdown("---")
            c_col1, c_col2 = st.columns([3, 2])
            with c_col1:
                st.subheader("📊 Sector Diversification vs 40% Cap")
                # Format sector weights for chart helper
                chart_data = {sec.title(): round(w / 100.0, 4) for sec, w in report.sector_exposures.items()}
                fig = plot_sector_allocations(chart_data)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)

            with c_col2:
                st.subheader("💡 Suggested Allocations / Replacements")
                st.caption("Top-ranked Arth IQ high-conviction ideas to deploy sell proceeds or fresh capital:")
                if report.suggested_replacements:
                    st.dataframe(
                        [
                            {
                                "Symbol": r["symbol"],
                                "Sector": r["sector"],
                                "Composite Score": f"{r['composite_score']:.1f}/100",
                                "Quality Score": f"{r['quality_score']:.1f}",
                                "Valuation Score": f"{r['valuation_score']:.1f}",
                            }
                            for r in report.suggested_replacements
                        ],
                        use_container_width=True,
                    )
                else:
                    st.info("No replacement ideas needed. Portfolio is well-diversified.")
        else:
            st.info("Please enter at least one stock holding with symbol, shares, and buy price.")

with tab2:
    st.subheader("Historical Model Portfolio Rebalances")
    cur = conn.cursor()
    cur.execute(
        """
        SELECT run_id, asof_date, symbol, target_weight, action, shares_target, rationale_text, executed
        FROM portfolio_history
        ORDER BY asof_date DESC, target_weight DESC
        """
    )
    rows = cur.fetchall()

    if rows:
        st.write(f"Total recorded automated portfolio actions: **{len(rows)}**")
        st.dataframe(
            [
                {
                    "Run ID": r[0][:8],
                    "Date": r[1],
                    "Symbol": r[2],
                    "Target Weight": f"{r[3]*100:.1f}%",
                    "Model Action": r[4],
                    "Target Shares": r[5] or "-",
                    "Rationale": r[6],
                    "Executed": "✅ Executed" if r[7] == 1 else "⏳ Pending",
                }
                for r in rows
            ],
            use_container_width=True,
        )
    else:
        st.info("No automated portfolio history runs recorded yet.")

conn.close()
