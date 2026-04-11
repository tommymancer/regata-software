"""Tests for the polar table loader and interpolation."""

import pytest
from aquarela.performance.polar import PolarTable


@pytest.fixture
def polar():
    return PolarTable.load("data/polars/2025_Polar.json")


class TestPolarLoad:
    def test_loads_tws_columns(self, polar):
        assert polar.tws_values == [6, 8, 10, 12, 14, 16, 20]

    def test_loads_polar_data(self, polar):
        assert len(polar.bsp_grid) > 50

    def test_loads_upwind_targets(self, polar):
        assert 6 in polar.upwind_targets
        twa, bsp, vmg = polar.upwind_targets[10]
        assert 35 < twa < 45
        assert 5 < bsp < 7
        assert 4 < vmg < 5.5

    def test_loads_downwind_targets(self, polar):
        twa, bsp, vmg = polar.downwind_targets[10]
        assert 140 < twa < 160
        assert 5 < bsp < 8
        assert 4.5 < vmg < 6.5


class TestPolarInterp:
    def test_exact_grid_point(self, polar):
        """BSP at an exact grid point should match the table."""
        bsp = polar.bsp(twa=52, tws=10)
        assert bsp == pytest.approx(6.5, abs=0.05)

    def test_exact_upwind(self, polar):
        """BSP at upwind target angle."""
        bsp = polar.bsp(twa=37.7, tws=10)
        assert bsp == pytest.approx(5.85, abs=0.1)

    def test_interpolation_between_tws(self, polar):
        """BSP at TWS=9 should be between TWS=8 and TWS=10 values."""
        bsp_8 = polar.bsp(twa=90, tws=8)
        bsp_10 = polar.bsp(twa=90, tws=10)
        bsp_9 = polar.bsp(twa=90, tws=9)
        assert bsp_8 < bsp_9 < bsp_10

    def test_interpolation_between_twa(self, polar):
        """BSP at TWA=66 should be between TWA=60 and TWA=75."""
        bsp_60 = polar.bsp(twa=60, tws=10)
        bsp_75 = polar.bsp(twa=75, tws=10)
        bsp_66 = polar.bsp(twa=66, tws=10)
        assert min(bsp_60, bsp_75) <= bsp_66 <= max(bsp_60, bsp_75)

    def test_symmetric_port_stbd(self, polar):
        """Port and starboard should give the same BSP."""
        assert polar.bsp(42, 10) == polar.bsp(-42, 10)

    def test_clamp_tws_low(self, polar):
        """TWS below table minimum should clamp, not return None."""
        bsp = polar.bsp(twa=90, tws=4)
        assert bsp is not None
        assert bsp > 0

    def test_clamp_tws_high(self, polar):
        """TWS above table maximum should clamp."""
        bsp = polar.bsp(twa=90, tws=25)
        assert bsp is not None
        assert bsp > 0

    def test_very_low_twa_returns_none(self, polar):
        """TWA < 20° is outside sailing range."""
        assert polar.bsp(twa=10, tws=10) is None


class TestTargetInterp:
    def test_upwind_exact(self, polar):
        result = polar.target_upwind(10)
        assert result is not None
        twa, bsp, vmg = result
        assert twa == pytest.approx(37.7, abs=0.1)
        assert bsp == pytest.approx(5.85, abs=0.1)

    def test_upwind_interpolated(self, polar):
        """Target at TWS=9 should interpolate between 8 and 10."""
        t8 = polar.target_upwind(8)
        t10 = polar.target_upwind(10)
        t9 = polar.target_upwind(9)
        assert t8[1] < t9[1] < t10[1]  # BSP increases with TWS

    def test_downwind_exact(self, polar):
        result = polar.target_downwind(10)
        assert result is not None
        twa, bsp, vmg = result
        assert twa == pytest.approx(151.6, abs=0.1)

    def test_target_clamp_low_tws(self, polar):
        """Should return first target for very low TWS."""
        result = polar.target_upwind(2)
        assert result is not None
