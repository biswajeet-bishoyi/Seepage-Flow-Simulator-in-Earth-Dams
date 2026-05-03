"""
Tests for the Darcy flow module.

Verifies discharge formula, velocity field, and seepage rating classification.
"""

import numpy as np
import pytest

from engine.darcy import (
    classify_seepage_rating,
    compute_seepage_discharge,
    compute_stream_function,
    compute_velocity_field,
    integrate_discharge,
)
from engine.types import SeepageRating


class TestSeepageDischarge:
    """Tests for compute_seepage_discharge (Dupuit-Forchheimer formula)."""

    def test_standard_case(self):
        """FAT-01: H_u=20, H_d=0, k=1e-5, L=50 → q = 4.0e-5."""
        q = compute_seepage_discharge(k=1e-5, H_u=20.0, H_d=0.0, L=50.0)
        expected = 1e-5 * (20.0**2) / (2.0 * 50.0)
        assert abs(q - expected) / expected < 0.001

    def test_with_downstream_head(self):
        """Discharge with non-zero downstream head."""
        q = compute_seepage_discharge(k=5e-5, H_u=30.0, H_d=5.0, L=80.0)
        expected = 5e-5 * (30.0**2 - 5.0**2) / (2.0 * 80.0)
        assert abs(q - expected) / expected < 0.001

    def test_zero_head_difference(self):
        """FAT-03: H_u=H_d → q = 0, no crash."""
        q = compute_seepage_discharge(k=1e-5, H_u=15.0, H_d=15.0, L=50.0)
        assert q == 0.0

    def test_invalid_k_raises(self):
        """Negative k should raise ValueError."""
        with pytest.raises(ValueError, match="k must be positive"):
            compute_seepage_discharge(k=-1e-5, H_u=20.0, H_d=0.0, L=50.0)

    def test_invalid_L_raises(self):
        """Zero L should raise ValueError."""
        with pytest.raises(ValueError, match="L must be positive"):
            compute_seepage_discharge(k=1e-5, H_u=20.0, H_d=0.0, L=0.0)

    def test_invalid_heads_raises(self):
        """H_u < H_d should raise ValueError."""
        with pytest.raises(ValueError, match="H_u"):
            compute_seepage_discharge(k=1e-5, H_u=5.0, H_d=20.0, L=50.0)


class TestVelocityField:
    """Tests for compute_velocity_field."""

    def test_uniform_gradient(self):
        """Uniform head gradient should produce uniform velocity."""
        Ny, Nx = 10, 20
        h = np.zeros((Ny, Nx))
        for i in range(Nx):
            h[:, i] = 20.0 - 20.0 * i / (Nx - 1)

        k = 1e-5
        dx = 1.0
        dy = 1.0
        v_x, v_y = compute_velocity_field(h, k, dx, dy)

        # v_x should be approximately constant and positive (flow downstream)
        # Interior points should have consistent gradient
        assert np.all(v_x[:, 1:-1] > 0)

    def test_no_flow_equal_heads(self):
        """Equal heads everywhere should produce zero velocity."""
        h = np.full((10, 20), 15.0)
        v_x, v_y = compute_velocity_field(h, 1e-5, 1.0, 1.0)
        np.testing.assert_allclose(v_x, 0.0, atol=1e-15)
        np.testing.assert_allclose(v_y, 0.0, atol=1e-15)


class TestStreamFunction:
    """Tests for compute_stream_function."""

    def test_shape(self):
        """Stream function should match velocity field shape."""
        v_x = np.ones((10, 20))
        v_y = np.zeros((10, 20))
        psi = compute_stream_function(v_x, v_y, dy=1.0)
        assert psi.shape == (10, 20)

    def test_base_is_zero(self):
        """Stream function at base (j=0) should be zero."""
        v_x = np.ones((10, 20))
        v_y = np.zeros((10, 20))
        psi = compute_stream_function(v_x, v_y, dy=1.0)
        np.testing.assert_allclose(psi[0, :], 0.0)


class TestSeepageRating:
    """Tests for classify_seepage_rating."""

    def test_low(self):
        assert classify_seepage_rating(5e-7) == SeepageRating.LOW

    def test_moderate(self):
        assert classify_seepage_rating(5e-6) == SeepageRating.MODERATE

    def test_high(self):
        assert classify_seepage_rating(5e-5) == SeepageRating.HIGH

    def test_critical(self):
        assert classify_seepage_rating(5e-4) == SeepageRating.CRITICAL
