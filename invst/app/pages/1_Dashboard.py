import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from datetime import date
import sqlite3
import streamlit as st

from invst.config import get_config
from invst.portfolio.health import (
    get_portfolio,
    list_portfolios,
    evaluate_portfolio_health,
    init_portfolio_db,
)
from invst.data_access import PointInTimeDataAccess
from app.components.kpi_tile import render_kpi_tile
from app.components.chart_helpers import plot_sector_allocations

st.set_page_config(page_title="Portfolio Dashboard — invst", page_icon="📊", layout="wide")

cfg = get_config()
db_path = str(cfg.database.path)
conn = sqlite3.connect(db_path)
init_portfolio_db(conn)

# Portfolio Selection (Only live investment portfolios, excluding tactical target lists)
portfolios = list_portfolios(conn, portfolio_type="PORTFOLIO")
if not portfolios:
    st.warning("No portfolios registered in database. Initializing default...")
    init_portfolio_db(conn)
    portfolios = list_portfolios(conn, portfolio_type="PORTFOLIO")

portfolio_options = {p["id"]: f"{p['name']} ({p['holdings_count']} holdings)" for p in portfolios}
default_keys = list(portfolio_options.keys())
default_index = default_keys.index("default") if "default" in default_keys else 0

st.sidebar.subheader("Portfolio Selector")
selected_id = st.sidebar.selectbox(
    "Active Investment Portfolio",
    options=default_keys,
    index=default_index,
    format_func=lambda x: portfolio_options.get(x, x),
)

fetch_live = st.sidebar.checkbox(
    "Fetch Live Quotes (yfinance)",
    value=False,
    help="When enabled, pulls latest live prices from yfinance. Uncheck for fast offline evaluation using local database.",
)

current_portfolio = get_portfolio(conn, selected_id)
if not current_portfolio:
    st.error(f"Portfolio `{selected_id}` not found.")
    st.stop()

# Header
st.title(f"📊 {current_portfolio.name} Dashboard")
st.caption(
    f"{current_portfolio.description or 'Live portfolio status & health diagnostic'} • "
    f"Type: **{current_portfolio.portfolio_type}** • "
    f"Last Updated: **{current_portfolio.updated_at or 'Today'}**"
)

# Check if portfolio has holdings
holdings = current_portfolio.holdings

if holdings:
    with st.spinner("Analyzing portfolio health, live prices, and factor scores..."):
        report = evaluate_portfolio_health(conn, holdings, fetch_live=fetch_live)

    # Top KPI Metrics (Real Data)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        pnl_s = "+" if report.total_unrealized_pnl >= 0 else ""
        delta_color = "normal" if report.total_unrealized_pnl >= 0 else "inverse"
        render_kpi_tile(
            "Portfolio Value",
            f"₹{report.total_current_value:,.2f}",
            subtitle=f"Total Invested: ₹{report.total_invested:,.2f}",
            delta=f"{pnl_s}₹{report.total_unrealized_pnl:,.2f} ({pnl_s}{report.total_unrealized_pnl_pct:.2f}%)",
            delta_color=delta_color,
        )
    with col2:
        grade_emoji = "🟢" if report.overall_health_grade in ["EXCELLENT", "GOOD"] else ("🟡" if report.overall_health_grade == "NEEDS_ATTENTION" else "🔴")
        render_kpi_tile(
            "Health Score",
            f"{report.overall_health_score:.1f}/100",
            subtitle=f"Grade: {report.overall_health_grade} {grade_emoji}",
            delta=f"Quality {report.weighted_business_score:.0f} | Val {report.weighted_valuation_score:.0f}",
        )
    with col3:
        hhi_tier = report.diversification.diversification_tier.replace("_", " ").title()
        render_kpi_tile(
            "Active Positions",
            f"{len(holdings)} Positions",
            subtitle=f"Top 3: {report.diversification.top_3_concentration_pct:.1f}% concentration",
            delta=f"HHI: {report.diversification.hhi_score:.0f} ({hhi_tier})",
        )
    with col4:
        urgency = report.rebalancing_blueprint.rebalance_urgency
        urgency_emoji = "🟢" if urgency == "LOW" else ("🟡" if urgency == "MEDIUM" else "🔴")
        render_kpi_tile(
            "Rebalance Urgency",
            f"{urgency} {urgency_emoji}",
            subtitle=f"Cadence: Quarterly ({cfg.rebalance.cadence})",
            delta=f"{len(report.rebalancing_blueprint.orders)} Action Orders Pending",
        )

    # Critical Alerts
    if report.critical_redline_alerts:
        st.error("🚨 **CRITICAL REDLINE ALERTS ON ACTIVE HOLDINGS:**\n\n" + "\n".join(f"• **{a}**" for a in report.critical_redline_alerts))
    if report.sector_warnings:
        st.warning("⚠️ **SECTOR CONCENTRATION WARNINGS (>40% CAP):**\n\n" + "\n".join(f"• {w}" for w in report.sector_warnings))

    st.markdown("---")

    # Tabbed Views
    tab1, tab2, tab3, tab4 = st.tabs([
        "💼 Active Holdings & Status",
        "📊 Sector Diversification",
        "⚖️ Rebalancing Blueprint",
        "🎯 Algorithmic Target Model",
    ])

    with tab1:
        st.info(f"💡 **Strategic Advisory Plan:** {report.summary_action_plan}")

        pos_table = []
        for p in report.positions:
            pnl_sign = "+" if p.unrealized_pnl >= 0 else ""
            pos_table.append(
                {
                    "Symbol": p.symbol,
                    "Sector": p.sector.replace("_", " ").title(),
                    "Shares": f"{p.shares:.0f}",
                    "Avg Buy Price": f"₹{p.buy_price:,.2f}",
                    "Current Price": f"₹{p.current_price:,.2f}",
                    "Current Value": f"₹{p.current_value:,.2f}",
                    "Weight": f"{p.weight_pct:.1f}%",
                    "Unrealized P&L": f"{pnl_sign}₹{p.unrealized_pnl:,.2f} ({pnl_sign}{p.unrealized_pnl_pct:.2f}%)",
                    "12M Return Exp": f"{p.expected_return_12m:>+5.1f}%",
                    "Action Advice": p.action_badge,
                    "Action Rationale": p.action_rationale,
                }
            )
        st.dataframe(pos_table, use_container_width=True)

        st.caption("To edit, add, or delete positions, go to the **My Portfolio** page.")

    with tab2:
        sec_col1, sec_col2 = st.columns([3, 2])
        with sec_col1:
            st.subheader("Sector Allocation vs 40% Concentration Cap")
            fig = plot_sector_allocations(report.sector_exposures, max_cap_pct=40.0)
            if fig:
                st.plotly_chart(fig, use_container_width=True)

        with sec_col2:
            st.subheader("Concentration Audit")
            sec_rows = []
            for s, w in report.sector_exposures.items():
                if w > 40.0:
                    status = "🚨 EXCEEDS 40% CAP"
                elif w > 30.0:
                    status = "⚠️ Near Cap (>30%)"
                else:
                    status = "✅ Within Limit"
                sec_rows.append(
                    {
                        "Sector": s.replace("_", " ").title(),
                        "Weight (%)": f"{w:.1f}%",
                        "Max Cap": "40.0%",
                        "Compliance": status,
                    }
                )
            st.dataframe(sec_rows, use_container_width=True)

    with tab3:
        st.subheader("Automated Rebalancing & Cash Flow Execution")
        st.caption(report.rebalancing_blueprint.strategic_summary)

        b_kpi1, b_kpi2, b_kpi3 = st.columns(3)
        with b_kpi1:
            render_kpi_tile(
                "Capital Unlocked (Trims)",
                f"₹{report.rebalancing_blueprint.total_capital_unlocked:,.2f}",
                subtitle="From exits & overweight trims",
            )
        with b_kpi2:
            render_kpi_tile(
                "Capital Needed (Adds)",
                f"₹{report.rebalancing_blueprint.total_capital_needed:,.2f}",
                subtitle="For conviction accumulation",
            )
        with b_kpi3:
            net_cf = report.rebalancing_blueprint.net_cash_flow
            net_sign = "+" if net_cf >= 0 else ""
            render_kpi_tile(
                "Net Cash Flow",
                f"{net_sign}₹{net_cf:,.2f}",
                subtitle="Surplus unlocked" if net_cf >= 0 else "Fresh capital required",
                delta="Capital Surplus" if net_cf >= 0 else "Deficit Needed",
                delta_color="normal" if net_cf >= 0 else "inverse",
            )

        if report.rebalancing_blueprint.orders:
            st.write("#### Recommended Execution Orders")
            st.dataframe(
                [
                    {
                        "Symbol": o.symbol,
                        "Action": o.action,
                        "Shares": f"{o.shares:.0f}",
                        "Est. Price": f"₹{o.estimated_price:,.2f}",
                        "Capital Impact": f"₹{o.capital_impact:,.2f}",
                        "Target Weight": f"{o.target_weight_pct:.1f}%",
                        "Rationale": o.rationale,
                    }
                    for o in report.rebalancing_blueprint.orders
                ],
                use_container_width=True,
            )
        else:
            st.success("No rebalancing orders required. Portfolio allocation is fully compliant.")

    with tab4:
        st.subheader("Algorithmic Strategy Target Model (Quarterly Nifty 500)")
        st.caption("Latest target holdings calculated by the institutional multi-factor optimization engine.")

        cur = conn.cursor()
        cur.execute(
            """
            SELECT run_id, asof_date, COUNT(*) as holdings_count
            FROM portfolio_history
            GROUP BY run_id, asof_date
            ORDER BY asof_date DESC
            LIMIT 1
            """
        )
        latest_run = cur.fetchone()

        if latest_run:
            run_id, asof_date, _ = latest_run
            st.write(f"**Latest Optimization Run:** `{run_id[:12]}` | As-Of Date: **{asof_date}**")

            cur.execute(
                """
                SELECT symbol, target_weight, action, shares_target, executed
                FROM portfolio_history
                WHERE run_id = ?
                ORDER BY target_weight DESC
                """,
                (run_id,),
            )
            model_holdings = cur.fetchall()

            # Compute REAL sectors using PointInTimeDataAccess
            pit = PointInTimeDataAccess(conn, asof=date.fromisoformat(asof_date))
            model_sector_alloc: dict[str, float] = {}
            model_table = []
            for h in model_holdings:
                sym, weight, act, shares, executed = h[0], float(h[1]), h[2], h[3], h[4]
                sec = pit.get_sector(sym) or "Diversified"
                model_sector_alloc[sec] = model_sector_alloc.get(sec, 0.0) + weight * 100.0
                model_table.append(
                    {
                        "Symbol": sym,
                        "Sector": sec.replace("_", " ").title(),
                        "Target Weight": f"{weight*100:.1f}%",
                        "Model Action": act,
                        "Target Shares": shares or "-",
                        "Status": "✅ Confirmed" if executed == 1 else "⏳ Pending",
                    }
                )

            m_col1, m_col2 = st.columns([3, 2])
            with m_col1:
                st.dataframe(model_table, use_container_width=True)
            with m_col2:
                model_fig = plot_sector_allocations(model_sector_alloc, max_cap_pct=40.0)
                if model_fig:
                    st.plotly_chart(model_fig, use_container_width=True)
        else:
            st.info("No algorithmic model runs found in database.")

else:
    # Portfolio is empty
    st.info(f"ℹ️ **{current_portfolio.name} has no holdings recorded yet.**")
    st.write(
        "To view real-time portfolio health status, P&L performance, sector concentration against the 40% cap, "
        "and automated rebalance guidance, add your stock holdings or import a CSV from your broker."
    )
    st.markdown("👉 **Go to the `My Portfolio` page (sidebar) to add holdings or upload a CSV.**")

    st.markdown("---")
    st.subheader("🎯 Algorithmic Strategy Target Model (Reference)")
    st.caption("Here is the latest multi-factor model portfolio recommended by the quantitative engine:")

    cur = conn.cursor()
    cur.execute(
        """
        SELECT run_id, asof_date, COUNT(*) as holdings_count
        FROM portfolio_history
        GROUP BY run_id, asof_date
        ORDER BY asof_date DESC
        LIMIT 1
        """
    )
    latest_run = cur.fetchone()
    if latest_run:
        run_id, asof_date, _ = latest_run
        st.write(f"**Run:** `{run_id[:12]}` | Date: **{asof_date}**")
        cur.execute(
            """
            SELECT symbol, target_weight, action, shares_target, executed
            FROM portfolio_history
            WHERE run_id = ?
            ORDER BY target_weight DESC
            """,
            (run_id,),
        )
        model_holdings = cur.fetchall()
        pit = PointInTimeDataAccess(conn, asof=date.fromisoformat(asof_date))
        model_sector_alloc = {}
        model_table = []
        for h in model_holdings:
            sym, weight, act, shares, executed = h[0], float(h[1]), h[2], h[3], h[4]
            sec = pit.get_sector(sym) or "Diversified"
            model_sector_alloc[sec] = model_sector_alloc.get(sec, 0.0) + weight * 100.0
            model_table.append(
                {
                    "Symbol": sym,
                    "Sector": sec.replace("_", " ").title(),
                    "Target Weight": f"{weight*100:.1f}%",
                    "Model Action": act,
                    "Target Shares": shares or "-",
                    "Status": "✅ Confirmed" if executed == 1 else "⏳ Pending",
                }
            )
        m_col1, m_col2 = st.columns([3, 2])
        with m_col1:
            st.dataframe(model_table, use_container_width=True)
        with m_col2:
            model_fig = plot_sector_allocations(model_sector_alloc, max_cap_pct=40.0)
            if model_fig:
                st.plotly_chart(model_fig, use_container_width=True)

conn.close()
