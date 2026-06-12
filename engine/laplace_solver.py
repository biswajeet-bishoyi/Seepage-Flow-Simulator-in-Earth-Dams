"""
Finite Difference Method (FDM) solver for the 2D Laplace equation.

Solves ∇²h = 0 (steady-state seepage) over a discretized 2D domain
using Gauss-Seidel with Successive Over-Relaxation (SOR), with a
fallback to scipy sparse direct solver for large grids.

Grid convention: h[j, i] where j=vertical (0=base), i=horizontal (0=upstream)

Physical coordinates:
    x = i * dx    [m, horizontal, left=upstream]
    y = j * dy    [m, vertical,   bottom=base]
"""

import logging

import numpy as np
from numpy.typing import NDArray
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve

from engine.constants import (
    CONVERGENCE_TOL,
    MAX_ITERATIONS,
    SOR_OMEGA,
    SPARSE_SOLVER_THRESHOLD,
)

logger = logging.getLogger(__name__)


def create_grid(
    Nx: int,
    Ny: int,
    L: float,
    H_dam: float,
) -> tuple[NDArray[np.float64], NDArray[np.float64], float, float]:
    """
    Create the 2D FDM grid for the dam domain.

    Domain spans [0, L] × [0, H_dam].

    Uniform spacing:
        Δx = L / (Nx − 1)
        Δy = H_dam / (Ny − 1)

    Parameters
    ----------
    Nx : int
        Number of horizontal grid nodes.
    Ny : int
        Number of vertical grid nodes.
    L : float
        Dam base width [m].
    H_dam : float
        Dam height [m].

    Returns
    -------
    tuple[NDArray, NDArray, float, float]
        (x_coords, y_coords, dx, dy) where x_coords has shape (Nx,)
        and y_coords has shape (Ny,).
    """
    dx = L / (Nx - 1)
    dy = H_dam / (Ny - 1)
    x_coords = np.linspace(0.0, L, Nx)
    y_coords = np.linspace(0.0, H_dam, Ny)
    return x_coords, y_coords, dx, dy


def initialize_head_field(
    Nx: int,
    Ny: int,
    H_u: float,
    H_d: float,
) -> NDArray[np.float64]:
    """
    Initialize the head field with a linear interpolation between H_u and H_d.

    This provides a reasonable initial guess for the iterative solver,
    reducing the number of iterations needed for convergence.

    Parameters
    ----------
    Nx, Ny : int
        Grid dimensions.
    H_u : float
        Upstream head [m].
    H_d : float
        Downstream head [m].

    Returns
    -------
    NDArray[np.float64]
        Initial head field, shape (Ny, Nx).
    """
    h = np.zeros((Ny, Nx), dtype=np.float64)
    for i in range(Nx):
        h[:, i] = H_u + (H_d - H_u) * i / (Nx - 1)
    return h


def apply_boundary_conditions(
    h: NDArray[np.float64],
    H_u: float,
    H_d: float,
    phreatic_j: NDArray[np.int_] | None = None,
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
    phreatic_j : NDArray[np.int_] or None
        Row index of phreatic line at each column i, shape (Nx,).
        If None, free surface BC is not applied (used for simplified analysis).

    Returns
    -------
    NDArray[np.float64]
        Updated head array (same reference as input).
    """
    Ny, Nx = h.shape

    # Upstream face — Dirichlet
    h[:, 0] = H_u

    # Downstream face — Dirichlet (seepage face properly modeled)
    for j in range(Ny):
        y_elevation = j * (H_u / (Ny - 1))
        h[j, -1] = max(H_d, y_elevation)

    # Base — Neumann (no-flow, zero normal gradient)
    h[0, :] = h[1, :]

    # Free surface — Dirichlet (nodes above phreatic line)
    if phreatic_j is not None:
        for i in range(Nx):
            j_phreatic = min(phreatic_j[i], Ny - 1)
            for j in range(j_phreatic + 1, Ny):
                y_elevation = j * (H_u / (Ny - 1))
                h[j, i] = y_elevation

    return h


def gauss_seidel_sor(
    h: NDArray[np.float64],
    H_u: float,
    H_d: float,
    dx: float,
    dy: float,
    omega: float = SOR_OMEGA,
    tol: float = CONVERGENCE_TOL,
    max_iter: int = MAX_ITERATIONS,
    phreatic_j: NDArray[np.int_] | None = None,
) -> tuple[NDArray[np.float64], int, float]:
    """
    Solve the Laplace equation using Gauss-Seidel with SOR acceleration.

    The update stencil for interior nodes:
        h_new[j,i] = (α²·(h[j,i+1] + h[j,i-1]) + h[j+1,i] + h[j-1,i]) / (2·(α² + 1))

        where α = Δy / Δx  (aspect ratio)

    SOR acceleration:
        h[j,i] ← h[j,i] + ω · (h_new[j,i] − h[j,i])

    Convergence criterion:
        max|h_new[j,i] − h_old[j,i]| < ε

    Parameters
    ----------
    h : NDArray[np.float64]
        Initial head field, shape (Ny, Nx). Modified in-place.
    H_u : float
        Upstream head [m].
    H_d : float
        Downstream head [m].
    dx : float
        Horizontal grid spacing [m].
    dy : float
        Vertical grid spacing [m].
    omega : float
        SOR relaxation factor. 1.0 = Gauss-Seidel, 1.0–2.0 = SOR.
    tol : float
        Convergence tolerance [m].
    max_iter : int
        Maximum number of iterations.
    phreatic_j : NDArray[np.int_] or None
        Phreatic line row indices for free surface BC.

    Returns
    -------
    tuple[NDArray, int, float]
        (h_solved, iterations_taken, final_residual)
    """
    Ny, Nx = h.shape
    alpha2 = (dy / dx) ** 2
    denom = 2.0 * (alpha2 + 1.0)

    residual = 0.0

    for iteration in range(max_iter):
        max_change = 0.0

        # Update interior nodes
        for j in range(1, Ny - 1):
            for i in range(1, Nx - 1):
                # Skip nodes above phreatic line if applicable
                if phreatic_j is not None and j > phreatic_j[i]:
                    continue

                h_new = (
                    alpha2 * (h[j, i + 1] + h[j, i - 1])
                    + h[j + 1, i]
                    + h[j - 1, i]
                ) / denom

                change = h_new - h[j, i]
                h[j, i] += omega * change
                max_change = max(max_change, abs(change))

        # Re-apply boundary conditions after each iteration
        apply_boundary_conditions(h, H_u, H_d, phreatic_j)

        residual = max_change

        if iteration % 100 == 0:
            logger.debug("Iter %d | Residual: %.2e", iteration, residual)

        if residual < tol:
            logger.info(
                "Converged at iteration %d | Residual: %.2e",
                iteration,
                residual,
            )
            return h, iteration, residual

    logger.warning(
        "Max iterations (%d) reached. Residual: %.2e", max_iter, residual
    )
    return h, max_iter, residual


def build_and_solve_sparse(
    Nx: int,
    Ny: int,
    dx: float,
    dy: float,
    H_u: float,
    H_d: float,
    phreatic_j: NDArray[np.int_] | None = None,
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
    H_u, H_d : float
        Upstream and downstream head [m].
    phreatic_j : NDArray[np.int_] or None
        Phreatic line row indices for free surface BC.

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
            is_bc = False

            # Upstream face — Dirichlet
            if i == 0:
                A[idx, idx] = 1.0
                b[idx] = H_u
                is_bc = True

            # Downstream face — Dirichlet
            elif i == Nx - 1:
                A[idx, idx] = 1.0
                y_elev = j * dy
                b[idx] = max(H_d, y_elev)
                is_bc = True

            # Base — Neumann (no-flow): h[0,i] = h[1,i]
            elif j == 0:
                A[idx, idx] = 1.0
                A[idx, idx + Nx] = -1.0
                b[idx] = 0.0
                is_bc = True

            # Top row
            elif j == Ny - 1:
                A[idx, idx] = 1.0
                y_elev = j * dy
                b[idx] = y_elev
                is_bc = True

            # Above phreatic line
            elif phreatic_j is not None and j > phreatic_j[i]:
                A[idx, idx] = 1.0
                y_elev = j * dy
                b[idx] = y_elev
                is_bc = True

            # Interior nodes — 5-point Laplacian stencil
            if not is_bc:
                A[idx, idx] = -2.0 * (alpha2 + 1.0)
                if i > 0:
                    A[idx, idx - 1] = alpha2
                if i < Nx - 1:
                    A[idx, idx + 1] = alpha2
                if j > 0:
                    A[idx, idx - Nx] = 1.0
                if j < Ny - 1:
                    A[idx, idx + Nx] = 1.0

    logger.info("Solving sparse system with %d unknowns...", N)
    h_vec = spsolve(A.tocsr(), b)
    logger.info("Sparse solve complete.")
    return h_vec.reshape(Ny, Nx)


def solve_laplace(
    H_u: float,
    H_d: float,
    L: float,
    Nx: int = 200,
    Ny: int = 80,
    omega: float = SOR_OMEGA,
    tol: float = CONVERGENCE_TOL,
    max_iter: int = MAX_ITERATIONS,
    phreatic_j: NDArray[np.int_] | None = None,
    force_iterative: bool = False,
) -> tuple[NDArray[np.float64], int | None, float | None, bool]:
    """
    High-level entry point for solving the Laplace equation over the dam domain.

    Automatically selects the solver based on grid size:
        - Grid ≤ SPARSE_SOLVER_THRESHOLD nodes: SOR iterative solver
        - Grid > SPARSE_SOLVER_THRESHOLD nodes: sparse direct solver

    Parameters
    ----------
    H_u : float
        Upstream head [m].
    H_d : float
        Downstream head [m].
    L : float
        Dam base width [m].
    Nx, Ny : int
        Grid dimensions.
    omega : float
        SOR relaxation factor.
    tol : float
        Convergence tolerance [m].
    max_iter : int
        Maximum iterations for SOR.
    phreatic_j : NDArray or None
        Phreatic line row indices.
    force_iterative : bool
        If True, always use SOR regardless of grid size.

    Returns
    -------
    tuple[NDArray, int | None, float | None, bool]
        (h_solved, iterations, residual, converged)
        iterations and residual are None if the sparse direct solver was used.
    """
    H_dam = H_u  # Dam height equals upstream head

    _, _, dx, dy = create_grid(Nx, Ny, L, H_dam)

    total_nodes = Nx * Ny
    use_sparse = total_nodes > SPARSE_SOLVER_THRESHOLD and not force_iterative

    if use_sparse:
        logger.info(
            "Using sparse direct solver (grid: %d×%d = %d nodes)",
            Nx, Ny, total_nodes,
        )
        h = build_and_solve_sparse(Nx, Ny, dx, dy, H_u, H_d, phreatic_j)
        return h, None, None, True
    else:
        logger.info(
            "Using SOR iterative solver (grid: %d×%d = %d nodes, ω=%.2f)",
            Nx, Ny, total_nodes, omega,
        )
        h = initialize_head_field(Nx, Ny, H_u, H_d)
        apply_boundary_conditions(h, H_u, H_d, phreatic_j)
        h, iterations, residual = gauss_seidel_sor(
            h, H_u, H_d, dx, dy, omega, tol, max_iter, phreatic_j
        )
        converged = residual < tol
        return h, iterations, residual, converged
