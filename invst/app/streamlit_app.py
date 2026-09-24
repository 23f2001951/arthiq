import sys
from pathlib import Path

# Ensure src/ and project root are in sys.path for direct streamlit execution
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import sqlite3
import streamlit as st

from invst.config import get_config

st.set_page_config(
    page_title="invst — Investment Decision Support",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

cfg = get_config()

st.title("📈 invst — Personal Investment Decision-Support")
st.caption("Personal Decision-Support Platform for Indian Listed Equities (NSE/BSE, Nifty 500 Universe)")

col1, col2, col3 = st.columns(3)
col1.info("🎯 **Objective:** Produce single, written, evidence-backed recommendations per stock.")
col2.info("⚖️ **Constraints:** Max 25% single-stock weight, Max 40% sector cap, 8 holdings.")
col3.info("🛡️ **Safety:** Strictly manual execution. Zero broker API order write permissions.")

st.markdown("---")
st.subheader("Platform Quick Navigation")

nav_col1, nav_col2, nav_col3 = st.columns(3)
with nav_col1:
    st.markdown("### 📊 [Dashboard](Dashboard)")
    st.write("Overview of active portfolio, current performance vs Nifty 500, and next rebalance schedule.")

with nav_col2:
    st.markdown("### 💡 [Recommendations](Recommendations)")
    st.write("Latest quarterly stock recommendations with plain-English rationales and underlying scorecards.")

with nav_col3:
    st.markdown("### 🧪 [Backtest Results](Backtest_Results)")
    st.write("Interactive 10-year walk-forward backtest equity curves, drawdowns, and risk-adjusted metrics.")

st.markdown("---")
st.caption(f"Database: `{cfg.database.path}` | Rebalance Cadence: `{cfg.rebalance.cadence}` | Benchmark: `{cfg.universe.benchmark}`")
