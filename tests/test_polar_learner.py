"""Tests for self-updating polar learning system."""

import math
import time

import pytest
from aquarela.performance.polar import PolarTable
from aquarela.performance.polar_learner import PolarLearner, BinStats
from aquarela.pipeline.state import BoatState
from datetime import datetime, timezone


@pytest.fixture
def base_polar():
    """Minimal base polar for testing."""
    return PolarTable(
        tws_values=[6.0, 8.0, 10.0, 12.0],
        twa_values=[37.0, 52.0, 60.0, 75.0, 90.0, 120.0, 150.0],
        bsp_grid={
            (6.0, 37.0): 4.0, (6.0, 52.0): 4.8, (6.0, 60.0): 5.2,
            (6.0, 75.0): 5.5, (6.0, 90.0): 5.8, (6.0, 120.0): 5.2, (6.0, 150.0): 4.5,
            (8.0, 37.0): 4.8, (8.0, 52.0): 5.5, (8.0, 60.0): 6.0,
            (8.0, 75.0): 6.3, (8.0, 90.0): 6.5, (8.0, 120.0): 6.0, (8.0, 150.0): 5.2,
            (10.0, 37.0): 5.5, (10.0, 52.0): 6.0, (10.0, 60.0): 6.5,
            (10.0, 75.0): 6.8, (10.0, 90.0): 7.0, (10.0, 120.0): 6.5, (10.0, 150.0): 5.8,
            (12.0, 37.0): 6.0, (12.0, 52.0): 6.5, (12.0, 60.0): 7.0,
            (12.0, 75.0): 7.3, (12.0, 90.0): 7.5, (12.0, 120.0): 7.0, (12.0, 150.0): 6.3,
        },
        upwind_targets={6.0: (37.0, 4.0, 3.19), 8.0: (37.0, 4.8, 3.83),
                        10.0: (37.0, 5.5, 4.39), 12.0: (37.0, 6.0, 4.79)},
        downwind_targets={6.0: (150.0, 4.5, 3.90), 8.0: (150.0, 5.2, 4.50),
                          10.0: (150.0, 5.8, 5.02), 12.0: (150.0, 6.3, 5.46)},
    )


@pytest.fixture
def learner(tmp_path, base_polar):
    """PolarLearner with temp DB and low thresholds for testing."""
    db = str(tmp_path / "test.db")
    return PolarLearner(
        base_polar=base_polar,
        hz=10,
        min_samples=5,  # low threshold for tests
        flush_interval_s=3600,  # don't auto-flush during tests
        db_path=db,
    )


@pytest.fixture
def learner_no_base(tmp_path):
    """PolarLearner without a base polar."""
    db = str(tmp_path / "test.db")
    return PolarLearner(
        base_polar=None,
        hz=10,
        min_samples=5,
        flush_interval_s=3600,
        db_path=db,
    )


def _make_state(bsp=6.0, twa=42.0, tws=10.0, perf_pct=95.0,
                wind_age_ms=None, bsp_age_ms=None):
    """Create a BoatState with given values."""
    s = BoatState(timestamp=datetime.now(timezone.utc))
    s.bsp_kt = bsp
    s.twa_deg = twa
    s.tws_kt = tws
    s.perf_pct = perf_pct
    s.wind_age_ms = wind_age_ms
    s.bsp_age_ms = bsp_age_ms
    return s


def _fill_tws_window(learner, tws=10.0, n=None):
    """Fill the TWS stability window with stable values."""
    count = n or learner._stability_samples
    for _ in range(count):
        learner._tws_window.append(tws)


def _accumulate_n(learner, n, bsp=6.0, twa=42.0, tws=10.0):
    """Force-accumulate N samples bypassing decimation and stability."""
    for _ in range(n):
        learner._buffer.append((
            None,
            datetime.now(timezone.utc).isoformat(),
            round(tws),
            min(learner._twa_bins, key=lambda x: abs(x - abs(twa))),
            bsp,
            tws,
            abs(twa),
            95.0,
            learner._sail_type,
        ))


# ── Bin Assignment ─────────────────────────────────────────────────

class TestBinAssignment:
    def test_tws_rounding(self, learner):
        assert learner._assign_bin(9.4, 52.0) == (9, 52.0)
        assert learner._assign_bin(9.6, 52.0) == (10, 52.0)

    def test_tws_clamp_low(self, learner):
        # round(3.5) = 4 in Python (banker's rounding), which is valid
        assert learner._assign_bin(3.5, 52.0) == (4, 52.0)
        assert learner._assign_bin(3.4, 52.0) is None  # rounds to 3, out of range

    def test_tws_clamp_high(self, learner):
        assert learner._assign_bin(20.4, 52.0) == (20, 52.0)
        assert learner._assign_bin(20.6, 52.0) is None  # rounds to 21

    def test_twa_nearest_breakpoint(self, learner):
        # 56 is equidistant between 52 and 60 — nearest is 52 (or 60)
        result = learner._assign_bin(10.0, 55.0)
        assert result is not None
        assert result[1] in (52.0, 60.0)

    def test_twa_symmetric(self, learner):
        """Port and starboard TWA map to same bin."""
        r1 = learner._assign_bin(10.0, 42.0)
        r2 = learner._assign_bin(10.0, -42.0)
        assert r1 is not None
        assert r2 is not None
        assert r1[1] == r2[1]

    def test_twa_too_far_from_bin(self, learner):
        """TWA far from any bin is rejected."""
        # 25° is far below the lowest TWA bin (37°)
        result = learner._assign_bin(10.0, 25.0)
        assert result is None


# ── Stability Filters ──────────────────────────────────────────────

class TestStabilityFilters:
    def test_rejects_low_bsp(self, learner):
        state = _make_state(bsp=0.5)
        _fill_tws_window(learner)
        assert not learner._is_stable(state, in_maneuver=False)

    def test_rejects_high_bsp(self, learner):
        state = _make_state(bsp=25.0)
        _fill_tws_window(learner)
        assert not learner._is_stable(state, in_maneuver=False)

    def test_rejects_low_tws(self, learner):
        state = _make_state(tws=2.0)
        _fill_tws_window(learner, tws=2.0)
        assert not learner._is_stable(state, in_maneuver=False)

    def test_rejects_high_tws(self, learner):
        state = _make_state(tws=25.0)
        _fill_tws_window(learner, tws=25.0)
        assert not learner._is_stable(state, in_maneuver=False)

    def test_rejects_during_maneuver(self, learner):
        state = _make_state()
        _fill_tws_window(learner)
        assert not learner._is_stable(state, in_maneuver=True)

    def test_rejects_maneuver_cooldown(self, learner):
        state = _make_state()
        _fill_tws_window(learner)
        learner._last_maneuver_time = time.monotonic()  # just happened
        assert not learner._is_stable(state, in_maneuver=False)

    def test_rejects_variable_tws(self, learner):
        state = _make_state(tws=10.0)
        # Fill window with variable TWS (range = 5 kt > threshold 2 kt)
        for i in range(learner._stability_samples):
            learner._tws_window.append(8.0 + (i % 2) * 5.0)
        assert not learner._is_stable(state, in_maneuver=False)

    def test_accepts_stable_conditions(self, learner):
        state = _make_state(bsp=6.0, twa=42.0, tws=10.0)
        _fill_tws_window(learner, tws=10.0)
        learner._last_maneuver_time = 0.0  # long ago
        assert learner._is_stable(state, in_maneuver=False)

    def test_rejects_missing_bsp(self, learner):
        state = _make_state(bsp=None)
        _fill_tws_window(learner)
        assert not learner._is_stable(state, in_maneuver=False)

    def test_rejects_missing_twa(self, learner):
        state = _make_state(twa=None)
        _fill_tws_window(learner)
        assert not learner._is_stable(state, in_maneuver=False)

    def test_rejects_missing_tws(self, learner):
        state = _make_state(tws=None)
        _fill_tws_window(learner)
        assert not learner._is_stable(state, in_maneuver=False)

    def test_rejects_stale_wind(self, learner):
        state = _make_state(wind_age_ms=3000)
        state.wind_age_ms = 3000  # realistic stale value, not default 9999
        _fill_tws_window(learner)
        assert not learner._is_stable(state, in_maneuver=False)

    def test_rejects_stale_bsp(self, learner):
        state = _make_state(bsp_age_ms=3000)
        state.bsp_age_ms = 3000  # realistic stale value, not default 9999
        _fill_tws_window(learner)
        assert not learner._is_stable(state, in_maneuver=False)

    def test_accepts_default_sensor_age(self, learner):
        """Default sensor age (9999 = not tracked) should not reject."""
        state = _make_state()
        state.wind_age_ms = 9999  # default
        state.bsp_age_ms = 9999  # default
        _fill_tws_window(learner)
        learner._last_maneuver_time = 0.0
        assert learner._is_stable(state, in_maneuver=False)

    def test_rejects_narrow_twa(self, learner):
        state = _make_state(twa=20.0)
        _fill_tws_window(learner)
        assert not learner._is_stable(state, in_maneuver=False)


# ── Accumulation and Flushing ──────────────────────────────────────

class TestAccumulation:
    def test_decimation(self, learner):
        """Only every 10th tick (1 Hz) produces a sample."""
        state = _make_state()
        _fill_tws_window(learner)
        learner._last_maneuver_time = 0.0

        for _ in range(9):
            learner.update(state)
        assert len(learner._buffer) == 0

        learner.update(state)  # 10th tick
        assert len(learner._buffer) == 1

    def test_buffer_grows(self, learner):
        """Buffer accumulates samples between flushes."""
        state = _make_state()
        _fill_tws_window(learner)
        learner._last_maneuver_time = 0.0

        for i in range(30):
            learner.update(state)

        assert len(learner._buffer) == 3  # 30 ticks / 10 decimation

    def test_flush_writes_to_db(self, learner):
        _accumulate_n(learner, 5)
        assert len(learner._buffer) == 5

        learner.flush()
        conn = learner._get_conn()
        count = conn.execute("SELECT COUNT(*) FROM polar_samples").fetchone()[0]
        assert count == 5

    def test_flush_clears_buffer(self, learner):
        _accumulate_n(learner, 5)
        learner.flush()
        assert len(learner._buffer) == 0

    def test_flush_empty_noop(self, learner):
        """Flushing empty buffer does nothing."""
        learner.flush()
        conn = learner._get_conn()
        count = conn.execute("SELECT COUNT(*) FROM polar_samples").fetchone()[0]
        assert count == 0


# ── Aggregation ────────────────────────────────────────────────────

class TestAggregation:
    def test_p95_calculation(self, learner):
        """95th percentile computed correctly for a known distribution."""
        # Add 100 samples with BSP from 5.0 to 7.0
        for i in range(100):
            bsp = 5.0 + (i / 100.0) * 2.0  # 5.0 to 6.98
            learner._buffer.append((
                None,
                datetime.now(timezone.utc).isoformat(),
                10, 52.0, bsp, 10.0, 52.0, 95.0, learner._sail_type,
            ))

        result = learner.rebuild()
        assert result is not None
        # p95 of uniform 5.0-6.98 should be ~6.9
        merged_bsp = result.bsp(52.0, 10.0)
        assert merged_bsp is not None
        assert merged_bsp > 6.0

    def test_min_samples_threshold(self, learner):
        """Bins with < min_samples are not used in learned polar."""
        # Add only 3 samples (below threshold of 5)
        _accumulate_n(learner, 3, bsp=8.0, twa=52.0, tws=10.0)
        result = learner.rebuild()

        # Should still get a polar (from base), but the learned bin
        # should NOT override the base (BSP 8.0 would be way above base 6.0)
        assert result is not None
        bsp = result.bsp(52.0, 10.0)
        assert bsp is not None
        assert bsp == pytest.approx(6.0, abs=0.1)  # base value, not learned

    def test_rebuild_produces_polar_table(self, learner):
        _accumulate_n(learner, 10, bsp=6.5, twa=52.0, tws=10.0)
        result = learner.rebuild()
        assert isinstance(result, PolarTable)
        assert len(result.tws_values) > 0
        assert len(result.twa_values) > 0

    def test_rebuild_returns_none_if_empty(self, learner):
        result = learner.rebuild()
        assert result is None

    def test_rebuild_stores_learned_polar(self, learner):
        _accumulate_n(learner, 10, bsp=6.5, twa=52.0, tws=10.0)
        learner.rebuild()
        assert learner.learned_polar is not None

    def test_rebuild_updates_polar_learned_table(self, learner):
        _accumulate_n(learner, 10, bsp=6.5, twa=52.0, tws=10.0)
        learner.rebuild()

        conn = learner._get_conn()
        rows = conn.execute("SELECT * FROM polar_learned").fetchall()
        assert len(rows) >= 1
        row = rows[0]
        assert row["sample_count"] == 10
        assert row["bsp_p95"] > 0


# ── Merge Logic ────────────────────────────────────────────────────

class TestMerge:
    def test_learned_only_when_no_base(self, learner_no_base):
        """Uses only learned data when base polar is None."""
        _accumulate_n(learner_no_base, 10, bsp=6.5, twa=52.0, tws=10.0)
        result = learner_no_base.rebuild()
        assert result is not None
        bsp = result.bsp(52.0, 10.0)
        assert bsp is not None
        assert bsp == pytest.approx(6.5, abs=0.1)

    def test_base_only_when_no_learned(self, learner, base_polar):
        """Bins without learned data use base polar value."""
        # Add data only at TWS=10, TWA=52
        _accumulate_n(learner, 10, bsp=6.5, twa=52.0, tws=10.0)
        result = learner.rebuild()
        assert result is not None

        # Check a bin with no learned data (TWS=8, TWA=90)
        bsp = result.bsp(90.0, 8.0)
        base_bsp = base_polar.bsp(90.0, 8.0)
        assert bsp is not None
        assert bsp == pytest.approx(base_bsp, abs=0.1)

    def test_blend_weights(self, learner, base_polar):
        """Blend weight increases with sample count."""
        base_bsp = base_polar.bsp(52.0, 10.0)  # 6.0
        learned_bsp = 7.0

        # With min_samples=5 and 10 samples:
        # weight = min(0.9, 10 / (10 + 5)) = 0.667
        # merged = 0.667 * 7.0 + 0.333 * 6.0 = 6.667
        _accumulate_n(learner, 10, bsp=learned_bsp, twa=52.0, tws=10.0)
        result = learner.rebuild()
        assert result is not None
        merged_bsp = result.bsp(52.0, 10.0)
        assert merged_bsp is not None
        assert merged_bsp > base_bsp
        assert merged_bsp < learned_bsp

    def test_targets_recomputed(self, learner):
        """Upwind/downwind targets recalculated from merged grid."""
        _accumulate_n(learner, 10, bsp=6.5, twa=37.0, tws=10.0)
        result = learner.rebuild()
        assert result is not None
        target = result.target_upwind(10.0)
        assert target is not None
        assert target[0] > 0  # TWA
        assert target[1] > 0  # BSP
        assert target[2] > 0  # VMG


# ── Stats and Coverage ─────────────────────────────────────────────

class TestStats:
    def test_empty_stats(self, learner):
        stats = learner.get_stats()
        assert stats["total_samples"] == 0
        assert stats["bins_filled"] == 0
        assert stats["bins_ready"] == 0
        assert stats["has_learned_polar"] is False

    def test_stats_after_accumulation(self, learner):
        _accumulate_n(learner, 10, bsp=6.0, twa=52.0, tws=10.0)
        learner.flush()
        stats = learner.get_stats()
        assert stats["total_samples"] == 10
        assert stats["bins_filled"] == 1

    def test_coverage_matrix(self, learner):
        _accumulate_n(learner, 10, bsp=6.0, twa=52.0, tws=10.0)
        learner.flush()
        learner.rebuild()
        coverage = learner.get_coverage_matrix()
        assert len(coverage) >= 1
        first = coverage[0]
        assert "tws" in first
        assert "twa" in first
        assert "count" in first
        assert "bsp_p95" in first
        assert first["ready"] is True


# ── Reset ──────────────────────────────────────────────────────────

class TestReset:
    def test_reset_clears_everything(self, learner):
        _accumulate_n(learner, 10, bsp=6.0, twa=52.0, tws=10.0)
        learner.flush()
        learner.rebuild()
        assert learner.learned_polar is not None

        learner.reset()
        assert learner.learned_polar is None
        assert len(learner._buffer) == 0
        stats = learner.get_stats()
        assert stats["total_samples"] == 0
        assert stats["bins_filled"] == 0


# ── Graceful Degradation ──────────────────────────────────────────

class TestGracefulDegradation:
    def test_no_base_polar_works(self, learner_no_base):
        """PolarLearner works without a base polar."""
        _accumulate_n(learner_no_base, 10, bsp=6.0, twa=52.0, tws=10.0)
        result = learner_no_base.rebuild()
        assert result is not None

    def test_empty_database(self, learner):
        stats = learner.get_stats()
        assert stats["total_samples"] == 0
        result = learner.rebuild()
        assert result is None

    def test_bin_stats_to_dict(self):
        bs = BinStats(tws_bin=10, twa_bin=52.0, bsp_p95=6.5,
                      sample_count=100, updated_at="2026-01-01T00:00:00Z")
        d = bs.to_dict()
        assert d["tws_bin"] == 10
        assert d["twa_bin"] == 52.0
        assert d["bsp_p95"] == 6.5
        assert d["sample_count"] == 100
