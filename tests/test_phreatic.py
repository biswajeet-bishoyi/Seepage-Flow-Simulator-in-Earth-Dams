"""
Tests for the Casagrande phreatic line module.

Verifies boundary conditions, monotonicity, and non-negativity.
"""

import numpy as np
import pytest

from engine.phreatic import (
    casagrande_phreatic_line,
    compute_focus_parameter,
    compute_phreatic_line_for_dam,
    phreatic_line_table,
)


class TestFocusParameter:
    """Tests for compute_focus_parameter (a₀)."""

    def test_positive(self):
        """a₀ should always be positive for valid inputs."""
        a0 = compute_focus_parameter(H_u=20.0, d=6.0)
        assert a0 > 0

    def test_formula(self):
        """a₀ = √(d² + H_u²) − d."""
        H_u, d = 20.0, 6.0
        expected = np.sqrt(d**2 + H_u**2) - d
        assert abs(compute_focus_parameter(H_u, d) - expected) < 1e-10

    def test_zero_distance(self):
        """When d=0, a₀ = H_u."""
        a0 = compute_focus_parameter(H_u=15.0, d=0.0)
        assert abs(a0 - 15.0) < 1e-10


class TestCasagrandePhreaticLine:
    """Tests for casagrande_phreatic_line."""

    def test_non_negative(self):
        """Phreatic line must not go below datum."""
        x = np.linspace(0, 50, 100)
        y = casagrande_phreatic_line(H_u=20.0, L=50.0, d=6.0, x_values=x)
        assert np.all(y >= 0), "Phreatic line must not go below datum"

    def test_at_focus(self):
        """At x=0 (focus), y should equal a₀."""
        a0 = compute_focus_parameter(H_u=20.0, d=6.0)
        y_at_zero = casagrande_phreatic_line(
            H_u=20.0, L=50.0, d=6.0, x_values=np.array([0.0])
        )
        assert abs(y_at_zero[0] - a0) < 1e-10

    def test_increasing_with_x(self):
        """Phreatic line y(x) should increase with x (away from focus)."""
        x = np.linspace(0, 50, 100)
        y = casagrande_phreatic_line(H_u=20.0, L=50.0, d=6.0, x_values=x)
        assert np.all(np.diff(y) >= 0), "y(x) should be non-decreasing"


class TestPhreaticLineForDam:
    """Tests for compute_phreatic_line_for_dam (convenience wrapper)."""

    def test_output_shape(self):
        """Should return arrays of the specified length."""
        x, y = compute_phreatic_line_for_dam(
            H_u=20.0, H_d=2.0, L=50.0, m_u=3.0, num_points=100
        )
        assert len(x) == 100
        assert len(y) == 100

    def test_y_clipped(self):
        """Phreatic y should be clipped to [H_d, H_u]."""
        x, y = compute_phreatic_line_for_dam(
            H_u=20.0, H_d=2.0, L=50.0, m_u=3.0
        )
        assert np.all(y >= 2.0)
        assert np.all(y <= 20.0)

    def test_x_spans_dam(self):
        """X should span from 0 to L."""
        L = 50.0
        x, y = compute_phreatic_line_for_dam(
            H_u=20.0, H_d=2.0, L=L, m_u=3.0
        )
        assert abs(x[0]) < 1e-10
        assert abs(x[-1] - L) < 1e-10


class TestPhreaticLineTable:
    """Tests for phreatic_line_table."""

    def test_station_count(self):
        """Should return the requested number of stations."""
        x = np.linspace(0, 50, 100)
        y = np.linspace(20, 2, 100)
        table = phreatic_line_table(x, y, num_stations=10)
        assert len(table) == 10

    def test_tuple_format(self):
        """Each entry should be a (x, y) tuple of floats."""
        x = np.linspace(0, 50, 100)
        y = np.linspace(20, 2, 100)
        table = phreatic_line_table(x, y, num_stations=5)
        for entry in table:
            assert len(entry) == 2
            assert isinstance(entry[0], float)
            assert isinstance(entry[1], float)
