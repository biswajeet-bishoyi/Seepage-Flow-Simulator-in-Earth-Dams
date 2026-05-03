"""
Physical constants and solver configuration for the Seepage Flow Simulator.

All physical constants are documented with their units and sources.
Derived constants are computed from fundamentals to avoid magic numbers.
"""

# =============================================================================
# Physical Constants
# =============================================================================

SPECIFIC_GRAVITY: float = 2.65
"""G_s — Specific gravity of soil solids [dimensionless]. Typical for quartz sand."""

VOID_RATIO_DEFAULT: float = 0.60
"""e — Default void ratio [dimensionless]. Typical for medium-dense sand."""

POROSITY_DEFAULT: float = 0.35
"""n — Default porosity [dimensionless]. Typical for granular soils."""

GRAVITY: float = 9.81
"""g — Gravitational acceleration [m/s²]."""

WATER_DENSITY: float = 1000.0
"""ρ_w — Density of water [kg/m³] at standard conditions."""

# =============================================================================
# Derived Constants
# =============================================================================

CRITICAL_GRADIENT: float = (SPECIFIC_GRAVITY - 1.0) / (1.0 + VOID_RATIO_DEFAULT)
"""
i_cr — Terzaghi's critical hydraulic gradient [dimensionless].

    i_cr = (G_s - 1) / (1 + e)
         = (2.65 - 1) / (1 + 0.60)
         = 1.03125

Above this gradient, piping (internal erosion) initiates.
"""

# =============================================================================
# Solver Configuration Defaults
# =============================================================================

SOR_OMEGA: float = 1.6
"""
ω — Successive Over-Relaxation factor [dimensionless].

    ω = 1.0 → standard Gauss-Seidel
    1.0 < ω < 2.0 → SOR (accelerated convergence)

Recommended range for earth dam geometries: 1.5–1.8.
"""

CONVERGENCE_TOL: float = 1e-5
"""ε — Solver convergence tolerance [m]. max|h_new - h_old| < ε."""

MAX_ITERATIONS: int = 10_000
"""Maximum number of solver iterations before early termination."""

SPARSE_SOLVER_THRESHOLD: int = 0
"""
Nx × Ny threshold above which the sparse direct solver (spsolve) is preferred
over iterative SOR. Set to 0 to always use the sparse solver as pure Python SOR is too slow.
"""

# =============================================================================
# Risk Classification Thresholds (Factor of Safety against Piping)
# =============================================================================

FS_LOW_THRESHOLD: float = 4.0
"""FS ≥ 4.0 → LOW risk. No action required."""

FS_MODERATE_THRESHOLD: float = 2.0
"""2.0 ≤ FS < 4.0 → MODERATE risk. Monitor; inspect annually."""

FS_HIGH_THRESHOLD: float = 1.5
"""1.5 ≤ FS < 2.0 → HIGH risk. Engineer review required."""

# FS < 1.5 → CRITICAL risk. Immediate intervention.

# =============================================================================
# Seepage Discharge Qualitative Thresholds
# =============================================================================

Q_LOW_THRESHOLD: float = 1e-6
"""q < 1e-6 m²/s → Low seepage."""

Q_MODERATE_THRESHOLD: float = 1e-5
"""1e-6 ≤ q < 1e-5 m²/s → Moderate seepage."""

Q_HIGH_THRESHOLD: float = 1e-4
"""1e-5 ≤ q < 1e-4 m²/s → High seepage."""

# q ≥ 1e-4 → Critical seepage.
