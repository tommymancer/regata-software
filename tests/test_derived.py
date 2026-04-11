"""Tests for derived calculations (VMG, leeway, current)."""

import math

import pytest

from aquarela.pipeline.state import BoatState
from aquarela.pipeline.derived import (
    compute_vmg,
    compute_leeway,
    compute_current,
    compute_derived,
)


class TestVMG:
    def test_upwind_vmg(self):
        s = BoatState.new()
        s.bsp_kt = 5.5
        s.twa_deg = 42.0
        compute_vmg(s)
        expected = 5.5 * math.cos(math.radians(42.0))
        assert abs(s.vmg_kt - expected) < 0.01

    def test_downwind_vmg(self):
        """VMG is negative when running downwind (TWA > 90°)."""
        s = BoatState.new()
        s.bsp_kt = 6.0
        s.twa_deg = 150.0
        compute_vmg(s)
        assert s.vmg_kt < 0

    def test_beam_reach_vmg(self):
        """VMG ≈ 0 on a beam reach (TWA = 90°)."""
        s = BoatState.new()
        s.bsp_kt = 7.0
        s.twa_deg = 90.0
        compute_vmg(s)
        assert abs(s.vmg_kt) < 0.1

    def test_vmg_missing_fields(self):
        s = BoatState.new()
        compute_vmg(s)
        assert s.vmg_kt is None


class TestLeeway:
    def test_leeway_with_heel(self):
        s = BoatState.new()
        s.heel_deg = 15.0
        s.bsp_kt = 5.0
        compute_leeway(s)
        # k=10: leeway = 10 * 15 / 25 = 6°
        assert abs(s.leeway_deg - 6.0) < 0.1

    def test_leeway_clamped(self):
        """Leeway capped at ±15°."""
        s = BoatState.new()
        s.heel_deg = 25.0
        s.bsp_kt = 2.0
        compute_leeway(s)
        assert abs(s.leeway_deg) <= 15.0

    def test_leeway_low_speed(self):
        """At very low speed, leeway = 0 to avoid division issues."""
        s = BoatState.new()
        s.heel_deg = 10.0
        s.bsp_kt = 0.3
        compute_leeway(s)
        assert s.leeway_deg == 0.0

    def test_leeway_no_heel(self):
        s = BoatState.new()
        s.bsp_kt = 5.0
        compute_leeway(s)
        assert s.leeway_deg is None


class TestCurrent:
    def test_no_current(self):
        """BSP/HDG matches SOG/COG → zero current."""
        s = BoatState.new()
        s.bsp_kt = 5.0
        s.heading_mag = 2.5  # heading_true = 0
        s.sog_kt = 5.0
        s.cog_deg = 0.0
        s.magnetic_variation = 2.5
        compute_current(s)
        assert s.current_drift_kt < 0.1

    def test_following_current(self):
        """SOG > BSP same direction → current pushing from behind."""
        s = BoatState.new()
        s.bsp_kt = 5.0
        s.heading_mag = 2.5  # heading_true = 0
        s.sog_kt = 6.0
        s.cog_deg = 0.0
        s.magnetic_variation = 2.5
        compute_current(s)
        assert abs(s.current_drift_kt - 1.0) < 0.15
        # Current flowing north (same as boat)
        assert s.current_set_deg < 30 or s.current_set_deg > 330

    def test_missing_data(self):
        s = BoatState.new()
        compute_current(s)
        assert s.current_drift_kt is None


class TestComputeDerived:
    def test_runs_all(self):
        s = BoatState.new()
        s.bsp_kt = 5.5
        s.twa_deg = 42.0
        s.heading_mag = 222.0
        s.sog_kt = 5.3
        s.cog_deg = 220.0
        s.magnetic_variation = 2.5
        compute_derived(s)
        assert s.vmg_kt is not None
