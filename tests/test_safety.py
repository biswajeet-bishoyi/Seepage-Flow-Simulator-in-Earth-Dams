"""
Tests for the safety analytics module.

Verifies exit gradient, piping FS, risk classification, heave check,
and seepage velocity calculations.
"""

import numpy as np
import pytest

from engine.constants import CRITICAL_GRADIENT
from engine.safety import (
    classify_piping_risk,
    compute_exit_gradient,
    compute_heave_fs,
    compute_piping_fs,
    compute_seepage_velocity,
    get_risk_color,
    get_risk_description,
)
from engine.types import RiskLevel


class TestExitGradient:
    """Tests for compute_exit_gradient."""

    def test_uniform_gradient(self):
        """Uniform head field should give consistent exit gradient."""
        Ny, Nx = 10, 20
        h = np.zeros((Ny, Nx))
        for i in range(Nx):
            h[:, i] = 20.0 - 20.0 * i / (Nx - 1)
        dx = 50.0 / (Nx - 1)
        i_e = compute_exit_gradient(h, dx)
        assert i_e > 0

    def test_zero_gradient(self):
        """Equal head everywhere → zero exit gradient."""
        h = np.full((10, 20), 15.0)
        dx = 1.0
        i_e = compute_exit_gradient(h, dx)
        assert i_e == 0.0


class TestPipingFS:
    """Tests for compute_piping_fs."""

    def test_zero_gradient(self):
        """Zero exit gradient → infinite FS."""
        fs = compute_piping_fs(0.0)
        assert fs == float("inf")

    def test_critical_gradient(self):
        """Exit gradient = critical → FS = 1.0."""
        fs = compute_piping_fs(CRITICAL_GRADIENT)
        assert abs(fs - 1.0) < 1e-10

    def test_half_critical(self):
        """Exit gradient = half critical → FS = 2.0."""
        fs = compute_piping_fs(CRITICAL_GRADIENT / 2.0)
        assert abs(fs - 2.0) < 1e-10


class TestRiskClassification:
    """Tests for classify_piping_risk."""

    def test_low_risk(self):
        """FS ≥ 4.0 → LOW."""
        i_e = CRITICAL_GRADIENT / 5.0  # FS = 5.0
        assert classify_piping_risk(i_e) == RiskLevel.LOW

    def test_moderate_risk(self):
        """2.0 ≤ FS < 4.0 → MODERATE."""
        i_e = CRITICAL_GRADIENT / 3.0  # FS = 3.0
        assert classify_piping_risk(i_e) == RiskLevel.MODERATE

    def test_high_risk(self):
        """1.5 ≤ FS < 2.0 → HIGH."""
        i_e = CRITICAL_GRADIENT / 1.7  # FS = 1.7
        assert classify_piping_risk(i_e) == RiskLevel.HIGH

    def test_critical_risk(self):
        """FS < 1.5 → CRITICAL (FAT-04)."""
        i_e = CRITICAL_GRADIENT * 0.9  # FS ≈ 1.11
        assert classify_piping_risk(i_e) == RiskLevel.CRITICAL

    def test_zero_gradient_is_low(self):
        """Zero gradient → infinite FS → LOW."""
        assert classify_piping_risk(0.0) == RiskLevel.LOW


class TestHeaveFS:
    """Tests for compute_heave_fs."""

    def test_no_vertical_gradient(self):
        """No vertical gradient → infinite FS."""
        h = np.full((10, 20), 15.0)
        fs = compute_heave_fs(h, dy=1.0)
        assert fs == float("inf")


class TestSeepageVelocity:
    """Tests for compute_seepage_velocity."""

    def test_formula(self):
        """v_s = k * i_e / n."""
        k = 1e-5
        i_e = 0.5
        n = 0.35
        expected = k * i_e / n
        result = compute_seepage_velocity(k, i_e, n)
        assert abs(result - expected) < 1e-15

    def test_zero_gradient(self):
        """Zero gradient → zero velocity."""
        assert compute_seepage_velocity(1e-5, 0.0) == 0.0


class TestRiskHelpers:
    """Tests for risk display helpers."""

    def test_risk_colors(self):
        """Each risk level should have a hex color."""
        for level in RiskLevel:
            color = get_risk_color(level)
            assert color.startswith("#")

    def test_risk_descriptions(self):
        """Each risk level should have a non-empty description."""
        for level in RiskLevel:
            desc = get_risk_description(level)
            assert len(desc) > 10
