"""Tests for maneuver persistence to SQLite."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from aquarela.training.maneuvers import ManeuverEvent, persist_maneuver, list_maneuvers_for_session
from aquarela.logging.db import init_schema


@pytest.fixture
def db_conn():
    with tempfile.TemporaryDirectory() as d:
        db_path = Path(d) / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        init_schema(conn)
        yield conn
        conn.close()


class TestManeuverPersistence:
    def test_persist_and_retrieve(self, db_conn):
        ev = ManeuverEvent(
            maneuver_type="tack",
            entry_time=100.0,
            exit_time=103.0,
            wall_time="2026-04-04T14:30:00.000Z",
            lat=46.002,
            lon=8.963,
            bsp_before=6.0,
            bsp_min=2.5,
            bsp_after=5.5,
            recovery_secs=4.2,
            vmg_before=5.1,
            vmg_loss_nm=0.0015,
            vmc_before=4.8,
            vmc_loss_nm=0.0012,
            hdg_before=300.0,
            hdg_after=30.0,
        )
        persist_maneuver(db_conn, session_id=1, event=ev)

        rows = list_maneuvers_for_session(db_conn, session_id=1)
        assert len(rows) == 1
        r = rows[0]
        assert r["maneuver_type"] == "tack"
        assert r["wall_time"] == "2026-04-04T14:30:00.000Z"
        assert r["lat"] == pytest.approx(46.002)
        assert r["vmg_loss_nm"] == pytest.approx(0.0015)
        assert r["vmc_loss_nm"] == pytest.approx(0.0012)

    def test_no_vmc_when_no_mark(self, db_conn):
        ev = ManeuverEvent(
            maneuver_type="gybe",
            entry_time=200.0,
            exit_time=203.0,
            wall_time="2026-04-04T15:00:00.000Z",
            lat=46.01,
            lon=8.97,
            bsp_before=7.0,
            bsp_min=4.0,
            bsp_after=6.5,
            recovery_secs=3.0,
            vmg_before=3.5,
            vmg_loss_nm=0.001,
            vmc_before=None,
            vmc_loss_nm=None,
            hdg_before=180.0,
            hdg_after=220.0,
        )
        persist_maneuver(db_conn, session_id=1, event=ev)

        rows = list_maneuvers_for_session(db_conn, session_id=1)
        assert len(rows) == 1
        assert rows[0]["vmc_before"] is None
        assert rows[0]["vmc_loss_nm"] is None

    def test_list_empty_session(self, db_conn):
        rows = list_maneuvers_for_session(db_conn, session_id=999)
        assert rows == []
