"""
Shared colormap definitions and normalization utilities for visualization.

Provides consistent color mapping across all plot types.
"""

import numpy as np
from numpy.typing import NDArray

# =============================================================================
# Colormap Definitions
# =============================================================================

# Head field colormap: Blue (high head) → Red (low head), diverging
HEAD_COLORSCALE = [
    [0.0, "rgb(5, 48, 97)"],       # Deep blue — high head
    [0.1, "rgb(33, 102, 172)"],
    [0.2, "rgb(67, 147, 195)"],
    [0.3, "rgb(146, 197, 222)"],
    [0.4, "rgb(209, 229, 240)"],
    [0.5, "rgb(247, 247, 247)"],    # White — midpoint
    [0.6, "rgb(253, 219, 199)"],
    [0.7, "rgb(244, 165, 130)"],
    [0.8, "rgb(214, 96, 77)"],
    [0.9, "rgb(178, 24, 43)"],
    [1.0, "rgb(103, 0, 31)"],       # Deep red — low head
]

# Velocity magnitude colormap: Viridis (standard, perceptually uniform)
VELOCITY_COLORSCALE = "Viridis"

# Colorblind-safe alternative: Cividis
VELOCITY_COLORSCALE_SAFE = "Cividis"

# Risk level colors
RISK_COLORS = {
    "LOW": "#22c55e",
    "MODERATE": "#eab308",
    "HIGH": "#f97316",
    "CRITICAL": "#ef4444",
}

# Gauge zone colors (for exit gradient gauge)
GAUGE_ZONES = [
    {"range": [0.0, 0.25], "color": "#22c55e"},    # Green — safe
    {"range": [0.25, 0.50], "color": "#eab308"},    # Yellow — moderate
    {"range": [0.50, 0.70], "color": "#f97316"},    # Orange — high
    {"range": [0.70, 1.0], "color": "#ef4444"},      # Red — critical
]

# Dam body color
DAM_FILL_COLOR = "rgba(139, 119, 101, 0.3)"    # Light brown, semi-transparent
DAM_LINE_COLOR = "rgba(101, 67, 33, 0.8)"       # Dark brown


def normalize_field(
    field: NDArray[np.float64],
    vmin: float | None = None,
    vmax: float | None = None,
) -> NDArray[np.float64]:
    """
    Normalize a 2D field to [0, 1] for colormap mapping.

    Parameters
    ----------
    field : NDArray[np.float64]
        Input field, shape (Ny, Nx).
    vmin : float or None
        Minimum value for normalization. If None, uses field minimum.
    vmax : float or None
        Maximum value for normalization. If None, uses field maximum.

    Returns
    -------
    NDArray[np.float64]
        Normalized field in [0, 1].
    """
    if vmin is None:
        vmin = float(np.nanmin(field))
    if vmax is None:
        vmax = float(np.nanmax(field))

    if vmax - vmin < 1e-12:
        return np.zeros_like(field)

    return (field - vmin) / (vmax - vmin)


def format_scientific(value: float, precision: int = 2) -> str:
    """
    Format a number in scientific notation with Unicode superscripts.

    Example: 3.42e-6 → "3.42 × 10⁻⁶"

    Parameters
    ----------
    value : float
        Number to format.
    precision : int
        Number of decimal places.

    Returns
    -------
    str
        Formatted string.
    """
    if value == 0:
        return "0.00"

    exp = int(np.floor(np.log10(abs(value))))
    mantissa = value / (10**exp)

    # Unicode superscript digits
    superscript_map = {
        "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
        "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
        "-": "⁻",
    }

    exp_str = "".join(superscript_map.get(c, c) for c in str(exp))
    return f"{mantissa:.{precision}f} × 10{exp_str}"
