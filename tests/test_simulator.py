"""Tests for the NMEA simulator source."""

import asyncio

import pytest

from aquarela.nmea.pgn_decoder import decode_pgn
from aquarela.nmea.source_simulator import (
    SimulatorScenario,
    SimulatorSource,
    LUGANO_TRAINING_SESSION,
    _polar_speed,
    _true_to_apparent,
    _interp_heading,
)


class TestPolarSpeed:
    def test_upwind(self):
        """Close-hauled at 42° in 10 kt should give ~7 kt."""
        bsp = _polar_speed(42, 10)
        assert 4.0 < bsp < 9.0

    def test_dead_downwind(self):
        """170° is slow zone."""
        bsp = _polar_speed(170, 10)
        assert bsp < _polar_speed(90, 10)

    def test_beam_reach_fastest(self):
        """Beam reach should be near peak speed."""
        bsp_beam = _polar_speed(90, 10)
        bsp_upwind = _polar_speed(42, 10)
        assert bsp_beam > bsp_upwind

    def test_zero_twa(self):
        """Very low TWA = very slow."""
        bsp = _polar_speed(10, 10)
        assert bsp < 5.0

    def test_speed_capped(self):
        """Speed capped at 12 kt even in strong wind."""
        bsp = _polar_speed(90, 30)
        assert bsp <= 12.0

    def test_symmetric(self):
        """Port/starboard TWA should give same speed."""
        assert _polar_speed(42, 10) == _polar_speed(-42, 10)


class TestTrueToApparent:
    def test_round_trip_basic(self):
        """Reverse wind triangle should give valid AWA/AWS."""
        awa, aws = _true_to_apparent(42.0, 10.0, 5.0)
        # Apparent wind should be tighter than true upwind
        assert abs(awa) < 42.0
        assert aws > 10.0  # AWS > TWS upwind

    def test_zero_bsp(self):
        """At rest: AWA=TWA, AWS=TWS."""
        awa, aws = _true_to_apparent(90.0, 10.0, 0.0)
        assert abs(awa - 90.0) < 0.1
        assert abs(aws - 10.0) < 0.1


class TestInterpHeading:
    def test_no_change(self):
        assert abs(_interp_heading(180, 180, 0.5) - 180.0) < 0.1

    def test_start_end(self):
        assert abs(_interp_heading(100, 200, 0.0) - 100.0) < 0.1
        assert abs(_interp_heading(100, 200, 1.0) - 200.0) < 0.1

    def test_wrap_positive(self):
        """350° → 10° should cross through 0, not 180."""
        mid = _interp_heading(350, 10, 0.5)
        assert mid > 350 or mid < 20  # Should be near 0

    def test_smoothstep_midpoint(self):
        """Smoothstep at t=0.5 → exactly midpoint."""
        result = _interp_heading(100, 200, 0.5)
        assert abs(result - 150.0) < 0.1


class TestSimulatorSource:
    @pytest.mark.asyncio
    async def test_generates_frames(self):
        """Simulator should yield PGN frames."""
        short_scenario = [
            SimulatorScenario("test", 0.5, 42, 10, 180, 180, 0.9),
        ]
        src = SimulatorSource(hz=10, scenarios=short_scenario, loop=False)
        await src.start()

        frames = []
        async for pgn, data in src.stream():
            frames.append((pgn, data))
            if len(frames) > 50:
                break

        await src.stop()
        assert len(frames) > 0

    @pytest.mark.asyncio
    async def test_frames_decode_valid(self):
        """All simulator frames should decode to valid values."""
        short_scenario = [
            SimulatorScenario("test", 0.3, 42, 10, 180, 180, 0.9),
        ]
        src = SimulatorSource(hz=10, scenarios=short_scenario, loop=False)
        await src.start()

        decoded_any = False
        async for pgn, data in src.stream():
            result = decode_pgn(pgn, data)
            if result:
                decoded_any = True
                # Check all values are reasonable
                for key, value in result.items():
                    if isinstance(value, float):
                        assert not (value != value), f"NaN in {key}"  # NaN check

        await src.stop()
        assert decoded_any

    @pytest.mark.asyncio
    async def test_stop_halts_stream(self):
        """Stopping the source should end the stream."""
        src = SimulatorSource(hz=10, loop=True)
        await src.start()

        count = 0
        async for pgn, data in src.stream():
            count += 1
            if count >= 20:
                await src.stop()

        assert count >= 20


class TestLuganoSession:
    def test_session_has_scenarios(self):
        assert len(LUGANO_TRAINING_SESSION) > 5

    def test_total_duration(self):
        total = sum(s.duration_s for s in LUGANO_TRAINING_SESSION)
        assert total > 300  # At least 5 minutes

    def test_includes_tack(self):
        names = [s.name for s in LUGANO_TRAINING_SESSION]
        assert any("tack" in n for n in names)

    def test_includes_gybe(self):
        names = [s.name for s in LUGANO_TRAINING_SESSION]
        assert any("gybe" in n for n in names)
