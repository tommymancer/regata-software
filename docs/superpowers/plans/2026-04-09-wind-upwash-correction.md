# Wind Upwash Correction System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add wind correction (heel + upwash) with auto-learning and CAN bus output to the Aquarela sailing instrument pipeline.

**Architecture:** Three new modules: `wind_correction.py` (pure correction chain), `upwash_learning.py` (auto-learning from tacks), `can_writer.py` (NMEA 2000 output). Plus `upwash_table.py` for the data model. Correction inserts between calibration and true wind in the existing pipeline.

**Tech Stack:** Python 3.11+, math/numpy, python-can (existing dep), pytest

**Spec:** `docs/superpowers/specs/2026-04-09-wind-upwash-correction-design.md`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `aquarela/pipeline/upwash_table.py` | Create | UpwashTable dataclass: load/save JSON, bilinear interpolation, initial value generation |
| `aquarela/pipeline/wind_correction.py` | Create | Heel correction + upwash lookup. Pure functions. |
| `aquarela/pipeline/upwash_learning.py` | Create | Tack detection, validity filter, residual calc, table update |
| `aquarela/nmea/can_writer.py` | Create | PGN 130306 encoding, address claim, bus writing |
| `aquarela/pipeline/state.py` | Modify | Add wind correction + sail config fields |
| `aquarela/config.py` | Modify | Add sail inventory, upwash, CAN writer config |
| `aquarela/pipeline/damping.py` | Modify | Export ScalarBuffer for standalone heel damper |
| `aquarela/pipeline/true_wind.py` | Modify | Use corrected values with fallback |
| `aquarela/main.py` | Modify | Wire up correction, learning, heel damper, CAN writer |
| `tests/test_upwash_table.py` | Create | Table interpolation, JSON round-trip, initial values |
| `tests/test_wind_correction.py` | Create | Heel correction, upwash lookup, full chain |
| `tests/test_upwash_learning.py` | Create | Tack detection, filter, residual, update |
| `tests/test_can_writer.py` | Create | PGN encoding, address claim, toggle |

---

### Task 1: UpwashTable Data Model

**Files:**
- Create: `aquarela/pipeline/upwash_table.py`
- Create: `tests/test_upwash_table.py`

- [ ] **Step 1: Write test for initial value generation**

```python
# tests/test_upwash_table.py
"""Tests for upwash table data model."""

import pytest
import json
import tempfile
from pathlib import Path

from aquarela.pipeline.upwash_table import UpwashTable, UpwashTableSet


class TestUpwashTable:
    def test_initial_values_shape(self):
        """Table has correct dimensions: 33 AWA x 8 heel."""
        t = UpwashTable.with_initial_values()
        assert len(t.awa_breakpoints) == 33
        assert len(t.heel_breakpoints) == 8
        assert len(t.offsets) == 33
        assert all(len(row) == 8 for row in t.offsets)

    def test_initial_values_monotonic_awa(self):
        """Upwash offset decreases as AWA increases (for any heel)."""
        t = UpwashTable.with_initial_values()
        # At heel=0 (column 0), offsets should decrease from close-hauled to run
        col0 = [t.offsets[r][0] for r in range(len(t.awa_breakpoints))]
        # All values >= 0
        assert all(v >= 0 for v in col0)
        # First value (AWA=20) >= last value (AWA=180)
        assert col0[0] >= col0[-1]

    def test_initial_values_zero_at_run(self):
        """At AWA=180 (dead run), upwash is zero for all heel values."""
        t = UpwashTable.with_initial_values()
        last_row = t.offsets[-1]  # AWA=180
        assert all(v == 0.0 for v in last_row)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/test_upwash_table.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: Implement UpwashTable with initial values**

```python
# aquarela/pipeline/upwash_table.py
"""Upwash correction lookup table with bilinear interpolation.

Each table is a 2D grid indexed by AWA (20-180°, step 5°) and
heel (0-35°, step 5°). Values are upwash offset in degrees.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


# Default AWA breakpoints: 20 to 180, step 5 (33 points)
DEFAULT_AWA_BREAKPOINTS = list(range(20, 181, 5))
# Default heel breakpoints: 0 to 35, step 5 (8 points)
DEFAULT_HEEL_BREAKPOINTS = list(range(0, 36, 5))

# Initial upwash values from literature (AWA, offset_at_heel_0)
# Linear interpolation fills the rest
_INITIAL_REFERENCE = [
    # (awa, heel_0, heel_35)
    (20, 2.0, 5.5),
    (45, 1.5, 4.0),
    (90, 0.5, 1.0),
    (135, 0.0, 0.0),
    (180, 0.0, 0.0),
]


def _interpolate_1d(x: float, xs: list, ys: list) -> float:
    """Linear interpolation with clamping at boundaries."""
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            t = (x - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] + t * (ys[i + 1] - ys[i])
    return ys[-1]


@dataclass
class UpwashTable:
    """Single upwash correction table for one sail configuration."""

    awa_breakpoints: List[int] = field(default_factory=lambda: list(DEFAULT_AWA_BREAKPOINTS))
    heel_breakpoints: List[int] = field(default_factory=lambda: list(DEFAULT_HEEL_BREAKPOINTS))
    offsets: List[List[float]] = field(default_factory=list)
    observations: List[List[int]] = field(default_factory=list)
    last_updated: Optional[str] = None

    @classmethod
    def with_initial_values(cls) -> UpwashTable:
        """Create a table pre-populated with literature-based initial values."""
        ref_awas = [r[0] for r in _INITIAL_REFERENCE]
        ref_heel0 = [r[1] for r in _INITIAL_REFERENCE]
        ref_heel35 = [r[2] for r in _INITIAL_REFERENCE]

        offsets = []
        observations = []
        for awa in DEFAULT_AWA_BREAKPOINTS:
            val_at_0 = _interpolate_1d(awa, ref_awas, ref_heel0)
            val_at_35 = _interpolate_1d(awa, ref_awas, ref_heel35)
            row = []
            for heel in DEFAULT_HEEL_BREAKPOINTS:
                t = heel / 35.0
                row.append(round(val_at_0 + t * (val_at_35 - val_at_0), 2))
            offsets.append(row)
            observations.append([0] * len(DEFAULT_HEEL_BREAKPOINTS))

        return cls(
            offsets=offsets,
            observations=observations,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )

    def lookup(self, awa_deg: float, heel_deg: float) -> float:
        """Bilinear interpolation of upwash offset.

        Args:
            awa_deg: absolute apparent wind angle (0-180)
            heel_deg: absolute heel angle (0-35+)

        Returns:
            Upwash offset in degrees (always positive).
        """
        awa = max(self.awa_breakpoints[0], min(self.awa_breakpoints[-1], abs(awa_deg)))
        heel = max(self.heel_breakpoints[0], min(self.heel_breakpoints[-1], abs(heel_deg)))

        # Find surrounding AWA indices
        ai = 0
        for i in range(len(self.awa_breakpoints) - 1):
            if self.awa_breakpoints[i] <= awa <= self.awa_breakpoints[i + 1]:
                ai = i
                break
        else:
            ai = len(self.awa_breakpoints) - 2

        # Find surrounding heel indices
        hi = 0
        for i in range(len(self.heel_breakpoints) - 1):
            if self.heel_breakpoints[i] <= heel <= self.heel_breakpoints[i + 1]:
                hi = i
                break
        else:
            hi = len(self.heel_breakpoints) - 2

        # Bilinear interpolation
        awa0 = self.awa_breakpoints[ai]
        awa1 = self.awa_breakpoints[ai + 1]
        heel0 = self.heel_breakpoints[hi]
        heel1 = self.heel_breakpoints[hi + 1]

        ta = (awa - awa0) / (awa1 - awa0) if awa1 != awa0 else 0.0
        th = (heel - heel0) / (heel1 - heel0) if heel1 != heel0 else 0.0

        v00 = self.offsets[ai][hi]
        v01 = self.offsets[ai][hi + 1]
        v10 = self.offsets[ai + 1][hi]
        v11 = self.offsets[ai + 1][hi + 1]

        v0 = v00 + th * (v01 - v00)
        v1 = v10 + th * (v11 - v10)

        return v0 + ta * (v1 - v0)

    def update_nearest(self, awa_deg: float, heel_deg: float,
                       residual: float, learning_rate: float) -> None:
        """Update the nearest cell with a learning residual.

        Args:
            awa_deg: absolute AWA where the observation was made
            heel_deg: absolute heel where the observation was made
            residual: upwash error to correct for (degrees)
            learning_rate: fraction of residual to apply (0-1)
        """
        awa = abs(awa_deg)
        heel = abs(heel_deg)

        # Find nearest AWA index
        ai = min(range(len(self.awa_breakpoints)),
                 key=lambda i: abs(self.awa_breakpoints[i] - awa))
        # Find nearest heel index
        hi = min(range(len(self.heel_breakpoints)),
                 key=lambda i: abs(self.heel_breakpoints[i] - heel))

        self.offsets[ai][hi] += learning_rate * residual
        self.observations[ai][hi] += 1
        self.last_updated = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "awa_breakpoints": self.awa_breakpoints,
            "heel_breakpoints": self.heel_breakpoints,
            "offsets": self.offsets,
            "observations": self.observations,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, d: dict) -> UpwashTable:
        return cls(
            awa_breakpoints=d["awa_breakpoints"],
            heel_breakpoints=d["heel_breakpoints"],
            offsets=d["offsets"],
            observations=d["observations"],
            last_updated=d.get("last_updated"),
        )


# ── Six sail configuration keys ────────────────────────────────────────
SAIL_CONFIG_KEYS = [
    "main_1__jib",
    "main_1__genoa",
    "main_1__gennaker",
    "main_2__jib",
    "main_2__genoa",
    "main_2__gennaker",
]


@dataclass
class UpwashTableSet:
    """All six upwash tables, one per sail configuration."""

    tables: dict[str, UpwashTable] = field(default_factory=dict)
    version: str = "1.0"
    boat: str = "Nitro 80"

    @classmethod
    def with_initial_values(cls) -> UpwashTableSet:
        """Create all six tables with literature-based initial values."""
        tables = {key: UpwashTable.with_initial_values() for key in SAIL_CONFIG_KEYS}
        return cls(tables=tables)

    def get_table(self, sail_config_key: str) -> Optional[UpwashTable]:
        """Get the table for a given sail configuration."""
        return self.tables.get(sail_config_key)

    def save(self, path: str = "data/upwash-tables.json") -> None:
        """Save all tables to JSON."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": self.version,
            "boat": self.boat,
            "updated": datetime.now(timezone.utc).isoformat(),
            "sail_configs": {
                key: table.to_dict() for key, table in self.tables.items()
            },
        }
        with open(p, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str = "data/upwash-tables.json") -> UpwashTableSet:
        """Load tables from JSON. Returns initial values if file doesn't exist."""
        p = Path(path)
        if not p.exists():
            return cls.with_initial_values()
        with open(p) as f:
            data = json.load(f)
        tables = {}
        for key, tdata in data.get("sail_configs", {}).items():
            tables[key] = UpwashTable.from_dict(tdata)
        return cls(
            tables=tables,
            version=data.get("version", "1.0"),
            boat=data.get("boat", "Nitro 80"),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/test_upwash_table.py -v`
Expected: 3 passed

- [ ] **Step 5: Write test for bilinear interpolation**

Add to `tests/test_upwash_table.py`:

```python
class TestBilinearInterpolation:
    def test_at_grid_point(self):
        """Lookup at exact grid point returns that cell's value."""
        t = UpwashTable.with_initial_values()
        # AWA=20, heel=0 is the first cell
        val = t.lookup(20, 0)
        assert val == t.offsets[0][0]

    def test_at_grid_point_mid(self):
        """Lookup at an interior grid point."""
        t = UpwashTable.with_initial_values()
        # AWA=45 is index 5 (20,25,30,35,40,45), heel=10 is index 2
        val = t.lookup(45, 10)
        assert val == t.offsets[5][2]

    def test_between_points(self):
        """Interpolated value is between the four surrounding cells."""
        t = UpwashTable.with_initial_values()
        val = t.lookup(32.5, 7.5)
        # Should be between the 4 surrounding values
        corners = [
            t.offsets[2][1],  # AWA=30, heel=5
            t.offsets[2][2],  # AWA=30, heel=10
            t.offsets[3][1],  # AWA=35, heel=5
            t.offsets[3][2],  # AWA=35, heel=10
        ]
        assert min(corners) <= val <= max(corners)

    def test_clamp_low_awa(self):
        """AWA below 20 clamps to 20."""
        t = UpwashTable.with_initial_values()
        val_10 = t.lookup(10, 0)
        val_20 = t.lookup(20, 0)
        assert val_10 == val_20

    def test_clamp_high_heel(self):
        """Heel above 35 clamps to 35."""
        t = UpwashTable.with_initial_values()
        val_40 = t.lookup(90, 40)
        val_35 = t.lookup(90, 35)
        assert val_40 == val_35

    def test_symmetry_awa(self):
        """Absolute value used for AWA — negative gives same result."""
        t = UpwashTable.with_initial_values()
        assert t.lookup(45, 10) == t.lookup(-45, 10)
```

- [ ] **Step 6: Run to verify passes (implementation already handles these)**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/test_upwash_table.py -v`
Expected: 9 passed

- [ ] **Step 7: Write test for JSON round-trip**

Add to `tests/test_upwash_table.py`:

```python
class TestTableSetPersistence:
    def test_save_load_round_trip(self, tmp_path):
        """Save and load preserves all data."""
        path = str(tmp_path / "upwash.json")
        original = UpwashTableSet.with_initial_values()
        original.save(path)
        loaded = UpwashTableSet.load(path)

        assert set(loaded.tables.keys()) == set(original.tables.keys())
        for key in original.tables:
            orig_t = original.tables[key]
            load_t = loaded.tables[key]
            assert load_t.awa_breakpoints == orig_t.awa_breakpoints
            assert load_t.heel_breakpoints == orig_t.heel_breakpoints
            assert load_t.offsets == orig_t.offsets

    def test_load_missing_file_returns_defaults(self, tmp_path):
        """Loading from nonexistent path returns initial values."""
        path = str(tmp_path / "nonexistent.json")
        ts = UpwashTableSet.load(path)
        assert len(ts.tables) == 6
        assert "main_1__jib" in ts.tables

    def test_update_nearest_persists(self, tmp_path):
        """update_nearest changes the offset and increments observations."""
        t = UpwashTable.with_initial_values()
        orig = t.offsets[0][0]
        t.update_nearest(20, 0, 1.0, 0.1)
        assert t.offsets[0][0] == pytest.approx(orig + 0.1)
        assert t.observations[0][0] == 1
```

- [ ] **Step 8: Run to verify passes**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/test_upwash_table.py -v`
Expected: 12 passed

- [ ] **Step 9: Commit**

```bash
cd /Users/tommaso/Documents/regata-software
git add aquarela/pipeline/upwash_table.py tests/test_upwash_table.py
git commit -m "feat: add UpwashTable data model with bilinear interpolation and persistence"
```

---

### Task 2: Wind Correction Functions

**Files:**
- Create: `aquarela/pipeline/wind_correction.py`
- Create: `tests/test_wind_correction.py`

- [ ] **Step 1: Write tests for heel correction**

```python
# tests/test_wind_correction.py
"""Tests for wind correction chain (heel + upwash)."""

import math
import pytest
from datetime import datetime, timezone

from aquarela.pipeline.state import BoatState
from aquarela.pipeline.wind_correction import (
    correct_heel,
    correct_upwash,
    apply_wind_correction,
)
from aquarela.pipeline.upwash_table import UpwashTable


class TestHeelCorrection:
    def test_zero_heel_no_change(self):
        """With zero heel, AWA and AWS are unchanged."""
        awa, aws = correct_heel(awa_deg=-42.0, aws_kt=12.0, heel_deg=0.0)
        assert awa == pytest.approx(-42.0, abs=0.01)
        assert aws == pytest.approx(12.0, abs=0.01)

    def test_heel_opens_angle(self):
        """Heel correction should make the apparent angle slightly larger (abs)."""
        awa_raw = -30.0  # 30° port
        awa_corr, _ = correct_heel(awa_deg=awa_raw, aws_kt=15.0, heel_deg=20.0)
        # Corrected angle should be more negative (larger absolute value)
        assert abs(awa_corr) > abs(awa_raw)

    def test_heel_reduces_speed(self):
        """Heel correction reduces apparent wind speed (projection effect)."""
        _, aws_raw = correct_heel(awa_deg=-30.0, aws_kt=15.0, heel_deg=0.0)
        _, aws_heeled = correct_heel(awa_deg=-30.0, aws_kt=15.0, heel_deg=20.0)
        assert aws_heeled < aws_raw

    def test_beam_wind_no_speed_change(self):
        """At AWA=90, heel doesn't change AWS (sin(90)=1, cos(90)=0)."""
        _, aws = correct_heel(awa_deg=90.0, aws_kt=15.0, heel_deg=25.0)
        assert aws == pytest.approx(15.0, abs=0.01)

    def test_known_geometry(self):
        """Verify against hand-calculated value.
        AWA=45°, heel=20°:
        awa_heel = atan2(sin(45), cos(45)*cos(20))
                 = atan2(0.7071, 0.7071*0.9397)
                 = atan2(0.7071, 0.6644)
                 = 46.76°
        """
        awa, _ = correct_heel(awa_deg=45.0, aws_kt=10.0, heel_deg=20.0)
        assert awa == pytest.approx(46.76, abs=0.1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/test_wind_correction.py::TestHeelCorrection -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: Implement heel correction**

```python
# aquarela/pipeline/wind_correction.py
"""Wind correction chain: heel correction + upwash table lookup.

Pipeline order:
  1. Heel correction (geometric projection from tilted mast to horizontal)
  2. Upwash correction (2D table lookup, compensates sail-induced deflection)

These are pure functions — no state, no side effects.
"""

import math
from typing import Optional, Tuple

from .state import BoatState
from .upwash_table import UpwashTable


def correct_heel(
    awa_deg: float, aws_kt: float, heel_deg: float
) -> Tuple[float, float]:
    """Correct apparent wind for mast heel angle.

    Projects the wind vector from the tilted mast frame back to horizontal.

    Args:
        awa_deg: apparent wind angle (signed, degrees)
        aws_kt: apparent wind speed (knots)
        heel_deg: heel angle (degrees, signed ok — abs used internally)

    Returns:
        (awa_corrected, aws_corrected) in degrees and knots.
    """
    awa_rad = math.radians(awa_deg)
    heel_rad = math.radians(abs(heel_deg))

    sin_awa = math.sin(awa_rad)
    cos_awa = math.cos(awa_rad)
    cos_heel = math.cos(heel_rad)

    # Angle: project back to horizontal plane
    awa_corr = math.degrees(math.atan2(sin_awa, cos_awa * cos_heel))

    # Speed: magnitude of projected wind vector
    aws_corr = aws_kt * math.sqrt(
        cos_heel ** 2 * cos_awa ** 2 + sin_awa ** 2
    )

    return awa_corr, aws_corr


def correct_upwash(
    awa_deg: float, table: UpwashTable, heel_deg: float
) -> Tuple[float, float]:
    """Apply upwash correction from lookup table.

    Args:
        awa_deg: apparent wind angle after heel correction (signed, degrees)
        table: upwash lookup table for current sail config
        heel_deg: heel angle (degrees)

    Returns:
        (awa_corrected, upwash_offset) — corrected AWA and the offset applied.
    """
    offset = table.lookup(abs(awa_deg), abs(heel_deg))
    # Upwash shifts AWA toward the bow — correction pushes it back out
    sign = 1.0 if awa_deg >= 0 else -1.0
    awa_corr = awa_deg + sign * offset
    return awa_corr, offset


def apply_wind_correction(
    state: BoatState,
    table: Optional[UpwashTable],
    heel_smoothed: Optional[float] = None,
) -> None:
    """Apply full wind correction chain to BoatState in-place.

    Reads state.awa_deg, state.aws_kt, uses heel_smoothed (or state.heel_deg).
    Writes state.awa_corrected_deg, state.aws_corrected_kt,
    state.heel_correction_deg, state.upwash_offset_deg.

    If inputs are missing, leaves corrected fields as None (graceful degradation).
    """
    if state.awa_deg is None or state.aws_kt is None:
        return

    awa = state.awa_deg
    aws = state.aws_kt
    heel = heel_smoothed if heel_smoothed is not None else (state.heel_deg or 0.0)

    # Stage 2: heel correction
    if abs(heel) > 0.5:  # skip if negligible
        awa_heel, aws_heel = correct_heel(awa, aws, heel)
        state.heel_correction_deg = awa_heel - awa
    else:
        awa_heel = awa
        aws_heel = aws
        state.heel_correction_deg = 0.0

    # Stage 3: upwash correction
    if table is not None:
        awa_final, upwash_offset = correct_upwash(awa_heel, table, heel)
        state.upwash_offset_deg = upwash_offset
    else:
        awa_final = awa_heel
        state.upwash_offset_deg = 0.0

    state.awa_corrected_deg = awa_final
    state.aws_corrected_kt = aws_heel
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/test_wind_correction.py::TestHeelCorrection -v`
Expected: 5 passed

- [ ] **Step 5: Write tests for upwash correction and full chain**

Add to `tests/test_wind_correction.py`:

```python
class TestUpwashCorrection:
    @pytest.fixture
    def table(self):
        return UpwashTable.with_initial_values()

    def test_upwash_opens_angle_starboard(self, table):
        """On starboard tack (AWA > 0), upwash adds to AWA."""
        awa_corr, offset = correct_upwash(30.0, table, 10.0)
        assert offset > 0
        assert awa_corr > 30.0

    def test_upwash_opens_angle_port(self, table):
        """On port tack (AWA < 0), upwash makes AWA more negative."""
        awa_corr, offset = correct_upwash(-30.0, table, 10.0)
        assert offset > 0
        assert awa_corr < -30.0

    def test_no_upwash_at_run(self, table):
        """At AWA=180, upwash offset is zero."""
        _, offset = correct_upwash(180.0, table, 10.0)
        assert offset == pytest.approx(0.0, abs=0.01)


class TestApplyWindCorrection:
    def test_full_chain(self):
        """Full chain: calibrated values → corrected values populated."""
        state = BoatState.new()
        state.awa_deg = -30.0
        state.aws_kt = 15.0
        state.heel_deg = 15.0
        table = UpwashTable.with_initial_values()

        apply_wind_correction(state, table, heel_smoothed=15.0)

        assert state.awa_corrected_deg is not None
        assert state.aws_corrected_kt is not None
        assert state.heel_correction_deg is not None
        assert state.upwash_offset_deg is not None
        # Corrected AWA should be more negative (more open) than raw
        assert abs(state.awa_corrected_deg) > abs(state.awa_deg)

    def test_missing_awa_graceful(self):
        """Missing AWA — corrected fields stay None."""
        state = BoatState.new()
        state.aws_kt = 15.0
        apply_wind_correction(state, UpwashTable.with_initial_values())
        assert state.awa_corrected_deg is None

    def test_no_table_heel_only(self):
        """No upwash table — only heel correction applied."""
        state = BoatState.new()
        state.awa_deg = -30.0
        state.aws_kt = 15.0
        apply_wind_correction(state, table=None, heel_smoothed=20.0)
        assert state.awa_corrected_deg is not None
        assert state.upwash_offset_deg == 0.0
```

- [ ] **Step 6: Run all wind correction tests**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/test_wind_correction.py -v`
Expected: 11 passed

- [ ] **Step 7: Commit**

```bash
cd /Users/tommaso/Documents/regata-software
git add aquarela/pipeline/wind_correction.py tests/test_wind_correction.py
git commit -m "feat: add wind correction chain (heel + upwash)"
```

---

### Task 3: BoatState and Config Changes

**Files:**
- Modify: `aquarela/pipeline/state.py:44-56` (add corrected wind fields after calibrated block)
- Modify: `aquarela/config.py:9-53` (add sail inventory, upwash, CAN writer config)
- Modify: `aquarela/pipeline/damping.py:17-37` (export AngleBuffer)

- [ ] **Step 1: Add new fields to BoatState**

In `aquarela/pipeline/state.py`, after line 43 (`water_temp_c`), add:

```python
    # ── Wind correction (after calibration, before true wind) ──────────
    awa_corrected_deg: Optional[float] = None   # after heel + upwash correction
    aws_corrected_kt: Optional[float] = None    # after heel correction
    upwash_offset_deg: Optional[float] = None   # upwash offset applied (debug)
    heel_correction_deg: Optional[float] = None  # heel angle correction applied (debug)

    # ── Sail configuration ───────────────────────────────────────────────
    active_sail_config: Optional[str] = None     # e.g. "main_1__genoa"

    # ── Upwash learning status ──────────────────────────────────────────
    upwash_learning_status: Optional[str] = None  # waiting|pre_tack|post_tack|updated|rejected
```

Remove the existing `sail_type` field at line 90 (it's replaced by `active_sail_config`). Keep it but mark deprecated:

```python
    # ── Sail configuration (deprecated — use active_sail_config) ─────────
    sail_type: str = "racing_white"             # kept for backward compat
```

- [ ] **Step 2: Add new config fields to AquarelaConfig**

In `aquarela/config.py`, after line 21 (`tws_downwind_factor`), add:

```python
    # Sail inventory
    sails: dict = field(default_factory=lambda: {
        "mains": ["main_1", "main_2"],
        "headsails": {
            "jib": ["jib_1"],
            "genoa": ["genoa_1"],
            "gennaker": ["gennaker_1", "gennaker_2"],
        },
    })
    active_main: str = "main_1"
    active_headsail: str = "genoa_1"

    # Upwash learning
    upwash_learning_rate: float = 0.1
    upwash_learning_enabled: bool = True

    # CAN writer
    can_writer_enabled: bool = False
    can_writer_dry_run: bool = True
```

Update `load()` (around line 63) to read the new fields from JSON:

```python
            sails=raw.get("sails", {
                "mains": ["main_1", "main_2"],
                "headsails": {
                    "jib": ["jib_1"],
                    "genoa": ["genoa_1"],
                    "gennaker": ["gennaker_1", "gennaker_2"],
                },
            }),
            active_main=raw.get("active_main", "main_1"),
            active_headsail=raw.get("active_headsail", "genoa_1"),
            upwash_learning_rate=raw.get("upwash_learning_rate", 0.1),
            upwash_learning_enabled=raw.get("upwash_learning_enabled", True),
            can_writer_enabled=raw.get("can_writer_enabled", False),
            can_writer_dry_run=raw.get("can_writer_dry_run", True),
```

Update `save()` (around line 91) to write the new fields:

```python
            "sails": self.sails,
            "active_main": self.active_main,
            "active_headsail": self.active_headsail,
            "upwash_learning_rate": self.upwash_learning_rate,
            "upwash_learning_enabled": self.upwash_learning_enabled,
            "can_writer_enabled": self.can_writer_enabled,
            "can_writer_dry_run": self.can_writer_dry_run,
```

Add a helper method to AquarelaConfig to derive the sail config key:

```python
    def sail_config_key(self) -> str:
        """Derive the upwash table key from active sail selection.

        Maps active_headsail name to its category (jib/genoa/gennaker)
        using the headsails dict, then combines with active_main.
        """
        headsails = self.sails.get("headsails", {})
        category = "genoa"  # default
        for cat, names in headsails.items():
            if self.active_headsail in names:
                category = cat
                break
        return f"{self.active_main}__{category}"
```

- [ ] **Step 3: Export ScalarBuffer from damping.py**

In `aquarela/pipeline/damping.py`, rename `_ScalarBuffer` to `ScalarBuffer` (remove underscore prefix). Update the reference in `DampingFilters.__init__` on line 77.

Line 41: `class _ScalarBuffer:` → `class ScalarBuffer:`
Line 77: `self._filters[name] = _ScalarBuffer(max_len=buf_len)` → `self._filters[name] = ScalarBuffer(max_len=buf_len)`

Note: We use `ScalarBuffer` (not `AngleBuffer`) for heel damping. Heel is a signed value in the range -35 to +35 degrees — a simple moving average handles zero-crossing correctly for this small range. `_AngleBuffer` uses `% 360` which would destroy the sign.

- [ ] **Step 4: Run existing tests to verify nothing breaks**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/test_calibration.py tests/test_config.py tests/test_damping.py tests/test_derived.py -v`
Expected: All pass (the new fields have defaults, so existing tests are unaffected)

- [ ] **Step 5: Commit**

```bash
cd /Users/tommaso/Documents/regata-software
git add aquarela/pipeline/state.py aquarela/config.py aquarela/pipeline/damping.py
git commit -m "feat: add wind correction fields to BoatState and config"
```

---

### Task 4: Modify True Wind to Use Corrected Values

**Files:**
- Modify: `aquarela/pipeline/true_wind.py:57-76`
- Modify: `tests/test_true_wind.py` (if exists, add test for fallback)

- [ ] **Step 1: Write test for corrected-value routing**

Add to `tests/test_true_wind.py` (or create if needed):

```python
class TestTrueWindWithCorrectedValues:
    def test_uses_corrected_when_available(self):
        """compute_true_wind uses awa_corrected_deg and aws_corrected_kt."""
        state = BoatState.new()
        state.bsp_kt = 6.0
        state.awa_deg = -30.0
        state.aws_kt = 15.0
        state.awa_corrected_deg = -33.0  # more open after correction
        state.aws_corrected_kt = 14.5
        state.heading_mag = 180.0
        state.magnetic_variation = 2.5

        compute_true_wind(state)

        # TWA should be computed from corrected values, not raw
        twa_expected, _ = calc_true_wind(6.0, -33.0, 14.5)
        assert state.twa_deg == pytest.approx(twa_expected, abs=0.01)

    def test_falls_back_to_uncorrected(self):
        """When corrected fields are None, uses awa_deg/aws_kt."""
        state = BoatState.new()
        state.bsp_kt = 6.0
        state.awa_deg = -30.0
        state.aws_kt = 15.0
        state.heading_mag = 180.0
        state.magnetic_variation = 2.5
        # awa_corrected_deg and aws_corrected_kt are None (default)

        compute_true_wind(state)

        twa_expected, _ = calc_true_wind(6.0, -30.0, 15.0)
        assert state.twa_deg == pytest.approx(twa_expected, abs=0.01)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/test_true_wind.py::TestTrueWindWithCorrectedValues -v`
Expected: FAIL — test_uses_corrected_when_available fails (currently ignores corrected fields)

- [ ] **Step 3: Modify compute_true_wind to prefer corrected values**

In `aquarela/pipeline/true_wind.py`, modify `compute_true_wind()` (lines 57-76):

```python
def compute_true_wind(state: BoatState) -> None:
    """Mutate *state* in-place: compute TWA, TWS, TWD from calibrated values.

    Prefers corrected wind values (awa_corrected_deg, aws_corrected_kt) when
    available. Falls back to calibrated values (awa_deg, aws_kt).
    """
    # Prefer corrected, fallback to calibrated
    awa = state.awa_corrected_deg if state.awa_corrected_deg is not None else state.awa_deg
    aws = state.aws_corrected_kt if state.aws_corrected_kt is not None else state.aws_kt

    if state.bsp_kt is None or awa is None or aws is None:
        return

    twa, tws = calc_true_wind(state.bsp_kt, awa, aws)
    state.twa_deg = twa
    state.tws_kt = tws

    if state.heading_mag is not None:
        state.twd_deg = calc_twd(twa, state.heading_mag, state.magnetic_variation)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/test_true_wind.py -v`
Expected: All pass

- [ ] **Step 5: Run full test suite to check no regressions**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/ -v --tb=short`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
cd /Users/tommaso/Documents/regata-software
git add aquarela/pipeline/true_wind.py tests/test_true_wind.py
git commit -m "feat: true wind uses corrected apparent wind with fallback"
```

---

### Task 5: Pipeline Integration (main.py)

**Files:**
- Modify: `aquarela/main.py` (imports, global state, pipeline loop)

- [ ] **Step 1: Add imports and global state**

At the top of `main.py`, add imports after line 36:

```python
from .pipeline.wind_correction import apply_wind_correction
from .pipeline.upwash_table import UpwashTableSet
from .pipeline.damping import ScalarBuffer
```

In the global state section (after line 77), add:

```python
# Wind correction: upwash tables + heel damper
upwash_tables: UpwashTableSet = UpwashTableSet.load()
heel_damper: ScalarBuffer = ScalarBuffer(
    max_len=max(1, int(4.0 * config.sample_rate_hz))  # 4-second window
)
```

- [ ] **Step 2: Wire correction into the pipeline loop**

In the pipeline loop in `_pipeline_loop()`, after `apply_calibration(state, config)` (line 264) and before `compute_true_wind(state)` (line 265), insert:

```python
                    # Smooth heel for wind correction (standalone damper)
                    _heel_smoothed = None
                    if state.heel_deg is not None:
                        _heel_smoothed = heel_damper.push(state.heel_deg)

                    # Wind correction: heel + upwash
                    _sail_key = config.sail_config_key()
                    state.active_sail_config = _sail_key
                    _upwash_table = upwash_tables.get_table(_sail_key)
                    apply_wind_correction(state, _upwash_table, _heel_smoothed)
```

- [ ] **Step 3: Run integration test**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/test_pipeline_integration.py -v`
Expected: All pass

- [ ] **Step 4: Run full test suite**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/ -v --tb=short`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
cd /Users/tommaso/Documents/regata-software
git add aquarela/main.py
git commit -m "feat: wire wind correction into pipeline loop"
```

---

### Task 6: Upwash Auto-Learning

**Files:**
- Create: `aquarela/pipeline/upwash_learning.py`
- Create: `tests/test_upwash_learning.py`

- [ ] **Step 1: Write tests for tack detection and validity filter**

```python
# tests/test_upwash_learning.py
"""Tests for upwash auto-learning."""

import pytest
from datetime import datetime, timezone

from aquarela.pipeline.upwash_learning import UpwashLearner


class TestTackDetection:
    def test_detects_tack_on_sign_change(self):
        """AWA sign change triggers maneuver detection."""
        learner = UpwashLearner(hz=1)
        # Feed 30 samples on starboard (positive AWA)
        for i in range(30):
            learner.update(
                twd=180.0, awa_corrected=30.0, heel=10.0, bsp=6.0,
                sail_config="main_1__genoa",
            )
        assert learner.state == "waiting"

        # Sign change: tack to port
        learner.update(
            twd=180.0, awa_corrected=-30.0, heel=-10.0, bsp=6.0,
            sail_config="main_1__genoa",
        )
        assert learner.state == "post_tack"

    def test_no_tack_same_sign(self):
        """No sign change — no tack detected."""
        learner = UpwashLearner(hz=1)
        for i in range(60):
            learner.update(
                twd=180.0, awa_corrected=30.0, heel=10.0, bsp=6.0,
                sail_config="main_1__genoa",
            )
        assert learner.state == "waiting"


class TestValidityFilter:
    def test_rejects_unstable_wind(self):
        """TWD with high variance → maneuver rejected."""
        learner = UpwashLearner(hz=1)
        # 2 min of stable data pre-tack
        for i in range(120):
            learner.update(
                twd=180.0, awa_corrected=30.0, heel=10.0, bsp=6.0,
                sail_config="main_1__genoa",
            )
        # Tack
        learner.update(
            twd=180.0, awa_corrected=-30.0, heel=-10.0, bsp=6.0,
            sail_config="main_1__genoa",
        )
        # 2 min of UNSTABLE data post-tack (TWD varies ±20°)
        import random
        random.seed(42)
        for i in range(120):
            learner.update(
                twd=180.0 + random.uniform(-20, 20),
                awa_corrected=-30.0, heel=-10.0, bsp=6.0,
                sail_config="main_1__genoa",
            )
        # 30s of stable AWA to "complete" the maneuver
        for i in range(30):
            learner.update(
                twd=200.0, awa_corrected=-30.0, heel=-10.0, bsp=6.0,
                sail_config="main_1__genoa",
            )
        # Should have been rejected due to TWD instability
        assert learner.last_result in ("rejected", None)

    def test_rejects_low_bsp(self):
        """BSP < 3 kt → maneuver rejected."""
        learner = UpwashLearner(hz=1)
        for i in range(120):
            learner.update(
                twd=180.0, awa_corrected=30.0, heel=5.0, bsp=2.0,
                sail_config="main_1__genoa",
            )
        learner.update(
            twd=180.0, awa_corrected=-30.0, heel=-5.0, bsp=2.0,
            sail_config="main_1__genoa",
        )
        for i in range(150):
            learner.update(
                twd=180.0, awa_corrected=-30.0, heel=-5.0, bsp=2.0,
                sail_config="main_1__genoa",
            )
        assert learner.last_result in ("rejected", None)


class TestResidualCalculation:
    def test_stable_tack_produces_update(self):
        """Clean tack with stable TWD → table update returned."""
        learner = UpwashLearner(hz=1)
        # 2+ min stable pre-tack, TWD=180
        for i in range(130):
            learner.update(
                twd=180.0, awa_corrected=30.0, heel=10.0, bsp=6.0,
                sail_config="main_1__genoa",
            )
        # Tack to port
        learner.update(
            twd=180.0, awa_corrected=-30.0, heel=-10.0, bsp=6.0,
            sail_config="main_1__genoa",
        )
        # 2+ min stable post-tack, TWD=184 (4° shift = 2° upwash error)
        for i in range(130):
            learner.update(
                twd=184.0, awa_corrected=-30.0, heel=-10.0, bsp=6.0,
                sail_config="main_1__genoa",
            )
        # 30s stable AWA to complete
        for i in range(30):
            learner.update(
                twd=184.0, awa_corrected=-30.0, heel=-10.0, bsp=6.0,
                sail_config="main_1__genoa",
            )
        assert learner.last_result == "updated"
        assert learner.last_residual == pytest.approx(2.0, abs=0.5)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/test_upwash_learning.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: Implement UpwashLearner**

```python
# aquarela/pipeline/upwash_learning.py
"""Upwash auto-learning from tack/gybe maneuvers.

Principle: in stable wind, TWD must be equal on both tacks. The systematic
difference after a tack is attributed to residual upwash error.

Conservative filter: only clean maneuvers in stable wind contribute.
"""

from __future__ import annotations

import math
import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Optional, Tuple

from .upwash_table import UpwashTable

logger = logging.getLogger("aquarela.upwash_learning")


@dataclass
class _Sample:
    twd: float
    awa_corrected: float
    heel: float
    bsp: float
    sail_config: str


class UpwashLearner:
    """Detects tacks/gybes and learns upwash corrections from TWD residuals.

    Args:
        hz: sample rate (used for internal downsampling — call update() at pipeline rate,
            but the buffer stores at 1 Hz).
        buffer_seconds: rolling buffer length (default 180 = 3 min).
        pre_window: seconds of stable data required before maneuver (default 120).
        post_window: seconds of stable data required after maneuver (default 120).
        twd_sigma_max: max TWD std dev for a window to be considered stable (degrees).
        bsp_min: minimum BSP for a valid maneuver (knots).
        awa_settle_sigma: AWA std dev threshold for maneuver completion (degrees).
        awa_settle_seconds: seconds of stable AWA required to consider maneuver complete.
    """

    def __init__(
        self,
        hz: int = 10,
        buffer_seconds: int = 180,
        pre_window: int = 120,
        post_window: int = 120,
        twd_sigma_max: float = 5.0,
        bsp_min: float = 3.0,
        awa_settle_sigma: float = 3.0,
        awa_settle_seconds: int = 30,
    ):
        self._hz = hz
        self._tick = 0
        self._buffer_seconds = buffer_seconds
        self._pre_window = pre_window
        self._post_window = post_window
        self._twd_sigma_max = twd_sigma_max
        self._bsp_min = bsp_min
        self._awa_settle_sigma = awa_settle_sigma
        self._awa_settle_seconds = awa_settle_seconds

        # Rolling buffer (1 Hz)
        self._buffer: Deque[_Sample] = deque(maxlen=buffer_seconds)

        # Maneuver tracking
        self._prev_awa_sign: Optional[int] = None
        self._pre_tack_snapshot: Optional[list[_Sample]] = None  # frozen at tack time
        self._post_tack_buffer: Deque[_Sample] = deque(maxlen=post_window + awa_settle_seconds + 30)
        self._post_tack_samples: int = 0
        self._post_awa_buffer: Deque[float] = deque(maxlen=awa_settle_seconds)

        # State machine
        self.state: str = "waiting"  # waiting | post_tack
        self.last_result: Optional[str] = None  # updated | rejected
        self.last_residual: Optional[float] = None
        self._last_update: Optional[Tuple[float, float, str]] = None  # (awa, heel, config)

    def update(
        self,
        twd: float,
        awa_corrected: float,
        heel: float,
        bsp: float,
        sail_config: str,
    ) -> Optional[Tuple[float, float, float, str]]:
        """Feed one pipeline sample. Returns update tuple if learning triggered.

        Called at pipeline rate (hz). Internally downsamples to 1 Hz for buffer.

        Returns:
            (residual, mean_awa, mean_heel, sail_config) if a valid update was made,
            None otherwise.
        """
        self._tick += 1
        should_store = (self._tick % self._hz == 0)

        if should_store:
            sample = _Sample(
                twd=twd,
                awa_corrected=awa_corrected,
                heel=heel,
                bsp=bsp,
                sail_config=sail_config,
            )
            self._buffer.append(sample)

        # Track AWA sign for tack detection
        awa_sign = 1 if awa_corrected >= 0 else -1

        if self._prev_awa_sign is not None and awa_sign != self._prev_awa_sign:
            # Sign change — tack/gybe detected
            if self.state == "waiting" and len(self._buffer) >= self._pre_window:
                self.state = "post_tack"
                # Snapshot pre-tack data immediately (avoids deque rotation issues)
                self._pre_tack_snapshot = list(self._buffer)[-self._pre_window:]
                self._post_tack_buffer.clear()
                self._post_tack_samples = 0
                self._post_awa_buffer.clear()
                logger.debug("Tack detected, pre-tack snapshot: %d samples", len(self._pre_tack_snapshot))

        self._prev_awa_sign = awa_sign

        # Post-tack: collect samples and wait for AWA to settle
        if self.state == "post_tack" and should_store:
            self._post_tack_buffer.append(sample)
            self._post_tack_samples += 1
            self._post_awa_buffer.append(awa_corrected)

            # Check if AWA has settled
            if len(self._post_awa_buffer) >= self._awa_settle_seconds:
                awa_std = _std(list(self._post_awa_buffer))
                if awa_std < self._awa_settle_sigma:
                    # Maneuver complete — evaluate using snapshots
                    result = self._evaluate_maneuver()
                    self.state = "waiting"
                    return result

            # Timeout: if we've been waiting too long, abandon
            if self._post_tack_samples > self._post_window + self._awa_settle_seconds + 30:
                logger.debug("Post-tack timeout — abandoning maneuver")
                self.state = "waiting"
                self.last_result = "rejected"

        return None

    def _evaluate_maneuver(self) -> Optional[Tuple[float, float, float, str]]:
        """Evaluate a completed maneuver for learning validity.

        Uses pre-tack snapshot (frozen at tack time) and post-tack buffer
        (collected after tack). This avoids deque rotation issues.

        Returns (residual, mean_awa, mean_heel, sail_config) or None if rejected.
        """
        pre_samples = self._pre_tack_snapshot
        post_samples = list(self._post_tack_buffer)[:self._post_window]

        if pre_samples is None or len(pre_samples) < self._pre_window or len(post_samples) < self._post_window:
            logger.debug("Insufficient samples: pre=%d post=%d", len(pre_samples), len(post_samples))
            self.last_result = "rejected"
            return None

        # Check sail config consistency
        pre_config = pre_samples[-1].sail_config
        post_config = post_samples[-1].sail_config
        if pre_config != post_config:
            logger.debug("Sail config changed during maneuver")
            self.last_result = "rejected"
            return None

        # Check BSP minimum (use pre-tack mean)
        pre_bsp_mean = sum(s.bsp for s in pre_samples) / len(pre_samples)
        if pre_bsp_mean < self._bsp_min:
            logger.debug("BSP too low: %.1f kt", pre_bsp_mean)
            self.last_result = "rejected"
            return None

        # Check TWD stability
        pre_twd = [s.twd for s in pre_samples]
        post_twd = [s.twd for s in post_samples]

        pre_twd_std = _angle_std(pre_twd)
        post_twd_std = _angle_std(post_twd)

        if pre_twd_std > self._twd_sigma_max:
            logger.debug("Pre-tack TWD unstable: σ=%.1f°", pre_twd_std)
            self.last_result = "rejected"
            return None

        if post_twd_std > self._twd_sigma_max:
            logger.debug("Post-tack TWD unstable: σ=%.1f°", post_twd_std)
            self.last_result = "rejected"
            return None

        # Calculate residual
        pre_twd_mean = _angle_mean(pre_twd)
        post_twd_mean = _angle_mean(post_twd)
        residual = _angle_diff(post_twd_mean, pre_twd_mean) / 2.0

        # Pre-tack mean AWA and heel (for table cell selection)
        mean_awa = sum(abs(s.awa_corrected) for s in pre_samples) / len(pre_samples)
        mean_heel = sum(abs(s.heel) for s in pre_samples) / len(pre_samples)

        self.last_result = "updated"
        self.last_residual = residual
        self._last_update = (mean_awa, mean_heel, pre_config)

        logger.info(
            "Upwash learning: residual=%.2f° at AWA=%.0f° heel=%.0f° config=%s",
            residual, mean_awa, mean_heel, pre_config,
        )

        return (residual, mean_awa, mean_heel, pre_config)


def _std(values: list[float]) -> float:
    """Standard deviation of a list of floats."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


def _angle_mean(angles: list[float]) -> float:
    """Circular mean of angles in degrees."""
    sin_sum = sum(math.sin(math.radians(a)) for a in angles)
    cos_sum = sum(math.cos(math.radians(a)) for a in angles)
    return math.degrees(math.atan2(sin_sum / len(angles), cos_sum / len(angles))) % 360


def _angle_std(angles: list[float]) -> float:
    """Circular standard deviation of angles in degrees."""
    n = len(angles)
    if n < 2:
        return 0.0
    sin_sum = sum(math.sin(math.radians(a)) for a in angles)
    cos_sum = sum(math.cos(math.radians(a)) for a in angles)
    r = math.sqrt(sin_sum ** 2 + cos_sum ** 2) / n
    # Circular std dev: sqrt(-2 * ln(R))
    if r >= 1.0:
        return 0.0
    if r <= 0.0:
        return 180.0
    return math.degrees(math.sqrt(-2.0 * math.log(r)))


def _angle_diff(a: float, b: float) -> float:
    """Signed difference a - b, handling 360° wrap. Result in -180..+180."""
    d = (a - b + 180) % 360 - 180
    return d
```

- [ ] **Step 4: Run tests**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/test_upwash_learning.py -v`
Expected: All pass

- [ ] **Step 5: Wire learning into main.py pipeline loop**

In `main.py`, add to global state section:

```python
from .pipeline.upwash_learning import UpwashLearner

upwash_learner: UpwashLearner = UpwashLearner(hz=config.sample_rate_hz)
```

In the pipeline loop, after `learning_check()` comment position (after targets, before broadcast), add:

```python
                    # Upwash learning check
                    if config.upwash_learning_enabled and state.twd_deg is not None:
                        _learn_result = upwash_learner.update(
                            twd=state.twd_deg,
                            awa_corrected=state.awa_corrected_deg or state.awa_deg or 0.0,
                            heel=state.heel_deg or 0.0,
                            bsp=state.bsp_kt or 0.0,
                            sail_config=state.active_sail_config or config.sail_config_key(),
                        )
                        state.upwash_learning_status = upwash_learner.state
                        if _learn_result is not None:
                            _residual, _mean_awa, _mean_heel, _learn_config = _learn_result
                            _learn_table = upwash_tables.get_table(_learn_config)
                            if _learn_table is not None:
                                _learn_table.update_nearest(
                                    _mean_awa, _mean_heel, _residual,
                                    config.upwash_learning_rate,
                                )
                                upwash_tables.save()
                                logger.info("Upwash table updated and saved")
```

- [ ] **Step 6: Run full test suite**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/ -v --tb=short`
Expected: All pass

- [ ] **Step 7: Commit**

```bash
cd /Users/tommaso/Documents/regata-software
git add aquarela/pipeline/upwash_learning.py tests/test_upwash_learning.py aquarela/main.py
git commit -m "feat: add upwash auto-learning from tack/gybe maneuvers"
```

---

### Task 7: CAN Writer

**Files:**
- Create: `aquarela/nmea/can_writer.py`
- Create: `tests/test_can_writer.py`

- [ ] **Step 1: Write tests for PGN encoding and writer behavior**

```python
# tests/test_can_writer.py
"""Tests for CAN bus writer (PGN 130306 true wind output)."""

import struct
import math
import pytest
from unittest.mock import MagicMock, patch

from aquarela.nmea.can_writer import (
    encode_pgn_130306,
    build_name_field,
    CanWriter,
)


class TestPgn130306Encoding:
    def test_encode_true_wind_water(self):
        """Encode TWA=45°, TWS=12kt as water-referenced PGN 130306."""
        data = encode_pgn_130306(twa_deg=45.0, tws_kt=12.0, reference=4)
        assert len(data) == 8
        # Decode and verify round-trip
        sid = data[0]
        speed_raw = struct.unpack_from("<H", data, 1)[0]
        angle_raw = struct.unpack_from("<H", data, 3)[0]
        ref = data[5] & 0x07
        assert ref == 4  # water referenced
        # Speed: 12 kt = 12/1.94384 m/s = 6.173 m/s → raw = 6173 (0.01 m/s units)
        assert abs(speed_raw - 617) < 2
        # Angle: 45° = 0.7854 rad → raw = 7854 (0.0001 rad units)
        assert abs(angle_raw - 7854) < 10

    def test_encode_true_wind_ground(self):
        """Ground-referenced uses reference=3."""
        data = encode_pgn_130306(twa_deg=90.0, tws_kt=15.0, reference=3)
        ref = data[5] & 0x07
        assert ref == 3


class TestNameField:
    def test_name_field_64_bits(self):
        """NAME field is exactly 8 bytes (64 bits)."""
        name = build_name_field()
        assert len(name) == 8

    def test_industry_group_marine(self):
        """Industry group = 4 (Marine) is encoded in the NAME."""
        name = build_name_field()
        # Industry group is in the high bits of byte 7
        ig = (name[7] >> 4) & 0x07
        assert ig == 4


class TestCanWriter:
    def test_disabled_does_nothing(self):
        """When disabled, update() does not call bus.send()."""
        writer = CanWriter(enabled=False)
        writer._bus = MagicMock()
        writer.update(twa_water=45.0, tws_water=12.0, twa_ground=46.0, tws_ground=11.5)
        writer._bus.send.assert_not_called()

    def test_dry_run_does_not_send(self):
        """In dry-run mode, encodes but does not send."""
        writer = CanWriter(enabled=True, dry_run=True)
        writer._bus = MagicMock()
        writer._address_claimed = True
        writer.update(twa_water=45.0, tws_water=12.0, twa_ground=46.0, tws_ground=11.5)
        writer._bus.send.assert_not_called()

    def test_enabled_sends(self):
        """When enabled and not dry-run, sends 2 messages (water + ground)."""
        writer = CanWriter(enabled=True, dry_run=False)
        writer._bus = MagicMock()
        writer._address_claimed = True
        writer.update(twa_water=45.0, tws_water=12.0, twa_ground=46.0, tws_ground=11.5)
        assert writer._bus.send.call_count == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/test_can_writer.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: Implement CAN Writer**

```python
# aquarela/nmea/can_writer.py
"""CAN bus writer for publishing corrected true wind on NMEA 2000.

Publishes PGN 130306 (Wind Data) with true wind reference types.
Handles ISO 11783 address claim for bus participation.
"""

from __future__ import annotations

import hashlib
import logging
import math
import struct
import time
import uuid
from typing import Optional

logger = logging.getLogger("aquarela.can_writer")

# Conversion constants
KT_TO_MS = 1.0 / 1.94384


def encode_pgn_130306(twa_deg: float, tws_kt: float, reference: int) -> bytes:
    """Encode PGN 130306 (Wind Data).

    Args:
        twa_deg: true wind angle in degrees (signed: -port +stbd).
                 Converted to 0-360 unsigned for NMEA 2000.
        tws_kt: true wind speed in knots.
        reference: 3=true ground, 4=true water.

    Returns:
        8-byte CAN frame payload.
    """
    # SID (sequence ID) — 0 is fine for single-source
    sid = 0

    # Speed: convert kt to m/s, scale to 0.01 m/s units
    speed_ms = tws_kt * KT_TO_MS
    speed_raw = int(round(speed_ms * 100))
    speed_raw = max(0, min(0xFFFE, speed_raw))

    # Angle: convert signed degrees to unsigned radians, scale to 0.0001 rad
    angle_deg = twa_deg % 360  # unsigned 0-360
    angle_rad = math.radians(angle_deg)
    angle_raw = int(round(angle_rad * 10000))
    angle_raw = max(0, min(0xFFFE, angle_raw))

    data = bytearray(8)
    data[0] = sid
    struct.pack_into("<H", data, 1, speed_raw)
    struct.pack_into("<H", data, 3, angle_raw)
    data[5] = reference & 0x07
    data[6] = 0xFF  # reserved
    data[7] = 0xFF  # reserved

    return bytes(data)


def build_name_field(unique_number: Optional[int] = None) -> bytes:
    """Build the 64-bit ISO 11783 NAME for address claim (PGN 60928).

    Returns:
        8 bytes (little-endian).
    """
    if unique_number is None:
        # Derive from machine UUID
        machine_hash = hashlib.md5(str(uuid.getnode()).encode()).digest()
        unique_number = int.from_bytes(machine_hash[:3], "little") & 0x1FFFFF

    # NAME fields (ISO 11783-5):
    #   Bits 0-20:  Unique Number (21 bits)
    #   Bits 21-31: Manufacturer Code (11 bits) → 2047
    #   Bits 32-34: Device Instance Lower (3 bits) → 0
    #   Bits 35-39: Device Instance Upper (5 bits) → 0
    #   Bits 40-47: Device Function (8 bits) → 130
    #   Bit  48:    Reserved → 0
    #   Bits 49-55: Device Class (7 bits) → 75
    #   Bits 56-59: System Instance (4 bits) → 0
    #   Bits 60-62: Industry Group (3 bits) → 4
    #   Bit  63:    Self-configurable → 1

    name = 0
    name |= (unique_number & 0x1FFFFF)        # bits 0-20
    name |= (2047 & 0x7FF) << 21              # bits 21-31: manufacturer
    name |= 0 << 32                            # bits 32-39: device instance
    name |= (130 & 0xFF) << 40                 # bits 40-47: function
    name |= 0 << 48                            # bit 48: reserved
    name |= (75 & 0x7F) << 49                  # bits 49-55: class
    name |= 0 << 56                            # bits 56-59: system instance
    name |= (4 & 0x07) << 60                   # bits 60-62: industry group
    name |= 1 << 63                            # bit 63: self-configurable

    return name.to_bytes(8, "little")


class CanWriter:
    """Publishes corrected true wind data on the NMEA 2000 bus.

    Args:
        enabled: master switch. If False, does nothing.
        dry_run: if True, encodes frames but does not call bus.send().
        interface: SocketCAN interface name.
        address: initial NMEA 2000 source address.
    """

    def __init__(
        self,
        enabled: bool = False,
        dry_run: bool = True,
        interface: str = "can0",
        address: int = 100,
    ):
        self._enabled = enabled
        self._dry_run = dry_run
        self._interface = interface
        self._address = address
        self._bus = None
        self._address_claimed = False
        self._name = build_name_field()
        self._sid = 0

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value
        if not value:
            self.stop()

    def start(self) -> None:
        """Open the CAN bus and perform address claim."""
        if not self._enabled:
            return
        try:
            import can
            self._bus = can.Bus(channel=self._interface, interface="socketcan")
            self._claim_address()
            logger.info("CAN writer started on %s (address=%d, dry_run=%s)",
                        self._interface, self._address, self._dry_run)
        except Exception as exc:
            logger.warning("CAN writer failed to start: %s — disabling", exc)
            self._enabled = False
            self._bus = None

    def stop(self) -> None:
        """Shut down the CAN bus."""
        if self._bus is not None:
            try:
                self._bus.shutdown()
            except Exception:
                pass
            self._bus = None
        self._address_claimed = False

    def _claim_address(self) -> None:
        """Send ISO address claim (PGN 60928).

        Tries addresses 100-127. If all fail, disables writer.
        """
        if self._bus is None:
            return

        import can

        for addr in range(100, 128):
            self._address = addr
            # Build address claim CAN ID: priority 6, PGN 60928, source=addr
            # PGN 60928 = 0xEE00 → PF=238, PS=0 (broadcast)
            can_id = (6 << 26) | (0xEE00 << 8) | addr
            msg = can.Message(
                arbitration_id=can_id,
                data=self._name,
                is_extended_id=True,
            )
            try:
                if not self._dry_run:
                    self._bus.send(msg)
                self._address_claimed = True
                logger.info("Address claimed: %d", addr)
                return
            except Exception as exc:
                logger.debug("Address claim failed for %d: %s", addr, exc)
                continue

        logger.error("All addresses 100-127 exhausted — CAN writer disabled")
        self._enabled = False

    def update(
        self,
        twa_water: Optional[float] = None,
        tws_water: Optional[float] = None,
        twa_ground: Optional[float] = None,
        tws_ground: Optional[float] = None,
    ) -> None:
        """Publish corrected true wind. Called at 1 Hz from main loop.

        Args:
            twa_water: TWA computed with STW (degrees)
            tws_water: TWS computed with STW (knots)
            twa_ground: TWA computed with SOG (degrees)
            tws_ground: TWS computed with SOG (knots)
        """
        if not self._enabled or not self._address_claimed:
            return

        self._sid = (self._sid + 1) % 253

        # PGN 130306 = 0x1FD02 (DP=1, PF=0xFD, PS=0x02)
        # CAN ID: priority(3) | reserved(1) | DP(1) | PF(8) | PS(8) | SA(8)
        # Using the shorthand: (priority << 26) | (pgn << 8) | source_address
        can_id = (2 << 26) | (0x1FD02 << 8) | self._address

        import can

        # Water-referenced true wind
        if twa_water is not None and tws_water is not None:
            payload = encode_pgn_130306(twa_water, tws_water, reference=4)
            msg = can.Message(
                arbitration_id=can_id, data=payload, is_extended_id=True
            )
            if self._dry_run:
                logger.debug("DRY-RUN PGN 130306 water: TWA=%.1f TWS=%.1f", twa_water, tws_water)
            elif self._bus is not None:
                try:
                    self._bus.send(msg)
                except Exception as exc:
                    logger.warning("CAN write error (water): %s", exc)

        # Ground-referenced true wind
        if twa_ground is not None and tws_ground is not None:
            payload = encode_pgn_130306(twa_ground, tws_ground, reference=3)
            msg = can.Message(
                arbitration_id=can_id, data=payload, is_extended_id=True
            )
            if self._dry_run:
                logger.debug("DRY-RUN PGN 130306 ground: TWA=%.1f TWS=%.1f", twa_ground, tws_ground)
            elif self._bus is not None:
                try:
                    self._bus.send(msg)
                except Exception as exc:
                    logger.warning("CAN write error (ground): %s", exc)
```

- [ ] **Step 4: Run tests**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/test_can_writer.py -v`
Expected: All pass

- [ ] **Step 5: Wire CAN writer into main.py**

Add to global state in `main.py`:

```python
from .nmea.can_writer import CanWriter

can_writer: CanWriter = CanWriter(
    enabled=config.can_writer_enabled,
    dry_run=config.can_writer_dry_run,
)
```

In `_pipeline_loop()`, add a 1 Hz CAN write timer. At the end of the pipeline tick (before broadcast), add:

```python
                    # CAN writer: 1 Hz publish handled by separate asyncio task (see below)
```

In the lifespan startup, after source creation:

```python
    # Start CAN writer if enabled
    if config.can_writer_enabled:
        try:
            can_writer.start()
        except Exception:
            logger.warning("CAN writer failed to start — continuing without it")
```

Add a separate 1 Hz asyncio task for CAN publishing (in lifespan or alongside the pipeline task):

```python
async def _can_writer_loop():
    """Publish corrected true wind on CAN bus at 1 Hz."""
    while True:
        await asyncio.sleep(1.0)
        if can_writer.enabled and current_state.twa_deg is not None:
            can_writer.update(
                twa_water=current_state.twa_deg,
                tws_water=current_state.tws_kt,
                # TODO: ground-referenced from SOG-based true wind
                twa_ground=None,
                tws_ground=None,
            )
```

Start this task in the lifespan alongside the pipeline task.

- [ ] **Step 6: Run full test suite**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/ -v --tb=short`
Expected: All pass

- [ ] **Step 7: Commit**

```bash
cd /Users/tommaso/Documents/regata-software
git add aquarela/nmea/can_writer.py tests/test_can_writer.py aquarela/main.py
git commit -m "feat: add CAN writer for publishing corrected true wind on NMEA 2000"
```

---

### Task 8: API Endpoints

**Files:**
- Create: `aquarela/api/sails.py`
- Modify: `aquarela/main.py` (register router, extend calibration endpoint)

- [ ] **Step 1: Create sails API router**

```python
# aquarela/api/sails.py
"""Sail configuration API — select active sails, view/reset upwash tables."""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/sails", tags=["sails"])


@router.get("")
async def get_sails():
    """Return current sail configuration and active selection."""
    from aquarela.main import config, upwash_tables
    return {
        "sails": config.sails,
        "active_main": config.active_main,
        "active_headsail": config.active_headsail,
        "active_config_key": config.sail_config_key(),
    }


@router.post("")
async def set_sails(payload: dict):
    """Update active sail selection.

    Accepted keys: active_main, active_headsail.
    """
    from aquarela.main import config
    changed = False

    if "active_main" in payload:
        if payload["active_main"] not in config.sails.get("mains", []):
            raise HTTPException(400, f"Unknown main: {payload['active_main']}")
        config.active_main = payload["active_main"]
        changed = True

    if "active_headsail" in payload:
        # Validate it exists in one of the headsail categories
        all_headsails = []
        for names in config.sails.get("headsails", {}).values():
            all_headsails.extend(names)
        if payload["active_headsail"] not in all_headsails:
            raise HTTPException(400, f"Unknown headsail: {payload['active_headsail']}")
        config.active_headsail = payload["active_headsail"]
        changed = True

    if changed:
        config.save()

    return {
        "active_main": config.active_main,
        "active_headsail": config.active_headsail,
        "active_config_key": config.sail_config_key(),
    }


@router.get("/upwash")
async def get_upwash():
    """Return the upwash table for the active sail configuration."""
    from aquarela.main import config, upwash_tables
    key = config.sail_config_key()
    table = upwash_tables.get_table(key)
    if table is None:
        raise HTTPException(404, f"No upwash table for config: {key}")
    return {
        "config_key": key,
        "table": table.to_dict(),
    }


@router.post("/upwash/reset")
async def reset_upwash(payload: dict = None):
    """Reset an upwash table to initial values.

    Optional payload: {"config_key": "main_1__genoa"}
    If omitted, resets the active config's table.
    """
    from aquarela.main import config, upwash_tables
    from aquarela.pipeline.upwash_table import UpwashTable

    key = (payload or {}).get("config_key", config.sail_config_key())
    if key not in upwash_tables.tables:
        raise HTTPException(404, f"No upwash table for config: {key}")

    upwash_tables.tables[key] = UpwashTable.with_initial_values()
    upwash_tables.save()

    return {"reset": key, "status": "ok"}
```

- [ ] **Step 2: Register router and extend calibration endpoint in main.py**

Add import:

```python
from .api.sails import router as sails_router
```

Register router (near other router includes):

```python
app.include_router(sails_router)
```

Extend the existing calibration endpoint to accept new fields (find the `set_calibration` function and add):

```python
    if "upwash_learning_rate" in payload:
        config.upwash_learning_rate = float(payload["upwash_learning_rate"])
    if "upwash_learning_enabled" in payload:
        config.upwash_learning_enabled = bool(payload["upwash_learning_enabled"])
    if "can_writer_enabled" in payload:
        config.can_writer_enabled = bool(payload["can_writer_enabled"])
        can_writer.enabled = config.can_writer_enabled
        if config.can_writer_enabled and not can_writer._address_claimed:
            can_writer.start()
    if "can_writer_dry_run" in payload:
        config.can_writer_dry_run = bool(payload["can_writer_dry_run"])
        can_writer._dry_run = config.can_writer_dry_run
```

- [ ] **Step 3: Run API tests**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/test_api_routes.py -v --tb=short`
Expected: All pass (existing tests unaffected)

- [ ] **Step 4: Commit**

```bash
cd /Users/tommaso/Documents/regata-software
git add aquarela/api/sails.py aquarela/main.py
git commit -m "feat: add sail configuration and upwash API endpoints"
```

---

### Task 9: Final Integration Test and Cleanup

**Files:**
- Modify: `tests/test_pipeline_integration.py` (add wind correction integration test)

- [ ] **Step 1: Write integration test**

Add to `tests/test_pipeline_integration.py`:

```python
class TestWindCorrectionIntegration:
    def test_pipeline_with_wind_correction(self):
        """Full pipeline: raw → calibrate → correct → true wind produces valid output."""
        from aquarela.pipeline.calibration import apply_calibration
        from aquarela.pipeline.wind_correction import apply_wind_correction
        from aquarela.pipeline.true_wind import compute_true_wind
        from aquarela.pipeline.upwash_table import UpwashTable
        from aquarela.config import AquarelaConfig

        state = BoatState.new()
        state.raw_awa_deg = -30.0
        state.raw_aws_kt = 15.0
        state.raw_bsp_kt = 6.5
        state.raw_heading_mag = 220.0
        state.heel_deg = 18.0

        cfg = AquarelaConfig()
        table = UpwashTable.with_initial_values()

        apply_calibration(state, cfg)
        apply_wind_correction(state, table, heel_smoothed=18.0)
        compute_true_wind(state)

        # True wind should be computed from corrected values
        assert state.twa_deg is not None
        assert state.tws_kt is not None
        assert state.awa_corrected_deg is not None
        assert abs(state.awa_corrected_deg) > abs(state.awa_deg)

    def test_pipeline_without_heel(self):
        """Pipeline works with no heel data (correction skips heel stage)."""
        from aquarela.pipeline.calibration import apply_calibration
        from aquarela.pipeline.wind_correction import apply_wind_correction
        from aquarela.pipeline.true_wind import compute_true_wind
        from aquarela.pipeline.upwash_table import UpwashTable
        from aquarela.config import AquarelaConfig

        state = BoatState.new()
        state.raw_awa_deg = -45.0
        state.raw_aws_kt = 12.0
        state.raw_bsp_kt = 5.0
        state.raw_heading_mag = 180.0
        # heel_deg is None — should still work

        cfg = AquarelaConfig()
        table = UpwashTable.with_initial_values()

        apply_calibration(state, cfg)
        apply_wind_correction(state, table)
        compute_true_wind(state)

        assert state.twa_deg is not None
        assert state.awa_corrected_deg is not None
```

- [ ] **Step 2: Run integration tests**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/test_pipeline_integration.py -v`
Expected: All pass

- [ ] **Step 3: Run complete test suite**

Run: `cd /Users/tommaso/Documents/regata-software && python -m pytest tests/ -v`
Expected: All pass

- [ ] **Step 4: Final commit**

```bash
cd /Users/tommaso/Documents/regata-software
git add tests/test_pipeline_integration.py
git commit -m "test: add wind correction integration tests"
```
