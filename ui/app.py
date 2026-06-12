"""
Streamlit application for the Seepage Flow Simulator.

Main entry point: streamlit run ui/app.py

Layout:
    LEFT SIDEBAR  (30%): Input controls, results summary, safety dashboard
    MAIN AREA     (70%): Flow net visualization, phreatic line, safety gauges
"""

import io
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import streamlit as st

from engine.constants import CRITICAL_GRADIENT, POROSITY_DEFAULT
from engine.darcy import (
    classify_seepage_rating,
    compute_seepage_discharge,
    compute_stream_function,
    compute_velocity_field,
)
from engine.geometry import compute_base_width, compute_dam_profile
from engine.laplace_solver import create_grid, solve_laplace
from engine.phreatic import (
    compute_phreatic_line_for_dam,
    phreatic_line_table,
    phreatic_to_grid_indices,
)
from engine.safety import (
    classify_piping_risk,
    compute_exit_gradient,
    compute_heave_fs,
    compute_piping_fs,
    compute_seepage_velocity,
    get_risk_color,
    get_risk_description,
)
from engine.types import RiskLevel
from viz.colormap import format_scientific
from viz.flow_net import (
    create_flow_net_figure,
    create_velocity_magnitude_plot,
)
from viz.animation import create_particle_animation
from viz.safety_gauges import (
    create_discharge_sparkline,
    create_exit_gradient_gauge,
    create_fs_gauge,
)

# =============================================================================
# Page Config
# =============================================================================

st.set_page_config(
    page_title="Seepage Flow Simulator — Earth Dam",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# Custom CSS for dark premium look
# =============================================================================

st.markdown("""
<style>
    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
        border-right: 1px solid rgba(59,130,246,0.2);
    }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(30,41,59,0.8), rgba(15,23,42,0.9));
        border: 1px solid rgba(59,130,246,0.2);
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.3);
    }

    div[data-testid="stMetric"] label {
        color: #94a3b8 !important;
        font-size: 0.85rem !important;
    }

    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #e2e8f0 !important;
        font-weight: 700 !important;
    }

    /* Headers */
    h1, h2, h3 {
        color: #e2e8f0 !important;
    }

    /* Slider labels */
    .stSlider label {
        color: #94a3b8 !important;
    }

    /* Info/warning boxes */
    .risk-badge {
        display: inline-block;
        padding: 4px 16px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.9rem;
        letter-spacing: 0.05em;
    }

    /* Divider style */
    hr {
        border-color: rgba(59,130,246,0.15) !important;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        background: rgba(30,41,59,0.5);
        border-radius: 8px;
        color: #94a3b8;
        border: 1px solid rgba(59,130,246,0.15);
    }

    .stTabs [aria-selected="true"] {
        background: rgba(59,130,246,0.15) !important;
        color: #3b82f6 !important;
        border-color: rgba(59,130,246,0.3) !important;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# Session State Initialization
# =============================================================================

if "q_history" not in st.session_state:
    st.session_state.q_history = []

# =============================================================================
# Sidebar — Input Controls
# =============================================================================

with st.sidebar:
    st.markdown("## 🌊 Seepage Simulator")
    st.markdown("##### Earth Dam Analysis Tool")
    st.markdown("---")

    st.markdown("### 🔧 Hydraulic Parameters")

    H_u = st.slider(
        "Upstream Head H_u [m]",
        min_value=1.0, max_value=100.0, value=20.0, step=0.5,
        help="Hydraulic head at the upstream face of the dam",
    )

    H_d = st.slider(
        "Downstream Head H_d [m]",
        min_value=0.0, max_value=float(H_u - 0.5), value=min(2.0, H_u - 0.5), step=0.5,
        help="Hydraulic head at the downstream face",
    )

    # Validate heads
    if H_u <= H_d:
        st.error("⚠️ H_u must be greater than H_d")
        st.stop()

    k_exp = st.slider(
        "Conductivity k (log₁₀) [m/s]",
        min_value=-9.0, max_value=-3.0, value=-5.0, step=0.1,
        help="Hydraulic conductivity in log scale",
    )
    k = 10**k_exp
    st.caption(f"k = {format_scientific(k)} m/s")

    st.markdown("---")
    st.markdown("### 📐 Dam Geometry")

    W = st.slider("Crest Width W [m]", 5.0, 50.0, 10.0, 1.0)
    m_u = st.slider("Upstream Slope m_u (H:V)", 1.5, 5.0, 3.0, 0.1)
    m_d = st.slider("Downstream Slope m_d (H:V)", 1.5, 5.0, 2.5, 0.1)

    L = compute_base_width(W, m_u, m_d, H_u)
    st.info(f"📏 Base Width L = {L:.1f} m")

    st.markdown("---")
    st.markdown("### 🔲 Grid Resolution")

    precision_mode = st.toggle("Precision Mode", value=False,
                               help="High-fidelity: Nx=400, Ny=150")

    if precision_mode:
        Nx, Ny = 400, 150
        st.caption(f"Grid: {Nx} × {Ny} (Precision Mode)")
    else:
        Nx = st.slider("Grid Columns (Nx)", 50, 500, 200, 10)
        Ny = st.slider("Grid Rows (Ny)", 20, 200, 80, 5)

    st.markdown("---")
    st.markdown("### 🎨 Display Options")

    show_equipotentials = st.checkbox("Show Equipotentials", True)
    show_streamlines = st.checkbox("Show Streamlines", True)
    show_phreatic = st.checkbox("Show Phreatic Line", True)
    n_eq = st.slider("Equipotential Lines", 4, 20, 10, 1)
    n_sf = st.slider("Streamlines", 2, 12, 6, 1)

# =============================================================================
# Computation
# =============================================================================

with st.spinner("🔄 Solving Laplace equation..."):
    # 1. Compute phreatic line
    phreatic_x, phreatic_y = compute_phreatic_line_for_dam(H_u, H_d, L, m_u)

    # 1b. Compute dam profile to bound the phreatic line
    dam_x, dam_y = compute_dam_profile(H_u, W, m_u, m_d)
    
    # 2. Convert to grid indices for masking
    x_coords, y_coords, dx, dy = create_grid(Nx, Ny, L, H_u)
    dam_y_interp = np.interp(x_coords, dam_x, dam_y)
    phreatic_y_interp = np.interp(x_coords, phreatic_x, phreatic_y)
    
    # The effective saturated boundary is the minimum of the phreatic line and the dam surface
    effective_phreatic_y = np.minimum(phreatic_y_interp, dam_y_interp)
    phreatic_j = phreatic_to_grid_indices(effective_phreatic_y, x_coords, Nx, Ny, L, H_u)

    # 3. Solve Laplace equation
    h, iterations, residual, converged = solve_laplace(
        H_u=H_u, H_d=H_d, L=L, Nx=Nx, Ny=Ny,
        phreatic_j=phreatic_j,
    )

    # 4. (create_grid moved up)
    
    # 5. Compute derived quantities
    q = compute_seepage_discharge(k, H_u, H_d, L)
    v_x, v_y = compute_velocity_field(h, k, dx, dy)
    psi = compute_stream_function(v_x, v_y, dy)
    i_e = compute_exit_gradient(h, dx)
    fs_piping = compute_piping_fs(i_e)
    risk = classify_piping_risk(i_e)
    seepage_rating = classify_seepage_rating(q)
    v_s = compute_seepage_velocity(k, i_e)
    fs_heave = compute_heave_fs(h, dy)

    # 6. (dam profile computed above)

    # 7. Track q history
    st.session_state.q_history.append(q)
    if len(st.session_state.q_history) > 20:
        st.session_state.q_history = st.session_state.q_history[-20:]

# =============================================================================
# Main Area — Header
# =============================================================================

st.markdown("""
<div style="text-align:center; padding: 10px 0 5px 0;">
    <h1 style="font-size:2rem; background: linear-gradient(90deg, #3b82f6, #06b6d4);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom:0;">
        🌊 Seepage Flow Simulator
    </h1>
    <p style="color:#64748b; font-size:0.95rem; margin-top:4px;">
        2D Steady-State Seepage Analysis in Earth Dams — Finite Difference Method
    </p>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# Results Bar
# =============================================================================

risk_color = get_risk_color(risk)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Discharge q", f"{format_scientific(q)} m²/s")
    st.caption(f"Rating: **{seepage_rating.value}**")

with col2:
    st.metric("Exit Gradient i_e", f"{i_e:.4f}")
    st.caption(f"Critical: {CRITICAL_GRADIENT:.3f}")

with col3:
    st.metric("FS (Piping)", f"{fs_piping:.2f}" if fs_piping < 100 else "∞")
    st.markdown(
        f'<span class="risk-badge" style="background:{risk_color}; color:white;">'
        f'{risk.value}</span>',
        unsafe_allow_html=True,
    )

with col4:
    st.metric("Seepage Velocity", f"{format_scientific(v_s)} m/s")

with col5:
    st.metric("FS (Heave)", f"{fs_heave:.2f}" if fs_heave < 100 else "∞")

# Convergence info
if not converged:
    st.warning(
        f"⚠️ Solver did not converge within {iterations} iterations. "
        f"Residual: {residual:.2e}. Results may be approximate."
    )

# Critical alert
if risk == RiskLevel.CRITICAL:
    st.error(f"🚨 **CRITICAL ALERT** — {get_risk_description(risk)}")
elif risk == RiskLevel.HIGH:
    st.warning(f"⚠️ **HIGH RISK** — {get_risk_description(risk)}")

st.markdown("---")

# =============================================================================
# Visualization Tabs
# =============================================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🌐 Flow Net", "⚡ Velocity Field", "🎬 Animation", "📊 Safety Dashboard", "📋 Data Tables"
])

with tab1:
    fig_flow = create_flow_net_figure(
        h=h, psi=psi, x=x_coords, y=y_coords,
        dam_x=dam_x, dam_y=dam_y,
        phreatic_x=phreatic_x, phreatic_y=phreatic_y,
        H_u=H_u, H_d=H_d,
        n_equipotentials=n_eq, n_streamlines=n_sf,
        show_equipotentials=show_equipotentials,
        show_streamlines=show_streamlines,
        show_phreatic=show_phreatic,
    )
    fig_flow.update_layout(height=500)
    st.plotly_chart(fig_flow, use_container_width=True)

with tab2:
    fig_vel = create_velocity_magnitude_plot(v_x, v_y, x_coords, y_coords, dam_x, dam_y)
    fig_vel.update_layout(height=500)
    st.plotly_chart(fig_vel, use_container_width=True)

with tab3:
    fig_anim = create_particle_animation(
        v_x=v_x, v_y=v_y, x=x_coords, y=y_coords, h=h,
        dam_x=dam_x, dam_y=dam_y,
        n_particles=80, n_frames=60,
    )
    fig_anim.update_layout(height=500)
    st.plotly_chart(fig_anim, use_container_width=True)

with tab4:
    gc1, gc2 = st.columns(2)
    with gc1:
        fig_gauge_ie = create_exit_gradient_gauge(i_e)
        st.plotly_chart(fig_gauge_ie, use_container_width=True)
    with gc2:
        fig_gauge_fs = create_fs_gauge(fs_piping, risk)
        st.plotly_chart(fig_gauge_fs, use_container_width=True)

    st.markdown("#### Discharge History (last 20 changes)")
    if len(st.session_state.q_history) > 1:
        fig_spark = create_discharge_sparkline(st.session_state.q_history)
        st.plotly_chart(fig_spark, use_container_width=True)
    else:
        st.caption("Adjust parameters to build history...")

    st.markdown("#### Risk Assessment")
    st.markdown(f"**Risk Level:** {risk.value}")
    st.markdown(get_risk_description(risk))

with tab5:
    st.markdown("#### Phreatic Line Coordinates")
    table_data = phreatic_line_table(phreatic_x, phreatic_y)
    df_phreatic = pd.DataFrame(table_data, columns=["x [m]", "y [m]"])
    st.dataframe(df_phreatic, use_container_width=True)

    st.markdown("#### Solver Summary")
    summary = {
        "Parameter": ["H_u", "H_d", "k", "L", "Nx", "Ny", "q", "i_e", "FS_piping", "Risk"],
        "Value": [
            f"{H_u} m", f"{H_d} m", f"{format_scientific(k)} m/s",
            f"{L:.1f} m", str(Nx), str(Ny),
            f"{format_scientific(q)} m²/s", f"{i_e:.4f}",
            f"{fs_piping:.2f}" if fs_piping < 100 else "∞", risk.value,
        ],
    }
    st.dataframe(pd.DataFrame(summary), use_container_width=True)

# =============================================================================
# Export Section
# =============================================================================

st.markdown("---")

exp1, exp2, exp3 = st.columns(3)

with exp1:
    if st.button("📸 Export PNG", use_container_width=True):
        st.info("Use the camera icon on each Plotly chart to save as PNG.")

with exp2:
    # CSV export
    csv_buffer = io.StringIO()
    # Flatten head grid and phreatic line into CSV
    export_data = {
        "q_m2_per_s": [q],
        "exit_gradient": [i_e],
        "fs_piping": [fs_piping],
        "risk": [risk.value],
    }
    df_export = pd.DataFrame(export_data)
    csv_str = df_export.to_csv(index=False)
    st.download_button(
        "📥 Export CSV",
        data=csv_str,
        file_name="seepage_results.csv",
        mime="text/csv",
        use_container_width=True,
    )

with exp3:
    if st.button("🔄 Reset Defaults", use_container_width=True):
        st.session_state.q_history = []
        st.rerun()

# =============================================================================
# Footer
# =============================================================================

st.markdown("---")
st.markdown(
    '<div style="text-align:center; color:#475569; font-size:0.8rem; padding:10px 0;">'
    '🌊 Seepage Flow Simulator v1.0 | '
    'Finite Difference Method | Casagrande Phreatic Line | '
    'Terzaghi Safety Analysis'
    '</div>',
    unsafe_allow_html=True,
)
