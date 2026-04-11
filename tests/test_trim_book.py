"""Tests for trim book CRUD and best-trim query."""

import os
import tempfile

import pytest
from aquarela.training.trim_book import TrimBook, TrimSnapshot


@pytest.fixture
def trim_book(tmp_path):
    """Fresh TrimBook backed by a temp SQLite database."""
    db_path = str(tmp_path / "test.db")
    return TrimBook(db_path=db_path)


class TestTrimBookCRUD:
    def test_save_and_get(self, trim_book):
        snap = TrimSnapshot(
            tws_kt=12.0,
            twa_deg=-42.0,
            bsp_kt=6.5,
            perf_pct=95.0,
            cunningham="medium",
            outhaul="light",
            vang="heavy",
        )
        snap_id = trim_book.save(snap)
        assert snap_id > 0

        got = trim_book.get(snap_id)
        assert got is not None
        assert got.tws_kt == 12.0
        assert got.twa_deg == -42.0
        assert got.cunningham == "medium"
        assert got.vang == "heavy"

    def test_timestamp_auto_set(self, trim_book):
        snap = TrimSnapshot(tws_kt=10.0, twa_deg=35.0)
        trim_book.save(snap)
        assert snap.timestamp != ""

    def test_delete(self, trim_book):
        snap = TrimSnapshot(tws_kt=10.0, twa_deg=40.0)
        snap_id = trim_book.save(snap)
        assert trim_book.delete(snap_id)
        assert trim_book.get(snap_id) is None

    def test_delete_nonexistent(self, trim_book):
        assert not trim_book.delete(9999)

    def test_list_all(self, trim_book):
        for i in range(5):
            trim_book.save(TrimSnapshot(tws_kt=10.0 + i, twa_deg=40.0))
        result = trim_book.list_all()
        assert len(result) == 5

    def test_list_all_limit(self, trim_book):
        for i in range(10):
            trim_book.save(TrimSnapshot(tws_kt=10.0 + i, twa_deg=40.0))
        result = trim_book.list_all(limit=3)
        assert len(result) == 3

    def test_to_dict(self, trim_book):
        snap = TrimSnapshot(
            tws_kt=12.0,
            twa_deg=42.0,
            bsp_kt=6.5,
            perf_pct=95.0,
            cunningham="medium",
            notes="flat water",
        )
        d = snap.to_dict()
        assert d["tws_kt"] == 12.0
        assert d["cunningham"] == "medium"
        assert d["notes"] == "flat water"


class TestBestForConditions:
    def test_best_by_perf(self, trim_book):
        """Returns the snapshot with highest PERF%."""
        trim_book.save(TrimSnapshot(
            tws_kt=12.0, twa_deg=42.0, bsp_kt=6.0, perf_pct=88.0,
            cunningham="light",
        ))
        trim_book.save(TrimSnapshot(
            tws_kt=11.0, twa_deg=40.0, bsp_kt=6.5, perf_pct=96.0,
            cunningham="medium",
        ))
        trim_book.save(TrimSnapshot(
            tws_kt=13.0, twa_deg=44.0, bsp_kt=6.2, perf_pct=92.0,
            cunningham="heavy",
        ))

        best = trim_book.best_for_conditions(12.0, 42.0)
        assert best is not None
        assert best.perf_pct == 96.0
        assert best.cunningham == "medium"

    def test_no_match(self, trim_book):
        """Returns None when no snapshots match conditions."""
        trim_book.save(TrimSnapshot(
            tws_kt=5.0, twa_deg=30.0, perf_pct=80.0
        ))
        result = trim_book.best_for_conditions(20.0, 120.0)
        assert result is None

    def test_port_stbd_equivalent(self, trim_book):
        """Matches port and starboard TWA equivalently."""
        # Save a port tack trim
        trim_book.save(TrimSnapshot(
            tws_kt=12.0, twa_deg=-42.0, perf_pct=95.0,
            cunningham="medium",
        ))
        # Query for starboard equivalent
        best = trim_book.best_for_conditions(12.0, 42.0)
        assert best is not None
        assert best.perf_pct == 95.0

    def test_tolerance_range(self, trim_book):
        """Finds matches within TWS ±3 and TWA ±10."""
        trim_book.save(TrimSnapshot(
            tws_kt=14.0, twa_deg=48.0, perf_pct=90.0,
        ))
        # Query at TWS=12, TWA=42 — within tolerances (14 is within ±3, 48 within ±10)
        best = trim_book.best_for_conditions(12.0, 42.0)
        assert best is not None

        # Out of range
        out = trim_book.best_for_conditions(20.0, 42.0)
        assert out is None
