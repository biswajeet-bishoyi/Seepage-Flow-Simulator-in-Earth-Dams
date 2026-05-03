"""
Particle animation and animated streamline visualization.

Creates animated particle tracers following streamlines through the dam.
"""

import numpy as np
import plotly.graph_objects as go
from numpy.typing import NDArray

from viz.colormap import VELOCITY_COLORSCALE


def create_particle_animation(
    v_x: NDArray[np.float64],
    v_y: NDArray[np.float64],
    x: NDArray[np.float64],
    y: NDArray[np.float64],
    h: NDArray[np.float64],
    dam_x: NDArray[np.float64] | None = None,
    dam_y: NDArray[np.float64] | None = None,
    phreatic_y_interp: NDArray[np.float64] | None = None,
    n_particles: int = 40,
    n_frames: int = 60,
    dt_scale: float = 0.3,
) -> go.Figure:
    """
    Create animated particle tracers following velocity field streamlines.

    Particles seed at upstream face, advect through the field, and respawn
    when they exit downstream.
    """
    Ny, Nx = v_x.shape
    dx_val = x[1] - x[0]
    dy_val = y[1] - y[0]
    x_max = float(x[-1])
    y_max = float(y[-1])

    v_mag = np.sqrt(v_x**2 + v_y**2)
    v_max = float(np.max(v_mag)) if np.max(v_mag) > 0 else 1.0
    dt = dt_scale * dx_val / v_max if v_max > 0 else 1.0

    max_y_seed = float(phreatic_y_interp[0]) if phreatic_y_interp is not None else y_max
    particle_x = np.zeros(n_particles)
    particle_y = np.linspace(dy_val, min(max_y_seed, y_max - dy_val), n_particles)

    frames = []
    for frame_idx in range(n_frames):
        for p in range(n_particles):
            i = int(np.clip(particle_x[p] / dx_val, 0, Nx - 2))
            j = int(np.clip(particle_y[p] / dy_val, 0, Ny - 2))
            fx = (particle_x[p] / dx_val) - i
            fy = (particle_y[p] / dy_val) - j
            i1 = min(i + 1, Nx - 1)
            j1 = min(j + 1, Ny - 1)

            vx_l = (1-fx)*(1-fy)*v_x[j,i] + fx*(1-fy)*v_x[j,i1] + (1-fx)*fy*v_x[j1,i] + fx*fy*v_x[j1,i1]
            vy_l = (1-fx)*(1-fy)*v_y[j,i] + fx*(1-fy)*v_y[j,i1] + (1-fx)*fy*v_y[j1,i] + fx*fy*v_y[j1,i1]

            particle_x[p] += vx_l * dt
            particle_y[p] += vy_l * dt

            if particle_x[p] >= x_max or particle_x[p] < 0 or particle_y[p] >= y_max or particle_y[p] < 0:
                particle_x[p] = 0.0
                particle_y[p] = np.random.uniform(dy_val, min(max_y_seed, y_max - dy_val))

        colors = []
        for p in range(n_particles):
            ci = int(np.clip(particle_x[p] / dx_val, 0, Nx - 1))
            cj = int(np.clip(particle_y[p] / dy_val, 0, Ny - 1))
            colors.append(float(v_mag[cj, ci]))

        frames.append(go.Frame(
            data=[go.Scatter(x=particle_x.copy(), y=particle_y.copy(), mode="markers",
                marker=dict(size=6, color=colors, colorscale=VELOCITY_COLORSCALE, cmin=0, cmax=v_max, opacity=0.85),
                hoverinfo="skip")],
            name=str(frame_idx),
        ))

    fig = go.Figure(data=frames[0].data if frames else [], frames=frames)
    
    # Add dam outline
    if dam_x is not None and dam_y is not None:
        fig.add_trace(go.Scatter(
            x=dam_x, y=dam_y, mode="lines",
            line=dict(color="#b45309", width=2.5),
            name="Dam Body", hoverinfo="skip"
        ))
        
    fig.update_layout(
        updatemenus=[dict(type="buttons", showactive=False, x=0.05, y=-0.05, buttons=[
            dict(label="▶ Play", method="animate",
                 args=[None, dict(frame=dict(duration=50, redraw=True), fromcurrent=True, transition=dict(duration=0))]),
            dict(label="⏸ Pause", method="animate",
                 args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate", transition=dict(duration=0))]),
        ])],
        template="plotly_dark", paper_bgcolor="#0f172a", plot_bgcolor="#1e293b",
        xaxis_title="Distance [m]", yaxis_title="Elevation [m]", yaxis_scaleanchor="x",
        title=dict(text="Particle Flow Animation", font=dict(size=16, color="#e2e8f0"), x=0.5),
        margin=dict(l=60, r=20, t=60, b=80),
    )
    return fig
