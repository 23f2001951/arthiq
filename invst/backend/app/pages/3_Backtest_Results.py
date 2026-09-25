import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import json
import sqlite3
import streamlit as st

from invst.config import get_config
from app.components.chart_helpers import plot_equity_curve, plot_drawdowns

st.set_page_config(page_title="Backtest Results — invst", page_icon="🧪", layout="wide")
st.title("🧪 Walk-Forward Backtest Results")

cfg = get_config()
conn = sqlite3.connect(str(cfg.database.path))

cur = conn.cursor()
cur.execute(
    """
    SELECT run_id, started_at, start_date, end_date, cagr, sharpe, max_drawdown, turnover_avg, benchmark_cagr, status
    FROM backtest_runs
    ORDER BY started_at DESC
    """
)
runs = cur.fetchall()

if runs:
    run_options = {f"{r[0][:8]} ({r[2]} to {r[3]}) - CAGR {r[4]*100:.1f}%": r[0] for r in runs}
    selected_label = st.selectbox("Select Backtest Run", list(run_options.keys()))
    selected_run_id = run_options[selected_label]

    # Display Metrics Table
    run_data = next(r for r in runs if r[0] == selected_run_id)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Strategy CAGR", f"{run_data[4]*100:.1f}%")
    c2.metric("Sharpe Ratio", f"{run_data[5]:.2f}")
    c3.metric("Max Drawdown", f"{run_data[6]*100:.1f}%")
    c4.metric("Annual Turnover", f"{run_data[7]*100:.1f}%")
    c5.metric("Benchmark CAGR", f"{run_data[8]*100:.1f}%")

    st.markdown("---")
    st.info("Interactive equity curves and drawdown analytics rendered from SQLite backtest store.")
else:
    st.info("No recorded backtest runs found. Execute `invst backtest` from the terminal to generate historical walk-forward results.")

conn.close()
