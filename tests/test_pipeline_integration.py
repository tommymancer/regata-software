"""Integration test: full pipeline from raw sensor data to computed state."""

import pytest

from aquarela.config import AquarelaConfig
from aquarela.performance.polar import PolarTable
from aquarela.performance.targets import compute_targets
from aquarela.pipeline.calibration import apply_calibration
from aquarela.pipeline.damping import DampingFilters
from aquarela.pipeline.derived import compute_derived
from aquarela.pipeline.state import BoatState
from aquarela.pipeline.true_wind import compute_true_wind
from aquarela.pipeline.wind_correction import apply_wind_correction
from aquarela.pipeline.upwash_table import UpwashTable


class TestPipelineIntegration:
    """Run the full pipeline on synthetic sensor data."""

    @pytest.fixture
    def config(self):
        return AquarelaConfig(
            compass_offset=0.0,
            speed_factor=1.0,
            awa_offset=0.0,
            magnetic_variation=2.5,
        )

    @pytest.fixture
    def damping(self, config):
        return DampingFilters(windows=config.damping, hz=config.sample_rate_hz)

    @pytest.fixture
    def polar(self):
        try:
            return PolarTable.load("data/polars/2025_Polar.json")
        except FileNotFoundError:
            pytest.skip("Polar file not available")

    def _run_pipeline(self, state, config, damping, polar=None):
        """Run one complete pipeline step."""
        apply_calibration(state, config)
        compute_true_wind(state)
        compute_derived(state)
        damping.apply(state)
        if polar is not None:
            compute_targets(state, polar)
        return state

    def test_upwind_close_hauled(self, config, damping, polar):
        """Close-hauled on starboard tack produces valid derived data."""
        state = BoatState.new()
        state.heading_mag = 40.0
        state.awa_deg = -35.0  # apparent wind from port
        state.aws_kt = 14.0
        state.bsp_kt = 5.5
        state.lat = 46.0
        state.lon = 8.963
        state.sog_kt = 5.3
        state.cog_deg = 42.0

        self._run_pipeline(state, config, damping, polar)

        # True wind should be computed
        assert state.tws_kt is not None
        assert state.twd_deg is not None
        assert state.twa_deg is not None

        # TWS should be reasonable (10-18 kt for 14 kt apparent in 5.5 kt BSP)
        assert 8 < state.tws_kt < 20

        # TWA should be negative (port tack) and in upwind range
        assert state.twa_deg < 0
        assert abs(state.twa_deg) < 60

        # VMG should be positive (making headway upwind)
        assert state.vmg_kt is not None
        assert state.vmg_kt > 0

        # Polar targets should be set
        assert state.target_bsp_kt is not None
        assert state.perf_pct is not None

    def test_downwind_run(self, config, damping, polar):
        """Deep downwind run produces valid data."""
        state = BoatState.new()
        state.heading_mag = 180.0
        state.awa_deg = 155.0  # apparent wind from astern starboard
        state.aws_kt = 6.0
        state.bsp_kt = 4.5
        state.lat = 46.0
        state.lon = 8.963
        state.sog_kt = 4.3
        state.cog_deg = 182.0

        self._run_pipeline(state, config, damping, polar)

        assert state.twa_deg is not None
        assert abs(state.twa_deg) > 90  # downwind
        assert state.tws_kt is not None
        assert state.tws_kt > 0

    def test_no_wind_data(self, config, damping):
        """Pipeline should survive with no wind sensor data."""
        state = BoatState.new()
        state.heading_mag = 180.0
        state.bsp_kt = 5.0
        state.lat = 46.0
        state.lon = 8.963

        self._run_pipeline(state, config, damping)

        # True wind not computable without apparent wind
        assert state.tws_kt is None
        assert state.twd_deg is None

    def test_no_speed_data(self, config, damping):
        """Pipeline should survive with no boat speed."""
        state = BoatState.new()
        state.heading_mag = 40.0
        state.awa_deg = -35.0
        state.aws_kt = 14.0

        self._run_pipeline(state, config, damping)

        # Some computed values should still be None
        assert state.vmg_kt is None or state.vmg_kt == 0.0

    def test_damping_smooths_values(self, config):
        """Multiple pipeline steps should produce damped output."""
        damping = DampingFilters(
            windows={"tws_kt": 1.0, "bsp_kt": 0.5},
            hz=10,
        )

        readings = []
        for i in range(20):
            state = BoatState.new()
            state.heading_mag = 40.0
            state.awa_deg = -35.0
            # Oscillating AWS to test damping
            state.aws_kt = 14.0 + (2.0 if i % 2 == 0 else -2.0)
            state.bsp_kt = 5.5
            state.lat = 46.0
            state.lon = 8.963

            self._run_pipeline(state, config, damping)
            if state.tws_kt is not None:
                readings.append(state.tws_kt)

        # Damped values should have less variance than input oscillation
        if len(readings) >= 10:
            later = readings[10:]
            variance = max(later) - min(later)
            assert variance < 4.0  # input has 4kt swing, damped should be less

    def test_calibration_applied(self):
        """Compass offset should shift heading."""
        config = AquarelaConfig(compass_offset=5.0, magnetic_variation=2.5)
        damping = DampingFilters(windows=config.damping, hz=config.sample_rate_hz)

        state = BoatState.new()
        state.raw_heading_mag = 100.0
        state.raw_awa_deg = -35.0
        state.raw_aws_kt = 14.0
        state.raw_bsp_kt = 5.5

        self._run_pipeline(state, config, damping)

        # Heading should be offset: 100 - 5 = 95
        assert state.heading_mag == pytest.approx(95.0)

    def test_multiple_steps_accumulate(self, config, damping, polar):
        """Multiple steps should work without errors."""
        for _ in range(50):
            state = BoatState.new()
            state.heading_mag = 40.0
            state.awa_deg = -35.0
            state.aws_kt = 14.0
            state.bsp_kt = 5.5
            state.lat = 46.0
            state.lon = 8.963
            state.sog_kt = 5.3
            state.cog_deg = 42.0
            self._run_pipeline(state, config, damping, polar)

        # Should complete without exception
        assert state.perf_pct is not None


class TestWindCorrectionIntegration:
    """Integration tests for the wind correction pipeline stage."""

    @pytest.fixture
    def config(self):
        return AquarelaConfig(
            compass_offset=0.0,
            speed_factor=1.0,
            awa_offset=0.0,
            magnetic_variation=2.5,
        )

    @pytest.fixture
    def damping(self, config):
        return DampingFilters(windows=config.damping, hz=config.sample_rate_hz)

    @pytest.fixture
    def upwash_table(self):
        return UpwashTable.with_initial_values()

    def test_pipeline_with_wind_correction(self, config, damping, upwash_table):
        """Full pipeline: raw → calibrate → heel+upwash correct → true wind."""
        state = BoatState.new()
        state.raw_heading_mag = 220.0
        state.raw_awa_deg = -30.0
        state.raw_aws_kt = 15.0
        state.raw_bsp_kt = 6.5
        state.heel_deg = 18.0
        state.lat = 46.0
        state.lon = 8.963
        state.raw_sog_kt = 6.2
        state.raw_cog_deg = 222.0

        # Pipeline stages in order
        apply_calibration(state, config)
        apply_wind_correction(state, upwash_table, heel_smoothed=18.0)
        compute_true_wind(state)
        compute_derived(state)
        damping.apply(state)

        # Wind correction should have produced corrected values
        assert state.awa_corrected_deg is not None
        assert state.aws_corrected_kt is not None

        # Heel correction widens AWA (mast tilted → apparent angle opens)
        assert abs(state.awa_corrected_deg) > abs(state.awa_deg)

        # True wind should be computed from corrected values
        assert state.twa_deg is not None
        assert state.tws_kt is not None
        assert state.twd_deg is not None

        # Upwash offset should be recorded
        assert state.upwash_offset_deg is not None
        assert state.upwash_offset_deg >= 0

        # Heel correction should be recorded
        assert state.heel_correction_deg is not None

    def test_pipeline_without_heel(self, config, damping, upwash_table):
        """Pipeline works when heel data is unavailable."""
        state = BoatState.new()
        state.raw_heading_mag = 220.0
        state.raw_awa_deg = -30.0
        state.raw_aws_kt = 15.0
        state.raw_bsp_kt = 6.5
        # No heel_deg set (None)
        state.lat = 46.0
        state.lon = 8.963

        apply_calibration(state, config)
        apply_wind_correction(state, upwash_table, heel_smoothed=None)
        compute_true_wind(state)
        compute_derived(state)
        damping.apply(state)

        # Corrected values should still exist (upwash applied, heel=0)
        assert state.awa_corrected_deg is not None
        assert state.aws_corrected_kt is not None

        # Heel correction should be zero (no heel data)
        assert state.heel_correction_deg == pytest.approx(0.0)

        # True wind should still be computed
        assert state.twa_deg is not None
        assert state.tws_kt is not None

    def test_pipeline_no_upwash_table(self, config, damping):
        """Pipeline works without an upwash table (table=None)."""
        state = BoatState.new()
        state.raw_heading_mag = 220.0
        state.raw_awa_deg = -30.0
        state.raw_aws_kt = 15.0
        state.raw_bsp_kt = 6.5
        state.heel_deg = 10.0

        apply_calibration(state, config)
        apply_wind_correction(state, table=None, heel_smoothed=10.0)
        compute_true_wind(state)

        # Heel correction applied, but no upwash
        assert state.awa_corrected_deg is not None
        assert state.upwash_offset_deg == pytest.approx(0.0)
        assert state.twa_deg is not None
