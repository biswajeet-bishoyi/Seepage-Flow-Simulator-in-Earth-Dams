# CLAUDE.md — Seepage Flow Simulator: Developer Guide
**Maintainer Reference | Architecture, Standards & Scaling Handbook**
Version: 1.0 | Audience: Contributing Engineers

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Project Structure](#2-project-structure)
3. [Build Commands & Environment Setup](#3-build-commands--environment-setup)
4. [Code Style Guidelines](#4-code-style-guidelines)
5. [Engineering Logic Standards](#5-engineering-logic-standards)
6. [Boundary Condition Specification](#6-boundary-condition-specification)
7. [Testing Strategy](#7-testing-strategy)
8. [Scaling Guide](#8-scaling-guide)
9. [Deployment](#9-deployment)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Project Overview

This project implements a **2D steady-state seepage simulator** for earth dams using the Finite Difference Method. The codebase is divided into three packages with strict separation of concerns:

- `/engine` — Pure numerical logic. No I/O, no plotting, no framework dependencies.
- `/viz` — All rendering code. Consumes engine outputs only; no physics.
- `/ui` — All user interface code. Calls engine via API or WebWorker; never contains equations.

**The Iron Rule:** A change to dam physics must never require a change in `/viz` or `/ui`. A UI redesign must never require a change in `/engine`.

---

## 2. Project Structure

```
seepage-simulator/
│
├── engine/                          # Numerical solver and hydraulic calculations
│   ├── __init__.py
│   ├── laplace_solver.py            # FDM grid setup + Gauss-Seidel / SOR solver
│   ├── darcy.py                     # Seepage discharge, velocity field, gradients
│   ├── phreatic.py                  # Casagrande parabolic phreatic line
│   ├── safety.py                    # Exit gradient, piping FS, heave check
│   ├── geometry.py                  # Dam cross-section geometry helpers
│   └── types.py                     # Pydantic models / dataclasses for all I/O
│
├── viz/                             # Visualization and animation scripts
│   ├── __init__.py
│   ├── flow_net.py                  # Equipotential + streamline plotting (Plotly)
│   ├── animation.py                 # Particle tracer and animated streamline logic
│   ├── colormap.py                  # Shared colormap definitions and normalization
│   └── safety_gauges.py            # Exit gradient gauge, FS display widgets
│
├── ui/                              # User interface layer
│   ├── app.py                       # Streamlit app entry point (prototype track)
│   ├── components/                  # React components (production track)
│   │   ├── InputPanel.tsx
│   │   ├── VisualizationCanvas.tsx
│   │   ├── SafetyDashboard.tsx
│   │   └── ResultsBar.tsx
│   ├── api/                         # FastAPI server (Track A)
│   │   ├── main.py
│   │   └── routes/
│   │       └── solve.py
│   └── state/
│       └── store.ts                 # Zustand state management
│
├── tests/
│   ├── test_laplace_solver.py       # Solver correctness + convergence tests
│   ├── test_darcy.py                # Discharge formula verification
│   ├── test_phreatic.py             # Casagrande solution validation
│   ├── test_safety.py               # Exit gradient and FS tests
│   └── fixtures/
│       └── analytical_cases.py      # Known closed-form benchmark cases
│
├── docs/
│   ├── PRD.md
│   ├── CLAUDE.md                    # This file
│   └── math_derivations.pdf         # Full LaTeX derivations
│
├── requirements.txt                 # Python dependencies
├── requirements-dev.txt             # Dev/test dependencies
├── package.json                     # JS dependencies (React track)
└── README.md
```

---

## 3. Build Commands & Environment Setup

### 3.1 Python Environment (Engine + API + Streamlit)

```bash
# 1. Create isolated environment
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
.\.venv\Scripts\activate           # Windows

# 2. Install core runtime dependencies
pip install numpy scipy fastapi uvicorn pydantic matplotlib plotly streamlit

# Or from requirements file:
pip install -r requirements.txt

# 3. Install development and testing dependencies
pip install -r requirements-dev.txt
# Includes: pytest pytest-cov black isort mypy ruff

# 4. Run the Streamlit prototype
streamlit run ui/app.py

# 5. Run the FastAPI server (production engine API)
uvicorn ui.api.main:app --host 0.0.0.0 --port 8000 --reload

# 6. Verify the engine independently
python -c "from engine.laplace_solver import Laplacesolver; print('Engine OK')"
```

### 3.2 JavaScript / React Frontend (Production Track)

```bash
# Install Node dependencies
npm install

# Run development server (Vite)
npm run dev

# Type-check TypeScript
npm run typecheck

# Build for production
npm run build

# Preview production build locally
npm run preview
```

### 3.3 Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage report
pytest tests/ --cov=engine --cov-report=html

# Specific module
pytest tests/test_laplace_solver.py -v

# Run only fast unit tests (exclude convergence benchmarks)
pytest tests/ -v -m "not slow"
```

### 3.4 Code Quality Checks (run before every commit)

```bash
# Format
black engine/ viz/ ui/ tests/
isort engine/ viz/ ui/ tests/

# Lint
ruff check engine/ viz/ ui/

# Type-check
mypy engine/ --strict

# All-in-one pre-commit
pre-commit run --all-files
```

---

## 4. Code Style Guidelines

### 4.1 Type Hinting — Mandatory for All Engineering Functions

Every public function in `/engine` and `/viz` must have complete type annotations. No exceptions.

```python
# ✅ CORRECT — full type hints, clear docstring
import numpy as np
from numpy.typing import NDArray

def compute_seepage_discharge(
    k: float,
    H_u: float,
    H_d: float,
    L: float
) -> float:
    """
    Compute seepage discharge per unit width via Dupuit–Forchheimer.

    Uses the formula:
        q = k * (H_u^2 - H_d^2) / (2 * L)

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
    if H_u <= H_d:
        raise ValueError(f"H_u ({H_u}) must be greater than H_d ({H_d})")
    if k <= 0:
        raise ValueError(f"k must be positive, got {k}")
    if L <= 0:
        raise ValueError(f"L must be positive, got {L}")
    return k * (H_u**2 - H_d**2) / (2.0 * L)


# ❌ WRONG — no type hints, no docstring, magic numbers
def q(k, Hu, Hd, L):
    return k * (Hu**2 - Hd**2) / (2 * L)
```

### 4.2 NumPy Array Type Annotations

Use `NDArray` from `numpy.typing` for all array arguments and returns:

```python
from numpy.typing import NDArray
import numpy as np

def solve_head_field(
    h_init: NDArray[np.float64],
    boundary_mask: NDArray[np.bool_],
    omega: float = 1.6,
    tol: float = 1e-5,
    max_iter: int = 10_000,
) -> tuple[NDArray[np.float64], int, float]:
    """
    Returns: (h_solved, iterations_taken, final_residual)
    """
    ...
```

### 4.3 Strict Engine/View Separation

The `/engine` package must remain **framework-free**:

```python
# ✅ engine/darcy.py — pure NumPy, no Plotly/Streamlit/React
import numpy as np
from numpy.typing import NDArray

def compute_velocity_field(
    h: NDArray[np.float64],
    k: float,
    dx: float,
    dy: float
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Returns (v_x, v_y) Darcy velocity components."""
    v_x = -k * np.gradient(h, dx, axis=1)
    v_y = -k * np.gradient(h, dy, axis=0)
    return v_x, v_y
```

```python
# ✅ viz/flow_net.py — imports from engine, outputs Plotly figure objects only
import plotly.graph_objects as go
from engine.darcy import compute_velocity_field

def plot_flow_net(h: NDArray, k: float, dx: float, dy: float) -> go.Figure:
    v_x, v_y = compute_velocity_field(h, k, dx, dy)
    fig = go.Figure()
    fig.add_trace(go.Contour(z=h, ...))
    return fig
```

```python
# ❌ FORBIDDEN — engine code importing from viz or ui
# engine/laplace_solver.py
import plotly  # FORBIDDEN
import streamlit  # FORBIDDEN
```

### 4.4 Constants and Configuration

All physical constants go in `engine/constants.py`:

```python
# engine/constants.py
SPECIFIC_GRAVITY: float = 2.65        # G_s, dimensionless
VOID_RATIO_DEFAULT: float = 0.60      # e, dimensionless
POROSITY_DEFAULT: float = 0.35        # n, dimensionless
GRAVITY: float = 9.81                 # g [m/s²]
WATER_DENSITY: float = 1000.0         # rho_w [kg/m³]

# Derived
CRITICAL_GRADIENT: float = (SPECIFIC_GRAVITY - 1.0) / (1.0 + VOID_RATIO_DEFAULT)
# i_cr = (2.65 - 1) / (1 + 0.60) = 1.03125
```

### 4.5 Naming Conventions

| Item | Convention | Example |
|---|---|---|
| Hydraulic variables | Snake_case with unit suffix comment | `h_u: float  # [m]` |
| Grid arrays | Lowercase with shape in docstring | `h_grid: NDArray` |
| Physical constants | SCREAMING_SNAKE_CASE | `CRITICAL_GRADIENT` |
| Pydantic models | PascalCase | `SolverInput`, `SolverOutput` |
| React components | PascalCase | `InputPanel`, `SafetyGauge` |
| Test functions | `test_<module>_<behavior>` | `test_darcy_zero_head_diff` |

---

## 5. Engineering Logic Standards

### 5.1 LaTeX Equations in Docstrings

All functions implementing a physical equation must document that equation in LaTeX within the docstring. Use the `math` block convention:

```python
def casagrande_phreatic_line(
    H_u: float,
    L: float,
    d: float,
    x_values: NDArray[np.float64]
) -> NDArray[np.float64]:
    """
    Compute the phreatic line using Casagrande's parabolic approximation.

    The parabola is constructed with its focus at the downstream toe.

    Step 1 — Base parabola parameter:
        a_0 = sqrt(d^2 + H_u^2) - d

    Step 2 — Phreatic surface elevation at horizontal position x:
        y(x) = sqrt(a_0^2 + 2 * a_0 * x)

    where:
        H_u  = upstream head [m]
        d    = horizontal distance from upstream toe to water entry point [m]
        a_0  = the minimum ordinate of the base parabola [m]
        x    = horizontal coordinate measured from focus [m]

    Reference: Casagrande, A. (1937). Seepage Through Dams.
               Journal of the New England Water Works Association, 51(2).

    Parameters
    ----------
    H_u : float
        Upstream water level above datum [m].
    L : float
        Base width of the dam [m].
    d : float
        Horizontal distance from upstream toe to water surface entry [m].
        Typically d = 0.3 * upstream slope length.
    x_values : NDArray[np.float64]
        Array of x-coordinates at which to evaluate y [m].

    Returns
    -------
    NDArray[np.float64]
        Array of phreatic surface elevations y(x) [m].
    """
    a0 = np.sqrt(d**2 + H_u**2) - d
    return np.sqrt(a0**2 + 2.0 * a0 * x_values)
```

### 5.2 Solver Convergence Logging

The solver must log convergence diagnostics without using `print()`. Use the `logging` module:

```python
import logging

logger = logging.getLogger(__name__)

def gauss_seidel_sor(h: NDArray, ...) -> tuple[NDArray, int, float]:
    for iteration in range(max_iter):
        ...
        residual = np.max(np.abs(h_new - h))
        if iteration % 100 == 0:
            logger.debug("Iter %d | Residual: %.2e", iteration, residual)
        if residual < tol:
            logger.info("Converged at iteration %d | Residual: %.2e", iteration, residual)
            return h, iteration, residual
    logger.warning("Max iterations (%d) reached. Residual: %.2e", max_iter, residual)
    return h, max_iter, residual
```

### 5.3 Grid Index Convention

**Canonical index convention (mandatory across all modules):**

```
h[j, i]  where:
    j = row index     (0 = base/bottom,  Ny-1 = top/crest)
    i = column index  (0 = upstream,     Nx-1 = downstream)

Physical coordinates:
    x = i * dx    [m, horizontal, left=upstream]
    y = j * dy    [m, vertical,   bottom=base]
```

This convention must never be violated. Document it at the top of every module that defines or accesses `h`:

```python
# Grid convention: h[j, i] where j=vertical (0=base), i=horizontal (0=upstream)
```

### 5.4 Sparse Matrix Direct Solver (Alternative to SOR)

For grids larger than 200×100, prefer `scipy.sparse.linalg.spsolve`:

```python
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve

def build_and_solve_system(
    Nx: int,
    Ny: int,
    dx: float,
    dy: float,
    h_boundary: NDArray[np.float64],
    is_boundary: NDArray[np.bool_]
) -> NDArray[np.float64]:
    """
    Assemble and directly solve the FDM linear system A*h = b.

    The 5-point Laplacian stencil in matrix form:
        A * h_vec = b
    where h_vec is the flattened head array and b encodes boundary values.

    Complexity: O(N * log(N)) using sparse direct solver.

    Parameters
    ----------
    Nx, Ny : int
        Grid dimensions.
    dx, dy : float
        Grid spacing [m].
    h_boundary : NDArray
        Head values at boundary nodes (ignored at interior nodes).
    is_boundary : NDArray[bool]
        Boolean mask; True where Dirichlet BC applies.

    Returns
    -------
    NDArray[np.float64]
        Solved head field h[j, i], shape (Ny, Nx).
    """
    N = Nx * Ny
    A = lil_matrix((N, N))
    b = np.zeros(N)
    alpha2 = (dy / dx) ** 2

    for j in range(Ny):
        for i in range(Nx):
            idx = j * Nx + i
            if is_boundary[j, i]:
                A[idx, idx] = 1.0
                b[idx] = h_boundary[j, i]
            else:
                A[idx, idx] = -2.0 * (alpha2 + 1.0)
                if i > 0:
                    A[idx, idx - 1] = alpha2
                if i < Nx - 1:
                    A[idx, idx + 1] = alpha2
                if j > 0:
                    A[idx, idx - Nx] = 1.0
                if j < Ny - 1:
                    A[idx, idx + Nx] = 1.0

    h_vec = spsolve(A.tocsr(), b)
    return h_vec.reshape(Ny, Nx)
```

---

## 6. Boundary Condition Specification

Boundary conditions are the most safety-critical part of the code. Any BC error invalidates the entire solution silently.

### 6.1 Complete BC Map

```
Domain: x ∈ [0, L], y ∈ [0, H_dam]

                 y = H_dam (dam crest — no BC, interior nodes)
                 ┌──────────────────────────────────┐
    x = 0        │                                  │  x = L
    (upstream)   │      INTERIOR NODES              │  (downstream)
    Dirichlet:   │      h governed by               │  Dirichlet:
    h = H_u      │      ∇²h = 0 (Laplace)           │  h = H_d
                 │                                  │
                 └──────────────────────────────────┘
                 y = 0 (dam base)
                 Neumann: ∂h/∂y = 0
                 Implementation: h[0, i] = h[1, i]  ← mirror condition
```

### 6.2 Boundary Condition Implementation

```python
def apply_boundary_conditions(
    h: NDArray[np.float64],
    H_u: float,
    H_d: float,
    phreatic_j: NDArray[np.int_]
) -> NDArray[np.float64]:
    """
    Apply all boundary conditions to the head array in-place.

    Boundary types:
        DIRICHLET (upstream):    h[:, 0]  = H_u
            Prescribed head on upstream face. All nodes, full height.
        DIRICHLET (downstream):  h[:, -1] = H_d
            Prescribed head on downstream face. Saturated nodes only.
        NEUMANN (base, no-flow): h[0, :]  = h[1, :]
            Zero vertical gradient at impervious foundation.
            Forward difference: (h[1,i] - h[0,i]) / dy = 0 => h[0,i] = h[1,i]
        DIRICHLET (free surface): h[j, i] = y_j  for j > phreatic_j[i]
            Nodes above phreatic line set to local elevation (pressure head = 0).

    Parameters
    ----------
    h : NDArray[np.float64]
        Head array, shape (Ny, Nx). Modified in-place.
    H_u : float
        Upstream prescribed head [m].
    H_d : float
        Downstream prescribed head [m].
    phreatic_j : NDArray[np.int_]
        Row index of phreatic line at each column i, shape (Nx,).

    Returns
    -------
    NDArray[np.float64]
        Updated head array.
    """
    # Upstream face — Dirichlet
    h[:, 0] = H_u

    # Downstream face — Dirichlet (saturated zone only)
    h[:, -1] = H_d

    # Base — Neumann (no-flow, zero normal gradient)
    h[0, :] = h[1, :]

    # Free surface — Dirichlet (nodes above phreatic line)
    Ny, Nx = h.shape
    for i in range(Nx):
        for j in range(phreatic_j[i], Ny):
            y_elevation = j * (H_u / (Ny - 1))  # physical y-coordinate
            h[j, i] = y_elevation

    return h
```

### 6.3 Boundary Condition Verification Checklist

Before merging any changes to `laplace_solver.py` or `darcy.py`, verify:

- [ ] `h[:, 0]` equals H_u after every iteration
- [ ] `h[:, -1]` equals H_d after every iteration
- [ ] `h[0, :] == h[1, :]` (Neumann condition holds at base)
- [ ] No node above phreatic line has h > local elevation y
- [ ] Solver conserves mass: `sum(v_x[:, 0]) ≈ sum(v_x[:, -1])` (continuity check)

---

## 7. Testing Strategy

### 7.1 Test Philosophy

Every function in `/engine` must be testable in isolation with pure numeric inputs/outputs. No mocking of physics. Tests are organized by verification type:

| Layer | Test Type | Tools |
|---|---|---|
| Unit | Individual function correctness | pytest |
| Verification | Solver vs. known analytical solutions | pytest + numpy.testing |
| Regression | Output must not change after refactor | pytest + stored fixtures |
| Performance | Solve time benchmarks | pytest-benchmark |

### 7.2 Analytical Verification Cases

The primary solver correctness test compares FDM output against the closed-form Dupuit–Forchheimer discharge formula:

```python
# tests/test_laplace_solver.py
import numpy as np
import pytest
from engine.laplace_solver import solve_laplace
from engine.darcy import integrate_discharge

@pytest.mark.parametrize("H_u, H_d, k, L, expected_q", [
    # Case 1: Standard dam, moderate head
    (20.0, 0.0, 1e-5, 50.0, 1e-5 * (20.0**2) / (2 * 50.0)),
    # Case 2: High head, high conductivity
    (30.0, 5.0, 5e-5, 80.0, 5e-5 * (30.0**2 - 5.0**2) / (2 * 80.0)),
    # Case 3: Near-zero downstream head
    (10.0, 0.1, 1e-6, 30.0, 1e-6 * (10.0**2 - 0.1**2) / (2 * 30.0)),
])
def test_solver_discharge_vs_analytical(H_u, H_d, k, L, expected_q):
    """
    Verify FDM solver-derived discharge matches Dupuit-Forchheimer formula.

    Analytical formula:
        q = k * (H_u^2 - H_d^2) / (2 * L)

    Tolerance: 5% relative error (coarse grid) to 2% (fine grid).
    """
    h_solved = solve_laplace(H_u=H_u, H_d=H_d, L=L, Nx=200, Ny=80)
    q_numerical = integrate_discharge(h_solved, k=k, dx=L/199)
    relative_error = abs(q_numerical - expected_q) / expected_q
    assert relative_error < 0.05, (
        f"Discharge error {relative_error:.1%} exceeds 5% tolerance. "
        f"Expected {expected_q:.3e}, got {q_numerical:.3e}"
    )
```

### 7.3 Phreatic Line Verification

```python
# tests/test_phreatic.py
def test_casagrande_boundary_conditions():
    """Phreatic line must satisfy: y(0) ≈ H_u and y(L) ≈ 0."""
    H_u, L, d = 20.0, 50.0, 6.0
    x = np.linspace(0, L, 100)
    y = casagrande_phreatic_line(H_u=H_u, L=L, d=d, x_values=x)
    # At x=0 (focus region), y ≈ H_u (within 10%)
    assert abs(y[0] - H_u) / H_u < 0.10
    # Monotonically decreasing
    assert np.all(np.diff(y) <= 0), "Phreatic line must be monotonically decreasing"
    # Never negative
    assert np.all(y >= 0), "Phreatic line must not go below datum"
```

### 7.4 Safety Calculation Tests

```python
# tests/test_safety.py
def test_critical_exit_gradient_triggers_warning():
    """Exit gradient exceeding i_cr must produce CRITICAL risk classification."""
    from engine.safety import classify_piping_risk, CRITICAL_GRADIENT
    i_e = CRITICAL_GRADIENT * 0.9  # Just below critical = FS < 1.11
    risk = classify_piping_risk(exit_gradient=i_e)
    assert risk == "CRITICAL"

def test_safe_exit_gradient():
    """Low exit gradient must produce LOW risk classification."""
    from engine.safety import classify_piping_risk, CRITICAL_GRADIENT
    i_e = CRITICAL_GRADIENT / 5.0  # FS = 5.0
    risk = classify_piping_risk(exit_gradient=i_e)
    assert risk == "LOW"
```

### 7.5 Regression Test Pattern

After any solver change, run regression suite to ensure outputs have not drifted:

```bash
# Generate baseline (run once after confirming correctness)
python tests/generate_regression_fixtures.py

# On every subsequent run, compare against baseline
pytest tests/test_regression.py -v
```

---

## 8. Scaling Guide

### 8.1 Performance Scaling

| Grid Size | Recommended Solver | Expected Time | Notes |
|---|---|---|---|
| Nx < 100, Ny < 50 | SOR (Gauss-Seidel) | < 100ms | Suitable for real-time sliders |
| 100 ≤ Nx ≤ 300 | SOR or spsolve | 100ms–2s | Default range |
| Nx > 300 | `scipy.sparse.spsolve` | 2–10s | Show progress bar in UI |
| Nx > 500 | Multigrid or GPU | > 10s | Not in current scope |

### 8.2 Adding New Soil Models

To extend the engine to anisotropic soils (k_x ≠ k_y), modify only `laplace_solver.py`:

The isotropic Laplace equation (∇²h = 0) becomes the anisotropic form:
```
k_x * ∂²h/∂x² + k_y * ∂²h/∂y² = 0
```

The FDM stencil update becomes:
```
h[j,i] = (k_x/dx² * (h[j,i+1] + h[j,i-1]) + k_y/dy² * (h[j+1,i] + h[j-1,i]))
          / (2*k_x/dx² + 2*k_y/dy²)
```

No changes required in `/viz` or `/ui`.

### 8.3 Adding New Visualization Types

New plot types go in `/viz` only. They must:
1. Accept `NDArray` inputs from engine functions
2. Return a `plotly.graph_objects.Figure` or `matplotlib.figure.Figure`
3. Never call any engine function directly — receive pre-computed arrays as arguments

---

## 9. Deployment

### 9.1 Streamlit (Prototype)

```bash
# Local
streamlit run ui/app.py

# Streamlit Cloud
# Push to GitHub → connect repo at share.streamlit.io
# Set secrets: none required for this app
```

### 9.2 FastAPI + React (Production)

**Backend:**
```bash
# Build Docker image
docker build -t seepage-api .

# Run container
docker run -p 8000:8000 seepage-api

# Environment variables
CORS_ORIGINS="https://your-frontend-domain.com"
MAX_GRID_NODES=100000   # Safety limit: Nx * Ny
SOLVER_TIMEOUT_SECONDS=30
```

**Frontend:**
```bash
# Build static assets
npm run build

# Deploy to Vercel
vercel deploy --prod
```

### 9.3 Environment Variable Reference

| Variable | Default | Description |
|---|---|---|
| `MAX_GRID_NODES` | 80000 | Maximum Nx × Ny to prevent DoS |
| `SOLVER_TIMEOUT_SECONDS` | 30 | API request timeout |
| `SOR_OMEGA` | 1.6 | Relaxation factor (tunable) |
| `CONVERGENCE_TOL` | 1e-5 | Solver convergence tolerance [m] |
| `MAX_ITERATIONS` | 10000 | Solver max iteration count |
| `LOG_LEVEL` | INFO | Logging verbosity |

---

## 10. Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Solver does not converge | ω too high (SOR instability) | Reduce `SOR_OMEGA` to 1.3–1.5 |
| Phreatic line goes negative | d parameter too small | Ensure d ≥ 0.3 × upstream slope length |
| q = 0 despite H_u > H_d | Boundary conditions not applied after each iteration | Check that BC application is inside the iteration loop |
| Exit gradient is NaN | h at downstream face is uniform (H_u = H_d) | Add guard: if H_u ≤ H_d, return 0 |
| Visualization flickers on slider drag | Recompute triggered on every keypress | Add 200ms debounce to slider `onChange` handler |
| Sparse solver `MemoryError` | Grid too large for available RAM | Enforce `MAX_GRID_NODES` limit; suggest reducing Nx, Ny |
| Particle animation freezes | Too many Plotly frames in memory | Limit animation to 120 frames; recycle oldest frames |
| `numpy.linalg.LinAlgError` | Singular matrix (degenerate geometry) | Check that L > 0 and Nx ≥ 3 before assembly |

---

## Quick Reference Card

```
q = k(Hu²-Hd²)/(2L)          Seepage discharge [m²/s]
i_e = Δh/Δx at x=L           Exit gradient [dimensionless]
i_cr = (Gs-1)/(1+e) ≈ 1.03   Critical gradient [dimensionless]
FS = i_cr / i_e               Factor of safety against piping
a0 = √(d²+Hu²) - d           Casagrande parabola parameter [m]
y(x) = √(a0² + 2·a0·x)       Phreatic surface [m]
h[j,i] convention: j=vertical (0=base), i=horizontal (0=upstream)
BC upstream:    h[:,0]  = Hu  (Dirichlet)
BC downstream:  h[:,-1] = Hd  (Dirichlet)
BC base:        h[0,:]  = h[1,:]  (Neumann, no-flow)
```

---

*End of CLAUDE.md — Seepage Flow Simulator Developer Guide*
*Keep this file updated whenever the architecture, solver, or BCs change.*
