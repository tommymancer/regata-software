"""Tests for start line capture and geometry."""

import math

import pytest
from aquarela.race.start_line import StartLine, _angle_diff


class TestAngleDiff:
    def test_same(self):
        assert _angle_diff(90.0, 90.0) == pytest.approx(0.0)

    def test_positive(self):
        assert _angle_diff(100.0, 90.0) == pytest.approx(10.0)

    def test_negative(self):
        assert _angle_diff(80.0, 90.0) == pytest.approx(-10.0)

    def test_wrap_positive(self):
        assert _angle_diff(10.0, 350.0) == pytest.approx(20.0)

    def test_wrap_negative(self):
        assert _angle_diff(350.0, 10.0) == pytest.approx(-20.0)

    def test_opposite(self):
        assert abs(_angle_diff(0.0, 180.0)) == pytest.approx(180.0)


class TestStartLineCapture:
    def test_initial_state(self):
        sl = StartLine()
        assert not sl.state.is_line_set()
        assert not sl.state.is_mark_set()

    def test_log_rc(self):
        sl = StartLine()
        sl.log_rc(46.0, 8.96)
        assert sl.state.rc_lat == 46.0
        assert sl.state.rc_lon == 8.96
        assert not sl.state.is_line_set()  # need pin too

    def test_log_pin(self):
        sl = StartLine()
        sl.log_pin(46.001, 8.961)
        assert sl.state.pin_lat == 46.001
        assert not sl.state.is_line_set()

    def test_line_set_when_both_logged(self):
        sl = StartLine()
        sl.log_rc(46.0, 8.96)
        sl.log_pin(46.001, 8.961)
        assert sl.state.is_line_set()

    def test_sight_mark(self):
        sl = StartLine()
        sl.sight_mark(355.0)
        assert sl.state.is_mark_set()
        assert sl.state.mark_bearing == 355.0

    def test_sight_mark_wraps(self):
        sl = StartLine()
        sl.sight_mark(720.0)
        assert sl.state.mark_bearing == 0.0

    def test_reset(self):
        sl = StartLine()
        sl.log_rc(46.0, 8.96)
        sl.log_pin(46.001, 8.961)
        sl.sight_mark(0.0)
        sl.reset()
        assert not sl.state.is_line_set()
        assert not sl.state.is_mark_set()

    def test_to_dict(self):
        sl = StartLine()
        sl.log_rc(46.0, 8.96)
        d = sl.state.to_dict()
        assert d["rc"]["lat"] == 46.0
        assert d["pin"] is None
        assert d["line_set"] is False


class TestStartLineGeometry:
    @pytest.fixture
    def line(self):
        """Start line roughly east-west on Lake Lugano."""
        sl = StartLine()
        sl.log_rc(46.0000, 8.9600)   # RC boat (west)
        sl.log_pin(46.0000, 8.9620)  # Pin end (east)
        return sl

    def test_line_bearing(self, line):
        """RC→Pin should be roughly east (~90°)."""
        lb = line.line_bearing()
        assert lb is not None
        assert 85.0 < lb < 95.0

    def test_line_length(self, line):
        """Line should be ~150m (0.002° lon at 46°N)."""
        ll = line.line_length_m()
        assert ll is not None
        assert 100 < ll < 200

    def test_line_midpoint(self, line):
        mid = line.line_midpoint()
        assert mid is not None
        assert mid[0] == pytest.approx(46.0, abs=0.001)
        assert mid[1] == pytest.approx(8.961, abs=0.001)

    def test_line_bias_square(self, line):
        """Wind from north (0°), line is E-W → perpendicular → square."""
        bias = line.line_bias_deg(0.0)
        assert bias is not None
        assert abs(bias) < 5.0  # approximately square

    def test_line_bias_pin_favored(self, line):
        """Wind from NNE → pin (east) end is more upwind (positive bias)."""
        # Line is E-W (RC west, Pin east), perpendicular is ~0° (north)
        # Wind from 10° (NNE) → eastern (pin) end closer to wind source
        bias = line.line_bias_deg(10.0)
        assert bias is not None
        assert bias > 0  # pin favored

    def test_line_bias_rc_favored(self, line):
        """Wind from NNW → RC (west) end is more upwind (negative bias)."""
        # Wind from 350° (NNW) → western (RC) end closer to wind source
        bias = line.line_bias_deg(350.0)
        assert bias is not None
        assert bias < 0  # RC favored

    def test_leg_bearing(self, line):
        line.sight_mark(5.0)
        assert line.leg_bearing() == 5.0

    def test_course_offset(self, line):
        """Mark at 5°, wind from 0° → offset = +5°."""
        line.sight_mark(5.0)
        offset = line.course_offset_deg(0.0)
        assert offset is not None
        assert offset == pytest.approx(5.0)

    def test_course_offset_negative(self, line):
        """Mark at 355°, wind from 0° → offset = -5°."""
        line.sight_mark(355.0)
        offset = line.course_offset_deg(0.0)
        assert offset is not None
        assert offset == pytest.approx(-5.0)

    def test_dist_to_line(self, line):
        """Boat 100m north of the line."""
        # ~0.001° latitude ≈ 111m
        dist = line.dist_to_line_nm(46.001, 8.961)
        assert dist is not None
        assert 0.05 < dist < 0.1  # roughly 100m = ~0.054 NM

    def test_no_line_returns_none(self):
        sl = StartLine()
        assert sl.line_bearing() is None
        assert sl.line_length_m() is None
        assert sl.line_bias_deg(0.0) is None
        assert sl.dist_to_line_nm(46.0, 8.96) is None
