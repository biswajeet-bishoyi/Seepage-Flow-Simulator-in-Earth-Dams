"""
Dam cross-section geometry helpers.

Provides functions for computing dam geometry, profiles, and point-in-dam
checks used for FDM domain masking.

Grid convention: h[j, i] where j=vertical (0=base), i=horizontal (0=upstream)
"""

import numpy as np
from numpy.typing import NDArray


def compute_base_width(
    W: float,
    m_u: float,
    m_d: float,
    H_u: float,
) -> float:
    """
    Compute the dam base width from geometry parameters.

    Formula:
        L = W + m_u × H_u + m_d × H_u

    Parameters
    ----------
    W : float
        Dam crest width [m]. Must be > 0.
    m_u : float
        Upstream slope ratio (H:V) [dimensionless]. Must be > 0.
    m_d : float
        Downstream slope ratio (H:V) [dimensionless]. Must be > 0.
    H_u : float
        Upstream hydraulic head / dam height [m]. Must be > 0.

    Returns
    -------
    float
        Dam base width L [m].
    """
    return W + m_u * H_u + m_d * H_u


def compute_dam_profile(
    H_u: float,
    W: float,
    m_u: float,
    m_d: float,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """
    Compute the dam cross-section profile as x,y coordinate arrays.

    The dam profile is a trapezoid with:
        - Base from x=0 to x=L
        - Upstream slope at angle defined by m_u (H:V)
        - Crest from upstream crest to downstream crest
        - Downstream slope at angle defined by m_d (H:V)

    Profile vertices (counterclockwise):
        (0, 0) → (L, 0) → (L - m_d·H_u, H_u) → (m_u·H_u, H_u) → (0, 0)

    Parameters
    ----------
    H_u : float
        Dam height [m].
    W : float
        Crest width [m].
    m_u : float
        Upstream slope ratio (H:V).
    m_d : float
        Downstream slope ratio (H:V).

    Returns
    -------
    tuple[NDArray, NDArray]
        (x_coords, y_coords) of the dam profile vertices.
    """
    L = compute_base_width(W, m_u, m_d, H_u)

    # Vertices of the trapezoidal dam cross-section
    x_upstream_toe = 0.0
    x_upstream_crest = m_u * H_u
    x_downstream_crest = m_u * H_u + W
    x_downstream_toe = L

    x = np.array([
        x_upstream_toe,
        x_downstream_toe,
        x_downstream_crest,
        x_upstream_crest,
        x_upstream_toe,  # close the polygon
    ])
    y = np.array([
        0.0,
        0.0,
        H_u,
        H_u,
        0.0,
    ])

    return x, y


def compute_dam_surface_elevation(
    x_values: NDArray[np.float64],
    H_u: float,
    W: float,
    m_u: float,
    m_d: float,
) -> NDArray[np.float64]:
    """
    Compute the dam surface elevation at given x-coordinates.

    For each x, returns the y-coordinate of the dam surface:
        - Upstream slope: y = x / m_u  (for x < m_u·H_u)
        - Crest: y = H_u  (for m_u·H_u ≤ x ≤ m_u·H_u + W)
        - Downstream slope: y = (L - x) / m_d  (for x > m_u·H_u + W)

    Parameters
    ----------
    x_values : NDArray[np.float64]
        Horizontal coordinates [m].
    H_u : float
        Dam height [m].
    W : float
        Crest width [m].
    m_u : float
        Upstream slope ratio (H:V).
    m_d : float
        Downstream slope ratio (H:V).

    Returns
    -------
    NDArray[np.float64]
        Dam surface elevation at each x [m].
    """
    L = compute_base_width(W, m_u, m_d, H_u)
    x_crest_start = m_u * H_u
    x_crest_end = m_u * H_u + W

    y_surface = np.zeros_like(x_values)

    # Upstream slope region
    mask_upstream = x_values < x_crest_start
    y_surface[mask_upstream] = x_values[mask_upstream] / m_u

    # Crest region
    mask_crest = (x_values >= x_crest_start) & (x_values <= x_crest_end)
    y_surface[mask_crest] = H_u

    # Downstream slope region
    mask_downstream = x_values > x_crest_end
    y_surface[mask_downstream] = (L - x_values[mask_downstream]) / m_d

    # Clamp to valid range
    y_surface = np.clip(y_surface, 0.0, H_u)

    return y_surface


def create_domain_mask(
    Nx: int,
    Ny: int,
    dx: float,
    dy: float,
    H_u: float,
    W: float,
    m_u: float,
    m_d: float,
) -> NDArray[np.bool_]:
    """
    Create a boolean mask indicating which grid nodes lie inside the dam body.

    Nodes inside the dam (below dam surface) are True; nodes outside are False.

    Parameters
    ----------
    Nx, Ny : int
        Grid dimensions.
    dx, dy : float
        Grid spacing [m].
    H_u : float
        Dam height [m].
    W : float
        Crest width [m].
    m_u, m_d : float
        Upstream and downstream slope ratios (H:V).

    Returns
    -------
    NDArray[np.bool_]
        Boolean mask, shape (Ny, Nx). True = inside dam.
    """
    x_coords = np.arange(Nx) * dx
    y_surface = compute_dam_surface_elevation(x_coords, H_u, W, m_u, m_d)

    mask = np.zeros((Ny, Nx), dtype=bool)
    for i in range(Nx):
        for j in range(Ny):
            y_node = j * dy
            if y_node <= y_surface[i]:
                mask[j, i] = True

    return mask
