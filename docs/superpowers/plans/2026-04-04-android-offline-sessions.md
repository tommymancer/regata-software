# Android Offline Sessions — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add offline session review to the Aquarela Android app with auto-sync, session stats (VMG/VMC), maneuver analysis, and performance-colored GPS track maps.

**Architecture:** Two-phase build. Phase A: backend changes (add Perf/BRG to CSV, VMG/VMC-based maneuver loss, persist maneuvers, new API endpoint). Phase B: Android app (Room DB, auto-sync, Compose UI with bottom nav, session list/detail, osmdroid map).

**Tech Stack:** Python/FastAPI/SQLite (backend), Kotlin/Jetpack Compose/Room/osmdroid (Android)

**Spec:** `docs/superpowers/specs/2026-04-04-android-offline-sessions-design.md`

---

## Phase A: Backend Changes

### Task 1: Add `Perf` and `BRG` columns to CSV logger

**Files:**
- Modify: `aquarela/logging/csv_logger.py:19-22` (CSV_HEADER)
- Modify: `aquarela/logging/csv_logger.py:111-128` (row construction)
- Modify: `tests/test_csv_logger.py` (update column count assertions)

- [ ] **Step 1: Update test expectations for 18 columns**

In `tests/test_csv_logger.py`, update tests to expect 18 columns instead of 16:

```python
# In test_handles_none_fields (line 90):
assert row.count(",") == 17  # 18 columns = 17 commas

# In test_csv_column_count (line 107):
assert len(parts) == 18
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/test_csv_logger.py -v`
Expected: 2 failures (column count mismatch)

- [ ] **Step 3: Update CSV_HEADER**

In `aquarela/logging/csv_logger.py`, replace lines 19-22:

```python
CSV_HEADER = (
    "Timestamp,Lat,Lon,SOG,COG,Heading,BSP,AWA,AWS,"
    "TWA,TWS,TWD,Heel,Trim,Depth,MagneticVariation,Perf,BRG\n"
)
```

- [ ] **Step 4: Update row construction**

In `aquarela/logging/csv_logger.py`, replace lines 111-128. After the `MagneticVariation` field, add Perf and BRG:

```python
        row = (
            f"{ts},"
            f"{_fmt(state.lat, 7)},"
            f"{_fmt(state.lon, 7)},"
            f"{_fmt(state.sog_kt)},"
            f"{_fmt(state.cog_deg, 1)},"
            f"{_fmt(state.heading_mag, 1)},"
            f"{_fmt(state.bsp_kt)},"
            f"{_fmt(state.awa_deg, 1)},"
            f"{_fmt(state.aws_kt)},"
            f"{_fmt(state.twa_deg, 1)},"
            f"{_fmt(state.tws_kt)},"
            f"{_fmt(state.twd_deg, 1)},"
            f"{_fmt(state.heel_deg, 1)},"
            f"{_fmt(state.trim_deg, 1)},"
            f"{_fmt(state.depth_m)},"
            f"{_fmt(state.magnetic_variation, 1)},"
            f"{_fmt(state.perf_pct, 1)},"
            f"{_fmt(state.btw_deg, 1)}\n"
        )
```

- [ ] **Step 5: Update header test**

In `tests/test_csv_logger.py`, update `test_header_matches_njord_spec` — the test asserts `header == CSV_HEADER` which auto-passes since it compares against the constant. No change needed there, but update the docstring of `csv_logger.py` (lines 7-8):

```python
"""Aquarela CSV logger.

Writes an 18-column CSV at 2 Hz (decimated from the 10 Hz pipeline).
Each sailing session gets its own file under data/sessions/.

CSV format:
  Timestamp,Lat,Lon,SOG,COG,Heading,BSP,AWA,AWS,TWA,TWS,TWD,Heel,Trim,Depth,MagneticVariation,Perf,BRG
"""
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/test_csv_logger.py -v`
Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add aquarela/logging/csv_logger.py tests/test_csv_logger.py
git commit -m "feat: add Perf and BRG columns to CSV logger"
```

---

### Task 2: Refactor ManeuverDetector for VMG/VMC-based loss metrics

**Files:**
- Modify: `aquarela/training/maneuvers.py` (ManeuverEvent, _Sample, ManeuverDetector)
- Modify: `tests/test_maneuvers.py` (update tests)

- [ ] **Step 1: Update ManeuverEvent tests**

In `tests/test_maneuvers.py`, update `test_maneuver_event_to_dict` (line 114):

```python
    def test_maneuver_event_to_dict(self):
        ev = ManeuverEvent(
            maneuver_type="tack",
            entry_time=100.0,
            exit_time=103.0,
            wall_time="2026-04-04T14:30:00Z",
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
        d = ev.to_dict()
        assert d["type"] == "tack"
        assert d["bsp_before"] == 6.0
        assert d["recovery_secs"] == 4.2
        assert d["vmg_loss_nm"] == 0.0015
        assert d["vmc_loss_nm"] == 0.0012
        assert d["wall_time"] == "2026-04-04T14:30:00Z"
        assert d["lat"] == 46.002
        assert "distance_lost_nm" not in d
```

Add a test for VMG/VMC loss calculation:

```python
    def test_vmg_loss_calculation(self):
        """VMG loss should be based on VMG difference, not BSP."""
        d = ManeuverDetector(hz=10)
        d.COOLDOWN_SECS = 0
        d.METRIC_WINDOW = 0.5

        # Sail close-hauled on port: HDG=300, TWA=-35, BSP=6
        # VMG = abs(6 * cos(-35°)) = 4.91 kt
        for _ in range(20):
            d.update(heading=300.0, twa=-35.0, bsp=6.0,
                     sog=5.8, cog=295.0, brg_to_mark=None,
                     lat=46.0, lon=8.9, wall_time="2026-04-04T14:30:00Z")
            time.sleep(0.01)

        # Tack: HDG swings to 30, TWA flips to +35, BSP drops
        completed = None
        for _ in range(50):
            result = d.update(heading=30.0, twa=35.0, bsp=3.0,
                              sog=2.8, cog=25.0, brg_to_mark=None,
                              lat=46.0, lon=8.9, wall_time="2026-04-04T14:30:01Z")
            if result is not None:
                completed = result
                break
            time.sleep(0.01)

        if completed is None:
            for _ in range(100):
                result = d.update(heading=30.0, twa=35.0, bsp=5.5,
                                  sog=5.3, cog=25.0, brg_to_mark=None,
                                  lat=46.0, lon=8.9, wall_time="2026-04-04T14:30:03Z")
                if result is not None:
                    completed = result
                    break
                time.sleep(0.01)

        if completed:
            assert completed.vmg_loss_nm is not None
            assert completed.vmg_loss_nm >= 0
            assert completed.vmc_loss_nm is None  # no mark active
            assert completed.lat == pytest.approx(46.0)
            assert completed.wall_time is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/test_maneuvers.py -v`
Expected: failures (new fields don't exist, update() signature changed)

- [ ] **Step 3: Update existing tests to new update() signature**

All existing calls to `d.update(heading=..., twa=..., bsp=...)` in `tests/test_maneuvers.py` need the new keyword args. Add defaults so existing tests pass with minimal changes — add these kwargs to every `d.update()` call:

```python
d.update(heading=300.0, twa=-35.0, bsp=6.0,
         sog=5.8, cog=295.0, brg_to_mark=None,
         lat=46.0, lon=8.9, wall_time="2026-04-04T14:30:00Z")
```

For `test_none_inputs_ignored`, update to:

```python
    def test_none_inputs_ignored(self):
        d = ManeuverDetector(hz=10)
        result = d.update(None, None, None, None, None, None, None, None, None)
        assert result is None
        result = d.update(45.0, None, 6.0, None, None, None, None, None, None)
        assert result is None
```

- [ ] **Step 4: Update ManeuverEvent dataclass**

Replace the `ManeuverEvent` dataclass in `aquarela/training/maneuvers.py` (lines 21-54):

```python
@dataclass
class ManeuverEvent:
    """Recorded tack or gybe with metrics."""

    maneuver_type: str  # "tack" or "gybe"
    entry_time: float  # monotonic timestamp
    exit_time: float = 0.0
    wall_time: Optional[str] = None  # ISO 8601
    lat: Optional[float] = None
    lon: Optional[float] = None
    bsp_before: float = 0.0
    bsp_min: float = 999.0
    bsp_after: float = 0.0
    recovery_secs: Optional[float] = None
    vmg_before: Optional[float] = None
    vmg_loss_nm: Optional[float] = None
    vmc_before: Optional[float] = None
    vmc_loss_nm: Optional[float] = None
    hdg_before: float = 0.0
    hdg_after: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "type": self.maneuver_type,
            "entry_time": self.entry_time,
            "exit_time": self.exit_time,
            "wall_time": self.wall_time,
            "lat": self.lat,
            "lon": self.lon,
            "bsp_before": round(self.bsp_before, 2),
            "bsp_min": round(self.bsp_min, 2),
            "bsp_after": round(self.bsp_after, 2),
            "recovery_secs": (
                round(self.recovery_secs, 1) if self.recovery_secs is not None else None
            ),
            "vmg_before": (
                round(self.vmg_before, 2) if self.vmg_before is not None else None
            ),
            "vmg_loss_nm": (
                round(self.vmg_loss_nm, 4) if self.vmg_loss_nm is not None else None
            ),
            "vmc_before": (
                round(self.vmc_before, 2) if self.vmc_before is not None else None
            ),
            "vmc_loss_nm": (
                round(self.vmc_loss_nm, 4) if self.vmc_loss_nm is not None else None
            ),
            "hdg_before": round(self.hdg_before, 1),
            "hdg_after": round(self.hdg_after, 1),
        }
```

- [ ] **Step 5: Update _Sample dataclass**

Replace the `_Sample` dataclass (lines 57-64):

```python
@dataclass
class _Sample:
    """Pipeline sample for the sliding window."""

    t: float        # monotonic time
    hdg: float      # heading degrees
    twa: float      # signed TWA
    bsp: float      # boat speed
    sog: float      # speed over ground
    cog: float      # course over ground
    brg: Optional[float]  # bearing to active mark (None if no mark)
    lat: Optional[float]
    lon: Optional[float]
    wall_time: Optional[str]
```

- [ ] **Step 6: Update ManeuverDetector.update() signature and _detect/_start_maneuver**

Replace the `update` method signature (lines 94-118):

```python
    def update(
        self,
        heading: Optional[float],
        twa: Optional[float],
        bsp: Optional[float],
        sog: Optional[float] = None,
        cog: Optional[float] = None,
        brg_to_mark: Optional[float] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        wall_time: Optional[str] = None,
    ) -> Optional[ManeuverEvent]:
        """Feed a pipeline step; returns a completed ManeuverEvent or None."""
        if heading is None or twa is None or bsp is None:
            return None

        now = time.monotonic()
        sample = _Sample(
            t=now, hdg=heading, twa=twa, bsp=bsp,
            sog=sog or 0.0, cog=cog or 0.0,
            brg=brg_to_mark, lat=lat, lon=lon, wall_time=wall_time,
        )
        self._window.append(sample)

        cutoff = now - self.WINDOW_SECS
        while self._window and self._window[0].t < cutoff:
            self._window.popleft()

        if self._active is not None:
            return self._track_recovery(sample, now)

        return self._detect(sample, now)
```

Update `_start_maneuver` (lines 147-181) to capture VMG/VMC and position:

```python
    def _start_maneuver(
        self,
        maneuver_type: str,
        now: float,
        oldest: _Sample,
        current: _Sample,
    ) -> None:
        """Begin tracking a new maneuver."""
        import math

        pre_samples = [
            s for s in self._window
            if s.t < now - (now - oldest.t) / 2
        ]
        bsp_before = (
            sum(s.bsp for s in pre_samples) / len(pre_samples)
            if pre_samples else oldest.bsp
        )
        bsp_min = min(s.bsp for s in self._window)

        # VMG before: average abs(BSP * cos(TWA)) in pre-samples
        vmg_before = None
        if pre_samples:
            vmgs = [abs(s.bsp * math.cos(math.radians(s.twa))) for s in pre_samples]
            vmg_before = sum(vmgs) / len(vmgs)

        # VMC before: average SOG * cos(COG - BRG) in pre-samples (if BRG available)
        vmc_before = None
        brg_samples = [s for s in pre_samples if s.brg is not None]
        if brg_samples:
            vmcs = [s.sog * math.cos(math.radians(s.cog - s.brg)) for s in brg_samples]
            vmc_before = sum(vmcs) / len(vmcs)

        self._active = ManeuverEvent(
            maneuver_type=maneuver_type,
            entry_time=oldest.t,
            exit_time=now,
            wall_time=current.wall_time,
            lat=current.lat,
            lon=current.lon,
            bsp_before=bsp_before,
            bsp_min=bsp_min,
            vmg_before=vmg_before,
            vmc_before=vmc_before,
            hdg_before=oldest.hdg,
            hdg_after=current.hdg,
        )
        self._post_samples = []
        self._last_detection = now
        return None
```

- [ ] **Step 7: Update _finalise() for VMG/VMC loss**

Replace `_finalise` (lines 211-241):

```python
    def _finalise(self, now: float) -> ManeuverEvent:
        """Complete the maneuver event and return it."""
        import math

        ev = self._active
        assert ev is not None

        if self._post_samples:
            ev.bsp_after = sum(s.bsp for s in self._post_samples) / len(
                self._post_samples
            )

        duration = now - ev.entry_time

        # VMG loss: (vmg_before - avg_vmg_during) * duration / 3600
        all_samples = list(self._window) + self._post_samples
        if ev.vmg_before is not None and all_samples:
            vmgs = [abs(s.bsp * math.cos(math.radians(s.twa))) for s in all_samples]
            avg_vmg = sum(vmgs) / len(vmgs)
            ev.vmg_loss_nm = max(0, (ev.vmg_before - avg_vmg) * duration / 3600.0)

        # VMC loss: (vmc_before - avg_vmc_during) * duration / 3600
        if ev.vmc_before is not None:
            brg_samples = [s for s in all_samples if s.brg is not None]
            if brg_samples:
                vmcs = [s.sog * math.cos(math.radians(s.cog - s.brg)) for s in brg_samples]
                avg_vmc = sum(vmcs) / len(vmcs)
                ev.vmc_loss_nm = max(0, (ev.vmc_before - avg_vmc) * duration / 3600.0)

        if ev.recovery_secs is None:
            ev.recovery_secs = now - ev.exit_time

        self.events.append(ev)
        self._active = None
        self._post_samples = []
        return ev
```

- [ ] **Step 8: Update get_stats() to include VMG/VMC loss averages**

Replace `get_stats` (lines 249-280):

```python
    def get_stats(self) -> Dict:
        """Summary stats for all detected maneuvers."""
        tacks = [e for e in self.events if e.maneuver_type == "tack"]
        gybes = [e for e in self.events if e.maneuver_type == "gybe"]

        def _avg(items, attr):
            vals = [getattr(e, attr) for e in items if getattr(e, attr) is not None]
            return round(sum(vals) / len(vals), 4) if vals else None

        return {
            "total_tacks": len(tacks),
            "total_gybes": len(gybes),
            "avg_tack_recovery": _avg(tacks, "recovery_secs"),
            "avg_gybe_recovery": _avg(gybes, "recovery_secs"),
            "avg_tack_bsp_min": _avg(tacks, "bsp_min"),
            "avg_gybe_bsp_min": _avg(gybes, "bsp_min"),
            "avg_tack_vmg_loss_nm": _avg(tacks, "vmg_loss_nm"),
            "avg_gybe_vmg_loss_nm": _avg(gybes, "vmg_loss_nm"),
            "avg_tack_vmc_loss_nm": _avg(tacks, "vmc_loss_nm"),
            "avg_gybe_vmc_loss_nm": _avg(gybes, "vmc_loss_nm"),
        }
```

- [ ] **Step 9: Run tests**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/test_maneuvers.py -v`
Expected: all pass

- [ ] **Step 10: Commit**

```bash
git add aquarela/training/maneuvers.py tests/test_maneuvers.py
git commit -m "feat: VMG/VMC-based maneuver loss metrics with position and wall-clock time"
```

---

### Task 3: Persist maneuvers to SQLite + update pipeline

**Files:**
- Modify: `aquarela/logging/db.py` (add maneuvers table + migration)
- Modify: `aquarela/training/maneuvers.py` (add persist method)
- Modify: `aquarela/main.py` (update ManeuverDetector call + persist on detection)
- Create: `tests/test_maneuver_persistence.py`

- [ ] **Step 1: Write test for maneuver persistence**

Create `tests/test_maneuver_persistence.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/test_maneuver_persistence.py -v`
Expected: ImportError (persist_maneuver, list_maneuvers_for_session don't exist)

- [ ] **Step 3: Add maneuvers table to db schema**

In `aquarela/logging/db.py`, add the maneuvers table inside `init_schema` — append this before the closing `""")` of `conn.executescript(...)` at line 86:

```sql
        CREATE TABLE IF NOT EXISTS maneuvers (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id      INTEGER REFERENCES sessions(id),
            maneuver_type   TEXT NOT NULL,
            wall_time       TEXT,
            lat             REAL,
            lon             REAL,
            bsp_before      REAL,
            bsp_min         REAL,
            bsp_after       REAL,
            recovery_secs   REAL,
            vmg_before      REAL,
            vmg_loss_nm     REAL,
            vmc_before      REAL,
            vmc_loss_nm     REAL,
            hdg_before      REAL,
            hdg_after       REAL
        );

        CREATE INDEX IF NOT EXISTS idx_maneuvers_session
            ON maneuvers(session_id);
```

- [ ] **Step 4: Add persist_maneuver and list_maneuvers_for_session functions**

At the bottom of `aquarela/training/maneuvers.py`, add:

```python
def persist_maneuver(
    conn: "sqlite3.Connection",
    session_id: int,
    event: ManeuverEvent,
) -> None:
    """Insert a completed maneuver event into the database."""
    conn.execute(
        """INSERT INTO maneuvers
           (session_id, maneuver_type, wall_time, lat, lon,
            bsp_before, bsp_min, bsp_after, recovery_secs,
            vmg_before, vmg_loss_nm, vmc_before, vmc_loss_nm,
            hdg_before, hdg_after)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            session_id,
            event.maneuver_type,
            event.wall_time,
            event.lat,
            event.lon,
            event.bsp_before,
            event.bsp_min,
            event.bsp_after,
            event.recovery_secs,
            event.vmg_before,
            event.vmg_loss_nm,
            event.vmc_before,
            event.vmc_loss_nm,
            event.hdg_before,
            event.hdg_after,
        ),
    )
    conn.commit()


def list_maneuvers_for_session(
    conn: "sqlite3.Connection",
    session_id: int,
) -> list:
    """Retrieve all maneuvers for a given session."""
    cur = conn.execute(
        "SELECT * FROM maneuvers WHERE session_id = ? ORDER BY wall_time",
        (session_id,),
    )
    return [dict(row) for row in cur.fetchall()]
```

Add `import sqlite3` at the top of the file (or use string annotation as shown).

- [ ] **Step 5: Run tests**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/test_maneuver_persistence.py -v`
Expected: all pass

- [ ] **Step 6: Wire into main pipeline — update ManeuverDetector call + persist**

In `aquarela/main.py`, replace lines 327-329 (the existing `maneuver_detector.update(...)` call):

```python
                    maneuver_result = maneuver_detector.update(
                        heading=state.heading_mag,
                        twa=state.twa_deg,
                        bsp=state.bsp_kt,
                        sog=state.sog_kt,
                        cog=state.cog_deg,
                        brg_to_mark=state.btw_deg,
                        lat=state.lat,
                        lon=state.lon,
                        wall_time=state.timestamp.strftime("%Y-%m-%dT%H:%M:%S.") +
                            f"{state.timestamp.microsecond // 1000:03d}Z",
                    )
                    if maneuver_result and session_manager.active_session:
                        from aquarela.training.maneuvers import persist_maneuver
                        persist_maneuver(
                            session_manager._get_conn(),
                            session_manager.active_session.id,
                            maneuver_result,
                        )
```

Note: Uses `session_manager._get_conn()` (not `._conn`) to ensure the connection is initialized.

- [ ] **Step 7: Commit**

```bash
git add aquarela/logging/db.py aquarela/training/maneuvers.py aquarela/main.py tests/test_maneuver_persistence.py
git commit -m "feat: persist maneuvers to SQLite with VMG/VMC loss metrics"
```

---

### Task 4: New API endpoint `GET /api/sessions/{id}/maneuvers`

**Files:**
- Modify: `aquarela/api/sessions.py`

- [ ] **Step 1: Add endpoint**

In `aquarela/api/sessions.py`, add at the bottom:

```python
@router.get("/{session_id}/maneuvers")
async def session_maneuvers(session_id: int):
    """List all maneuvers for a specific session."""
    from ..training.maneuvers import list_maneuvers_for_session
    mgr = _mgr()
    rows = list_maneuvers_for_session(mgr._get_conn(), session_id)
    return rows
```

Note: Uses the existing `_mgr()` helper (not `_manager()`). Uses `_get_conn()` to ensure connection is initialized.

- [ ] **Step 2: Commit**

```bash
git add aquarela/api/sessions.py
git commit -m "feat: add GET /api/sessions/{id}/maneuvers endpoint"
```

---

## Phase B: Android App

### Task 5: Add Compose, Room, and osmdroid dependencies

**Files:**
- Modify: `aquarela-android/app/build.gradle.kts`
- Modify: `aquarela-android/build.gradle.kts` (if needed for Compose compiler)

- [ ] **Step 1: Update build.gradle.kts**

Replace `aquarela-android/app/build.gradle.kts`:

```kotlin
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.google.devtools.ksp")
}

android {
    namespace = "com.aquarela.viewer"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.aquarela.viewer"
        minSdk = 29
        targetSdk = 34
        versionCode = 2
        versionName = "2.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
    }

    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.8"
    }
}

dependencies {
    // Existing
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.11.0")
    implementation("androidx.webkit:webkit:1.9.0")

    // Compose
    implementation(platform("androidx.compose:compose-bom:2024.02.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.activity:activity-compose:1.8.2")
    implementation("androidx.navigation:navigation-compose:2.7.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.7.0")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.7.0")

    // Room
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    ksp("androidx.room:room-compiler:2.6.1")

    // osmdroid (OpenStreetMap)
    implementation("org.osmdroid:osmdroid-android:6.1.18")

    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")
}
```

Check if the project-level `build.gradle.kts` needs KSP plugin. Read it first:

```kotlin
// In aquarela-android/build.gradle.kts, add to plugins block:
id("com.google.devtools.ksp") version "1.9.22-1.0.17" apply false
```

- [ ] **Step 2: Sync and build**

Run: `cd /Users/tommaso/Documents/regata-software/aquarela-android && ./gradlew assembleDebug`
Expected: build succeeds

- [ ] **Step 3: Commit**

```bash
cd /Users/tommaso/Documents/regata-software
git add aquarela-android/app/build.gradle.kts aquarela-android/build.gradle.kts
git commit -m "feat: add Compose, Room, osmdroid dependencies to Android app"
```

---

### Task 6: Room database entities and DAOs

**Files:**
- Create: `aquarela-android/app/src/main/java/com/aquarela/viewer/data/Session.kt`
- Create: `aquarela-android/app/src/main/java/com/aquarela/viewer/data/TrackPoint.kt`
- Create: `aquarela-android/app/src/main/java/com/aquarela/viewer/data/Maneuver.kt`
- Create: `aquarela-android/app/src/main/java/com/aquarela/viewer/data/SessionDao.kt`
- Create: `aquarela-android/app/src/main/java/com/aquarela/viewer/data/TrackPointDao.kt`
- Create: `aquarela-android/app/src/main/java/com/aquarela/viewer/data/ManeuverDao.kt`
- Create: `aquarela-android/app/src/main/java/com/aquarela/viewer/data/AppDatabase.kt`

- [ ] **Step 1: Create Session entity**

Create `data/Session.kt`:

```kotlin
package com.aquarela.viewer.data

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "sessions")
data class Session(
    @PrimaryKey val id: Int,
    val start_time: String,
    val end_time: String,
    val session_type: String,
    val notes: String? = null,
    val duration_secs: Int = 0,
    val distance_nm: Double = 0.0,
    val avg_bsp_kt: Double = 0.0,
    val max_bsp_kt: Double = 0.0,
    val avg_tws_kt: Double = 0.0,
    val avg_vmg_kt: Double = 0.0,
    val avg_vmc_kt: Double? = null,
    val synced_at: String = "",
)
```

- [ ] **Step 2: Create TrackPoint entity**

Create `data/TrackPoint.kt`:

```kotlin
package com.aquarela.viewer.data

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "track_points",
    foreignKeys = [ForeignKey(
        entity = Session::class,
        parentColumns = ["id"],
        childColumns = ["session_id"],
        onDelete = ForeignKey.CASCADE,
    )],
    indices = [Index("session_id")],
)
data class TrackPoint(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val session_id: Int,
    val timestamp: String,
    val lat: Double,
    val lon: Double,
    val bsp_kt: Double = 0.0,
    val sog_kt: Double = 0.0,
    val cog_deg: Double = 0.0,
    val perf_pct: Double? = null,
    val hdg_deg: Double = 0.0,
    val twa_deg: Double = 0.0,
    val tws_kt: Double = 0.0,
    val brg_deg: Double? = null,
)
```

- [ ] **Step 3: Create Maneuver entity**

Create `data/Maneuver.kt`:

```kotlin
package com.aquarela.viewer.data

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "maneuvers",
    foreignKeys = [ForeignKey(
        entity = Session::class,
        parentColumns = ["id"],
        childColumns = ["session_id"],
        onDelete = ForeignKey.CASCADE,
    )],
    indices = [Index("session_id")],
)
data class Maneuver(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val session_id: Int,
    val maneuver_type: String,
    val entry_time: String,
    val lat: Double = 0.0,
    val lon: Double = 0.0,
    val bsp_before: Double = 0.0,
    val bsp_min: Double = 0.0,
    val bsp_after: Double = 0.0,
    val recovery_secs: Double = 0.0,
    val vmg_before: Double = 0.0,
    val vmg_loss_nm: Double = 0.0,
    val vmc_before: Double? = null,
    val vmc_loss_nm: Double? = null,
    val hdg_before: Double = 0.0,
    val hdg_after: Double = 0.0,
)
```

- [ ] **Step 4: Create DAOs**

Create `data/SessionDao.kt`:

```kotlin
package com.aquarela.viewer.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface SessionDao {
    @Query("SELECT * FROM sessions ORDER BY start_time DESC")
    fun allSessions(): Flow<List<Session>>

    @Query("SELECT id FROM sessions")
    suspend fun allSessionIds(): List<Int>

    @Query("SELECT * FROM sessions WHERE id = :id")
    suspend fun getById(id: Int): Session?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(session: Session)
}
```

Create `data/TrackPointDao.kt`:

```kotlin
package com.aquarela.viewer.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query

@Dao
interface TrackPointDao {
    @Query("SELECT * FROM track_points WHERE session_id = :sessionId ORDER BY timestamp")
    suspend fun forSession(sessionId: Int): List<TrackPoint>

    @Insert
    suspend fun insertAll(points: List<TrackPoint>)
}
```

Create `data/ManeuverDao.kt`:

```kotlin
package com.aquarela.viewer.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query

@Dao
interface ManeuverDao {
    @Query("SELECT * FROM maneuvers WHERE session_id = :sessionId ORDER BY entry_time")
    suspend fun forSession(sessionId: Int): List<Maneuver>

    @Insert
    suspend fun insertAll(maneuvers: List<Maneuver>)
}
```

- [ ] **Step 5: Create AppDatabase**

Create `data/AppDatabase.kt`:

```kotlin
package com.aquarela.viewer.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(
    entities = [Session::class, TrackPoint::class, Maneuver::class],
    version = 1,
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun sessionDao(): SessionDao
    abstract fun trackPointDao(): TrackPointDao
    abstract fun maneuverDao(): ManeuverDao

    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null

        fun get(context: Context): AppDatabase =
            INSTANCE ?: synchronized(this) {
                INSTANCE ?: Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "aquarela_sessions.db",
                ).build().also { INSTANCE = it }
            }
    }
}
```

- [ ] **Step 6: Build to verify Room compiles**

Run: `cd /Users/tommaso/Documents/regata-software/aquarela-android && ./gradlew assembleDebug`
Expected: build succeeds

- [ ] **Step 7: Commit**

```bash
cd /Users/tommaso/Documents/regata-software
git add aquarela-android/app/src/main/java/com/aquarela/viewer/data/
git commit -m "feat: Room database with Session, TrackPoint, Maneuver entities and DAOs"
```

---

### Task 7: CSV parser and utility functions

**Files:**
- Create: `aquarela-android/app/src/main/java/com/aquarela/viewer/util/CsvParser.kt`
- Create: `aquarela-android/app/src/main/java/com/aquarela/viewer/util/Haversine.kt`

- [ ] **Step 1: Create Haversine utility**

Create `util/Haversine.kt`:

```kotlin
package com.aquarela.viewer.util

import kotlin.math.*

/** Haversine distance in nautical miles between two lat/lon points. */
fun haversineNm(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
    val R = 3440.065 // Earth radius in NM
    val dLat = Math.toRadians(lat2 - lat1)
    val dLon = Math.toRadians(lon2 - lon1)
    val a = sin(dLat / 2).pow(2) +
            cos(Math.toRadians(lat1)) * cos(Math.toRadians(lat2)) *
            sin(dLon / 2).pow(2)
    return 2 * R * asin(sqrt(a))
}
```

- [ ] **Step 2: Create CsvParser**

Create `util/CsvParser.kt`:

```kotlin
package com.aquarela.viewer.util

import com.aquarela.viewer.data.TrackPoint
import kotlin.math.abs
import kotlin.math.cos

data class ParsedSession(
    val trackPoints: List<TrackPoint>,
    val durationSecs: Int,
    val distanceNm: Double,
    val avgBspKt: Double,
    val maxBspKt: Double,
    val avgTwsKt: Double,
    val avgVmgKt: Double,
    val avgVmcKt: Double?,
)

fun parseCsv(sessionId: Int, csvText: String): ParsedSession {
    val lines = csvText.lines().filter { it.isNotBlank() }
    if (lines.size < 2) return ParsedSession(
        emptyList(), 0, 0.0, 0.0, 0.0, 0.0, 0.0, null,
    )

    val header = lines[0].split(",")
    val colIndex = header.withIndex().associate { (i, name) -> name.trim() to i }

    fun col(row: List<String>, name: String): String? {
        val idx = colIndex[name] ?: return null
        return row.getOrNull(idx)?.takeIf { it.isNotBlank() }
    }

    fun colDouble(row: List<String>, name: String): Double? =
        col(row, name)?.toDoubleOrNull()

    val points = mutableListOf<TrackPoint>()

    for (i in 1 until lines.size) {
        val cols = lines[i].split(",")
        val lat = colDouble(cols, "Lat") ?: continue
        val lon = colDouble(cols, "Lon") ?: continue
        val ts = col(cols, "Timestamp") ?: continue

        points.add(
            TrackPoint(
                session_id = sessionId,
                timestamp = ts,
                lat = lat,
                lon = lon,
                bsp_kt = colDouble(cols, "BSP") ?: 0.0,
                sog_kt = colDouble(cols, "SOG") ?: 0.0,
                cog_deg = colDouble(cols, "COG") ?: 0.0,
                perf_pct = colDouble(cols, "Perf"),
                hdg_deg = colDouble(cols, "Heading") ?: 0.0,
                twa_deg = colDouble(cols, "TWA") ?: 0.0,
                tws_kt = colDouble(cols, "TWS") ?: 0.0,
                brg_deg = colDouble(cols, "BRG"),
            )
        )
    }

    if (points.isEmpty()) return ParsedSession(
        emptyList(), 0, 0.0, 0.0, 0.0, 0.0, 0.0, null,
    )

    // Duration: parse first and last timestamp
    val durationSecs = parseDurationSecs(points.first().timestamp, points.last().timestamp)

    // Distance: sum of haversine segments
    var distanceNm = 0.0
    for (i in 1 until points.size) {
        distanceNm += haversineNm(
            points[i - 1].lat, points[i - 1].lon,
            points[i].lat, points[i].lon,
        )
    }

    val avgBsp = points.map { it.bsp_kt }.average()
    val maxBsp = points.maxOf { it.bsp_kt }
    val avgTws = points.map { it.tws_kt }.average()

    // VMG: abs(BSP * cos(TWA))
    val vmgs = points.filter { it.twa_deg != 0.0 }
        .map { abs(it.bsp_kt * cos(Math.toRadians(it.twa_deg))) }
    val avgVmg = if (vmgs.isNotEmpty()) vmgs.average() else 0.0

    // VMC: SOG * cos(COG - BRG), only where BRG available
    val vmcPoints = points.filter { it.brg_deg != null }
    val avgVmc = if (vmcPoints.isNotEmpty()) {
        vmcPoints.map { pt ->
            pt.sog_kt * cos(Math.toRadians(pt.cog_deg - pt.brg_deg!!))
        }.average()
    } else null

    return ParsedSession(
        trackPoints = points,
        durationSecs = durationSecs,
        distanceNm = distanceNm,
        avgBspKt = avgBsp,
        maxBspKt = maxBsp,
        avgTwsKt = avgTws,
        avgVmgKt = avgVmg,
        avgVmcKt = avgVmc,
    )
}

private fun parseDurationSecs(first: String, last: String): Int {
    // Timestamps are ISO 8601: "2026-04-04T14:30:00.000Z"
    return try {
        val fmt = java.time.format.DateTimeFormatter.ISO_DATE_TIME
        val t1 = java.time.Instant.from(fmt.parse(first))
        val t2 = java.time.Instant.from(fmt.parse(last))
        java.time.Duration.between(t1, t2).seconds.toInt()
    } catch (e: Exception) {
        0
    }
}
```

- [ ] **Step 3: Build**

Run: `cd /Users/tommaso/Documents/regata-software/aquarela-android && ./gradlew assembleDebug`

- [ ] **Step 4: Commit**

```bash
cd /Users/tommaso/Documents/regata-software
git add aquarela-android/app/src/main/java/com/aquarela/viewer/util/
git commit -m "feat: CSV parser and haversine utility for Android"
```

---

### Task 8: SyncManager

**Files:**
- Create: `aquarela-android/app/src/main/java/com/aquarela/viewer/sync/SyncManager.kt`

- [ ] **Step 1: Create SyncManager**

Create `sync/SyncManager.kt`:

```kotlin
package com.aquarela.viewer.sync

import android.util.Log
import androidx.room.withTransaction
import com.aquarela.viewer.data.AppDatabase
import com.aquarela.viewer.data.Maneuver
import com.aquarela.viewer.data.Session
import com.aquarela.viewer.util.parseCsv
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import org.osmdroid.tileprovider.cachemanager.CacheManager
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.BoundingBox
import org.osmdroid.views.MapView
import java.net.HttpURLConnection
import java.net.URL

private const val TAG = "AquarelaSync"

class SyncManager(private val db: AppDatabase) {

    /** Sync sessions from the Pi. Returns the number of new sessions synced. */
    suspend fun sync(baseUrl: String): Int = withContext(Dispatchers.IO) {
        try {
            val sessionsJson = httpGet("$baseUrl/api/sessions?limit=200")
            val arr = JSONArray(sessionsJson)
            val existing = db.sessionDao().allSessionIds().toSet()
            var synced = 0

            for (i in 0 until arr.length()) {
                val obj = arr.getJSONObject(i)
                val id = obj.getInt("id")
                val endTime = obj.optString("end_time", "")
                val csvFile = obj.optString("csv_file", "")

                // Skip active or CSV-less sessions, and already-synced
                if (endTime.isBlank() || csvFile.isBlank() || id in existing) continue

                try {
                    syncSession(baseUrl, id, obj)
                    synced++
                } catch (e: Exception) {
                    Log.w(TAG, "Failed to sync session $id: ${e.message}")
                }
            }

            Log.d(TAG, "Sync complete: $synced new sessions")
            synced
        } catch (e: Exception) {
            Log.e(TAG, "Sync failed: ${e.message}")
            0
        }
    }

    private suspend fun syncSession(baseUrl: String, id: Int, meta: JSONObject) {
        val csvFile = meta.getString("csv_file")
        val filename = csvFile.substringAfterLast("/")

        // Download CSV
        val csvText = httpGet("$baseUrl/api/logs/$filename")
        val parsed = parseCsv(id, csvText)
        if (parsed.trackPoints.isEmpty()) return

        // Fetch maneuvers
        val maneuversJson = httpGet("$baseUrl/api/sessions/$id/maneuvers")
        val manArr = JSONArray(maneuversJson)
        val maneuvers = (0 until manArr.length()).map { i ->
            val m = manArr.getJSONObject(i)
            Maneuver(
                session_id = id,
                maneuver_type = m.optString("maneuver_type", ""),
                entry_time = m.optString("wall_time", ""),
                lat = m.optDouble("lat", 0.0),
                lon = m.optDouble("lon", 0.0),
                bsp_before = m.optDouble("bsp_before", 0.0),
                bsp_min = m.optDouble("bsp_min", 0.0),
                bsp_after = m.optDouble("bsp_after", 0.0),
                recovery_secs = m.optDouble("recovery_secs", 0.0),
                vmg_before = m.optDouble("vmg_before", 0.0),
                vmg_loss_nm = m.optDouble("vmg_loss_nm", 0.0),
                vmc_before = if (m.isNull("vmc_before")) null else m.optDouble("vmc_before"),
                vmc_loss_nm = if (m.isNull("vmc_loss_nm")) null else m.optDouble("vmc_loss_nm"),
                hdg_before = m.optDouble("hdg_before", 0.0),
                hdg_after = m.optDouble("hdg_after", 0.0),
            )
        }

        // Insert all in one transaction
        val now = java.time.Instant.now().toString()
        val session = Session(
            id = id,
            start_time = meta.optString("start_time", ""),
            end_time = meta.optString("end_time", ""),
            session_type = meta.optString("session_type", "training"),
            notes = meta.optString("notes", null),
            duration_secs = parsed.durationSecs,
            distance_nm = parsed.distanceNm,
            avg_bsp_kt = parsed.avgBspKt,
            max_bsp_kt = parsed.maxBspKt,
            avg_tws_kt = parsed.avgTwsKt,
            avg_vmg_kt = parsed.avgVmgKt,
            avg_vmc_kt = parsed.avgVmcKt,
            synced_at = now,
        )

        db.withTransaction {
            db.sessionDao().insert(session)
            db.trackPointDao().insertAll(parsed.trackPoints)
            if (maneuvers.isNotEmpty()) db.maneuverDao().insertAll(maneuvers)
        }

        Log.d(TAG, "Synced session $id: ${parsed.trackPoints.size} points, ${maneuvers.size} maneuvers")
    }

    /** Pre-download OSM tiles for the bounding box of track points at zoom 10-15. */
    fun preCacheTiles(mapView: MapView, points: List<com.aquarela.viewer.data.TrackPoint>) {
        if (points.isEmpty()) return
        val lats = points.map { it.lat }
        val lons = points.map { it.lon }
        val bb = BoundingBox(
            lats.max(), lons.max(), lats.min(), lons.min(),
        )
        val cm = CacheManager(mapView)
        cm.downloadAreaAsync(mapView.context, bb, 10, 15)
    }

    private fun httpGet(url: String): String {
        val conn = URL(url).openConnection() as HttpURLConnection
        conn.connectTimeout = 10_000
        conn.readTimeout = 30_000
        conn.requestMethod = "GET"
        return try {
            if (conn.responseCode != 200) throw Exception("HTTP ${conn.responseCode}")
            conn.inputStream.bufferedReader().readText()
        } finally {
            conn.disconnect()
        }
    }
}
```

- [ ] **Step 2: Build**

Run: `cd /Users/tommaso/Documents/regata-software/aquarela-android && ./gradlew assembleDebug`

- [ ] **Step 3: Commit**

```bash
cd /Users/tommaso/Documents/regata-software
git add aquarela-android/app/src/main/java/com/aquarela/viewer/sync/
git commit -m "feat: SyncManager — auto-downloads sessions, CSV, maneuvers from Pi"
```

---

### Task 9: Extract WebView into LiveTab composable

**Files:**
- Create: `aquarela-android/app/src/main/java/com/aquarela/viewer/live/LiveTab.kt`

- [ ] **Step 1: Create LiveTab**

Create `live/LiveTab.kt`. This extracts the WebView + Pi discovery logic from the current `MainActivity` into a Composable that can be hosted in a tab. The key logic (network binding, mDNS, probing) stays the same, wrapped in `AndroidView`:

```kotlin
package com.aquarela.viewer.live

import android.annotation.SuppressLint
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.net.wifi.WifiNetworkSuggestion
import android.net.wifi.WifiManager
import android.os.Environment
import android.content.ContentValues
import android.provider.MediaStore
import android.util.Log
import android.view.ViewGroup
import android.webkit.*
import android.widget.Toast
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread

private const val TAG = "AquarelaViewer"
private const val HOTSPOT_IP = "10.42.0.1"
private const val PORT = 8080
private const val PROBE_PATH = "/api/source"
private const val PROBE_TIMEOUT_MS = 3000
private const val AQUARELA_SSID = "Aquarela"
private const val AQUARELA_PSK = "aquarela1"
private const val NSD_SERVICE_TYPE = "_http._tcp."

@SuppressLint("SetJavaScriptEnabled")
@Composable
fun LiveTab(onPiFound: (String) -> Unit) {
    val context = LocalContext.current
    var resolvedUrl by remember { mutableStateOf<String?>(null) }
    var nsdDiscoveryActive by remember { mutableStateOf(false) }
    var wifiNetwork by remember { mutableStateOf<Network?>(null) }

    val connectivityManager = remember { context.getSystemService(ConnectivityManager::class.java) }
    val nsdManager = remember { context.getSystemService(NsdManager::class.java) }

    val webView = remember {
        WebView(context).apply {
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT,
            )
            settings.apply {
                javaScriptEnabled = true
                domStorageEnabled = true
                loadWithOverviewMode = true
                useWideViewPort = true
                cacheMode = WebSettings.LOAD_NO_CACHE
            }
            clearCache(true)
            CookieManager.getInstance().removeAllCookies(null)

            webViewClient = WebViewClient()
            webChromeClient = WebChromeClient()

            setDownloadListener { url, userAgent, contentDisposition, mimeType, _ ->
                val filename = URLUtil.guessFileName(url, contentDisposition, mimeType)
                Toast.makeText(context, "Downloading $filename…", Toast.LENGTH_SHORT).show()
                thread(name = "aquarela-download") {
                    try {
                        val conn = URL(url).openConnection() as HttpURLConnection
                        conn.setRequestProperty("User-Agent", userAgent)
                        conn.connectTimeout = 10_000
                        conn.readTimeout = 30_000
                        conn.connect()
                        if (conn.responseCode != 200) throw Exception("HTTP ${conn.responseCode}")
                        val bytes = conn.inputStream.use { it.readBytes() }
                        conn.disconnect()
                        val values = ContentValues().apply {
                            put(MediaStore.Downloads.DISPLAY_NAME, filename)
                            put(MediaStore.Downloads.MIME_TYPE, mimeType ?: "text/csv")
                            put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS)
                        }
                        val uri = context.contentResolver.insert(
                            MediaStore.Downloads.EXTERNAL_CONTENT_URI, values
                        ) ?: throw Exception("Failed to create file in Downloads")
                        context.contentResolver.openOutputStream(uri)!!.use { it.write(bytes) }
                        (context as? android.app.Activity)?.runOnUiThread {
                            Toast.makeText(context, "$filename saved to Downloads", Toast.LENGTH_SHORT).show()
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "Download failed", e)
                        (context as? android.app.Activity)?.runOnUiThread {
                            Toast.makeText(context, "Download failed: ${e.message}", Toast.LENGTH_LONG).show()
                        }
                    }
                }
            }
        }
    }

    fun probeHost(host: String): String? {
        return try {
            val url = URL("http://$host:$PORT$PROBE_PATH")
            val conn = url.openConnection() as HttpURLConnection
            conn.connectTimeout = PROBE_TIMEOUT_MS
            conn.readTimeout = PROBE_TIMEOUT_MS
            conn.requestMethod = "GET"
            val code = conn.responseCode
            conn.disconnect()
            if (code == 200) "http://$host:$PORT" else null
        } catch (e: Exception) { null }
    }

    fun onFound(url: String) {
        if (resolvedUrl != null) return
        resolvedUrl = url
        onPiFound(url)
        (context as? android.app.Activity)?.runOnUiThread {
            webView.loadUrl(url)
        }
    }

    DisposableEffect(Unit) {
        // Suggest WiFi
        val suggestion = WifiNetworkSuggestion.Builder()
            .setSsid(AQUARELA_SSID)
            .setWpa2Passphrase(AQUARELA_PSK)
            .setIsAppInteractionRequired(false)
            .build()
        val wifiManager = context.getSystemService(WifiManager::class.java)
        wifiManager.addNetworkSuggestions(listOf(suggestion))

        val nsdListener = object : NsdManager.DiscoveryListener {
            override fun onDiscoveryStarted(serviceType: String) {}
            override fun onServiceFound(serviceInfo: NsdServiceInfo) {
                if (serviceInfo.serviceName.contains("aquarela", ignoreCase = true)) {
                    nsdManager?.resolveService(serviceInfo, object : NsdManager.ResolveListener {
                        override fun onResolveFailed(si: NsdServiceInfo, err: Int) {}
                        override fun onServiceResolved(si: NsdServiceInfo) {
                            val host = si.host?.hostAddress ?: return
                            onFound("http://$host:${si.port}")
                        }
                    })
                }
            }
            override fun onServiceLost(serviceInfo: NsdServiceInfo) {}
            override fun onDiscoveryStopped(serviceType: String) {}
            override fun onStartDiscoveryFailed(serviceType: String, errorCode: Int) {}
            override fun onStopDiscoveryFailed(serviceType: String, errorCode: Int) {}
        }

        val networkCallback = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) {
                wifiNetwork = network
                connectivityManager.bindProcessToNetwork(network)
                // Probe hotspot
                thread(name = "aquarela-probe") {
                    probeHost(HOTSPOT_IP)?.let { onFound(it) }
                }
                // Start NSD
                if (!nsdDiscoveryActive) {
                    try {
                        nsdManager?.discoverServices(NSD_SERVICE_TYPE, NsdManager.PROTOCOL_DNS_SD, nsdListener)
                        nsdDiscoveryActive = true
                    } catch (_: Exception) {}
                }
            }
            override fun onLost(network: Network) {
                wifiNetwork = null
                resolvedUrl = null
                connectivityManager.bindProcessToNetwork(null)
            }
        }

        val request = NetworkRequest.Builder()
            .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
            .removeCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            .build()
        connectivityManager.requestNetwork(request, networkCallback)

        // Direct fallback
        thread(name = "aquarela-direct-fallback") {
            Thread.sleep(5000)
            if (resolvedUrl != null) return@thread
            connectivityManager.bindProcessToNetwork(null)
            for (host in listOf("localhost", "aquarela.local", "192.168.1.138", HOTSPOT_IP, "10.42.1.1", "10.0.2.2")) {
                if (resolvedUrl != null) return@thread
                probeHost(host)?.let { onFound(it); return@thread }
            }
        }

        onDispose {
            connectivityManager.bindProcessToNetwork(null)
            if (nsdDiscoveryActive) {
                try { nsdManager?.stopServiceDiscovery(nsdListener) } catch (_: Exception) {}
            }
            try { connectivityManager.unregisterNetworkCallback(networkCallback) } catch (_: Exception) {}
        }
    }

    AndroidView(
        factory = { webView },
        modifier = Modifier.fillMaxSize(),
    )
}
```

- [ ] **Step 2: Build**

Run: `cd /Users/tommaso/Documents/regata-software/aquarela-android && ./gradlew assembleDebug`

- [ ] **Step 3: Commit**

```bash
cd /Users/tommaso/Documents/regata-software
git add aquarela-android/app/src/main/java/com/aquarela/viewer/live/
git commit -m "feat: extract WebView + Pi discovery into LiveTab composable"
```

---

### Task 10: Session screens (list + detail + map)

**Files:**
- Create: `aquarela-android/app/src/main/java/com/aquarela/viewer/sessions/SessionListViewModel.kt`
- Create: `aquarela-android/app/src/main/java/com/aquarela/viewer/sessions/SessionListScreen.kt`
- Create: `aquarela-android/app/src/main/java/com/aquarela/viewer/sessions/SessionDetailViewModel.kt`
- Create: `aquarela-android/app/src/main/java/com/aquarela/viewer/sessions/SessionDetailScreen.kt`
- Create: `aquarela-android/app/src/main/java/com/aquarela/viewer/sessions/TrackMapView.kt`

- [ ] **Step 1: Create SessionListViewModel**

Create `sessions/SessionListViewModel.kt`:

```kotlin
package com.aquarela.viewer.sessions

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import com.aquarela.viewer.data.AppDatabase
import com.aquarela.viewer.data.Session
import kotlinx.coroutines.flow.Flow

class SessionListViewModel(app: Application) : AndroidViewModel(app) {
    private val db = AppDatabase.get(app)
    val sessions: Flow<List<Session>> = db.sessionDao().allSessions()
}
```

- [ ] **Step 2: Create SessionListScreen**

Create `sessions/SessionListScreen.kt`:

```kotlin
package com.aquarela.viewer.sessions

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.aquarela.viewer.data.Session

@Composable
fun SessionListScreen(
    onSessionClick: (Int) -> Unit,
    vm: SessionListViewModel = viewModel(),
) {
    val sessions by vm.sessions.collectAsState(initial = emptyList())

    if (sessions.isEmpty()) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text(
                "Nessuna sessione.\nConnettiti al Pi per sincronizzare.",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    } else {
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            items(sessions, key = { it.id }) { session ->
                SessionCard(session, onClick = { onSessionClick(session.id) })
            }
        }
    }
}

@Composable
private fun SessionCard(session: Session, onClick: () -> Unit) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
    ) {
        Column(Modifier.padding(16.dp)) {
            Text(
                formatDate(session.start_time),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
            )
            Spacer(Modifier.height(4.dp))
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(formatDuration(session.duration_secs))
                Text("%.1f nm".format(session.distance_nm))
                Text("TWS %.0f kt".format(session.avg_tws_kt))
            }
        }
    }
}

private fun formatDate(iso: String): String {
    return try {
        val instant = java.time.Instant.parse(iso)
        val zoned = instant.atZone(java.time.ZoneId.systemDefault())
        val fmt = java.time.format.DateTimeFormatter.ofPattern("d MMM yyyy — HH:mm")
        zoned.format(fmt)
    } catch (_: Exception) { iso }
}

private fun formatDuration(secs: Int): String {
    val h = secs / 3600
    val m = (secs % 3600) / 60
    return if (h > 0) "${h}h ${m}m" else "${m}m"
}
```

- [ ] **Step 3: Create SessionDetailViewModel**

Create `sessions/SessionDetailViewModel.kt`:

```kotlin
package com.aquarela.viewer.sessions

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.aquarela.viewer.data.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class SessionDetail(
    val session: Session,
    val trackPoints: List<TrackPoint>,
    val maneuvers: List<Maneuver>,
)

class SessionDetailViewModel(app: Application) : AndroidViewModel(app) {
    private val db = AppDatabase.get(app)
    private val _detail = MutableStateFlow<SessionDetail?>(null)
    val detail: StateFlow<SessionDetail?> = _detail

    fun load(sessionId: Int) {
        viewModelScope.launch {
            val session = db.sessionDao().getById(sessionId) ?: return@launch
            val points = db.trackPointDao().forSession(sessionId)
            val maneuvers = db.maneuverDao().forSession(sessionId)
            _detail.value = SessionDetail(session, points, maneuvers)
        }
    }
}
```

- [ ] **Step 4: Create TrackMapView**

Create `sessions/TrackMapView.kt`:

```kotlin
package com.aquarela.viewer.sessions

import android.graphics.Color
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import com.aquarela.viewer.data.Maneuver
import com.aquarela.viewer.data.TrackPoint
import org.osmdroid.config.Configuration
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.BoundingBox
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.MapView
import org.osmdroid.views.overlay.Marker
import org.osmdroid.views.overlay.Polyline

private const val MAX_RENDER_POINTS = 5000

@Composable
fun TrackMapView(
    trackPoints: List<TrackPoint>,
    maneuvers: List<Maneuver>,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current

    // Decimate if needed
    val displayPoints = remember(trackPoints) {
        if (trackPoints.size <= MAX_RENDER_POINTS) trackPoints
        else {
            val step = trackPoints.size / MAX_RENDER_POINTS + 1
            trackPoints.filterIndexed { i, _ -> i % step == 0 }
        }
    }

    AndroidView(
        factory = { ctx ->
            Configuration.getInstance().userAgentValue = ctx.packageName
            MapView(ctx).apply {
                setTileSource(TileSourceFactory.MAPNIK)
                setMultiTouchControls(true)
                minZoomLevel = 8.0
                maxZoomLevel = 18.0
            }
        },
        modifier = modifier,
        update = { mapView ->
            mapView.overlays.clear()

            if (displayPoints.isEmpty()) return@AndroidView

            // Draw track segments colored by performance
            var segStart = 0
            while (segStart < displayPoints.size - 1) {
                val perf = displayPoints[segStart].perf_pct
                val color = perfColor(perf)
                val segment = Polyline()
                segment.outlinePaint.color = color
                segment.outlinePaint.strokeWidth = 6f

                var i = segStart
                while (i < displayPoints.size) {
                    val pt = displayPoints[i]
                    segment.addPoint(GeoPoint(pt.lat, pt.lon))
                    // Start new segment when perf band changes
                    if (i > segStart && perfColor(pt.perf_pct) != color) break
                    i++
                }
                mapView.overlays.add(segment)
                segStart = (i - 1).coerceAtLeast(segStart + 1)
            }

            // Maneuver markers
            for (m in maneuvers) {
                val marker = Marker(mapView)
                marker.position = GeoPoint(m.lat, m.lon)
                marker.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
                marker.title = if (m.maneuver_type == "tack") "Tack" else "Gybe"
                marker.snippet = "Recovery: %.1fs".format(m.recovery_secs)
                mapView.overlays.add(marker)
            }

            // Zoom to fit
            val lats = displayPoints.map { it.lat }
            val lons = displayPoints.map { it.lon }
            val bb = BoundingBox(lats.max(), lons.max(), lats.min(), lons.min())
            mapView.zoomToBoundingBox(bb.increaseByScale(1.2f), false)
            mapView.invalidate()
        },
    )
}

private fun perfColor(perf: Double?): Int {
    if (perf == null) return Color.GRAY
    return when {
        perf >= 90.0 -> Color.parseColor("#4CAF50")  // green
        perf >= 70.0 -> Color.parseColor("#FFC107")  // yellow
        else -> Color.parseColor("#FF5722")           // red
    }
}
```

- [ ] **Step 5: Create SessionDetailScreen**

Create `sessions/SessionDetailScreen.kt`:

```kotlin
package com.aquarela.viewer.sessions

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.aquarela.viewer.data.Maneuver
import com.aquarela.viewer.data.Session

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SessionDetailScreen(
    sessionId: Int,
    onBack: () -> Unit,
    vm: SessionDetailViewModel = viewModel(),
) {
    LaunchedEffect(sessionId) { vm.load(sessionId) }
    val detail by vm.detail.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Sessione") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back")
                    }
                },
            )
        },
    ) { padding ->
        val d = detail
        if (d == null) {
            Box(Modifier.fillMaxSize().padding(padding))
        } else {
            Column(
                Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .verticalScroll(rememberScrollState()),
            ) {
                StatsSection(d.session)
                ManeuversSection(d.maneuvers)
                TrackMapView(
                    trackPoints = d.trackPoints,
                    maneuvers = d.maneuvers,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(400.dp)
                        .padding(12.dp),
                )
            }
        }
    }
}

@Composable
private fun StatsSection(s: Session) {
    Column(Modifier.padding(12.dp)) {
        Text("Statistiche", style = MaterialTheme.typography.titleMedium)
        Spacer(Modifier.height(8.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
            StatCard("Durata", formatDuration(s.duration_secs))
            StatCard("Distanza", "%.1f nm".format(s.distance_nm))
        }
        Spacer(Modifier.height(8.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
            StatCard("BSP", "%.1f / %.1f kt".format(s.avg_bsp_kt, s.max_bsp_kt))
            StatCard("VMG", "%.1f kt".format(s.avg_vmg_kt))
        }
        Spacer(Modifier.height(8.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
            StatCard("Vento", "TWS %.0f kt".format(s.avg_tws_kt))
            if (s.avg_vmc_kt != null) {
                StatCard("VMC", "%.1f kt".format(s.avg_vmc_kt))
            }
        }
    }
}

@Composable
private fun StatCard(label: String, value: String) {
    Card(Modifier.width(160.dp)) {
        Column(Modifier.padding(12.dp)) {
            Text(label, style = MaterialTheme.typography.labelSmall)
            Text(value, style = MaterialTheme.typography.titleLarge)
        }
    }
}

@Composable
private fun ManeuversSection(maneuvers: List<Maneuver>) {
    Column(Modifier.padding(12.dp)) {
        Text("Manovre", style = MaterialTheme.typography.titleMedium)
        Spacer(Modifier.height(8.dp))
        if (maneuvers.isEmpty()) {
            Text(
                "Nessuna manovra registrata.",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        } else {
            val tacks = maneuvers.filter { it.maneuver_type == "tack" }
            val gybes = maneuvers.filter { it.maneuver_type == "gybe" }
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(12.dp)) {
                    Text("Virate: ${tacks.size}  |  Strambate: ${gybes.size}")

                    val avgRecovery = maneuvers.map { it.recovery_secs }.average()
                    Text("Recovery medio: %.1fs".format(avgRecovery))

                    val avgVmgLoss = maneuvers.map { it.vmg_loss_nm }.average()
                    Text("VMG loss medio: %.4f nm".format(avgVmgLoss))

                    val vmcLosses = maneuvers.mapNotNull { it.vmc_loss_nm }
                    if (vmcLosses.isNotEmpty()) {
                        Text("VMC loss medio: %.4f nm".format(vmcLosses.average()))
                    }
                }
            }
        }
    }
}

private fun formatDuration(secs: Int): String {
    val h = secs / 3600
    val m = (secs % 3600) / 60
    return if (h > 0) "${h}h ${m}m" else "${m}m"
}
```

- [ ] **Step 6: Build**

Run: `cd /Users/tommaso/Documents/regata-software/aquarela-android && ./gradlew assembleDebug`

- [ ] **Step 7: Commit**

```bash
cd /Users/tommaso/Documents/regata-software
git add aquarela-android/app/src/main/java/com/aquarela/viewer/sessions/
git commit -m "feat: session list, detail, and track map screens with Compose"
```

---

### Task 11: Rewrite MainActivity with BottomNav + auto-sync

**Files:**
- Modify: `aquarela-android/app/src/main/java/com/aquarela/viewer/MainActivity.kt`
- Modify: `aquarela-android/app/src/main/res/layout/activity_main.xml` (no longer used, can keep for reference)
- Modify: `aquarela-android/app/src/main/AndroidManifest.xml` (add osmdroid config)

- [ ] **Step 1: Rewrite MainActivity**

Replace the entire content of `MainActivity.kt`:

```kotlin
package com.aquarela.viewer

import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.navigation.NavType
import androidx.navigation.compose.*
import androidx.navigation.navArgument
import com.aquarela.viewer.data.AppDatabase
import com.aquarela.viewer.live.LiveTab
import com.aquarela.viewer.sessions.SessionDetailScreen
import com.aquarela.viewer.sessions.SessionListScreen
import com.aquarela.viewer.sync.SyncManager
import kotlinx.coroutines.launch
import org.osmdroid.config.Configuration

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // osmdroid config
        Configuration.getInstance().load(this, getSharedPreferences("osmdroid", MODE_PRIVATE))

        setContent {
            MaterialTheme(colorScheme = darkColorScheme()) {
                AquarelaApp()
            }
        }
    }

    @Composable
    private fun AquarelaApp() {
        val navController = rememberNavController()
        var selectedTab by remember { mutableIntStateOf(0) }
        val scope = rememberCoroutineScope()
        val db = remember { AppDatabase.get(this@MainActivity) }
        val syncManager = remember { SyncManager(db) }

        Scaffold(
            bottomBar = {
                NavigationBar {
                    NavigationBarItem(
                        selected = selectedTab == 0,
                        onClick = {
                            selectedTab = 0
                            navController.navigate("live") {
                                popUpTo("live") { inclusive = true }
                            }
                        },
                        icon = { Icon(Icons.Default.PlayArrow, "Live") },
                        label = { Text("Live") },
                    )
                    NavigationBarItem(
                        selected = selectedTab == 1,
                        onClick = {
                            selectedTab = 1
                            navController.navigate("sessions") {
                                popUpTo("sessions") { inclusive = true }
                            }
                        },
                        icon = { Icon(Icons.Default.DateRange, "Sessioni") },
                        label = { Text("Sessioni") },
                    )
                }
            },
        ) { padding ->
            NavHost(
                navController,
                startDestination = "live",
                modifier = Modifier.padding(padding),
            ) {
                composable("live") {
                    LiveTab(
                        onPiFound = { url ->
                            scope.launch {
                                val count = syncManager.sync(url)
                                if (count > 0) {
                                    runOnUiThread {
                                        Toast.makeText(
                                            this@MainActivity,
                                            "$count sessioni sincronizzate",
                                            Toast.LENGTH_SHORT,
                                        ).show()
                                    }
                                }
                            }
                        },
                    )
                }
                composable("sessions") {
                    SessionListScreen(
                        onSessionClick = { id ->
                            navController.navigate("session/$id")
                        },
                    )
                }
                composable(
                    "session/{id}",
                    arguments = listOf(navArgument("id") { type = NavType.IntType }),
                ) { backStack ->
                    val id = backStack.arguments!!.getInt("id")
                    SessionDetailScreen(
                        sessionId = id,
                        onBack = { navController.popBackStack() },
                    )
                }
            }
        }
    }
}
```

- [ ] **Step 2: Update AndroidManifest for Compose activity**

In `AndroidManifest.xml`, the activity declaration should stay the same. The `setContentView` is replaced by `setContent` in code. The old XML layout is unused now but harmless.

- [ ] **Step 3: Build and test**

Run: `cd /Users/tommaso/Documents/regata-software/aquarela-android && ./gradlew assembleDebug`
Expected: build succeeds

- [ ] **Step 4: Commit**

```bash
cd /Users/tommaso/Documents/regata-software
git add aquarela-android/app/src/main/java/com/aquarela/viewer/MainActivity.kt
git commit -m "feat: rewrite MainActivity with BottomNav (Live + Sessioni) and auto-sync"
```

---

### Task 12: Tile pre-download during sync

**Files:**
- Modify: `aquarela-android/app/src/main/java/com/aquarela/viewer/sync/SyncManager.kt`

Tile pre-caching requires a MapView, which must be created on the main thread. The approach: after sync completes, the SessionDetailScreen's TrackMapView triggers tile caching when first displayed while online.

- [ ] **Step 1: Add tile pre-caching to TrackMapView**

In `sessions/TrackMapView.kt`, after `mapView.zoomToBoundingBox(...)`, add tile caching:

```kotlin
            // Pre-cache tiles for offline viewing
            try {
                val cm = CacheManager(mapView)
                cm.downloadAreaAsync(mapView.context, bb.increaseByScale(1.2f), 10, 15)
            } catch (e: Exception) {
                Log.w("TrackMap", "Tile cache failed: ${e.message}")
            }
```

This runs on the main thread (inside `AndroidView.update`) where MapView is safe to use. Tiles are cached on first view of each session's track. Subsequent offline views use the cached tiles.

Also update `SyncManager.kt`: remove the `preCacheTiles` method (it's no longer needed — caching happens in the map composable).

- [ ] **Step 2: Build and commit**

```bash
cd /Users/tommaso/Documents/regata-software
git add aquarela-android/app/src/main/java/com/aquarela/viewer/sync/SyncManager.kt
git commit -m "feat: pre-download OSM tiles for synced session tracks"
```

---

### Task 13: End-to-end verification

- [ ] **Step 1: Run all backend tests**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/ -v`
Expected: all pass

- [ ] **Step 2: Build Android APK**

Run: `cd /Users/tommaso/Documents/regata-software/aquarela-android && ./gradlew assembleDebug`
Expected: build succeeds

- [ ] **Step 3: Manual smoke test on emulator/device**

1. Install APK on device/emulator
2. Verify Live tab shows WebView and discovers Pi (if available)
3. Verify Sessioni tab shows empty state when no sessions synced
4. Connect to Pi → verify auto-sync toast
5. Verify session list populates after sync
6. Tap a session → verify stats, maneuvers, map display correctly
7. Go offline → verify sessions still viewable
8. Verify map shows territory (OSM tiles cached)

- [ ] **Step 4: Final commit**

```bash
cd /Users/tommaso/Documents/regata-software
git add -A
git commit -m "feat: Android offline sessions — complete implementation"
```
