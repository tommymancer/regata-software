"""Tests for maneuver detector — tack and gybe detection."""

import math
import time

import pytest
from aquarela.training.maneuvers import ManeuverDetector, ManeuverEvent


class TestManeuverDetector:
    def test_initial_state(self):
        d = ManeuverDetector(hz=10)
        assert d.events == []

    def test_no_detect_on_steady(self):
        """No maneuver detected when sailing steady."""
        d = ManeuverDetector(hz=10)
        for _ in range(100):
            result = d.update(
                heading=45.0, twa=-35.0, bsp=6.0,
                sog=5.8, cog=45.0, brg_to_mark=None,
                lat=46.0, lon=8.9, wall_time="2026-04-04T14:30:00Z",
            )
        assert d.events == []

    def test_heading_delta(self):
        """Static helper for heading difference."""
        assert ManeuverDetector._heading_delta(10.0, 350.0) == pytest.approx(20.0)
        assert ManeuverDetector._heading_delta(180.0, 0.0) == pytest.approx(180.0)
        assert ManeuverDetector._heading_delta(90.0, 90.0) == pytest.approx(0.0)

    def test_detect_tack(self):
        """Detects a tack when HDG changes >60° with TWA sign flip."""
        d = ManeuverDetector(hz=10)
        d.COOLDOWN_SECS = 0  # disable cooldown for testing
        d.METRIC_WINDOW = 0.5

        # Sail on port tack
        for _ in range(20):
            d.update(
                heading=300.0, twa=-35.0, bsp=6.0,
                sog=5.8, cog=300.0, brg_to_mark=None,
                lat=46.0, lon=8.9, wall_time="2026-04-04T14:30:00Z",
            )
            time.sleep(0.01)

        # Simulate tack: heading swings from 300 to 30, TWA flips to +35
        completed = None
        for _ in range(50):
            result = d.update(
                heading=30.0, twa=35.0, bsp=3.0,
                sog=2.8, cog=30.0, brg_to_mark=None,
                lat=46.0, lon=8.9, wall_time="2026-04-04T14:30:00Z",
            )
            if result is not None:
                completed = result
                break
            time.sleep(0.01)

        # May need more samples for recovery tracking
        if completed is None:
            for _ in range(100):
                result = d.update(
                    heading=30.0, twa=35.0, bsp=5.5,
                    sog=5.3, cog=30.0, brg_to_mark=None,
                    lat=46.0, lon=8.9, wall_time="2026-04-04T14:30:00Z",
                )
                if result is not None:
                    completed = result
                    break
                time.sleep(0.01)

        assert completed is not None or len(d.events) > 0
        if completed:
            assert completed.maneuver_type == "tack"
            assert completed.bsp_min <= 6.0

    def test_detect_gybe(self):
        """Detects a gybe when HDG changes >30° while downwind with TWA sign flip."""
        d = ManeuverDetector(hz=10)
        d.COOLDOWN_SECS = 0
        d.METRIC_WINDOW = 0.5

        # Sail downwind on port
        for _ in range(20):
            d.update(
                heading=180.0, twa=-150.0, bsp=7.0,
                sog=6.8, cog=180.0, brg_to_mark=None,
                lat=46.0, lon=8.9, wall_time="2026-04-04T14:30:00Z",
            )
            time.sleep(0.01)

        # Gybe: HDG changes 40°, TWA flips to +150
        completed = None
        for _ in range(50):
            result = d.update(
                heading=220.0, twa=150.0, bsp=5.0,
                sog=4.8, cog=220.0, brg_to_mark=None,
                lat=46.0, lon=8.9, wall_time="2026-04-04T14:30:00Z",
            )
            if result is not None:
                completed = result
                break
            time.sleep(0.01)

        if completed is None:
            for _ in range(100):
                result = d.update(
                    heading=220.0, twa=150.0, bsp=6.8,
                    sog=6.6, cog=220.0, brg_to_mark=None,
                    lat=46.0, lon=8.9, wall_time="2026-04-04T14:30:00Z",
                )
                if result is not None:
                    completed = result
                    break
                time.sleep(0.01)

        assert completed is not None or len(d.events) > 0
        if completed:
            assert completed.maneuver_type == "gybe"

    def test_none_inputs_ignored(self):
        """None sensor values don't crash the detector."""
        d = ManeuverDetector(hz=10)
        result = d.update(None, None, None, None, None, None, None, None, None)
        assert result is None
        result = d.update(45.0, None, 6.0, None, None, None, None, None, None)
        assert result is None

    def test_get_stats_empty(self):
        d = ManeuverDetector(hz=10)
        stats = d.get_stats()
        assert stats["total_tacks"] == 0
        assert stats["total_gybes"] == 0
        assert stats["avg_tack_recovery"] is None

    def test_reset(self):
        d = ManeuverDetector(hz=10)
        d.events.append(ManeuverEvent(maneuver_type="tack", entry_time=0))
        d.reset()
        assert d.events == []

    def test_maneuver_event_to_dict(self):
        ev = ManeuverEvent(
            maneuver_type="tack",
            entry_time=100.0,
            exit_time=103.0,
            wall_time="2026-04-04T14:30:00Z",
            lat=46.0,
            lon=8.9,
            bsp_before=6.0,
            bsp_min=2.5,
            bsp_after=5.5,
            recovery_secs=4.2,
            vmg_before=4.9,
            vmg_loss_nm=0.0015,
            vmc_before=None,
            vmc_loss_nm=None,
            hdg_before=300.0,
            hdg_after=30.0,
        )
        d = ev.to_dict()
        assert d["type"] == "tack"
        assert d["bsp_before"] == 6.0
        assert d["recovery_secs"] == 4.2
        assert d["wall_time"] == "2026-04-04T14:30:00Z"
        assert d["lat"] == 46.0
        assert d["lon"] == 8.9
        assert d["vmg_before"] == pytest.approx(4.9)
        assert d["vmg_loss_nm"] == pytest.approx(0.0015)
        assert d["vmc_before"] is None
        assert d["vmc_loss_nm"] is None
        assert "distance_lost_nm" not in d

    def test_vmg_loss_calculation(self):
        """VMG loss is computed; vmc_loss_nm is None when no mark is active."""
        d = ManeuverDetector(hz=10)
        d.COOLDOWN_SECS = 0
        d.METRIC_WINDOW = 0.5

        # Sail on port tack — upwind, bsp=6, twa=-35
        for _ in range(20):
            d.update(
                heading=300.0, twa=-35.0, bsp=6.0,
                sog=5.8, cog=300.0, brg_to_mark=None,
                lat=46.0, lon=8.9, wall_time="2026-04-04T14:30:00Z",
            )
            time.sleep(0.01)

        # Tack: heading flips, bsp drops
        completed = None
        for _ in range(50):
            result = d.update(
                heading=30.0, twa=35.0, bsp=3.0,
                sog=2.8, cog=30.0, brg_to_mark=None,
                lat=46.0, lon=8.9, wall_time="2026-04-04T14:30:05Z",
            )
            if result is not None:
                completed = result
                break
            time.sleep(0.01)

        if completed is None:
            for _ in range(100):
                result = d.update(
                    heading=30.0, twa=35.0, bsp=5.5,
                    sog=5.3, cog=30.0, brg_to_mark=None,
                    lat=46.0, lon=8.9, wall_time="2026-04-04T14:30:06Z",
                )
                if result is not None:
                    completed = result
                    break
                time.sleep(0.01)

        assert completed is not None or len(d.events) > 0
        ev = completed or d.events[-1]
        assert ev.maneuver_type == "tack"

        # VMG should be computed (pre-samples had upwind data)
        assert ev.vmg_before is not None
        # VMG before should be roughly abs(6.0 * cos(-35°))
        expected_vmg = abs(6.0 * math.cos(math.radians(-35.0)))
        assert ev.vmg_before == pytest.approx(expected_vmg, rel=0.3)

        # vmg_loss_nm should be non-negative
        assert ev.vmg_loss_nm is not None
        assert ev.vmg_loss_nm >= 0.0

        # No mark active — vmc fields should be None
        assert ev.vmc_before is None
        assert ev.vmc_loss_nm is None

    def test_cooldown_prevents_double_detect(self):
        """Cooldown prevents detecting two maneuvers in quick succession."""
        d = ManeuverDetector(hz=10)
        d.COOLDOWN_SECS = 5.0  # 5 second cooldown
        d.METRIC_WINDOW = 0.2

        # First "tack"
        for _ in range(20):
            d.update(
                heading=300.0, twa=-35.0, bsp=6.0,
                sog=5.8, cog=300.0, brg_to_mark=None,
                lat=46.0, lon=8.9, wall_time="2026-04-04T14:30:00Z",
            )
            time.sleep(0.005)

        for _ in range(20):
            d.update(
                heading=30.0, twa=35.0, bsp=3.0,
                sog=2.8, cog=30.0, brg_to_mark=None,
                lat=46.0, lon=8.9, wall_time="2026-04-04T14:30:00Z",
            )
            time.sleep(0.005)

        count_after_first = len(d.events)

        # Immediately try another "tack" — should be blocked by cooldown
        for _ in range(20):
            d.update(
                heading=300.0, twa=-35.0, bsp=6.0,
                sog=5.8, cog=300.0, brg_to_mark=None,
                lat=46.0, lon=8.9, wall_time="2026-04-04T14:30:00Z",
            )
            time.sleep(0.005)

        for _ in range(20):
            d.update(
                heading=30.0, twa=35.0, bsp=3.0,
                sog=2.8, cog=30.0, brg_to_mark=None,
                lat=46.0, lon=8.9, wall_time="2026-04-04T14:30:00Z",
            )
            time.sleep(0.005)

        # Should not have detected a second maneuver so quickly
        # (at most 1 more if recovery completed)
        assert len(d.events) <= count_after_first + 1
