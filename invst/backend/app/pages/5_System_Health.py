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
from invst.monitoring.data_quality import run_all_data_quality_checks
from invst.monitoring.pit_audit import run_full_pit_audit

st.set_page_config(page_title="System Health — invst", page_icon="🛡️", layout="wide")
st.title("🛡️ System Health & Data Integrity")

cfg = get_config()
conn = sqlite3.connect(str(cfg.database.path))

st.subheader("Data Quality Checks")
dq_results = run_all_data_quality_checks(conn, asof=date.today())
for res in dq_results:
    if res.passed:
        st.success(f"**{res.check_name}**: {res.message}")
    else:
        st.warning(f"**{res.check_name}**: {res.message}")

st.markdown("---")
st.subheader("Point-in-Time (PIT) Anti-Lookahead Audits")
pit_results = run_full_pit_audit(conn, asof=date.today())
for res in pit_results:
    if res.passed:
        st.success(f"**{res.audit_name}**: {res.message}")
    else:
        st.error(f"**{res.audit_name}**: {res.message} ({res.violations_count} violations)")

conn.close()
