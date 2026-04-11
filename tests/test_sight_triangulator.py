"""Tests for sight-mark triangulation."""

import math

import pytest

from aquarela.race.sight_triangulator import SightTriangulator


class TestSightTriangulator:
    def test_empty_has_no_mark(self):
        tri = SightTriangulator()
        assert tri.computed_mark() is None
        assert tri.count == 0

    def test_single_sighting_no_triangulation(self):
        tri = SightTriangulator()
        tri.add_sighting(46.0, 8.963, 0.0)
        assert tri.computed_mark() is None
        assert tri.count == 1

    def test_two_sightings_computes_mark(self):
        """Two sightings from different positions with good geometry."""
        tri = SightTriangulator()
        # SW observer looks north (0°), NE observer looks east (90°)
        # ~600m apart with 90° angle difference — reliable geometry
        tri.add_sighting(45.998, 8.960, 0.0)
        tri.add_sighting(46.002, 8.966, 90.0)
        mark = tri.computed_mark()
        assert mark is not None
        assert mark["lat"] > 46.0

    def test_parallel_bearings_returns_none(self):
        """Nearly parallel bearings should not triangulate."""
        tri = SightTriangulator()
        tri.add_sighting(46.0, 8.960, 0.0)
        tri.add_sighting(46.0, 8.966, 2.0)  # nearly parallel
        assert tri.computed_mark() is None

    def test_sightings_too_close_returns_none(self):
        """Sightings from very close positions should fail."""
        tri = SightTriangulator()
        tri.add_sighting(46.0, 8.963, 10.0)
        tri.add_sighting(46.0, 8.96301, 350.0)  # tiny baseline
        assert tri.computed_mark() is None

    def test_reset_clears_state(self):
        tri = SightTriangulator()
        tri.add_sighting(46.0, 8.960, 10.0)
        tri.add_sighting(46.0, 8.966, 350.0)
        assert tri.count == 2
        tri.reset()
        assert tri.count == 0
        assert tri.computed_mark() is None

    def test_get_sightings_returns_dicts(self):
        tri = SightTriangulator()
        tri.add_sighting(46.0, 8.960, 10.0)
        sightings = tri.get_sightings()
        assert len(sightings) == 1
        assert "lat" in sightings[0]
        assert "bearing" in sightings[0]

    def test_bearing_wraps(self):
        """Bearing of 361 should wrap to 1."""
        tri = SightTriangulator()
        tri.add_sighting(46.0, 8.960, 361.0)
        sightings = tri.get_sightings()
        assert sightings[0]["bearing"] == pytest.approx(1.0)


class TestCourseSetupManager:
    """Tests for the pre-race buoy mapping manager."""

    def test_add_and_get_mark(self):
        from aquarela.race.course_setup import CourseSetupManager

        mgr = CourseSetupManager()
        m = mgr.add_mark("Windward", "windward")
        assert m.name == "Windward"
        assert m.mark_type == "windward"
        assert not m.is_resolved

    def test_log_gps_resolves_mark(self):
        from aquarela.race.course_setup import CourseSetupManager

        mgr = CourseSetupManager()
        mgr.add_mark("WM")
        result = mgr.log_gps("WM", 46.01, 8.97)
        assert result["method"] == "gps"
        m = mgr.get_mark("WM")
        assert m.is_resolved
        assert m.lat == 46.01

    def test_remove_mark(self):
        from aquarela.race.course_setup import CourseSetupManager

        mgr = CourseSetupManager()
        mgr.add_mark("WM")
        assert mgr.remove_mark("WM")
        assert not mgr.remove_mark("WM")

    def test_reset_mark_clears_position(self):
        from aquarela.race.course_setup import CourseSetupManager

        mgr = CourseSetupManager()
        mgr.add_mark("WM")
        mgr.log_gps("WM", 46.01, 8.97)
        assert mgr.get_mark("WM").is_resolved
        mgr.reset_mark("WM")
        assert not mgr.get_mark("WM").is_resolved

    def test_set_sequence(self):
        from aquarela.race.course_setup import CourseSetupManager

        mgr = CourseSetupManager()
        seq = mgr.set_sequence(["WM", "LM", "WM"])
        assert seq == ["WM", "LM", "WM"]
        assert mgr.sequence == ["WM", "LM", "WM"]

    def test_status(self):
        from aquarela.race.course_setup import CourseSetupManager

        mgr = CourseSetupManager()
        mgr.add_mark("WM")
        mgr.add_mark("LM")
        mgr.log_gps("WM", 46.01, 8.97)
        status = mgr.status()
        assert status["total"] == 2
        assert status["resolved"] == 1
        assert not status["ready"]  # not all resolved

    def test_apply_pushes_to_mark_store(self):
        from aquarela.race.course_setup import CourseSetupManager
        from aquarela.race.marks import MarkStore

        mgr = CourseSetupManager()
        ms = MarkStore()

        mgr.add_mark("WM", "windward")
        mgr.log_gps("WM", 46.01, 8.97)
        mgr.add_mark("RC", "start_rc")
        mgr.log_gps("RC", 46.0, 8.960)
        mgr.set_sequence(["WM"])

        result = mgr.apply(ms)
        assert result["total"] == 2
        assert result["rc"] is not None
        assert result["rc"]["lat"] == 46.0
        assert ms.get("WM") is not None

    def test_set_mark_type(self):
        from aquarela.race.course_setup import CourseSetupManager

        mgr = CourseSetupManager()
        mgr.add_mark("M1")
        assert mgr.set_mark_type("M1", "windward")
        assert mgr.get_mark("M1").mark_type == "windward"
        assert not mgr.set_mark_type("nonexistent", "windward")
