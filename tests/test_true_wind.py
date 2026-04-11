"""Tests for true wind calculation — known vectors and edge cases."""

import math

import pytest

from aquarela.pipeline.state import BoatState
from aquarela.pipeline.true_wind import calc_true_wind, calc_twd, compute_true_wind


class TestCalcTrueWind:
    def test_head_to_wind(self):
        """Boat sailing directly into wind: AWA=0, AWS>BSP → TWA≈0, TWS=AWS-BSP."""
        twa, tws = calc_true_wind(bsp_kt=5.0, awa_deg=0.0, aws_kt=15.0)
        assert abs(twa) < 1.0
        assert abs(tws - 10.0) < 0.1

    def test_downwind_run(self):
        """Boat running dead downwind: AWA=180, AWS < TWS."""
        twa, tws = calc_true_wind(bsp_kt=5.0, awa_deg=180.0, aws_kt=5.0)
        assert abs(twa - 180.0) < 1.0 or abs(twa + 180.0) < 1.0
        assert tws > 5.0  # TWS > AWS when running

    def test_starboard_upwind(self):
        """Typical close-hauled starboard: AWA~30°, expect TWA > AWA."""
        twa, tws = calc_true_wind(bsp_kt=5.5, awa_deg=30.0, aws_kt=14.0)
        assert twa > 30.0  # True wind always wider than apparent upwind
        assert tws < 14.0  # TWS < AWS upwind

    def test_port_upwind(self):
        """Mirror of starboard: AWA = -30°."""
        twa, tws = calc_true_wind(bsp_kt=5.5, awa_deg=-30.0, aws_kt=14.0)
        assert twa < -30.0  # Negative, wider angle
        assert tws < 14.0

    def test_zero_bsp(self):
        """Anchored: TWA=AWA, TWS=AWS."""
        twa, tws = calc_true_wind(bsp_kt=0.0, awa_deg=45.0, aws_kt=10.0)
        assert abs(twa - 45.0) < 0.1
        assert abs(tws - 10.0) < 0.1

    def test_beam_reach(self):
        """Beam reach: AWA~90°."""
        twa, tws = calc_true_wind(bsp_kt=6.0, awa_deg=90.0, aws_kt=10.0)
        assert 90 < twa < 180  # TWA > AWA on a reach

    def test_symmetry(self):
        """Port/starboard should produce mirror results."""
        twa_s, tws_s = calc_true_wind(5.0, 42.0, 12.0)
        twa_p, tws_p = calc_true_wind(5.0, -42.0, 12.0)
        assert abs(twa_s + twa_p) < 0.01  # Mirror angles
        assert abs(tws_s - tws_p) < 0.01  # Same speed


class TestCalcTWD:
    def test_basic_twd(self):
        """Heading 0° true + TWA 180° → TWD = 180°."""
        twd = calc_twd(180.0, heading_mag=2.5, mag_var=2.5)
        assert abs(twd - 180.0) < 0.1

    def test_twd_wrapping(self):
        """TWD should wrap to 0-360."""
        twd = calc_twd(-30.0, heading_mag=10.0, mag_var=2.5)
        assert 0 <= twd < 360

    def test_southerly_breva(self):
        """Lake Lugano Breva: heading ~220° mag, TWA ~-42° → TWD ~180°."""
        twd = calc_twd(-42.0, heading_mag=222.0, mag_var=2.5)
        # heading_true = 222 - 2.5 = 219.5, twd = 219.5 - 42 = 177.5
        assert abs(twd - 177.5) < 0.5


class TestComputeTrueWind:
    def test_full_pipeline(self):
        s = BoatState.new()
        s.bsp_kt = 5.5
        s.awa_deg = -42.0
        s.aws_kt = 12.0
        s.heading_mag = 222.0
        s.magnetic_variation = 2.5
        compute_true_wind(s)
        assert s.twa_deg is not None
        assert s.tws_kt is not None
        assert s.twd_deg is not None
        assert s.twa_deg < -42.0  # TWA wider than AWA upwind
        assert 0 <= s.twd_deg < 360

    def test_missing_bsp(self):
        s = BoatState.new()
        s.awa_deg = 30.0
        s.aws_kt = 10.0
        compute_true_wind(s)
        assert s.twa_deg is None

    def test_missing_heading_no_twd(self):
        """TWA/TWS computed but TWD needs heading."""
        s = BoatState.new()
        s.bsp_kt = 5.0
        s.awa_deg = 30.0
        s.aws_kt = 10.0
        compute_true_wind(s)
        assert s.twa_deg is not None
        assert s.twd_deg is None  # no heading → no TWD


class TestCorrectedValueRouting:
    def test_uses_corrected_when_available(self):
        """compute_true_wind uses awa_corrected_deg and aws_corrected_kt."""
        s = BoatState.new()
        s.bsp_kt = 6.0
        s.awa_deg = -30.0
        s.aws_kt = 15.0
        s.awa_corrected_deg = -33.0  # more open after correction
        s.aws_corrected_kt = 14.5
        s.heading_mag = 180.0
        s.magnetic_variation = 2.5

        compute_true_wind(s)

        # TWA should be computed from corrected values
        twa_expected, _ = calc_true_wind(6.0, -33.0, 14.5)
        assert s.twa_deg == pytest.approx(twa_expected, abs=0.01)

    def test_falls_back_to_uncorrected(self):
        """When corrected fields are None, uses awa_deg/aws_kt."""
        s = BoatState.new()
        s.bsp_kt = 6.0
        s.awa_deg = -30.0
        s.aws_kt = 15.0
        s.heading_mag = 180.0
        s.magnetic_variation = 2.5

        compute_true_wind(s)

        twa_expected, _ = calc_true_wind(6.0, -30.0, 15.0)
        assert s.twa_deg == pytest.approx(twa_expected, abs=0.01)

    def test_partial_correction_awa_only(self):
        """If only awa_corrected is set, aws falls back to aws_kt."""
        s = BoatState.new()
        s.bsp_kt = 6.0
        s.awa_deg = -30.0
        s.aws_kt = 15.0
        s.awa_corrected_deg = -33.0
        # aws_corrected_kt is None

        compute_true_wind(s)

        twa_expected, _ = calc_true_wind(6.0, -33.0, 15.0)
        assert s.twa_deg == pytest.approx(twa_expected, abs=0.01)
