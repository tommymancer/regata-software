"""Edge case tests for polar table interpolation."""

import pytest

from aquarela.performance.polar import PolarTable


class TestPolarEdgeCases:
    """Test polar with synthetic minimal data."""

    @pytest.fixture
    def single_tws_polar(self):
        """Polar with only one TWS column."""
        return PolarTable(
            tws_values=[10],
            twa_values=[40, 60, 90, 120, 150],
            bsp_grid={
                (10, 40): 5.0,
                (10, 60): 6.0,
                (10, 90): 6.5,
                (10, 120): 6.0,
                (10, 150): 5.5,
            },
            upwind_targets={10: (40.0, 5.0, 3.83)},
            downwind_targets={10: (150.0, 5.5, 4.76)},
        )

    @pytest.fixture
    def two_tws_polar(self):
        """Minimal polar with two TWS columns for interpolation."""
        return PolarTable(
            tws_values=[8, 12],
            twa_values=[40, 90, 150],
            bsp_grid={
                (8, 40): 4.0,
                (8, 90): 5.0,
                (8, 150): 4.5,
                (12, 40): 6.0,
                (12, 90): 7.0,
                (12, 150): 6.5,
            },
            upwind_targets={
                8: (40.0, 4.0, 3.06),
                12: (40.0, 6.0, 4.60),
            },
            downwind_targets={
                8: (150.0, 4.5, 3.90),
                12: (150.0, 6.5, 5.63),
            },
        )

    def test_single_tws_exact(self, single_tws_polar):
        """Exact TWA lookup at the only TWS column."""
        assert single_tws_polar.bsp(90, 10) == pytest.approx(6.5)

    def test_single_tws_interpolate_twa(self, single_tws_polar):
        """TWA interpolation within the single column."""
        bsp = single_tws_polar.bsp(75, 10)
        assert bsp is not None
        assert 6.0 <= bsp <= 6.5

    def test_single_tws_clamp_high(self, single_tws_polar):
        """TWS above only column should clamp to it."""
        assert single_tws_polar.bsp(90, 20) == pytest.approx(6.5)

    def test_single_tws_clamp_low(self, single_tws_polar):
        """TWS below only column should clamp to it."""
        assert single_tws_polar.bsp(90, 5) == pytest.approx(6.5)

    def test_two_tws_interpolation(self, two_tws_polar):
        """BSP at TWS=10 should be midpoint of 8 and 12 columns."""
        bsp = two_tws_polar.bsp(90, 10)
        assert bsp == pytest.approx(6.0)  # midpoint of 5.0 and 7.0

    def test_two_tws_exact_low(self, two_tws_polar):
        assert two_tws_polar.bsp(90, 8) == pytest.approx(5.0)

    def test_two_tws_exact_high(self, two_tws_polar):
        assert two_tws_polar.bsp(90, 12) == pytest.approx(7.0)

    def test_port_stbd_symmetric(self, two_tws_polar):
        """Negative TWA (port) should equal positive (starboard)."""
        assert two_tws_polar.bsp(-90, 10) == two_tws_polar.bsp(90, 10)

    def test_very_low_twa_returns_none(self, single_tws_polar):
        """TWA < 20 is below sailing range."""
        assert single_tws_polar.bsp(10, 10) is None

    def test_bsp_zero_handled(self):
        """BSP = 0.0 should be returned correctly, not treated as falsy."""
        polar = PolarTable(
            tws_values=[6, 10],
            twa_values=[30, 90],
            bsp_grid={
                (6, 30): 0.0,
                (6, 90): 3.0,
                (10, 30): 2.0,
                (10, 90): 5.0,
            },
            upwind_targets={},
            downwind_targets={},
        )
        bsp = polar.bsp(30, 6)
        assert bsp is not None
        assert bsp == pytest.approx(0.0)

    def test_empty_grid_returns_none(self):
        polar = PolarTable(
            tws_values=[],
            twa_values=[],
            bsp_grid={},
            upwind_targets={},
            downwind_targets={},
        )
        assert polar.bsp(90, 10) is None


class TestTargetEdgeCases:
    def test_empty_targets(self):
        polar = PolarTable(
            tws_values=[10],
            twa_values=[90],
            bsp_grid={(10, 90): 5.0},
            upwind_targets={},
            downwind_targets={},
        )
        assert polar.target_upwind(10) is None
        assert polar.target_downwind(10) is None

    def test_single_target_clamp(self):
        polar = PolarTable(
            tws_values=[10],
            twa_values=[40],
            bsp_grid={(10, 40): 5.0},
            upwind_targets={10: (40.0, 5.0, 3.83)},
            downwind_targets={},
        )
        # TWS below and above the only target should return it
        result_low = polar.target_upwind(5)
        result_high = polar.target_upwind(20)
        assert result_low is not None
        assert result_high is not None
        assert result_low[0] == pytest.approx(40.0)
        assert result_high[0] == pytest.approx(40.0)

    def test_target_exact_tws_match(self):
        """Exact TWS in target dict should return exact values."""
        polar = PolarTable(
            tws_values=[8, 10, 12],
            twa_values=[40],
            bsp_grid={(8, 40): 4.0, (10, 40): 5.0, (12, 40): 6.0},
            upwind_targets={
                8: (42.0, 4.0, 2.97),
                10: (40.0, 5.0, 3.83),
                12: (38.0, 6.0, 4.73),
            },
            downwind_targets={},
        )
        result = polar.target_upwind(10)
        assert result is not None
        assert result[0] == pytest.approx(40.0)
        assert result[1] == pytest.approx(5.0)
