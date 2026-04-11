"""Tests for mark navigation — haversine calculations."""

import math

import pytest
from aquarela.pipeline.state import BoatState
from aquarela.race.navigation import (
    bearing_to,
    compute_navigation,
    haversine_distance,
)


class TestHaversine:
    def test_same_point(self):
        """Distance from a point to itself is 0."""
        d = haversine_distance(46.0, 8.96, 46.0, 8.96)
        assert d == pytest.approx(0.0, abs=0.001)

    def test_known_distance(self):
        """Lugano to Melide is roughly 3 NM."""
        # Lugano ~46.003, 8.952  Melide ~45.958, 8.949
        d = haversine_distance(46.003, 8.952, 45.958, 8.949)
        assert 2.5 < d < 3.5  # approximately 3 NM

    def test_short_distance(self):
        """Two points ~0.4 NM apart (windward mark)."""
        # Start: 46.0000, Windward: 46.0065 (≈0.39 NM north)
        d = haversine_distance(46.0, 8.963, 46.0065, 8.963)
        assert 0.3 < d < 0.5

    def test_symmetry(self):
        """Distance A→B == distance B→A."""
        d1 = haversine_distance(46.0, 8.96, 46.01, 8.97)
        d2 = haversine_distance(46.01, 8.97, 46.0, 8.96)
        assert d1 == pytest.approx(d2, abs=0.001)


class TestBearing:
    def test_due_north(self):
        """Point due north → bearing ≈ 0°."""
        b = bearing_to(46.0, 8.96, 46.1, 8.96)
        assert b == pytest.approx(0, abs=1)

    def test_due_east(self):
        """Point due east → bearing ≈ 90°."""
        b = bearing_to(46.0, 8.96, 46.0, 9.06)
        assert b == pytest.approx(90, abs=2)

    def test_due_south(self):
        """Point due south → bearing ≈ 180°."""
        b = bearing_to(46.0, 8.96, 45.9, 8.96)
        assert b == pytest.approx(180, abs=1)

    def test_due_west(self):
        """Point due west → bearing ≈ 270°."""
        b = bearing_to(46.0, 8.96, 46.0, 8.86)
        assert b == pytest.approx(270, abs=2)

    def test_bearing_range(self):
        """Bearing is always 0–360."""
        b = bearing_to(46.0, 8.96, 45.99, 8.95)
        assert 0 <= b < 360


class TestComputeNavigation:
    def test_sets_btw_dtw(self):
        """compute_navigation populates BTW and DTW on state."""
        s = BoatState.new()
        s.lat = 46.0
        s.lon = 8.963
        compute_navigation(s, 46.0065, 8.963, "Windward")
        assert s.btw_deg is not None
        assert s.dtw_nm is not None
        assert s.next_mark_name == "Windward"
        assert s.btw_deg == pytest.approx(0, abs=2)  # ~north
        assert 0.3 < s.dtw_nm < 0.5

    def test_no_gps(self):
        """Without GPS fix, BTW/DTW are None."""
        s = BoatState.new()
        compute_navigation(s, 46.0065, 8.963, "Windward")
        assert s.btw_deg is None
        assert s.dtw_nm is None
        assert s.next_mark_name == "Windward"

    def test_mark_name_set(self):
        """Mark name is always set, even without GPS."""
        s = BoatState.new()
        compute_navigation(s, 46.0, 8.96, "Pin End")
        assert s.next_mark_name == "Pin End"
