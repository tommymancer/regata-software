"""Tests for VMC computation and VMC-optimal targets."""

import math

import pytest
from aquarela.performance.vmc import compute_vmc, compute_vmc_targets
from aquarela.pipeline.state import BoatState
from datetime import datetime, timezone


class TestComputeVMC:
    def test_sailing_directly_at_mark(self):
        """Heading equals leg bearing → VMC = BSP."""
        vmc = compute_vmc(bsp=6.0, heading=0.0, leg_bearing=0.0)
        assert vmc == pytest.approx(6.0)

    def test_sailing_perpendicular(self):
        """Heading 90° off leg bearing → VMC ≈ 0."""
        vmc = compute_vmc(bsp=6.0, heading=90.0, leg_bearing=0.0)
        assert abs(vmc) < 0.01

    def test_sailing_away(self):
        """Heading 180° off → VMC = -BSP."""
        vmc = compute_vmc(bsp=6.0, heading=180.0, leg_bearing=0.0)
        assert vmc == pytest.approx(-6.0)

    def test_typical_upwind(self):
        """Upwind at ~40° off → VMC = 6 × cos(40°) ≈ 4.6."""
        vmc = compute_vmc(bsp=6.0, heading=40.0, leg_bearing=0.0)
        expected = 6.0 * math.cos(math.radians(40.0))
        assert vmc == pytest.approx(expected, abs=0.01)

    def test_wrap_around(self):
        """Heading 350°, leg bearing 10° → 20° off → positive VMC."""
        vmc = compute_vmc(bsp=6.0, heading=350.0, leg_bearing=10.0)
        expected = 6.0 * math.cos(math.radians(-20.0))
        assert vmc == pytest.approx(expected, abs=0.01)


class TestComputeVMCTargets:
    """Test VMC target adjustment with a simple mock polar."""

    @pytest.fixture
    def polar(self):
        """Minimal polar table for testing."""
        from aquarela.performance.polar import PolarTable
        # Create a simple polar with upwind target at TWA=42°, BSP=6.0, VMG=4.46
        return PolarTable(
            tws_values=[8.0, 10.0, 12.0],
            twa_values=[30.0, 42.0, 60.0, 90.0, 120.0, 150.0],
            bsp_grid={
                (8.0, 30.0): 4.0, (8.0, 42.0): 5.5, (8.0, 60.0): 6.0,
                (8.0, 90.0): 6.5, (8.0, 120.0): 6.0, (8.0, 150.0): 5.0,
                (10.0, 30.0): 4.5, (10.0, 42.0): 6.0, (10.0, 60.0): 6.5,
                (10.0, 90.0): 7.0, (10.0, 120.0): 6.5, (10.0, 150.0): 5.5,
                (12.0, 30.0): 5.0, (12.0, 42.0): 6.5, (12.0, 60.0): 7.0,
                (12.0, 90.0): 7.5, (12.0, 120.0): 7.0, (12.0, 150.0): 6.0,
            },
            upwind_targets={8.0: (42.0, 5.5, 4.09), 10.0: (42.0, 6.0, 4.46), 12.0: (42.0, 6.5, 4.83)},
            downwind_targets={8.0: (150.0, 5.0, 4.33), 10.0: (150.0, 5.5, 4.76), 12.0: (150.0, 6.0, 5.20)},
        )

    def _make_state(self, twa, tws, bsp, heading=None, leg_bearing=None):
        s = BoatState(timestamp=datetime.now(timezone.utc))
        s.twa_deg = twa
        s.tws_kt = tws
        s.bsp_kt = bsp
        s.heading_mag = heading
        s.leg_bearing_deg = leg_bearing
        return s

    def test_zero_offset_no_change(self, polar):
        """With 0° course offset, VMC target ≈ polar target."""
        state = self._make_state(twa=42.0, tws=10.0, bsp=6.0)
        compute_vmc_targets(state, polar, course_offset=0.0)
        # Should be close to polar target (42°)
        assert state.target_twa_vmc_deg is not None
        assert state.target_twa_vmc_deg == pytest.approx(42.0, abs=1.0)

    def test_positive_offset_starboard(self, polar):
        """Mark right of wind, starboard tack → sail tighter."""
        state = self._make_state(twa=42.0, tws=10.0, bsp=6.0)
        compute_vmc_targets(state, polar, course_offset=10.0)
        # Starboard: tighter (lower TWA)
        assert state.target_twa_vmc_deg is not None
        assert state.target_twa_vmc_deg < 42.0

    def test_positive_offset_port(self, polar):
        """Mark right of wind, port tack → sail wider."""
        state = self._make_state(twa=-42.0, tws=10.0, bsp=6.0)
        compute_vmc_targets(state, polar, course_offset=10.0)
        # Port: wider (higher absolute TWA, negative sign)
        assert state.target_twa_vmc_deg is not None
        assert abs(state.target_twa_vmc_deg) > 42.0

    def test_negative_offset_port(self, polar):
        """Mark left of wind, port tack → sail tighter."""
        state = self._make_state(twa=-42.0, tws=10.0, bsp=6.0)
        compute_vmc_targets(state, polar, course_offset=-10.0)
        assert state.target_twa_vmc_deg is not None
        assert abs(state.target_twa_vmc_deg) < 42.0

    def test_clamp_minimum(self, polar):
        """Large offset doesn't push target below minimum TWA."""
        state = self._make_state(twa=42.0, tws=10.0, bsp=6.0)
        compute_vmc_targets(state, polar, course_offset=30.0)
        assert state.target_twa_vmc_deg is not None
        assert abs(state.target_twa_vmc_deg) >= 25.0

    def test_vmc_computed_with_heading(self, polar):
        """VMC is computed when heading and leg bearing are available."""
        state = self._make_state(
            twa=42.0, tws=10.0, bsp=6.0,
            heading=5.0, leg_bearing=0.0,
        )
        compute_vmc_targets(state, polar, course_offset=5.0)
        assert state.vmc_kt is not None
        assert state.vmc_kt > 0

    def test_missing_data_graceful(self, polar):
        """Missing TWA/TWS/BSP doesn't crash."""
        state = self._make_state(twa=None, tws=None, bsp=None)
        compute_vmc_targets(state, polar, course_offset=5.0)
        assert state.target_twa_vmc_deg is None
