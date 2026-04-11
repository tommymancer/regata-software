"""Tests for race timer state machine."""

import time

import pytest
from aquarela.pipeline.state import BoatState
from aquarela.race.timer import RaceTimer


class TestRaceTimer:
    def test_initial_state(self):
        """Timer starts idle."""
        t = RaceTimer()
        assert t.state == "idle"
        assert t.get_seconds() is None

    def test_start_countdown(self):
        """Starting sets countdown state with correct duration."""
        t = RaceTimer()
        t.start(5)
        assert t.state == "countdown"
        secs = t.get_seconds()
        assert secs is not None
        assert 299 < secs <= 300

    def test_start_1min(self):
        """1-minute countdown."""
        t = RaceTimer()
        t.start(1)
        secs = t.get_seconds()
        assert secs is not None
        assert 59 < secs <= 60

    def test_sync_up(self):
        """Sync up adds 1 minute."""
        t = RaceTimer()
        t.start(3)
        before = t.get_seconds()
        t.sync_up()
        after = t.get_seconds()
        # Should be ~60 seconds more (minus tiny elapsed time)
        assert after > before + 59

    def test_sync_down(self):
        """Sync down removes 1 minute."""
        t = RaceTimer()
        t.start(5)
        before = t.get_seconds()
        t.sync_down()
        after = t.get_seconds()
        assert after < before - 59

    def test_sync_down_floor(self):
        """Sync down won't go below 0."""
        t = RaceTimer()
        t.start(1)
        t.sync_down()
        t.sync_down()  # try to go negative
        # Should transition to racing (countdown reached 0)
        secs = t.get_seconds()
        assert secs is not None

    def test_sync_on_idle_noop(self):
        """Sync on idle timer does nothing."""
        t = RaceTimer()
        t.sync_up()
        t.sync_down()
        assert t.state == "idle"

    def test_stop(self):
        """Stop returns to idle."""
        t = RaceTimer()
        t.start(5)
        assert t.state == "countdown"
        t.stop()
        assert t.state == "idle"
        assert t.get_seconds() is None

    def test_reset(self):
        """Reset clears everything."""
        t = RaceTimer()
        t.start(3)
        t.reset()
        assert t.state == "idle"
        assert t.get_seconds() is None

    def test_countdown_to_racing_transition(self):
        """When countdown reaches 0, transitions to racing."""
        t = RaceTimer()
        # Start with very short countdown
        t._countdown_secs = 0.05  # 50ms
        t._start_mono = time.monotonic()
        t.state = "countdown"
        time.sleep(0.1)  # wait past countdown
        secs = t.get_seconds()
        assert t.state == "racing"
        assert secs is not None
        assert secs >= 0

    def test_update_sets_state_on_boatstate(self):
        """update() populates race fields on BoatState."""
        t = RaceTimer()
        t.start(5)
        s = BoatState.new()
        t.update(s)
        assert s.race_state == "countdown"
        assert s.race_timer_secs is not None
        assert s.race_timer_secs > 0

    def test_update_idle(self):
        """Idle timer sets idle state and None seconds."""
        t = RaceTimer()
        s = BoatState.new()
        t.update(s)
        assert s.race_state == "idle"
        assert s.race_timer_secs is None
