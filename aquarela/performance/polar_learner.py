"""Self-updating polar — accumulates BSP samples and builds empirical polar.

Accumulates BSP observations from real sailing, bins them by TWS (1-kt
resolution, 4–20 kt) and TWA (using base polar TWA breakpoints), computes
95th-percentile BSP per bin, and merges with the base polar to produce
improved performance targets.

Pipeline integration:
    polar_learner.update(state, in_maneuver=...)   # every pipeline tick
    polar_learner.flush()                           # at session end
    polar_learner.rebuild()                         # on demand / session end
"""

import json
import math
import sqlite3
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..logging.db import DB_PATH, get_connection, init_schema
from ..pipeline.state import BoatState
from .polar import PolarTable


@dataclass
class BinStats:
    """Aggregation stats for a single (tws, twa) bin."""

    tws_bin: int
    twa_bin: float
    bsp_p95: float
    sample_count: int
    updated_at: str

    def to_dict(self) -> dict:
        return {
            "tws_bin": self.tws_bin,
            "twa_bin": round(self.twa_bin, 1),
            "bsp_p95": round(self.bsp_p95, 2),
            "sample_count": self.sample_count,
            "updated_at": self.updated_at,
        }


class PolarLearner:
    """Accumulates sailing data and builds a learned polar table.

    Call ``update(state)`` once per pipeline tick.  Samples are buffered
    in memory and flushed to SQLite in batches.  Call ``rebuild()`` to
    recompute the learned polar from all accumulated data.
    """

    # Stability filter thresholds
    MIN_BSP_KT: float = 1.5
    MIN_TWS_KT: float = 4.0
    MAX_TWS_KT: float = 20.0
    MAX_BSP_KT: float = 20.0
    MANEUVER_COOLDOWN_S: float = 15.0
    TWS_STABILITY_THRESHOLD: float = 2.0  # kt max range in 5s window

    def __init__(
        self,
        base_polar: Optional[PolarTable] = None,
        hz: int = 10,
        min_samples: int = 50,
        flush_interval_s: float = 60.0,
        db_path: Optional[str] = None,
        sail_type: str = "main_1__genoa",
    ) -> None:
        self._base_polar: Optional[PolarTable] = base_polar
        self._hz = hz
        self._sail_type = sail_type
        self._min_samples = min_samples
        self._flush_interval_s = flush_interval_s
        self._db_path = db_path

        # TWA bins from base polar (or default upwind/downwind set)
        if base_polar and base_polar.twa_values:
            self._twa_bins = sorted(base_polar.twa_values)
        else:
            self._twa_bins = [37.0, 52.0, 60.0, 75.0, 90.0, 110.0, 120.0, 135.0, 150.0]

        # Decimation: accumulate at 1 Hz
        self._decimation = max(1, hz)
        self._tick_count = 0

        # In-memory buffer of samples waiting to be flushed
        self._buffer: List[tuple] = []
        self._last_flush = time.monotonic()

        # TWS stability window (5 seconds of raw TWS values)
        self._stability_samples = hz * 5
        self._tws_window: deque = deque(maxlen=max(1, self._stability_samples))

        # Maneuver cooldown tracking
        self._last_maneuver_time: float = 0.0

        # Cached learned polar
        self._learned_polar: Optional[PolarTable] = None
        self._last_rebuild: Optional[str] = None

        # Lazy DB connection
        self._conn: Optional[sqlite3.Connection] = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            if self._db_path:
                self._conn = sqlite3.connect(self._db_path)
                self._conn.row_factory = sqlite3.Row
                self._conn.execute("PRAGMA journal_mode=WAL")
            else:
                self._conn = get_connection()
            init_schema(self._conn)
        return self._conn

    # ── Public API ─────────────────────────────────────────────────

    def update(
        self,
        state: BoatState,
        in_maneuver: bool = False,
        session_id: Optional[int] = None,
    ) -> None:
        """Feed a pipeline tick.  Accumulates sample if conditions are stable."""
        # Track TWS for stability check (every tick, before decimation)
        if state.tws_kt is not None:
            self._tws_window.append(state.tws_kt)

        # Track maneuver timing
        if in_maneuver:
            self._last_maneuver_time = time.monotonic()

        # Decimation: only process every Nth tick (1 Hz effective)
        self._tick_count += 1
        if self._tick_count < self._decimation:
            return
        self._tick_count = 0

        # Stability check
        if not self._is_stable(state, in_maneuver):
            return

        # Assign to bin
        result = self._assign_bin(state.tws_kt, state.twa_deg)
        if result is None:
            return
        tws_bin, twa_bin = result

        # Buffer sample
        self._buffer.append((
            session_id,
            datetime.now(timezone.utc).isoformat(),
            tws_bin,
            twa_bin,
            state.bsp_kt,
            state.tws_kt,
            abs(state.twa_deg),
            state.perf_pct,
            self._sail_type,
        ))

        # Auto-flush on interval
        if time.monotonic() - self._last_flush >= self._flush_interval_s:
            self.flush()

    def flush(self) -> None:
        """Write buffered samples to SQLite."""
        if not self._buffer:
            return
        conn = self._get_conn()
        conn.executemany(
            """INSERT INTO polar_samples
               (session_id, timestamp, tws_bin, twa_bin, bsp_kt, tws_kt, twa_deg, perf_pct, sail_type)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            self._buffer,
        )
        conn.commit()
        self._buffer.clear()
        self._last_flush = time.monotonic()

    def rebuild(self, session_ids: Optional[List[int]] = None) -> Optional[PolarTable]:
        """Recompute learned polar from accumulated samples.

        Args:
            session_ids: If provided, only use samples from these sessions.
                         If None, use samples from all sessions marked
                         polar_included=1.

        Returns a new PolarTable that merges learned data with the base,
        or None if no bins have sufficient samples.

        Upwind bins (TWA < 90) are shared across all sail types since
        gennaker/runner sails are only used downwind.
        """
        self.flush()  # ensure all buffered data is in DB

        conn = self._get_conn()

        if session_ids is not None:
            # Explicit session list
            placeholders = ",".join("?" for _ in session_ids)
            rows = conn.execute(
                f"""SELECT tws_bin, twa_bin, bsp_kt FROM polar_samples
                   WHERE session_id IN ({placeholders})
                     AND ((twa_bin < 90) OR (twa_bin >= 90 AND sail_type = ?))
                   ORDER BY tws_bin, twa_bin""",
                (*session_ids, self._sail_type),
            ).fetchall()
        else:
            # All samples from sessions marked as included
            rows = conn.execute(
                """SELECT ps.tws_bin, ps.twa_bin, ps.bsp_kt
                   FROM polar_samples ps
                   LEFT JOIN sessions s ON ps.session_id = s.id
                   WHERE (s.polar_included = 1 OR s.id IS NULL)
                     AND ((ps.twa_bin < 90) OR (ps.twa_bin >= 90 AND ps.sail_type = ?))
                   ORDER BY ps.tws_bin, ps.twa_bin""",
                (self._sail_type,),
            ).fetchall()

        if not rows:
            return None

        # Group samples by bin
        from collections import defaultdict
        bins: Dict[Tuple[int, float], List[float]] = defaultdict(list)
        for row in rows:
            bins[(row["tws_bin"], row["twa_bin"])].append(row["bsp_kt"])

        # Compute 95th percentile per bin
        now_iso = datetime.now(timezone.utc).isoformat()
        learned_bins: Dict[Tuple[int, float], BinStats] = {}
        for (tws_bin, twa_bin), bsp_values in bins.items():
            count = len(bsp_values)
            sorted_vals = sorted(bsp_values)
            # 95th percentile using nearest-rank method
            idx = int(math.ceil(0.95 * count)) - 1
            idx = max(0, min(idx, count - 1))
            bsp_p95 = sorted_vals[idx]

            learned_bins[(tws_bin, twa_bin)] = BinStats(
                tws_bin=tws_bin,
                twa_bin=twa_bin,
                bsp_p95=bsp_p95,
                sample_count=count,
                updated_at=now_iso,
            )

            # Update polar_learned cache
            conn.execute(
                """INSERT OR REPLACE INTO polar_learned
                   (sail_type, tws_bin, twa_bin, bsp_p95, sample_count, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (self._sail_type, tws_bin, twa_bin, bsp_p95, count, now_iso),
            )
        conn.commit()

        # Merge with base polar
        merged = self._merge_with_base(learned_bins)
        if merged is not None:
            self._learned_polar = merged
            self._last_rebuild = now_iso
            self._export_snapshot(merged, learned_bins)

        return merged

    @property
    def learned_polar(self) -> Optional[PolarTable]:
        """The most recently rebuilt learned polar, or None."""
        return self._learned_polar

    @property
    def base_polar(self) -> Optional[PolarTable]:
        """The original base polar table, or None."""
        return self._base_polar

    def get_stats(self) -> dict:
        """Summary statistics for polar learning progress.

        Only counts samples from sessions marked as polar_included.
        Upwind bins (TWA < 90) are shared across all sail types.
        """
        conn = self._get_conn()
        total = conn.execute(
            """SELECT COUNT(*) FROM polar_samples ps
               LEFT JOIN sessions s ON ps.session_id = s.id
               WHERE (s.polar_included = 1 OR s.id IS NULL)
                 AND ((ps.twa_bin < 90) OR (ps.twa_bin >= 90 AND ps.sail_type = ?))""",
            (self._sail_type,),
        ).fetchone()[0]
        bins_filled = conn.execute(
            """SELECT COUNT(DISTINCT ps.tws_bin || '_' || ps.twa_bin) FROM polar_samples ps
               LEFT JOIN sessions s ON ps.session_id = s.id
               WHERE (s.polar_included = 1 OR s.id IS NULL)
                 AND ((ps.twa_bin < 90) OR (ps.twa_bin >= 90 AND ps.sail_type = ?))""",
            (self._sail_type,),
        ).fetchone()[0]
        bins_ready = conn.execute(
            """SELECT COUNT(*) FROM polar_learned
               WHERE sail_type = ? AND sample_count >= ?""",
            (self._sail_type, self._min_samples),
        ).fetchone()[0]

        total_bins = 17 * len(self._twa_bins)  # 4-20 kt × TWA breakpoints

        return {
            "total_samples": total,
            "buffered": len(self._buffer),
            "bins_filled": bins_filled,
            "bins_total": total_bins,
            "bins_ready": bins_ready,
            "coverage_pct": round(bins_ready / total_bins * 100, 1) if total_bins > 0 else 0,
            "last_rebuild": self._last_rebuild,
            "has_learned_polar": self._learned_polar is not None,
        }

    def get_coverage_matrix(self) -> List[dict]:
        """Per-bin sample counts and learned BSP.

        Upwind learned bins (TWA < 90) are shared — show them regardless
        of sail type.  Downwind bins are sail-type-specific.
        """
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT tws_bin, twa_bin, bsp_p95, sample_count
               FROM polar_learned
               WHERE sail_type = ?
               ORDER BY tws_bin, twa_bin""",
            (self._sail_type,),
        ).fetchall()

        result = []
        for row in rows:
            base_bsp = None
            if self._base_polar:
                base_bsp = self._base_polar.bsp(row["twa_bin"], float(row["tws_bin"]))

            result.append({
                "tws": row["tws_bin"],
                "twa": row["twa_bin"],
                "count": row["sample_count"],
                "bsp_p95": round(row["bsp_p95"], 2),
                "base_bsp": round(base_bsp, 2) if base_bsp is not None else None,
                "ready": row["sample_count"] >= self._min_samples,
            })
        return result

    def get_session_polar_stats(self) -> List[dict]:
        """Per-session polar sample counts for the current sail type."""
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT ps.session_id, COUNT(*) as sample_count,
                      MIN(ps.timestamp) as first_sample,
                      MAX(ps.timestamp) as last_sample
               FROM polar_samples ps
               WHERE (ps.twa_bin < 90) OR (ps.twa_bin >= 90 AND ps.sail_type = ?)
               GROUP BY ps.session_id
               ORDER BY first_sample DESC""",
            (self._sail_type,),
        ).fetchall()
        return [
            {
                "session_id": row["session_id"],
                "sample_count": row["sample_count"],
                "first_sample": row["first_sample"],
                "last_sample": row["last_sample"],
            }
            for row in rows
        ]

    def reset(self) -> None:
        """Clear accumulated data for this sail type (memory + SQLite)."""
        self._buffer.clear()
        self._tws_window.clear()
        self._learned_polar = None
        self._last_rebuild = None
        conn = self._get_conn()
        conn.execute("DELETE FROM polar_samples WHERE sail_type = ?", (self._sail_type,))
        conn.execute("DELETE FROM polar_learned WHERE sail_type = ?", (self._sail_type,))
        conn.commit()

    # ── Private helpers ────────────────────────────────────────────

    def _is_stable(self, state: BoatState, in_maneuver: bool) -> bool:
        """Check if conditions are stable enough to accumulate."""
        # Required data present
        if state.bsp_kt is None or state.twa_deg is None or state.tws_kt is None:
            return False

        # Range checks
        if state.bsp_kt < self.MIN_BSP_KT or state.bsp_kt > self.MAX_BSP_KT:
            return False
        if state.tws_kt < self.MIN_TWS_KT or state.tws_kt > self.MAX_TWS_KT:
            return False
        if abs(state.twa_deg) < 25:
            return False

        # Maneuver exclusion
        if in_maneuver:
            return False
        if time.monotonic() - self._last_maneuver_time < self.MANEUVER_COOLDOWN_S:
            return False

        # TWS stability: range in 5s window must be < threshold
        if len(self._tws_window) >= self._stability_samples:
            tws_range = max(self._tws_window) - min(self._tws_window)
            if tws_range > self.TWS_STABILITY_THRESHOLD:
                return False

        # Sensor freshness (9999 = default/not tracked → skip check)
        wam = state.wind_age_ms if state.wind_age_ms is not None else 9999
        bam = state.bsp_age_ms if state.bsp_age_ms is not None else 9999
        if 0 < wam < 9999 and wam > 2000:
            return False
        if 0 < bam < 9999 and bam > 2000:
            return False

        return True

    def _assign_bin(
        self, tws: float, twa: float
    ) -> Optional[Tuple[int, float]]:
        """Assign TWS/TWA values to the nearest bin.

        Returns (tws_bin, twa_bin) or None if outside range.
        """
        # TWS: round to nearest integer, clamp to 4-20
        tws_bin = round(tws)
        if tws_bin < 4 or tws_bin > 20:
            return None

        # TWA: find nearest breakpoint from base polar
        abs_twa = abs(twa)
        if not self._twa_bins:
            return None

        twa_bin = min(self._twa_bins, key=lambda x: abs(x - abs_twa))

        # Reject if too far from nearest bin (> half distance to next neighbor)
        idx = self._twa_bins.index(twa_bin)
        if idx > 0:
            lo_dist = twa_bin - self._twa_bins[idx - 1]
        else:
            lo_dist = float("inf")
        if idx < len(self._twa_bins) - 1:
            hi_dist = self._twa_bins[idx + 1] - twa_bin
        else:
            hi_dist = float("inf")
        max_tolerance = min(lo_dist, hi_dist) / 2.0
        if abs(abs_twa - twa_bin) > max_tolerance:
            return None

        return (tws_bin, twa_bin)

    def _merge_with_base(
        self, learned_bins: Dict[Tuple[int, float], BinStats]
    ) -> Optional[PolarTable]:
        """Build a PolarTable merging learned data with the base polar."""
        merged_grid: Dict[Tuple[float, float], float] = {}
        tws_set: set = set()
        twa_set: set = set(self._twa_bins)

        for tws in range(4, 21):
            tws_f = float(tws)
            tws_set.add(tws_f)
            for twa in self._twa_bins:
                key = (tws, twa)
                base_bsp = (
                    self._base_polar.bsp(twa, tws_f) if self._base_polar else None
                )
                learned = learned_bins.get(key)

                if learned and learned.sample_count >= self._min_samples:
                    if base_bsp is not None:
                        # Weighted blend: weight grows with sample count
                        weight = min(
                            0.9,
                            learned.sample_count
                            / (learned.sample_count + self._min_samples),
                        )
                        merged_grid[(tws_f, twa)] = (
                            weight * learned.bsp_p95 + (1 - weight) * base_bsp
                        )
                    else:
                        merged_grid[(tws_f, twa)] = learned.bsp_p95
                elif base_bsp is not None:
                    merged_grid[(tws_f, twa)] = base_bsp
                # else: no data for this bin — skip

        if not merged_grid:
            return None

        # Recompute upwind/downwind targets from the merged grid
        upwind_targets = {}
        downwind_targets = {}
        for tws in range(4, 21):
            tws_f = float(tws)
            best_up_vmg = 0.0
            best_down_vmg = 0.0
            for twa in self._twa_bins:
                bsp = merged_grid.get((tws_f, twa))
                if bsp is None:
                    continue
                vmg = bsp * math.cos(math.radians(twa))
                if twa < 90 and vmg > best_up_vmg:
                    best_up_vmg = vmg
                    upwind_targets[tws_f] = (twa, bsp, round(vmg, 3))
                if twa > 90 and abs(vmg) > best_down_vmg:
                    best_down_vmg = abs(vmg)
                    downwind_targets[tws_f] = (twa, bsp, round(abs(vmg), 3))

        return PolarTable(
            tws_values=sorted(tws_set),
            twa_values=sorted(twa_set),
            bsp_grid=merged_grid,
            upwind_targets=upwind_targets,
            downwind_targets=downwind_targets,
        )

    def _export_snapshot(
        self,
        polar: PolarTable,
        learned_bins: Dict[Tuple[int, float], BinStats],
    ) -> Optional[str]:
        """Save a timestamped polar snapshot to data/polars/.

        Returns the file path, or None on failure.
        """
        try:
            polars_dir = Path("data/polars")
            polars_dir.mkdir(parents=True, exist_ok=True)

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            sail_tag = self._sail_type

            # Build JSON in the same format as the base polar file
            polar_data = []
            for (tws, twa), bsp in sorted(polar.bsp_grid.items()):
                polar_data.append({"tws": tws, "twa": twa, "metricValue": round(bsp, 2)})

            targets = []
            # Upwind targets
            for metric in ("BoatSpeed", "TWA", "VMG"):
                target_data = []
                for tws_f in sorted(polar.upwind_targets):
                    twa_val, bsp_val, vmg_val = polar.upwind_targets[tws_f]
                    val = {"BoatSpeed": bsp_val, "TWA": twa_val, "VMG": vmg_val}[metric]
                    target_data.append({"tws": tws_f, "metricValue": round(val, 2)})
                targets.append({"pointOfSail": "Upwind", "metric": metric, "targetData": target_data})

            for metric in ("BoatSpeed", "TWA", "VMG"):
                target_data = []
                for tws_f in sorted(polar.downwind_targets):
                    twa_val, bsp_val, vmg_val = polar.downwind_targets[tws_f]
                    val = {"BoatSpeed": bsp_val, "TWA": twa_val, "VMG": vmg_val}[metric]
                    target_data.append({"tws": tws_f, "metricValue": round(val, 2)})
                targets.append({"pointOfSail": "Downwind", "metric": metric, "targetData": target_data})

            # Bin details (samples, p95, base comparison)
            bin_details = []
            for (tws, twa), stats in sorted(learned_bins.items()):
                base_bsp = self._base_polar.bsp(twa, float(tws)) if self._base_polar else None
                bin_details.append({
                    "tws": tws, "twa": twa,
                    "bsp_p95": round(stats.bsp_p95, 2),
                    "samples": stats.sample_count,
                    "base_bsp": round(base_bsp, 2) if base_bsp is not None else None,
                })

            doc = {
                "name": f"Learned Polar {sail_tag} {ts}",
                "sail_type": sail_tag,
                "created": datetime.now(timezone.utc).isoformat(),
                "total_samples": sum(s.sample_count for s in learned_bins.values()),
                "bins_ready": sum(1 for s in learned_bins.values() if s.sample_count >= self._min_samples),
                "targets": targets,
                "polars": [{"metric": "BoatSpeed", "polarData": polar_data}],
                "learned_bins": bin_details,
            }

            path = polars_dir / f"learned_{sail_tag}_{ts}.json"
            path.write_text(json.dumps(doc, indent=2))
            return str(path)
        except Exception:
            return None
