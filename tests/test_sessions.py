"""Tests for session manager — auto-start/stop."""

import time

import pytest
from aquarela.training.sessions import Session, SessionManager


@pytest.fixture
def session_mgr(tmp_path):
    """Fresh SessionManager backed by a temp SQLite database."""
    db_path = str(tmp_path / "test.db")
    return SessionManager(hz=10, db_path=db_path)


class TestSessionManager:
    def test_initial_state(self, session_mgr):
        assert session_mgr.active_session is None

    def test_auto_start_bsp_above_threshold(self, session_mgr):
        """Session starts after BSP > 0.5 kt for START_DURATION_SECS."""
        session_mgr.START_DURATION_SECS = 0.1

        result = None
        for _ in range(50):
            result = session_mgr.update(bsp=5.0, sog=0.0)
            if result == "started":
                break
            time.sleep(0.01)

        assert result == "started"
        assert session_mgr.active_session is not None
        assert session_mgr.active_session.id is not None

    def test_auto_start_sog_above_threshold(self, session_mgr):
        """Session starts when SOG alone is above threshold."""
        session_mgr.START_DURATION_SECS = 0.1

        result = None
        for _ in range(50):
            result = session_mgr.update(bsp=0.0, sog=2.0)
            if result == "started":
                break
            time.sleep(0.01)

        assert result == "started"
        assert session_mgr.active_session is not None

    def test_no_start_below_threshold(self, session_mgr):
        """No session starts when both BSP and SOG are below threshold."""
        session_mgr.START_DURATION_SECS = 0.1

        for _ in range(30):
            result = session_mgr.update(bsp=0.3, sog=0.2)
            assert result is None
            time.sleep(0.01)

        assert session_mgr.active_session is None

    def test_auto_stop_after_idle(self, session_mgr):
        """Session stops after both BSP and SOG < 0.3 for STOP_DURATION_SECS."""
        session_mgr.START_DURATION_SECS = 0.05
        session_mgr.STOP_DURATION_SECS = 0.1

        # Start session
        for _ in range(30):
            r = session_mgr.update(bsp=5.0, sog=5.0)
            if r == "started":
                break
            time.sleep(0.01)
        assert session_mgr.active_session is not None

        # Stop: both drop below threshold
        result = None
        for _ in range(50):
            result = session_mgr.update(bsp=0.1, sog=0.1)
            if result == "stopped":
                break
            time.sleep(0.01)

        assert result == "stopped"
        assert session_mgr.active_session is None

    def test_no_stop_if_sog_still_moving(self, session_mgr):
        """Session stays open if SOG is above stop threshold even with BSP=0."""
        session_mgr.START_DURATION_SECS = 0.05
        session_mgr.STOP_DURATION_SECS = 0.1

        # Start
        for _ in range(30):
            r = session_mgr.update(bsp=5.0, sog=5.0)
            if r == "started":
                break
            time.sleep(0.01)
        assert session_mgr.active_session is not None

        # BSP drops but SOG stays up (motoring, current, etc.)
        for _ in range(30):
            r = session_mgr.update(bsp=0.0, sog=1.0)
            assert r is None
            time.sleep(0.01)

        assert session_mgr.active_session is not None

    def test_none_values_treated_as_zero(self, session_mgr):
        """None BSP/SOG treated same as 0 for auto-stop."""
        session_mgr.START_DURATION_SECS = 0.05
        session_mgr.STOP_DURATION_SECS = 0.1

        for _ in range(30):
            r = session_mgr.update(bsp=5.0, sog=5.0)
            if r == "started":
                break
            time.sleep(0.01)

        result = None
        for _ in range(50):
            result = session_mgr.update(bsp=None, sog=None)
            if result == "stopped":
                break
            time.sleep(0.01)

        assert result == "stopped"

    def test_nmea_timeout_stops_session(self, session_mgr):
        """Session stops if no NMEA frames for NMEA_TIMEOUT_SECS."""
        session_mgr.START_DURATION_SECS = 0.05
        session_mgr.NMEA_TIMEOUT_SECS = 0.1

        # Simulate NMEA arriving and session starting
        session_mgr.notify_nmea_frame()
        for _ in range(30):
            session_mgr.notify_nmea_frame()
            r = session_mgr.update(bsp=5.0, sog=5.0)
            if r == "started":
                break
            time.sleep(0.01)
        assert session_mgr.active_session is not None

        # Stop notifying NMEA frames, but keep calling update
        time.sleep(0.15)
        result = session_mgr.update(bsp=5.0, sog=5.0)
        assert result == "stopped"
        assert session_mgr.active_session is None

    def test_force_start(self, session_mgr):
        s = session_mgr.force_start("race")
        assert s.session_type == "race"
        assert session_mgr.active_session is not None

    def test_force_stop(self, session_mgr):
        session_mgr.force_start()
        s = session_mgr.force_stop()
        assert s is not None
        assert s.end_time is not None
        assert session_mgr.active_session is None

    def test_force_stop_when_idle(self, session_mgr):
        assert session_mgr.force_stop() is None

    def test_list_sessions(self, session_mgr):
        session_mgr.force_start("training")
        session_mgr.force_stop()
        session_mgr.force_start("race")
        session_mgr.force_stop()

        sessions = session_mgr.list_sessions()
        assert len(sessions) == 2

    def test_get_session(self, session_mgr):
        s = session_mgr.force_start()
        session_mgr.force_stop()
        got = session_mgr.get_session(s.id)
        assert got is not None
        assert got.end_time is not None

    def test_set_csv_file(self, session_mgr):
        session_mgr.force_start()
        session_mgr.set_csv_file("/data/sessions/test.csv")
        assert session_mgr.active_session.csv_file == "/data/sessions/test.csv"

    def test_session_to_dict(self, session_mgr):
        s = session_mgr.force_start()
        d = s.to_dict()
        assert "id" in d
        assert "start_time" in d
        assert d["session_type"] == "training"

    def test_reset(self, session_mgr):
        session_mgr.force_start()
        session_mgr.reset()
        assert session_mgr.active_session is None

    def test_force_start_stops_existing(self, session_mgr):
        """Force starting a new session stops the existing one."""
        s1 = session_mgr.force_start("training")
        s2 = session_mgr.force_start("race")
        assert s2.id != s1.id
        got = session_mgr.get_session(s1.id)
        assert got.end_time is not None
