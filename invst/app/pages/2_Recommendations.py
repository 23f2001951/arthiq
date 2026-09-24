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
from invst.data_access import PointInTimeDataAccess
from invst.scoring.composite import compute_composite_scores
from invst.reporting.rationale import generate_plain_english_rationale
from app.components.stock_card import render_stock_card

st.set_page_config(page_title="Recommendations — invst", page_icon="💡", layout="wide")
st.title("💡 Quarterly Stock Recommendations")

cfg = get_config()
conn = sqlite3.connect(str(cfg.database.path))

st.sidebar.subheader("Filter Settings")
asof_input = st.sidebar.date_input("As-Of Date", value=date.today())

pit = PointInTimeDataAccess(conn, asof=asof_input)
scorecards = compute_composite_scores(pit, filter_universe_first=False)

if scorecards:
    top_candidates = scorecards[:8]
    st.write(f"Showing Top {len(top_candidates)} evidence-backed recommendations as of **{asof_input.isoformat()}**.")

    for idx, sc in enumerate(top_candidates):
        rationale = generate_plain_english_rationale(
            symbol=sc.symbol,
            company_name=sc.symbol,
            sector=sc.sector,
            action="BUY",
            target_weight=0.125,
            current_weight=0.0,
            scorecard={
                "quality_details": sc.quality_details,
                "valuation_details": sc.valuation_details,
                "risk_details": sc.risk_details,
                "sentiment_details": sc.sentiment_details,
            },
        )

        render_stock_card(
            symbol=sc.symbol,
            sector=sc.sector,
            action="BUY",
            target_weight=0.125,
            current_weight=0.0,
            rationale=rationale,
            scorecard={
                "composite_score": sc.composite_score,
                "quality_score": sc.quality_score,
                "valuation_score": sc.valuation_score,
                "risk_score": sc.risk_score,
                "sentiment_overlay_points": sc.sentiment_overlay_points,
                "quality_details": sc.quality_details,
                "valuation_details": sc.valuation_details,
                "risk_details": sc.risk_details,
            },
        )
else:
    st.warning("No stocks passed screening criteria or insufficient data as-of the selected date.")

conn.close()
