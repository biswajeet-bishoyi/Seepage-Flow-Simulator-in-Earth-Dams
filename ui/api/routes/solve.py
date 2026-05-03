"""
Solver API route: POST /api/solve

Accepts SolverInput parameters and returns the full analysis result.
"""

import os
import logging

from fastapi import APIRouter, HTTPException

from engine.constants import CRITICAL_GRADIENT, POROSITY_DEFAULT
from engine.darcy import (
    classify_seepage_rating,
    compute_seepage_discharge,
    compute_stream_function,
    compute_velocity_field,
)
from engine.geometry import compute_base_width
from engine.laplace_solver import create_grid, solve_laplace
from engine.phreatic import (
    compute_phreatic_line_for_dam,
    phreatic_to_grid_indices,
)
from engine.safety import (
    classify_piping_risk,
    compute_exit_gradient,
    compute_piping_fs,
    compute_seepage_velocity,
)
from engine.types import SolverInput, SolverOutput

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_GRID_NODES = int(os.getenv("MAX_GRID_NODES", "80000"))
SOLVER_TIMEOUT = int(os.getenv("SOLVER_TIMEOUT_SECONDS", "30"))


@router.post("/solve", response_model=SolverOutput)
async def solve(params: SolverInput) -> SolverOutput:
    """
    Solve the seepage problem for the given parameters.

    Request Body (SolverInput):
        H_u, H_d, k, W, m_u, m_d, Nx, Ny

    Response (SolverOutput):
        h_grid, q, phreatic_x/y, exit_gradient, piping_risk, fs_piping, etc.
    """
    # Validate grid size
    total_nodes = params.Nx * params.Ny
    if total_nodes > MAX_GRID_NODES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Grid too large: {params.Nx}×{params.Ny} = {total_nodes} nodes. "
                f"Maximum allowed: {MAX_GRID_NODES}. Reduce Nx or Ny."
            ),
        )

    try:
        L = params.L

        # 1. Phreatic line
        phreatic_x, phreatic_y = compute_phreatic_line_for_dam(
            params.H_u, params.H_d, L, params.m_u
        )
        phreatic_j = phreatic_to_grid_indices(
            phreatic_y, phreatic_x, params.Nx, params.Ny, L, params.H_u
        )

        # 2. Solve Laplace
        h, iterations, residual, converged = solve_laplace(
            H_u=params.H_u, H_d=params.H_d, L=L,
            Nx=params.Nx, Ny=params.Ny,
            phreatic_j=phreatic_j,
        )

        # 3. Derived quantities
        _, _, dx, dy = create_grid(params.Nx, params.Ny, L, params.H_u)
        q = compute_seepage_discharge(params.k, params.H_u, params.H_d, L)
        i_e = compute_exit_gradient(h, dx)
        fs = compute_piping_fs(i_e)
        risk = classify_piping_risk(i_e)
        rating = classify_seepage_rating(q)
        v_s = compute_seepage_velocity(params.k, i_e)

        return SolverOutput(
            h_grid=h.tolist(),
            q=q,
            phreatic_x=phreatic_x.tolist(),
            phreatic_y=phreatic_y.tolist(),
            exit_gradient=i_e,
            piping_risk=risk,
            fs_piping=fs if fs < 1e6 else 999999.0,
            seepage_rating=rating,
            seepage_velocity=v_s,
            iterations=iterations,
            residual=residual,
            converged=converged,
            dam_base_width=L,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Solver error")
        raise HTTPException(status_code=500, detail=f"Solver error: {str(e)}")
