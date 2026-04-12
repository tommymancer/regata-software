"""Tests for the calibration pipeline."""

import pytest
from datetime import datetime, timezone

from aquarela.config import AquarelaConfig
from aquarela.pipeline.state import BoatState
from aquarela.pipeline.calibration import apply_calibration


@pytest.fixture
def default_config():
    return AquarelaConfig()


@pytest.fixture
def state_with_raw_data():
    s = BoatState.new()
    s.raw_heading_mag = 222.0
    s.raw_bsp_kt = 5.5
    s.raw_awa_deg = -42.0
    s.raw_aws_kt = 12.0
    s.raw_depth_m = 15.0
    s.raw_water_temp_c = 12.5
    s.raw_sog_kt = 5.3
    s.raw_cog_deg = 220.0
    return s


class TestCalibrationPassThrough:
    """With default config (zero offsets, factor=1), calibrated = raw."""

    def test_heading_no_offset(self, state_with_raw_data, default_config):
        apply_calibration(state_with_raw_data, default_config)
        assert state_with_raw_data.heading_mag == 222.0

    def test_bsp_no_factor(self, state_with_raw_data, default_config):
        apply_calibration(state_with_raw_data, default_config)
        assert state_with_raw_data.bsp_kt == 5.5

    def test_awa_no_offset(self, state_with_raw_data, default_config):
        apply_calibration(state_with_raw_data, default_config)
        assert state_with_raw_data.awa_deg == -42.0

    def test_depth_with_waterline_offset(self, state_with_raw_data, default_config):
        """Default depth_offset is +0.30 (transducer 30cm below waterline)."""
        apply_calibration(state_with_raw_data, default_config)
        assert abs(state_with_raw_data.depth_m - (15.0 + 0.30)) < 0.01

    def test_sog_pass_through(self, state_with_raw_data, default_config):
        apply_calibration(state_with_raw_data, default_config)
        assert state_with_raw_data.sog_kt == 5.3


class TestCalibrationWithOffsets:
    def test_compass_offset(self, state_with_raw_data):
        cfg = AquarelaConfig(compass_offset=3.0)
        apply_calibration(state_with_raw_data, cfg)
        assert abs(state_with_raw_data.heading_mag - 219.0) < 0.01

    def test_compass_wraps_360(self):
        s = BoatState.new()
        s.raw_heading_mag = 1.0
        cfg = AquarelaConfig(compass_offset=5.0)
        apply_calibration(s, cfg)
        assert abs(s.heading_mag - 356.0) < 0.01

    def test_speed_factor(self, state_with_raw_data):
        cfg = AquarelaConfig(speed_factor=1.05)
        apply_calibration(state_with_raw_data, cfg)
        assert abs(state_with_raw_data.bsp_kt - (5.5 * 1.05)) < 0.01

    def test_awa_offset(self, state_with_raw_data):
        cfg = AquarelaConfig(awa_offset=2.0)
        apply_calibration(state_with_raw_data, cfg)
        assert abs(state_with_raw_data.awa_deg - (-44.0)) < 0.01

    def test_awa_wraps_signed(self):
        """AWA stays in -180..+180 range."""
        s = BoatState.new()
        s.raw_awa_deg = -178.0
        cfg = AquarelaConfig(awa_offset=5.0)
        apply_calibration(s, cfg)
        assert -180 < s.awa_deg <= 180

    def test_depth_offset_custom(self, state_with_raw_data):
        cfg = AquarelaConfig(depth_offset=-2.0)
        apply_calibration(state_with_raw_data, cfg)
        assert abs(state_with_raw_data.depth_m - 13.0) < 0.01

    def test_depth_floor_zero(self):
        """Depth can't go negative."""
        s = BoatState.new()
        s.raw_depth_m = 1.0
        cfg = AquarelaConfig(depth_offset=-5.0)
        apply_calibration(s, cfg)
        assert s.depth_m == 0.0


class TestCalibrationNoneHandling:
    def test_missing_heading(self, default_config):
        s = BoatState.new()
        apply_calibration(s, default_config)
        assert s.heading_mag is None

    def test_missing_bsp(self, default_config):
        s = BoatState.new()
        apply_calibration(s, default_config)
        assert s.bsp_kt is None

    def test_partial_data(self, default_config):
        """Only BSP present — heading stays None."""
        s = BoatState.new()
        s.raw_bsp_kt = 4.0
        apply_calibration(s, default_config)
        assert s.bsp_kt == 4.0
        assert s.heading_mag is None
