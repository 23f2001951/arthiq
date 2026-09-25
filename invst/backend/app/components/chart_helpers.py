"""Plotly Chart Helper Utilities for Streamlit."""

from __future__ import annotations

from typing import Sequence
import pandas as pd

try:
    import plotly.graph_objects as go
except ImportError:
    go = None


def plot_equity_curve(
    dates: Sequence[str],
    portfolio_values: Sequence[float],
    benchmark_values: Optional[Sequence[float]] = None,
    benchmark_label: str = "Nifty 500 TRI",
):
    """Generate an interactive line chart comparing strategy vs benchmark equity."""
    if go is None or not dates or not portfolio_values:
        return None

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=list(dates),
            y=list(portfolio_values),
            mode="lines",
            name="Strategy Portfolio",
            line=dict(color="#2b6cb0", width=2.5),
        )
    )

    if benchmark_values and len(benchmark_values) == len(portfolio_values):
        fig.add_trace(
            go.Scatter(
                x=list(dates),
                y=list(benchmark_values),
                mode="lines",
                name=benchmark_label,
                line=dict(color="#718096", width=1.5, dash="dash"),
            )
        )

    fig.update_layout(
        title="Walk-Forward Equity Curve",
        xaxis_title="Date",
        yaxis_title="Portfolio Value (INR)",
        hovermode="x unified",
        template="plotly_white",
        margin=dict(l=40, r=40, t=50, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def plot_drawdowns(dates: Sequence[str], drawdowns: Sequence[float]):
    """Generate an area chart of historical peak-to-trough drawdowns."""
    if go is None or not dates or not drawdowns:
        return None

    dd_pct = [d * 100 for d in drawdowns]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=list(dates),
            y=dd_pct,
            mode="lines",
            fill="tozeroy",
            name="Drawdown",
            line=dict(color="#e53e3e", width=1.5),
            fillcolor="rgba(229, 62, 62, 0.2)",
        )
    )
    fig.update_layout(
        title="Historical Drawdown (%)",
        xaxis_title="Date",
        yaxis_title="Drawdown (%)",
        template="plotly_white",
        margin=dict(l=40, r=40, t=50, b=40),
    )
    return fig


def plot_sector_allocations(allocations: dict[str, float], max_cap_pct: float = 40.0):
    """Generate a horizontal bar chart of sector allocations with cap reference."""
    if go is None or not allocations:
        return None

    sectors = [s.replace("_", " ").title() for s in allocations.keys()]
    raw_weights = list(allocations.values())
    
    # Auto-detect whether weights are fractions (0.0-1.0) or already percentages (0.0-100.0)
    is_fraction = max(raw_weights) <= 1.0 if raw_weights else True
    weights = [round(w * 100.0 if is_fraction else w, 1) for w in raw_weights]

    colors = ["#e53e3e" if w > max_cap_pct else "#3182ce" for w in weights]

    fig = go.Figure(
        go.Bar(
            x=weights,
            y=sectors,
            orientation="h",
            marker=dict(color=colors),
            text=[f"{w:.1f}%" for w in weights],
            textposition="auto",
        )
    )
    if max_cap_pct > 0:
        fig.add_vline(
            x=max_cap_pct,
            line_dash="dash",
            line_color="#e53e3e",
            annotation_text=f"Max {max_cap_pct:.0f}% Cap",
            annotation_position="top right",
        )
    fig.update_layout(
        title="Sector Weight Allocations (%) vs 40% Cap",
        xaxis_title="Weight (%)",
        template="plotly_white",
        margin=dict(l=40, r=40, t=50, b=40),
    )
    return fig

