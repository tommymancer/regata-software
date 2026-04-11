"""Tests for damping filters."""

import pytest

from aquarela.pipeline.state import BoatState
from aquarela.pipeline.damping import DampingFilters, _ScalarBuffer, _AngleBuffer


class TestScalarBuffer:
    def test_single_value(self):
        buf = _ScalarBuffer(max_len=5)
        result = buf.push(10.0)
        assert result == 10.0

    def test_moving_average(self):
        buf = _ScalarBuffer(max_len=3)
        buf.push(10.0)
        buf.push(20.0)
        result = buf.push(30.0)
        assert abs(result - 20.0) < 0.01

    def test_buffer_eviction(self):
        buf = _ScalarBuffer(max_len=2)
        buf.push(10.0)
        buf.push(20.0)
        result = buf.push(30.0)
        # Only 20 and 30 in buffer
        assert abs(result - 25.0) < 0.01


class TestAngleBuffer:
    def test_simple_angle(self):
        buf = _AngleBuffer(max_len=5)
        result = buf.push(90.0)
        assert abs(result - 90.0) < 0.1

    def test_wrapping_near_zero(self):
        """Average of 350° and 10° should be ~0°, not 180°."""
        buf = _AngleBuffer(max_len=2)
        buf.push(350.0)
        result = buf.push(10.0)
        assert result > 350 or result < 10  # Near 0°

    def test_consistent_angle(self):
        buf = _AngleBuffer(max_len=5)
        for _ in range(5):
            result = buf.push(180.0)
        assert abs(result - 180.0) < 0.1


class TestDampingFilters:
    def test_damps_tws(self):
        filters = DampingFilters({"tws_kt": 0.3}, hz=10)  # 3 samples
        values = []
        for v in [10.0, 10.0, 10.0, 20.0]:
            s = BoatState.new()
            s.tws_kt = v
            filters.apply(s)
            values.append(s.tws_kt)
        # After spike, damped value should be less than 20
        assert values[-1] < 20.0

    def test_damps_twd_with_wrapping(self):
        filters = DampingFilters({"twd_deg": 0.2}, hz=10)  # 2 samples
        s1 = BoatState.new()
        s1.twd_deg = 355.0
        filters.apply(s1)

        s2 = BoatState.new()
        s2.twd_deg = 5.0
        filters.apply(s2)
        # Average of 355 and 5 should be ~0, not ~180
        assert s2.twd_deg > 350 or s2.twd_deg < 10

    def test_none_values_skipped(self):
        filters = DampingFilters({"bsp_kt": 0.5}, hz=10)
        s = BoatState.new()
        # bsp_kt is None
        filters.apply(s)
        assert s.bsp_kt is None
