"""KPI Tile UI Component for Streamlit."""

from __future__ import annotations

import streamlit as st


def render_kpi_tile(title: str, value: str, subtitle: str = "", delta: str = "", delta_color: str = "normal") -> None:
    """Render a styled metric tile."""
    st.metric(label=title, value=value, delta=delta if delta else None, delta_color=delta_color)
    if subtitle:
        st.caption(subtitle)
