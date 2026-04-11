"""Tests for wind correction functions (heel geometry + upwash)."""

import math

import pytest

from aquarela.pipeline.state import BoatState
from aquarela.pipeline.upwash_table import UpwashTable
from aquarela.pipeline.wind_correction import (
    apply_wind_correction,
    correct_heel,
    correct_upwash,
)


# ── Heel correction tests ───────────────────────────────────────────


class TestCorrectHeel:
    def test_zero_heel_no_change(self):
        """Zero heel should return the original AWA and AWS."""
        awa, aws = correct_heel(45.0, 10.0, 0.0)
        assert abs(awa - 45.0) < 0.01
        assert abs(aws - 10.0) < 0.01

    def test_heel_opens_angle(self):
        """Heel should increase the absolute apparent wind angle."""
        awa_orig = 30.0
        awa_corr, _ = correct_heel(awa_orig, 10.0, 20.0)
        assert abs(awa_corr) > abs(awa_orig)

    def test_heel_reduces_speed(self):
        """Heel should reduce apparent wind speed (non-beam angles)."""
        _, aws_orig = correct_heel(45.0, 10.0, 0.0)
        _, aws_heel = correct_heel(45.0, 10.0, 20.0)
        assert aws_heel < aws_orig

    def test_beam_wind_no_speed_change(self):
        """At AWA=90 (beam), heel should not change speed."""
        _, aws_0 = correct_heel(90.0, 10.0, 0.0)
        _, aws_20 = correct_heel(90.0, 10.0, 20.0)
        assert abs(aws_0 - aws_20) < 0.01

    def test_known_geometry(self):
        """AWA=45, heel=20 should give approximately 46.76 degrees."""
        awa_corr, _ = correct_heel(45.0, 10.0, 20.0)
        assert abs(awa_corr - 46.76) < 0.1

    def test_negative_awa_preserved(self):
        """Negative AWA (port) should remain negative after correction."""
        awa_corr, _ = correct_heel(-30.0, 10.0, 15.0)
        assert awa_corr < 0


# ── Upwash correction tests ─────────────────────────────────────────


class TestCorrectUpwash:
    @pytest.fixture()
    def table(self):
        return UpwashTable.with_initial_values()

    def test_starboard_adds_to_awa(self, table):
        """Positive AWA (starboard) — upwash offset should increase AWA."""
        awa_corr, offset = correct_upwash(30.0, table, 10.0)
        assert offset > 0
        assert awa_corr > 30.0

    def test_port_makes_more_negative(self, table):
        """Negative AWA (port) — upwash should make AWA more negative."""
        awa_corr, offset = correct_upwash(-30.0, table, 10.0)
        assert offset > 0
        assert awa_corr < -30.0

    def test_zero_at_180(self, table):
        """At dead downwind (AWA=180), upwash should be zero."""
        _, offset = correct_upwash(180.0, table, 0.0)
        assert abs(offset) < 0.01


# ── Full-chain tests ────────────────────────────────────────────────


class TestApplyWindCorrection:
    @pytest.fixture()
    def table(self):
        return UpwashTable.with_initial_values()

    def test_populates_all_corrected_fields(self, table):
        s = BoatState.new()
        s.awa_deg = 40.0
        s.aws_kt = 12.0
        s.heel_deg = 15.0

        apply_wind_correction(s, table=table)

        assert s.awa_corrected_deg is not None
        assert s.aws_corrected_kt is not None
        assert s.heel_correction_deg is not None
        assert s.upwash_offset_deg is not None

    def test_missing_awa_graceful(self, table):
        """If AWA is None, correction should be a no-op."""
        s = BoatState.new()
        s.awa_deg = None
        s.aws_kt = 10.0

        apply_wind_correction(s, table=table)

        assert s.awa_corrected_deg is None
        assert s.aws_corrected_kt is None

    def test_missing_aws_graceful(self, table):
        """If AWS is None, correction should be a no-op."""
        s = BoatState.new()
        s.awa_deg = 30.0
        s.aws_kt = None

        apply_wind_correction(s, table=table)

        assert s.awa_corrected_deg is None

    def test_no_table_heel_only(self):
        """Without upwash table, only heel correction is applied."""
        s = BoatState.new()
        s.awa_deg = 40.0
        s.aws_kt = 12.0
        s.heel_deg = 15.0

        apply_wind_correction(s, table=None)

        assert s.awa_corrected_deg is not None
        assert s.upwash_offset_deg == 0.0
        # heel correction should have been applied
        assert s.heel_correction_deg != 0.0

    def test_small_heel_skipped(self):
        """Heel < 0.5 deg should skip heel correction."""
        s = BoatState.new()
        s.awa_deg = 40.0
        s.aws_kt = 12.0
        s.heel_deg = 0.3

        apply_wind_correction(s, table=None)

        assert s.heel_correction_deg == 0.0
        assert s.awa_corrected_deg == 40.0
        assert s.aws_corrected_kt == 12.0

    def test_heel_smoothed_override(self, table):
        """heel_smoothed parameter should override state.heel_deg."""
        s = BoatState.new()
        s.awa_deg = 40.0
        s.aws_kt = 12.0
        s.heel_deg = 0.0  # would skip heel correction

        apply_wind_correction(s, table=table, heel_smoothed=20.0)

        # heel correction should have been applied (heel_smoothed=20)
        assert s.heel_correction_deg != 0.0
