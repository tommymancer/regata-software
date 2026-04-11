"""Tests for auto-generated race course."""

import pytest

from aquarela.race.course_generator import CourseSetup, generate_course


class TestCourseGeneration:
    """Core course geometry tests."""

    def test_generates_valid_course(self):
        cs = generate_course(twd=180, start_lat=46.0, start_lon=8.963)
        assert isinstance(cs, CourseSetup)
        assert cs.twd == 180

    def test_line_perpendicular_to_wind(self):
        """RC-Pin line should be roughly perpendicular to TWD."""
        cs = generate_course(twd=180, start_lat=46.0, start_lon=8.963)
        # Wind from south: line bearing = 270° (west).
        # RC is offset along 270° (west), Pin along 90° (east).
        assert cs.rc_lon < cs.pin_lon
        # Both should be at roughly same latitude
        assert abs(cs.rc_lat - cs.pin_lat) < 0.001

    def test_windward_mark_upwind(self):
        """Windward mark should be upwind (toward wind source)."""
        cs = generate_course(twd=0, start_lat=46.0, start_lon=8.963)
        # Wind from north (0°), so windward mark is north of start
        assert cs.windward_lat > 46.0

    def test_windward_mark_south_wind(self):
        """With wind from south, windward mark should be to the south."""
        cs = generate_course(twd=180, start_lat=46.0, start_lon=8.963)
        assert cs.windward_lat < 46.0

    def test_line_length_parameter(self):
        """Custom line length should affect RC-Pin separation."""
        short = generate_course(twd=180, start_lat=46.0, start_lon=8.963, line_length_m=100)
        long = generate_course(twd=180, start_lat=46.0, start_lon=8.963, line_length_m=300)
        short_dist = abs(short.rc_lon - short.pin_lon)
        long_dist = abs(long.rc_lon - long.pin_lon)
        assert long_dist > short_dist * 2.5

    def test_leg_length_parameter(self):
        """Custom leg length should affect windward mark distance."""
        short = generate_course(twd=180, start_lat=46.0, start_lon=8.963, leg_length_m=400)
        long = generate_course(twd=180, start_lat=46.0, start_lon=8.963, leg_length_m=1200)
        short_d = abs(short.windward_lat - 46.0)
        long_d = abs(long.windward_lat - 46.0)
        assert long_d > short_d * 2.5

    def test_to_dict_structure(self):
        cs = generate_course(twd=180, start_lat=46.0, start_lon=8.963)
        d = cs.to_dict()
        assert "rc" in d and "pin" in d and "windward" in d
        assert d["twd"] == 180
        assert "lat" in d["rc"] and "lon" in d["rc"]

    def test_various_wind_directions(self):
        """Course should generate for any wind direction."""
        for twd in [0, 45, 90, 135, 180, 225, 270, 315, 359]:
            cs = generate_course(twd=twd, start_lat=46.0, start_lon=8.963)
            assert cs is not None
            assert cs.twd == twd
