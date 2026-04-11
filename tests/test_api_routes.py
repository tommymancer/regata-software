"""Tests for API route modules (unit-level, no running server)."""

import pytest

from aquarela.race.marks import Mark, MarkStore
from aquarela.race.course_setup import CourseSetupManager


class TestMarkStoreCourseSequence:
    """Test mark store course sequence and leg advancement."""

    def test_set_course_sequence(self):
        ms = MarkStore()
        ms.add_mark(Mark("WM", 46.01, 8.97, "windward"))
        ms.add_mark(Mark("LM", 45.99, 8.96, "leeward"))
        ms.set_course_sequence(["WM", "LM", "WM"])
        assert ms.course_leg == 0
        assert ms.course_total_legs == 3

    def test_next_mark_advances_leg(self):
        ms = MarkStore()
        ms.add_mark(Mark("WM", 46.01, 8.97, "windward"))
        ms.add_mark(Mark("LM", 45.99, 8.96, "leeward"))
        ms.set_course_sequence(["WM", "LM", "WM"])

        # First call goes from index -1 to 0 (WM)
        m0 = ms.next_mark()
        assert m0 is not None
        assert m0.name == "WM"
        assert ms.course_leg == 1

        # Second call advances to index 1 (LM)
        m1 = ms.next_mark()
        assert m1 is not None
        assert m1.name == "LM"
        assert ms.course_leg == 2

    def test_next_mark_at_end_clamps(self):
        ms = MarkStore()
        ms.add_mark(Mark("WM", 46.01, 8.97, "windward"))
        ms.set_course_sequence(["WM"])
        # First call goes to index 0 (WM)
        m = ms.next_mark()
        assert m is not None
        assert m.name == "WM"
        # Second call stays clamped at index 0
        m2 = ms.next_mark()
        assert m2 is not None  # clamps, doesn't return None

    def test_next_mark_no_sequence(self):
        ms = MarkStore()
        assert ms.next_mark() is None

    def test_active_mark_after_next(self):
        ms = MarkStore()
        ms.add_mark(Mark("WM", 46.01, 8.97, "windward"))
        ms.add_mark(Mark("LM", 45.99, 8.96, "leeward"))
        ms.set_course_sequence(["WM", "LM"])
        # No active mark until next_mark() is called
        assert ms.active_mark is None
        ms.next_mark()
        assert ms.active_mark is not None
        assert ms.active_mark.name == "WM"


class TestInteractiveSourceAPI:
    """Test that InteractiveSource methods work correctly."""

    def test_set_heading_absolute(self):
        from aquarela.nmea.source_interactive import InteractiveSource
        src = InteractiveSource(hz=10, twd=180, tws=10)
        hdg = src.set_heading(heading=90.0)
        assert hdg == pytest.approx(90.0)

    def test_set_heading_delta(self):
        from aquarela.nmea.source_interactive import InteractiveSource
        src = InteractiveSource(hz=10, twd=180, tws=10)
        initial = src.heading
        hdg = src.set_heading(delta=10.0)
        assert hdg == pytest.approx(initial + 10.0)

    def test_set_heading_wraps(self):
        from aquarela.nmea.source_interactive import InteractiveSource
        src = InteractiveSource(hz=10, twd=180, tws=10)
        src.set_heading(heading=355.0)
        hdg = src.set_heading(delta=10.0)
        assert hdg == pytest.approx(5.0)

    def test_set_wind(self):
        from aquarela.nmea.source_interactive import InteractiveSource
        src = InteractiveSource(hz=10, twd=180, tws=10)
        result = src.set_wind(twd=200.0, tws=15.0)
        assert result["twd"] == pytest.approx(200.0)
        assert result["tws"] == pytest.approx(15.0)

    def test_set_wind_delta(self):
        from aquarela.nmea.source_interactive import InteractiveSource
        src = InteractiveSource(hz=10, twd=180, tws=10)
        result = src.set_wind(twd_delta=10.0, tws_delta=2.0)
        assert result["twd"] == pytest.approx(190.0)
        assert result["tws"] == pytest.approx(12.0)

    def test_set_position(self):
        from aquarela.nmea.source_interactive import InteractiveSource
        src = InteractiveSource(hz=10, twd=180, tws=10)
        result = src.set_position(lat=46.1, lon=9.0)
        assert src.lat == pytest.approx(46.1)
        assert src.lon == pytest.approx(9.0)
