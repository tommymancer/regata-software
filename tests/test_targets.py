"""Tests for performance target computation."""

import pytest
from aquarela.performance.polar import PolarTable
from aquarela.performance.targets import compute_targets
from aquarela.pipeline.state import BoatState


@pytest.fixture
def polar():
    return PolarTable.load("data/polars/2025_Polar.json")


def _make_state(bsp=6.0, twa=-42.0, tws=10.0, vmg=4.5):
    s = BoatState.new()
    s.bsp_kt = bsp
    s.twa_deg = twa
    s.tws_kt = tws
    s.vmg_kt = vmg
    return s


class TestComputeTargets:
    def test_upwind_perf_near_polar(self, polar):
        """Sailing at polar BSP → PERF% ≈ 100%."""
        # At TWA=37.7, TWS=10, polar BSP=5.85
        s = _make_state(bsp=5.85, twa=-37.7, tws=10.0)
        compute_targets(s, polar)
        assert s.perf_pct == pytest.approx(100.0, abs=2)

    def test_upwind_perf_below_polar(self, polar):
        """Sailing below polar → PERF% < 100%."""
        s = _make_state(bsp=4.5, twa=-42.0, tws=10.0)
        compute_targets(s, polar)
        assert s.perf_pct is not None
        assert s.perf_pct < 100

    def test_target_twa_signed_port(self, polar):
        """Target TWA should match sign of current TWA (port=negative)."""
        s = _make_state(twa=-42.0, tws=10.0)
        compute_targets(s, polar)
        assert s.target_twa_deg is not None
        assert s.target_twa_deg < 0

    def test_target_twa_signed_stbd(self, polar):
        """Starboard tack → positive target TWA."""
        s = _make_state(twa=42.0, tws=10.0)
        compute_targets(s, polar)
        assert s.target_twa_deg is not None
        assert s.target_twa_deg > 0

    def test_downwind_targets(self, polar):
        """Downwind sailing should get downwind targets."""
        s = _make_state(bsp=6.0, twa=150.0, tws=10.0, vmg=-5.0)
        compute_targets(s, polar)
        assert s.target_twa_deg is not None
        assert abs(s.target_twa_deg) > 100

    def test_vmg_perf(self, polar):
        """VMG-PERF% should be computed."""
        s = _make_state(bsp=5.85, twa=-37.7, tws=10.0, vmg=4.5)
        compute_targets(s, polar)
        assert s.vmg_perf_pct is not None
        assert 80 < s.vmg_perf_pct < 120

    def test_missing_data_graceful(self, polar):
        """Missing TWA/TWS/BSP should not crash."""
        s = BoatState.new()
        compute_targets(s, polar)
        assert s.perf_pct is None
        assert s.target_twa_deg is None

    def test_target_bsp_set(self, polar):
        """Target BSP should be populated from polar."""
        s = _make_state(twa=-42.0, tws=10.0)
        compute_targets(s, polar)
        assert s.target_bsp_kt is not None
        assert s.target_bsp_kt > 0
