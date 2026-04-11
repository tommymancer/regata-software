"""Tests for the upwash correction lookup tables."""

import json
import pytest
from pathlib import Path

from aquarela.pipeline.upwash_table import (
    AWA_BREAKPOINTS,
    HEEL_BREAKPOINTS,
    SAIL_CONFIG_KEYS,
    UpwashTable,
    UpwashTableSet,
)


# ── Initial values ───────────────────────────────────────────────────

class TestInitialValues:
    def test_shape(self):
        tbl = UpwashTable.with_initial_values()
        assert len(tbl.offsets) == 33
        assert all(len(row) == 8 for row in tbl.offsets)
        assert len(tbl.observations) == 33
        assert all(len(row) == 8 for row in tbl.observations)

    def test_observations_start_zero(self):
        tbl = UpwashTable.with_initial_values()
        for row in tbl.observations:
            assert all(c == 0 for c in row)

    def test_monotonically_decreasing_with_awa(self):
        """At any fixed heel, upwash should not increase as AWA grows."""
        tbl = UpwashTable.with_initial_values()
        for j in range(len(HEEL_BREAKPOINTS)):
            for i in range(len(AWA_BREAKPOINTS) - 1):
                assert tbl.offsets[i][j] >= tbl.offsets[i + 1][j], (
                    f"Not monotonic at AWA={AWA_BREAKPOINTS[i]}, "
                    f"heel={HEEL_BREAKPOINTS[j]}"
                )

    def test_zero_at_awa_180(self):
        tbl = UpwashTable.with_initial_values()
        awa_180_idx = AWA_BREAKPOINTS.index(180)
        for j in range(len(HEEL_BREAKPOINTS)):
            assert tbl.offsets[awa_180_idx][j] == 0.0

    def test_positive_at_low_awa(self):
        tbl = UpwashTable.with_initial_values()
        awa_20_idx = AWA_BREAKPOINTS.index(20)
        for j in range(len(HEEL_BREAKPOINTS)):
            assert tbl.offsets[awa_20_idx][j] >= 0.0


# ── Bilinear interpolation ──────────────────────────────────────────

class TestLookup:
    def test_at_grid_point_returns_exact(self):
        tbl = UpwashTable.with_initial_values()
        awa_20_idx = AWA_BREAKPOINTS.index(20)
        heel_0_idx = HEEL_BREAKPOINTS.index(0)
        expected = tbl.offsets[awa_20_idx][heel_0_idx]
        assert tbl.lookup(20, 0) == pytest.approx(expected)

    def test_between_points_within_corner_bounds(self):
        tbl = UpwashTable.with_initial_values()
        # Pick a point between grid nodes
        val = tbl.lookup(32.5, 12.5)
        # Corners: AWA 30&35, heel 10&15
        i30 = AWA_BREAKPOINTS.index(30)
        i35 = AWA_BREAKPOINTS.index(35)
        j10 = HEEL_BREAKPOINTS.index(10)
        j15 = HEEL_BREAKPOINTS.index(15)
        corners = [
            tbl.offsets[i30][j10],
            tbl.offsets[i30][j15],
            tbl.offsets[i35][j10],
            tbl.offsets[i35][j15],
        ]
        assert min(corners) <= val <= max(corners)

    def test_clamp_low_awa(self):
        tbl = UpwashTable.with_initial_values()
        # AWA below minimum should clamp to 20
        assert tbl.lookup(5, 0) == pytest.approx(tbl.lookup(20, 0))

    def test_clamp_high_awa(self):
        tbl = UpwashTable.with_initial_values()
        assert tbl.lookup(200, 0) == pytest.approx(tbl.lookup(180, 0))

    def test_clamp_high_heel(self):
        tbl = UpwashTable.with_initial_values()
        assert tbl.lookup(45, 50) == pytest.approx(tbl.lookup(45, 35))

    def test_symmetry_negative_awa(self):
        """lookup takes absolute values, so negative AWA == positive."""
        tbl = UpwashTable.with_initial_values()
        assert tbl.lookup(-45, 10) == pytest.approx(tbl.lookup(45, 10))

    def test_symmetry_negative_heel(self):
        tbl = UpwashTable.with_initial_values()
        assert tbl.lookup(45, -15) == pytest.approx(tbl.lookup(45, 15))


# ── update_nearest ───────────────────────────────────────────────────

class TestUpdateNearest:
    def test_changes_offset(self):
        tbl = UpwashTable.with_initial_values()
        awa_45_idx = AWA_BREAKPOINTS.index(45)
        heel_0_idx = HEEL_BREAKPOINTS.index(0)
        before = tbl.offsets[awa_45_idx][heel_0_idx]

        tbl.update_nearest(45, 0, residual=1.0, learning_rate=0.1)

        after = tbl.offsets[awa_45_idx][heel_0_idx]
        assert after == pytest.approx(before + 0.1)

    def test_increments_observations(self):
        tbl = UpwashTable.with_initial_values()
        awa_45_idx = AWA_BREAKPOINTS.index(45)
        heel_0_idx = HEEL_BREAKPOINTS.index(0)
        assert tbl.observations[awa_45_idx][heel_0_idx] == 0

        tbl.update_nearest(45, 0, residual=1.0, learning_rate=0.1)
        assert tbl.observations[awa_45_idx][heel_0_idx] == 1

        tbl.update_nearest(45, 0, residual=0.5, learning_rate=0.1)
        assert tbl.observations[awa_45_idx][heel_0_idx] == 2

    def test_snaps_to_nearest(self):
        """AWA=47 should snap to 45 (nearest breakpoint)."""
        tbl = UpwashTable.with_initial_values()
        awa_45_idx = AWA_BREAKPOINTS.index(45)
        heel_0_idx = HEEL_BREAKPOINTS.index(0)
        before = tbl.offsets[awa_45_idx][heel_0_idx]

        tbl.update_nearest(47, 1, residual=2.0, learning_rate=0.05)

        assert tbl.offsets[awa_45_idx][heel_0_idx] == pytest.approx(
            before + 0.1
        )


# ── JSON round-trip ──────────────────────────────────────────────────

class TestSerialization:
    def test_table_round_trip(self):
        tbl = UpwashTable.with_initial_values()
        tbl.update_nearest(90, 15, residual=0.5, learning_rate=0.2)

        d = tbl.to_dict()
        restored = UpwashTable.from_dict(d)

        assert restored.offsets == tbl.offsets
        assert restored.observations == tbl.observations

    def test_tableset_save_load(self, tmp_path):
        ts = UpwashTableSet.with_initial_values()
        # Mutate one table so it's not all defaults
        ts.get_table("main_1__jib").update_nearest(
            60, 10, residual=1.0, learning_rate=0.1
        )

        fpath = tmp_path / "upwash.json"
        ts.save(fpath)

        loaded = UpwashTableSet.load(fpath)
        for key in SAIL_CONFIG_KEYS:
            orig = ts.get_table(key)
            rest = loaded.get_table(key)
            assert rest is not None
            assert rest.offsets == orig.offsets
            assert rest.observations == orig.observations

    def test_load_missing_file_returns_defaults(self, tmp_path):
        fpath = tmp_path / "nonexistent.json"
        loaded = UpwashTableSet.load(fpath)
        assert len(loaded.tables) == 6
        # Should be initial values
        tbl = loaded.get_table("main_1__jib")
        fresh = UpwashTable.with_initial_values()
        assert tbl.offsets == fresh.offsets


# ── UpwashTableSet ───────────────────────────────────────────────────

class TestUpwashTableSet:
    def test_has_all_keys(self):
        ts = UpwashTableSet.with_initial_values()
        for key in SAIL_CONFIG_KEYS:
            assert ts.get_table(key) is not None

    def test_unknown_key_returns_none(self):
        ts = UpwashTableSet.with_initial_values()
        assert ts.get_table("spinnaker_only") is None

    def test_tables_are_independent(self):
        ts = UpwashTableSet.with_initial_values()
        ts.get_table("main_1__jib").update_nearest(
            45, 0, residual=10.0, learning_rate=1.0
        )
        # Other table should be unaffected
        other = ts.get_table("main_1__genoa")
        fresh = UpwashTable.with_initial_values()
        awa_45_idx = AWA_BREAKPOINTS.index(45)
        assert other.offsets[awa_45_idx][0] == fresh.offsets[awa_45_idx][0]
