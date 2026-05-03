"""
Safety analytics: exit gradient, piping factor of safety, heave check.

These are the most safety-critical calculations in the simulator.
Any error here could produce misleading safety assessments.

Grid convention: h[j, i] where j=vertical (0=base), i=horizontal (0=upstream)
"""

import numpy as np
from numpy.typing import NDArray

from engine.constants import (
    CRITICAL_GRADIENT,
    FS_HIGH_THRESHOLD,
    FS_LOW_THRESHOLD,
    FS_MODERATE_THRESHOLD,
    POROSITY_DEFAULT,
)
from engine.types import RiskLevel


def compute_exit_gradient(
    h: NDArray[np.float64],
    dx: float,
) -> float:
    """
    Compute the exit gradient at the downstream toe of the dam.

    The exit gradient is the hydraulic gradient where seepage exits the
    embankment. This is the primary indicator of piping failure risk.

    Formula:
        i_e = |∂h/∂x| at x=L
            = (h[:, -2] − h[:, -1]) / Δx
            averaged over the saturated zone at x = L

    Parameters
    ----------
    h : NDArray[np.float64]
        Solved head field, shape (Ny, Nx) [m].
    dx : float
        Horizontal grid spacing [m].

    Returns
    -------
    float
        Exit gradient i_e [dimensionless].
    """
    # Gradient at downstream face (last two columns)
    gradient = (h[:, -2] - h[:, -1]) / dx

    # Average over all rows (saturated zone)
    # Use only positive gradients (flow towards downstream)
    positive_gradients = gradient[gradient > 0]
    if len(positive_gradients) == 0:
        return 0.0

    return float(np.mean(positive_gradients))


def compute_piping_fs(
    exit_gradient: float,
    i_cr: float = CRITICAL_GRADIENT,
) -> float:
    """
    Compute the Factor of Safety against piping.

    Formula:
        FS_piping = i_cr / i_e

    where:
        i_cr = Terzaghi's critical gradient ≈ 1.03 for typical soils
        i_e  = exit gradient at downstream toe

    Parameters
    ----------
    exit_gradient : float
        Exit gradient i_e [dimensionless].
    i_cr : float
        Critical hydraulic gradient [dimensionless].

    Returns
    -------
    float
        Factor of safety against piping. Returns infinity if i_e = 0.
    """
    if exit_gradient <= 0:
        return float("inf")
    return i_cr / exit_gradient


def classify_piping_risk(
    exit_gradient: float,
    i_cr: float = CRITICAL_GRADIENT,
) -> RiskLevel:
    """
    Classify piping risk based on the Factor of Safety.

    Risk classification table:
        FS ≥ 4.0       → LOW       (Green)   No action required
        2.0 ≤ FS < 4.0 → MODERATE  (Yellow)  Monitor; inspect annually
        1.5 ≤ FS < 2.0 → HIGH      (Orange)  Engineer review required
        FS < 1.5        → CRITICAL  (Red)     Immediate intervention

    Parameters
    ----------
    exit_gradient : float
        Exit gradient i_e [dimensionless].
    i_cr : float
        Critical hydraulic gradient [dimensionless].

    Returns
    -------
    RiskLevel
        Piping risk classification.
    """
    fs = compute_piping_fs(exit_gradient, i_cr)

    if fs >= FS_LOW_THRESHOLD:
        return RiskLevel.LOW
    elif fs >= FS_MODERATE_THRESHOLD:
        return RiskLevel.MODERATE
    elif fs >= FS_HIGH_THRESHOLD:
        return RiskLevel.HIGH
    else:
        return RiskLevel.CRITICAL


def compute_heave_fs(
    h: NDArray[np.float64],
    dy: float,
    i_cr: float = CRITICAL_GRADIENT,
) -> float:
    """
    Compute the Factor of Safety against heave at the upstream face.

    Heave occurs when the upward seepage force exceeds the submerged
    weight of the soil at the upstream face.

    Formula:
        i_upstream = |∂h/∂y| at y=0, x=0
        FS_heave = i_cr / i_upstream

    Parameters
    ----------
    h : NDArray[np.float64]
        Solved head field, shape (Ny, Nx) [m].
    dy : float
        Vertical grid spacing [m].
    i_cr : float
        Critical hydraulic gradient [dimensionless].

    Returns
    -------
    float
        Factor of safety against heave.
    """
    # Vertical gradient at the base, upstream face
    i_upstream = abs(h[1, 0] - h[0, 0]) / dy
    if i_upstream <= 0:
        return float("inf")
    return i_cr / i_upstream


def compute_seepage_velocity(
    k: float,
    exit_gradient: float,
    porosity: float = POROSITY_DEFAULT,
) -> float:
    """
    Compute the seepage velocity at the exit point.

    The seepage velocity accounts for the actual pore velocity,
    which is higher than the Darcy velocity by a factor of 1/n.

    Formula:
        v_s = k · i_e / n

    Parameters
    ----------
    k : float
        Hydraulic conductivity [m/s].
    exit_gradient : float
        Exit gradient i_e [dimensionless].
    porosity : float
        Soil porosity n [dimensionless].

    Returns
    -------
    float
        Seepage velocity [m/s].
    """
    return k * exit_gradient / porosity


def get_risk_color(risk: RiskLevel) -> str:
    """
    Get the UI display color for a risk level.

    Parameters
    ----------
    risk : RiskLevel
        Risk classification.

    Returns
    -------
    str
        Hex color code.
    """
    colors = {
        RiskLevel.LOW: "#22c55e",       # Green
        RiskLevel.MODERATE: "#eab308",   # Yellow
        RiskLevel.HIGH: "#f97316",       # Orange
        RiskLevel.CRITICAL: "#ef4444",   # Red
    }
    return colors.get(risk, "#9ca3af")


def get_risk_description(risk: RiskLevel) -> str:
    """
    Get a human-readable description and recommended action for a risk level.

    Parameters
    ----------
    risk : RiskLevel
        Risk classification.

    Returns
    -------
    str
        Description string with recommended action.
    """
    descriptions = {
        RiskLevel.LOW: "No action required. Dam is operating within safe limits.",
        RiskLevel.MODERATE: (
            "Monitor condition. Recommend annual inspection of downstream "
            "toe area for signs of seepage or erosion."
        ),
        RiskLevel.HIGH: (
            "Engineer review required. Exit gradient approaching critical "
            "levels. Consider installing filter toe drain or relief wells."
        ),
        RiskLevel.CRITICAL: (
            "⚠️ IMMEDIATE INTERVENTION REQUIRED. Exit gradient near or above "
            "Terzaghi's critical gradient. Risk of piping failure. "
            "Recommended remediation: filter toe drain, relief wells, "
            "upstream impervious blanket."
        ),
    }
    return descriptions.get(risk, "Unknown risk level.")
