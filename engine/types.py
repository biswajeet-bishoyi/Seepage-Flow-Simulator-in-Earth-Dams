"""
Data models for solver input/output using Pydantic.

All I/O types for the engine are defined here. These models enforce
validation rules from the PRD and provide serialization for the API.
"""

from enum import Enum
from typing import List, Optional

import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator


class RiskLevel(str, Enum):
    """Piping risk classification based on Factor of Safety."""

    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SeepageRating(str, Enum):
    """Qualitative seepage discharge rating."""

    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    CRITICAL = "Critical"


class SolverInput(BaseModel):
    """
    Input parameters for the seepage solver.

    All parameters are validated against the ranges specified in the PRD.
    """

    H_u: float = Field(
        default=20.0,
        ge=1.0,
        le=100.0,
        description="Upstream hydraulic head [m]",
    )
    H_d: float = Field(
        default=2.0,
        ge=0.0,
        le=99.0,
        description="Downstream hydraulic head [m]",
    )
    k: float = Field(
        default=1e-5,
        gt=0,
        description="Hydraulic conductivity [m/s]",
    )
    W: float = Field(
        default=10.0,
        ge=5.0,
        le=50.0,
        description="Dam crest width [m]",
    )
    m_u: float = Field(
        default=3.0,
        ge=1.5,
        le=5.0,
        description="Upstream slope ratio (H:V) [dimensionless]",
    )
    m_d: float = Field(
        default=2.5,
        ge=1.5,
        le=5.0,
        description="Downstream slope ratio (H:V) [dimensionless]",
    )
    Nx: int = Field(
        default=200,
        ge=50,
        le=500,
        description="Number of horizontal FDM grid nodes",
    )
    Ny: int = Field(
        default=80,
        ge=20,
        le=200,
        description="Number of vertical FDM grid nodes",
    )

    @field_validator("k")
    @classmethod
    def validate_k_range(cls, v: float) -> float:
        """Hydraulic conductivity must be between 1e-9 and 1e-3 m/s."""
        if v < 1e-9 or v > 1e-3:
            raise ValueError(
                f"k must be between 1e-9 and 1e-3 m/s, got {v:.2e}"
            )
        return v

    @model_validator(mode="after")
    def validate_heads(self) -> "SolverInput":
        """Upstream head must be greater than downstream head."""
        if self.H_u <= self.H_d:
            raise ValueError(
                f"H_u ({self.H_u}) must be greater than H_d ({self.H_d})"
            )
        return self

    @property
    def L(self) -> float:
        """Dam base width [m], auto-computed from geometry: L = W + m_u×H_u + m_d×H_u."""
        return self.W + self.m_u * self.H_u + self.m_d * self.H_u


class SolverOutput(BaseModel):
    """
    Output from the seepage solver.

    Contains the full solution field, derived quantities, and safety metrics.
    """

    model_config = {"arbitrary_types_allowed": True}

    h_grid: List[List[float]] = Field(
        description="Solved hydraulic head field h[j,i], shape (Ny, Nx) [m]"
    )
    q: float = Field(
        description="Seepage discharge per unit width [m²/s]"
    )
    phreatic_x: List[float] = Field(
        description="X-coordinates of the phreatic line [m]"
    )
    phreatic_y: List[float] = Field(
        description="Y-coordinates of the phreatic line [m]"
    )
    exit_gradient: float = Field(
        description="Exit gradient i_e at downstream toe [dimensionless]"
    )
    piping_risk: RiskLevel = Field(
        description="Piping risk classification"
    )
    fs_piping: float = Field(
        description="Factor of safety against piping = i_cr / i_e"
    )
    seepage_rating: SeepageRating = Field(
        description="Qualitative seepage discharge rating"
    )
    seepage_velocity: float = Field(
        description="Seepage velocity at exit v_s = k·i_e/n [m/s]"
    )
    iterations: Optional[int] = Field(
        default=None,
        description="Number of solver iterations (None if direct solver used)"
    )
    residual: Optional[float] = Field(
        default=None,
        description="Final solver residual [m]"
    )
    converged: bool = Field(
        default=True,
        description="Whether the solver converged within tolerance"
    )
    dam_base_width: float = Field(
        description="Computed dam base width L [m]"
    )
