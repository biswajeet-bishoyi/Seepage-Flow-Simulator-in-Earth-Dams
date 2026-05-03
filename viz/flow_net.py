"""
Flow net visualization: equipotential lines, streamlines, and combined flow nets.

All functions accept pre-computed arrays from the engine and return Plotly figure objects.
No physics calculations are performed here.
"""

import numpy as np
import plotly.graph_objects as go
from numpy.typing import NDArray

from viz.colormap import (
    DAM_FILL_COLOR,
    DAM_LINE_COLOR,
    HEAD_COLORSCALE,
    VELOCITY_COLORSCALE,
)


def plot_head_contour(
    h: NDArray[np.float64],
    x: NDArray[np.float64],
    y: NDArray[np.float64],
    dam_x: NDArray[np.float64] | None = None,
    dam_y: NDArray[np.float64] | None = None,
) -> go.Figure:
    """
    Create a color flood map of the hydraulic head distribution.

    Blue = high head (upstream), Red = low head (downstream).

    Parameters
    ----------
    h : NDArray[np.float64]
        Head field, shape (Ny, Nx) [m].
    x : NDArray[np.float64]
        X-coordinates, shape (Nx,) [m].
    y : NDArray[np.float64]
        Y-coordinates, shape (Ny,) [m].
    dam_x, dam_y : NDArray or None
        Dam profile vertices for overlay.

    Returns
    -------
    go.Figure
        Plotly figure with head contour.
    """
    fig = go.Figure()

    # Head field color flood
    fig.add_trace(go.Contour(
        x=x,
        y=y,
        z=h,
        colorscale=HEAD_COLORSCALE,
        contours=dict(
            coloring="heatmap",
            showlines=False,
        ),
        colorbar=dict(
            title=dict(text="Head h [m]", side="right"),
            thickness=15,
            len=0.8,
        ),
        name="Head Field",
        hovertemplate="x: %{x:.1f} m<br>y: %{y:.1f} m<br>h: %{z:.2f} m<extra></extra>",
    ))

    # Dam outline
    if dam_x is not None and dam_y is not None:
        fig.add_trace(go.Scatter(
            x=dam_x,
            y=dam_y,
            mode="lines",
            line=dict(color=DAM_LINE_COLOR, width=3),
            fill="toself",
            fillcolor=DAM_FILL_COLOR,
            name="Dam Body",
            hoverinfo="skip",
        ))

    fig.update_layout(
        xaxis_title="Distance [m]",
        yaxis_title="Elevation [m]",
        yaxis_scaleanchor="x",
        yaxis_scaleratio=1,
        margin=dict(l=60, r=20, t=40, b=50),
        template="plotly_dark",
    )

    return fig


def plot_equipotential_lines(
    h: NDArray[np.float64],
    x: NDArray[np.float64],
    y: NDArray[np.float64],
    n_levels: int = 10,
    H_u: float | None = None,
    H_d: float | None = None,
) -> go.Contour:
    """
    Create equipotential contour lines at equally spaced head intervals.

    Parameters
    ----------
    h : NDArray[np.float64]
        Head field, shape (Ny, Nx) [m].
    x : NDArray[np.float64]
        X-coordinates [m].
    y : NDArray[np.float64]
        Y-coordinates [m].
    n_levels : int
        Number of equipotential lines (potential drops).
    H_u, H_d : float or None
        Head range. If None, derived from data.

    Returns
    -------
    go.Contour
        Plotly contour trace.
    """
    if H_u is None:
        H_u = float(np.max(h))
    if H_d is None:
        H_d = float(np.min(h))

    dh = (H_u - H_d) / (n_levels + 1)
    levels = np.arange(H_d + dh, H_u, dh)

    return go.Contour(
        x=x,
        y=y,
        z=h,
        contours=dict(
            coloring="none",
            showlines=True,
            start=float(levels[0]) if len(levels) > 0 else H_d,
            end=float(levels[-1]) if len(levels) > 0 else H_u,
            size=dh,
        ),
        line=dict(color="rgba(255, 255, 255, 0.6)", width=1.5),
        showscale=False,
        name="Equipotential Lines",
        hovertemplate="x: %{x:.1f} m<br>y: %{y:.1f} m<br>h: %{z:.2f} m<extra></extra>",
    )


def plot_streamlines(
    psi: NDArray[np.float64],
    x: NDArray[np.float64],
    y: NDArray[np.float64],
    n_tubes: int = 6,
) -> go.Contour:
    """
    Create streamline contours from the stream function.

    Streamlines are iso-contours of ψ, spaced at Δψ = q / N_f.

    Parameters
    ----------
    psi : NDArray[np.float64]
        Stream function, shape (Ny, Nx).
    x : NDArray[np.float64]
        X-coordinates [m].
    y : NDArray[np.float64]
        Y-coordinates [m].
    n_tubes : int
        Number of flow tubes (streamlines).

    Returns
    -------
    go.Contour
        Plotly contour trace for streamlines.
    """
    psi_min = float(np.min(psi))
    psi_max = float(np.max(psi))
    dpsi = (psi_max - psi_min) / (n_tubes + 1) if psi_max > psi_min else 1.0

    return go.Contour(
        x=x,
        y=y,
        z=psi,
        contours=dict(
            coloring="none",
            showlines=True,
            start=psi_min + dpsi,
            end=psi_max - dpsi / 2,
            size=dpsi,
        ),
        line=dict(color="rgba(0, 200, 255, 0.5)", width=1.5, dash="dot"),
        showscale=False,
        name="Streamlines",
        hoverinfo="skip",
    )


def plot_phreatic_line(
    phreatic_x: NDArray[np.float64],
    phreatic_y: NDArray[np.float64],
) -> go.Scatter:
    """
    Create the phreatic line overlay trace.

    Rendered as a bold dashed blue line with a red exit point marker.

    Parameters
    ----------
    phreatic_x : NDArray[np.float64]
        X-coordinates of the phreatic line [m].
    phreatic_y : NDArray[np.float64]
        Y-coordinates of the phreatic line [m].

    Returns
    -------
    go.Scatter
        Plotly scatter trace.
    """
    return go.Scatter(
        x=phreatic_x,
        y=phreatic_y,
        mode="lines+markers",
        line=dict(color="#3b82f6", width=3, dash="dash"),
        marker=dict(
            size=[0] * (len(phreatic_x) - 1) + [12],
            color=["rgba(0,0,0,0)"] * (len(phreatic_x) - 1) + ["#ef4444"],
            symbol="circle",
            line=dict(width=2, color="white"),
        ),
        name="Phreatic Line",
        hovertemplate="x: %{x:.1f} m<br>y: %{y:.2f} m<extra>Phreatic</extra>",
    )


def create_flow_net_figure(
    h: NDArray[np.float64],
    psi: NDArray[np.float64] | None,
    x: NDArray[np.float64],
    y: NDArray[np.float64],
    dam_x: NDArray[np.float64],
    dam_y: NDArray[np.float64],
    phreatic_x: NDArray[np.float64],
    phreatic_y: NDArray[np.float64],
    H_u: float,
    H_d: float,
    n_equipotentials: int = 10,
    n_streamlines: int = 6,
    show_equipotentials: bool = True,
    show_streamlines: bool = True,
    show_phreatic: bool = True,
    title: str = "Seepage Flow Net — Earth Dam",
) -> go.Figure:
    """
    Create the complete flow net visualization combining all layers.

    Parameters
    ----------
    h : NDArray
        Head field.
    psi : NDArray or None
        Stream function (None to skip streamlines).
    x, y : NDArray
        Grid coordinates.
    dam_x, dam_y : NDArray
        Dam profile vertices.
    phreatic_x, phreatic_y : NDArray
        Phreatic line coordinates.
    H_u, H_d : float
        Head range.
    n_equipotentials : int
        Number of equipotential lines.
    n_streamlines : int
        Number of streamlines.
    show_equipotentials, show_streamlines, show_phreatic : bool
        Layer visibility toggles.
    title : str
        Figure title.

    Returns
    -------
    go.Figure
        Complete flow net figure.
    """
    fig = go.Figure()

    # Layer 1: Head field color flood
    fig.add_trace(go.Contour(
        x=x,
        y=y,
        z=h,
        colorscale=HEAD_COLORSCALE,
        contours=dict(coloring="heatmap", showlines=False),
        colorbar=dict(
            title=dict(text="h [m]", side="right"),
            thickness=12,
            len=0.7,
            x=1.02,
        ),
        name="Head Field",
        hovertemplate="x: %{x:.1f} m<br>y: %{y:.1f} m<br>h: %{z:.2f} m<extra></extra>",
    ))

    # Layer 2: Equipotential lines
    if show_equipotentials:
        fig.add_trace(plot_equipotential_lines(h, x, y, n_equipotentials, H_u, H_d))

    # Layer 3: Streamlines
    if show_streamlines and psi is not None:
        fig.add_trace(plot_streamlines(psi, x, y, n_streamlines))

    # Layer 4: Dam outline
    fig.add_trace(go.Scatter(
        x=dam_x,
        y=dam_y,
        mode="lines",
        line=dict(color=DAM_LINE_COLOR, width=2.5),
        name="Dam Body",
        hoverinfo="skip",
    ))

    # Layer 5: Phreatic line
    if show_phreatic:
        fig.add_trace(plot_phreatic_line(phreatic_x, phreatic_y))

    # Layout
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=16, color="#e2e8f0"),
            x=0.5,
        ),
        xaxis=dict(
            title="Horizontal Distance [m]",
            showgrid=True,
            gridcolor="rgba(255,255,255,0.1)",
            zeroline=False,
        ),
        yaxis=dict(
            title="Elevation [m]",
            showgrid=True,
            gridcolor="rgba(255,255,255,0.1)",
            zeroline=False,
            scaleanchor="x",
            scaleratio=1,
        ),
        template="plotly_dark",
        paper_bgcolor="#0f172a",
        plot_bgcolor="#1e293b",
        margin=dict(l=60, r=80, t=60, b=50),
        legend=dict(
            x=0.01,
            y=0.99,
            bgcolor="rgba(15,23,42,0.8)",
            bordercolor="rgba(255,255,255,0.2)",
            borderwidth=1,
            font=dict(size=11),
        ),
        hoverlabel=dict(bgcolor="#1e293b", font_size=12),
    )

    return fig


def create_velocity_magnitude_plot(
    v_x: NDArray[np.float64],
    v_y: NDArray[np.float64],
    x: NDArray[np.float64],
    y: NDArray[np.float64],
    dam_x: NDArray[np.float64],
    dam_y: NDArray[np.float64],
) -> go.Figure:
    """
    Create a velocity magnitude contour plot.

    Parameters
    ----------
    v_x, v_y : NDArray
        Velocity components [m/s].
    x, y : NDArray
        Grid coordinates [m].
    dam_x, dam_y : NDArray
        Dam profile vertices.

    Returns
    -------
    go.Figure
        Velocity magnitude plot.
    """
    v_mag = np.sqrt(v_x**2 + v_y**2)

    fig = go.Figure()

    fig.add_trace(go.Contour(
        x=x,
        y=y,
        z=v_mag,
        colorscale=VELOCITY_COLORSCALE,
        contours=dict(coloring="heatmap", showlines=True),
        colorbar=dict(
            title=dict(text="|v| [m/s]", side="right"),
            thickness=12,
            len=0.7,
        ),
        name="Velocity Magnitude",
        hovertemplate=(
            "x: %{x:.1f} m<br>y: %{y:.1f} m<br>"
            "|v|: %{z:.2e} m/s<extra></extra>"
        ),
    ))

    fig.add_trace(go.Scatter(
        x=dam_x, y=dam_y,
        mode="lines",
        line=dict(color=DAM_LINE_COLOR, width=2.5),
        name="Dam Body",
        hoverinfo="skip",
    ))

    fig.update_layout(
        title=dict(
            text="Darcy Velocity Magnitude",
            font=dict(size=16, color="#e2e8f0"),
            x=0.5,
        ),
        xaxis_title="Distance [m]",
        yaxis_title="Elevation [m]",
        yaxis_scaleanchor="x",
        template="plotly_dark",
        paper_bgcolor="#0f172a",
        plot_bgcolor="#1e293b",
        margin=dict(l=60, r=80, t=60, b=50),
    )

    return fig
