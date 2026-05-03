"""
Safety dashboard gauge and display widgets.

Creates Plotly gauge charts and visual indicators for exit gradient,
factor of safety, and risk badges.
"""

import plotly.graph_objects as go

from engine.constants import CRITICAL_GRADIENT
from engine.safety import get_risk_color, get_risk_description
from engine.types import RiskLevel


def create_exit_gradient_gauge(
    i_e: float,
    i_cr: float = CRITICAL_GRADIENT,
) -> go.Figure:
    """
    Create a radial gauge for the exit gradient.

    Scale: 0 → 2.0, with colored zones matching risk classification.
    """
    ratio = i_e / i_cr if i_cr > 0 else 0

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=i_e,
        number=dict(suffix="", font=dict(size=28, color="#e2e8f0")),
        delta=dict(reference=i_cr, relative=False, position="bottom",
                   increasing=dict(color="#ef4444"), decreasing=dict(color="#22c55e")),
        title=dict(text="Exit Gradient (i<sub>e</sub>)", font=dict(size=14, color="#94a3b8")),
        gauge=dict(
            axis=dict(range=[0, 2.0], tickwidth=1, tickcolor="#475569",
                      tickfont=dict(color="#94a3b8")),
            bar=dict(color="#3b82f6", thickness=0.3),
            bgcolor="#1e293b",
            borderwidth=2,
            bordercolor="#334155",
            steps=[
                dict(range=[0.0, 0.25], color="rgba(34,197,94,0.3)"),
                dict(range=[0.25, 0.50], color="rgba(234,179,8,0.3)"),
                dict(range=[0.50, 0.70], color="rgba(249,115,22,0.3)"),
                dict(range=[0.70, 2.0], color="rgba(239,68,68,0.3)"),
            ],
            threshold=dict(line=dict(color="#ef4444", width=3), thickness=0.8, value=i_cr),
        ),
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=30, r=30, t=60, b=30), height=250,
        font=dict(color="#e2e8f0"),
    )
    return fig


def create_fs_gauge(
    fs: float,
    risk: RiskLevel,
) -> go.Figure:
    """
    Create a Factor of Safety gauge display.
    """
    color = get_risk_color(risk)

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=min(fs, 10.0),
        number=dict(font=dict(size=36, color=color)),
        title=dict(text="FS<sub>piping</sub>", font=dict(size=14, color="#94a3b8")),
        gauge=dict(
            axis=dict(range=[0, 10], tickwidth=1, tickcolor="#475569",
                      tickfont=dict(color="#94a3b8")),
            bar=dict(color=color, thickness=0.3),
            bgcolor="#1e293b",
            borderwidth=2,
            bordercolor="#334155",
            steps=[
                dict(range=[0, 1.5], color="rgba(239,68,68,0.3)"),
                dict(range=[1.5, 2.0], color="rgba(249,115,22,0.3)"),
                dict(range=[2.0, 4.0], color="rgba(234,179,8,0.3)"),
                dict(range=[4.0, 10.0], color="rgba(34,197,94,0.3)"),
            ],
            threshold=dict(line=dict(color="#22c55e", width=3), thickness=0.8, value=4.0),
        ),
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=30, r=30, t=60, b=30), height=250,
        font=dict(color="#e2e8f0"),
    )
    return fig


def create_discharge_sparkline(q_history: list[float]) -> go.Figure:
    """
    Create a sparkline chart showing discharge history across parameter changes.
    """
    fig = go.Figure(go.Scatter(
        y=q_history,
        mode="lines+markers",
        line=dict(color="#3b82f6", width=2),
        marker=dict(size=4, color="#60a5fa"),
        fill="tozeroy",
        fillcolor="rgba(59,130,246,0.1)",
        hovertemplate="q: %{y:.2e} m²/s<extra></extra>",
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=5, r=5, t=5, b=5), height=60,
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        showlegend=False,
    )
    return fig
