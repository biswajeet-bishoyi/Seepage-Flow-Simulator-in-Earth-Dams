"""
Darcy flow calculations: seepage discharge, velocity fields, and stream function.

All functions operate on the solved head field from the Laplace solver.
No visualization code; pure numerical computations.

Grid convention: h[j, i] where j=vertical (0=base), i=horizontal (0=upstream)
"""

import numpy as np
from numpy.typing import NDArray

from engine.constants import Q_HIGH_THRESHOLD, Q_LOW_THRESHOLD, Q_MODERATE_THRESHOLD
from engine.types import SeepageRating


def compute_seepage_discharge(
    k: float,
    H_u: float,
    H_d: float,
    L: float,
) -> float:
    """
    Compute seepage discharge per unit width via Dupuit–Forchheimer.

    Uses the formula:
        q = k * (H_u² − H_d²) / (2 * L)

    Parameters
    ----------
    k : float
        Hydraulic conductivity [m/s]. Must be > 0.
    H_u : float
        Upstream hydraulic head [m]. Must be > H_d.
    H_d : float
        Downstream hydraulic head [m]. Must be >= 0.
    L : float
        Effective seepage path length (dam base width) [m]. Must be > 0.

    Returns
    -------
    float
        Seepage discharge per unit width q [m²/s].

    Raises
    ------
    ValueError
        If H_u <= H_d, k <= 0, or L <= 0.
    """
    if k <= 0:
        raise ValueError(f"k must be positive, got {k}")
    if L <= 0:
        raise ValueError(f"L must be positive, got {L}")
    if H_u < H_d:
        raise ValueError(f"H_u ({H_u}) must be >= H_d ({H_d})")
    if H_u == H_d:
        return 0.0
    return k * (H_u**2 - H_d**2) / (2.0 * L)


def compute_velocity_field(
    h: NDArray[np.float64],
    k: float,
    dx: float,
    dy: float,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """
    Compute Darcy velocity components from the solved head field.

    Darcy's Law:
        v_x = −k · ∂h/∂x    (horizontal velocity)
        v_y = −k · ∂h/∂y    (vertical velocity)

    Central differences are used for the gradient computation.

    Parameters
    ----------
    h : NDArray[np.float64]
        Solved head field, shape (Ny, Nx) [m].
    k : float
        Hydraulic conductivity [m/s].
    dx : float
        Horizontal grid spacing [m].
    dy : float
        Vertical grid spacing [m].

    Returns
    -------
    tuple[NDArray, NDArray]
        (v_x, v_y) Darcy velocity components [m/s], each shape (Ny, Nx).
    """
    v_x = -k * np.gradient(h, dx, axis=1)
    v_y = -k * np.gradient(h, dy, axis=0)
    return v_x, v_y


def integrate_discharge(
    h: NDArray[np.float64],
    k: float,
    dx: float,
    dy: float,
) -> float:
    """
    Numerically integrate Darcy velocity across a vertical section to get discharge.

    Integrates v_x at the midpoint of the domain (x = L/2) over the full height:
        q = ∫ v_x dy  ≈  Σ v_x[j, i_mid] · dy

    This provides a numerical check against the analytical Dupuit formula.

    Parameters
    ----------
    h : NDArray[np.float64]
        Solved head field, shape (Ny, Nx) [m].
    k : float
        Hydraulic conductivity [m/s].
    dx : float
        Horizontal grid spacing [m].
    dy : float
        Vertical grid spacing [m].

    Returns
    -------
    float
        Numerically integrated discharge per unit width [m²/s].
    """
    v_x, _ = compute_velocity_field(h, k, dx, dy)
    Ny, Nx = h.shape
    i_mid = Nx // 2

    # Integrate v_x across the vertical section at x = L/2
    q = np.sum(v_x[:, i_mid]) * dy
    return abs(q)


def compute_stream_function(
    v_x: NDArray[np.float64],
    v_y: NDArray[np.float64],
    dy: float,
) -> NDArray[np.float64]:
    """
    Compute the stream function ψ by integrating Darcy velocities.

    The stream function satisfies:
        ∂ψ/∂y = v_x    and    ∂ψ/∂x = −v_y

    Integration is performed upward from the base (j=0):
        ψ[j, i] = ψ[j−1, i] + v_x[j, i] · Δy

    Streamlines are iso-contours of ψ.

    Parameters
    ----------
    v_x : NDArray[np.float64]
        Horizontal Darcy velocity, shape (Ny, Nx) [m/s].
    v_y : NDArray[np.float64]
        Vertical Darcy velocity, shape (Ny, Nx) [m/s].
    dy : float
        Vertical grid spacing [m].

    Returns
    -------
    NDArray[np.float64]
        Stream function ψ, shape (Ny, Nx).
    """
    Ny, Nx = v_x.shape
    psi = np.zeros((Ny, Nx), dtype=np.float64)

    # Integrate upward from base
    for j in range(1, Ny):
        psi[j, :] = psi[j - 1, :] + v_x[j, :] * dy

    return psi


def classify_seepage_rating(q: float) -> SeepageRating:
    """
    Classify seepage discharge qualitatively.

    Parameters
    ----------
    q : float
        Seepage discharge [m²/s].

    Returns
    -------
    SeepageRating
        LOW, MODERATE, HIGH, or CRITICAL.
    """
    q_abs = abs(q)
    if q_abs < Q_LOW_THRESHOLD:
        return SeepageRating.LOW
    elif q_abs < Q_MODERATE_THRESHOLD:
        return SeepageRating.MODERATE
    elif q_abs < Q_HIGH_THRESHOLD:
        return SeepageRating.HIGH
    else:
        return SeepageRating.CRITICAL
