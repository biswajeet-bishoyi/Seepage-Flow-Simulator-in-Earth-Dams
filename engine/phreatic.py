"""
Casagrande's parabolic approximation for the phreatic line in earth dams.

The phreatic line (free surface / line of seepage) defines the upper boundary
of the saturated zone within the dam body. It is computed using Casagrande's
classical parabolic method.

Reference: Casagrande, A. (1937). Seepage Through Dams.
           Journal of the New England Water Works Association, 51(2).

Grid convention: h[j, i] where j=vertical (0=base), i=horizontal (0=upstream)
"""

import numpy as np
from numpy.typing import NDArray


def compute_focus_parameter(
    H_u: float,
    d: float,
) -> float:
    """
    Compute the base parabola parameter a₀ (Casagrande's method).

    Step 1 — Focus point parameter:
        a₀ = √(d² + H_u²) − d

    where:
        H_u = upstream water level [m]
        d   = horizontal distance from upstream toe to water entry point [m]
            Typically d ≈ 0.3 × upstream slope length

    Parameters
    ----------
    H_u : float
        Upstream water level above datum [m].
    d : float
        Horizontal distance from upstream toe to water surface entry [m].

    Returns
    -------
    float
        Parabola parameter a₀ [m].
    """
    return np.sqrt(d**2 + H_u**2) - d


def casagrande_phreatic_line(
    H_u: float,
    L: float,
    d: float,
    x_values: NDArray[np.float64],
) -> NDArray[np.float64]:
    """
    Compute the phreatic line using Casagrande's parabolic approximation.

    The parabola is constructed with its focus at the downstream toe.

    Step 1 — Base parabola parameter:
        a₀ = √(d² + H_u²) − d

    Step 2 — Phreatic surface elevation at horizontal position x:
        y(x) = √(a₀² + 2·a₀·x)

    where:
        H_u  = upstream head [m]
        d    = horizontal distance from upstream toe to water entry point [m]
        a₀   = the minimum ordinate of the base parabola [m]
        x    = horizontal coordinate measured from focus [m]

    Parameters
    ----------
    H_u : float
        Upstream water level above datum [m].
    L : float
        Base width of the dam [m].
    d : float
        Horizontal distance from upstream toe to water surface entry [m].
        Typically d = 0.3 × upstream slope length.
    x_values : NDArray[np.float64]
        Array of x-coordinates at which to evaluate y [m].
        Measured from the downstream toe (focus), going upstream.

    Returns
    -------
    NDArray[np.float64]
        Array of phreatic surface elevations y(x) [m].
    """
    a0 = compute_focus_parameter(H_u, d)

    # x_values are measured from the downstream toe (focus)
    # Ensure non-negative under the sqrt
    arg = a0**2 + 2.0 * a0 * x_values
    arg = np.maximum(arg, 0.0)

    y = np.sqrt(arg)
    return y


def compute_phreatic_line_for_dam(
    H_u: float,
    H_d: float,
    L: float,
    m_u: float,
    num_points: int = 100,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """
    Compute the phreatic line for the full dam cross-section.

    This is a convenience wrapper that:
    1. Computes d from the upstream slope geometry
    2. Creates x-coordinates spanning the dam base
    3. Evaluates the Casagrande parabola
    4. Clips results to valid range

    Parameters
    ----------
    H_u : float
        Upstream water level [m].
    H_d : float
        Downstream water level [m].
    L : float
        Dam base width [m].
    m_u : float
        Upstream slope ratio (H:V).
    num_points : int
        Number of evaluation points along the dam base.

    Returns
    -------
    tuple[NDArray, NDArray]
        (x_coords, y_coords) of the phreatic line [m].
        x_coords are in the dam coordinate system (0 = upstream toe).
    """
    # d = 0.3 × upstream slope length (Casagrande's correction)
    upstream_slope_length = np.sqrt(H_u**2 + (m_u * H_u) ** 2)
    d = 0.3 * upstream_slope_length

    # x measured from downstream toe (focus), going upstream
    # In dam coordinates: x_dam = L - x_focus
    x_focus = np.linspace(0.0, L, num_points)

    y = casagrande_phreatic_line(H_u, L, d, x_focus)

    # Convert to dam coordinate system (x=0 at upstream toe)
    x_dam = L - x_focus[::-1]
    y_dam = y[::-1]

    # Clip: phreatic line cannot exceed dam height or go below downstream head
    y_dam = np.clip(y_dam, H_d, H_u)

    return x_dam, y_dam


def phreatic_to_grid_indices(
    phreatic_y: NDArray[np.float64],
    phreatic_x: NDArray[np.float64],
    Nx: int,
    Ny: int,
    L: float,
    H_dam: float,
) -> NDArray[np.int_]:
    """
    Convert phreatic line y-values to grid row indices for domain masking.

    For each column i in the grid, finds the row index j corresponding to
    the phreatic surface elevation. Nodes above this index (j > phreatic_j[i])
    are outside the saturated zone.

    Parameters
    ----------
    phreatic_y : NDArray[np.float64]
        Phreatic surface elevations [m].
    phreatic_x : NDArray[np.float64]
        Corresponding x-coordinates [m].
    Nx, Ny : int
        Grid dimensions.
    L : float
        Dam base width [m].
    H_dam : float
        Dam height [m].

    Returns
    -------
    NDArray[np.int_]
        Row indices of phreatic line, shape (Nx,).
    """
    dx = L / (Nx - 1)
    dy = H_dam / (Ny - 1)

    x_grid = np.arange(Nx) * dx
    # Interpolate phreatic y onto grid x-coordinates
    y_interp = np.interp(x_grid, phreatic_x, phreatic_y)

    # Convert y to row index
    j_indices = np.round(y_interp / dy).astype(np.int_)
    j_indices = np.clip(j_indices, 0, Ny - 1)

    return j_indices


def phreatic_line_table(
    phreatic_x: NDArray[np.float64],
    phreatic_y: NDArray[np.float64],
    num_stations: int = 10,
) -> list[tuple[float, float]]:
    """
    Generate a data table of phreatic line coordinates at evenly spaced stations.

    Parameters
    ----------
    phreatic_x : NDArray[np.float64]
        X-coordinates of the phreatic line [m].
    phreatic_y : NDArray[np.float64]
        Y-coordinates of the phreatic line [m].
    num_stations : int
        Number of stations to sample (default: 10).

    Returns
    -------
    list[tuple[float, float]]
        List of (x, y) coordinate pairs at sampled stations.
    """
    indices = np.linspace(0, len(phreatic_x) - 1, num_stations, dtype=int)
    return [(float(phreatic_x[i]), float(phreatic_y[i])) for i in indices]
