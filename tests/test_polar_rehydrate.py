"""Test that learned polars rehydrate from DB at startup.

Without rehydration, after every Pi restart the active polar reverted to
the conservative base table, so the crew saw too-easy targets until the
next session_stop rebuilt the learned data. This test verifies the
rehydrate-at-boot path: given polar_samples in the DB, rebuild() returns
a learned table that the PolarManager can use.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

from aquarela.logging.db import init_schema
from aquarela.performance.polar import PolarTable
from aquarela.performance.polar_learner import PolarLearner
from aquarela.performance.polar_manager import PolarManager, SAIL_CONFIGS


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """A fresh SQLite DB at a temp path. Monkeypatches DB_PATH so the
    learner's _get_conn() uses it."""
    db_path = tmp_path / "aquarela.db"
    from aquarela.logging import db as db_mod
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    conn = sqlite3.connect(str(db_path))
    init_schema(conn)
    conn.close()
    yield db_path


@pytest.fixture
def base_polar():
    return PolarTable.load("data/polars/2025_Polar.json")


def _insert_polar_samples(
    db_path: Path, sail_type: str, n: int = 200,
    twa_bin: float = 52.0, tws_bin: int = 10, bsp: float = 6.5,
) -> None:
    """Seed the DB with enough samples for one bin to be 'ready' (>=50).

    Defaults to (TWS=10, TWA=52) — both are real breakpoints in the
    Vakaros 2025 polar, so the merge_with_base loop visits this bin.
    Passing TWA >= 90 makes the sample downwind (per-sail-type, not shared).
    """
    conn = sqlite3.connect(str(db_path))
    rows = [
        (None, "2025-01-01T00:00:00Z", tws_bin, twa_bin, bsp,
         float(tws_bin), twa_bin, 100.0, sail_type)
        for _ in range(n)
    ]
    conn.executemany(
        """INSERT INTO polar_samples
           (session_id, timestamp, tws_bin, twa_bin, bsp_kt, tws_kt, twa_deg, perf_pct, sail_type)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )
    conn.commit()
    conn.close()


class TestPolarRehydrate:
    def test_rebuild_returns_learned_when_samples_exist(
        self, temp_db, base_polar, monkeypatch
    ):
        sail = "main_1__genoa"
        _insert_polar_samples(temp_db, sail, n=200)
        learner = PolarLearner(base_polar=base_polar, sail_type=sail)
        result = learner.rebuild()
        assert result is not None
        assert isinstance(result, PolarTable)
        # The learned bin (10, 52) should reflect the seeded BSP=6.5
        # (merged with base, weighted by sample_count vs min_samples)
        bsp_at_bin = result.bsp_grid.get((10.0, 52.0))
        assert bsp_at_bin is not None
        # With 200 samples vs default min_samples=50, weight ~ 200/250 = 0.8
        # for the learned value 6.5 blended with base; result is in [base, 6.5]
        assert 5.0 < bsp_at_bin < 7.5

    def test_rebuild_returns_none_when_no_samples(self, temp_db, base_polar):
        learner = PolarLearner(base_polar=base_polar, sail_type="main_2__jib")
        result = learner.rebuild()
        assert result is None

    def test_manager_holds_learned_after_set_polar(
        self, temp_db, base_polar
    ):
        sail = "main_1__genoa"
        _insert_polar_samples(temp_db, sail, n=200)
        mgr = PolarManager(base_polar=base_polar)
        learner = PolarLearner(base_polar=base_polar, sail_type=sail)
        learned = learner.rebuild()
        assert learned is not None
        mgr.set_polar(sail, learned)
        # The manager now returns the learned table for that sail
        assert mgr.get_polar(sail) is learned
        # Other sails still hold base
        for other in SAIL_CONFIGS:
            if other == sail:
                continue
            assert mgr.get_polar(other) is base_polar

    def test_rehydrate_loop_picks_up_only_sails_with_data(
        self, temp_db, base_polar
    ):
        """Simulates the main.py boot loop: rebuild for every sail, set_polar
        on those that returned non-None.

        Seed a DOWNWIND sample (TWA >= 90) so it is per-sail-type. Upwind
        bins are shared across sails by design, so an upwind-only seed
        would activate every sail. Here we want only the seeded sail to
        activate.
        """
        # Seed only main_1__gennaker with downwind samples
        _insert_polar_samples(
            temp_db, "main_1__gennaker", n=200, twa_bin=135.0, bsp=7.0,
        )

        mgr = PolarManager(base_polar=base_polar)
        learners = {
            key: PolarLearner(base_polar=base_polar, sail_type=key)
            for key in SAIL_CONFIGS
        }
        loaded = []
        for sail in SAIL_CONFIGS:
            learned = learners[sail].rebuild()
            if learned is not None:
                mgr.set_polar(sail, learned)
                loaded.append(sail)

        assert loaded == ["main_1__gennaker"]
        assert mgr.get_polar("main_1__gennaker") is not base_polar
        for other in SAIL_CONFIGS:
            if other == "main_1__gennaker":
                continue
            assert mgr.get_polar(other) is base_polar
