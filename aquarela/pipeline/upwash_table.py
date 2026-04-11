"""2-D upwash correction lookup tables indexed by AWA and heel.

Each UpwashTable is a grid of correction offsets (degrees) that capture
how much the measured apparent wind angle is distorted by the sail plan
and boat heel.  A full set contains one table per sail configuration.

Grid dimensions:
  AWA  — 20 to 180° in 5° steps  → 33 breakpoints
  Heel —  0 to  35° in 5° steps  →  8 breakpoints
  Total: 264 cells per table, 6 tables.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

# ── constants ────────────────────────────────────────────────────────

AWA_MIN, AWA_MAX, AWA_STEP = 20, 180, 5
HEEL_MIN, HEEL_MAX, HEEL_STEP = 0, 35, 5

AWA_BREAKPOINTS = list(range(AWA_MIN, AWA_MAX + 1, AWA_STEP))   # 33
HEEL_BREAKPOINTS = list(range(HEEL_MIN, HEEL_MAX + 1, HEEL_STEP))  # 8

SAIL_CONFIG_KEYS = [
    "main_1__jib",
    "main_1__genoa",
    "main_1__gennaker",
    "main_2__jib",
    "main_2__genoa",
    "main_2__gennaker",
]


def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation: a when t=0, b when t=1."""
    return a + (b - a) * t


# ── literature-based initial values ─────────────────────────────────

# Reference points: (AWA, upwash_at_heel0, upwash_at_heel35)
_INITIAL_REFS: list[tuple[float, float, float]] = [
    (20,  2.0, 5.5),
    (45,  1.5, 4.0),
    (90,  0.5, 1.0),
    (135, 0.0, 0.0),
    (180, 0.0, 0.0),
]


def _initial_upwash(awa: float, heel: float) -> float:
    """Return initial upwash offset for an (awa, heel) point by
    linearly interpolating the literature reference table."""
    # Clamp
    awa = max(AWA_MIN, min(AWA_MAX, awa))
    heel = max(HEEL_MIN, min(HEEL_MAX, heel))

    # Find bracketing AWA refs
    for i in range(len(_INITIAL_REFS) - 1):
        a0, v0_lo, v0_hi = _INITIAL_REFS[i]
        a1, v1_lo, v1_hi = _INITIAL_REFS[i + 1]
        if awa <= a1:
            t = (awa - a0) / (a1 - a0) if a1 != a0 else 0.0
            val_lo = _lerp(v0_lo, v1_lo, t)  # heel=0
            val_hi = _lerp(v0_hi, v1_hi, t)  # heel=35
            heel_t = heel / HEEL_MAX if HEEL_MAX else 0.0
            return _lerp(val_lo, val_hi, heel_t)

    # Beyond last ref → 0
    return 0.0


# ── UpwashTable ──────────────────────────────────────────────────────

class UpwashTable:
    """2-D lookup grid of wind upwash correction offsets."""

    __slots__ = ("offsets", "observations")

    def __init__(self) -> None:
        n_awa = len(AWA_BREAKPOINTS)
        n_heel = len(HEEL_BREAKPOINTS)
        self.offsets: list[list[float]] = [
            [0.0] * n_heel for _ in range(n_awa)
        ]
        self.observations: list[list[int]] = [
            [0] * n_heel for _ in range(n_awa)
        ]

    # ── constructors ────────────────────────────────────────────────

    @classmethod
    def with_initial_values(cls) -> UpwashTable:
        """Create a table pre-filled with literature-based upwash estimates."""
        tbl = cls()
        for i, awa in enumerate(AWA_BREAKPOINTS):
            for j, heel in enumerate(HEEL_BREAKPOINTS):
                tbl.offsets[i][j] = round(_initial_upwash(awa, heel), 6)
        return tbl

    # ── lookup ──────────────────────────────────────────────────────

    def lookup(self, awa_deg: float, heel_deg: float) -> float:
        """Bilinear interpolation of the upwash offset.

        *awa_deg* and *heel_deg* are taken as absolute values and clamped
        to the grid boundaries.
        """
        awa = abs(awa_deg)
        heel = abs(heel_deg)

        # Clamp to grid
        awa = max(AWA_MIN, min(AWA_MAX, awa))
        heel = max(HEEL_MIN, min(HEEL_MAX, heel))

        # Find surrounding indices for AWA
        ia = min(
            int((awa - AWA_MIN) / AWA_STEP),
            len(AWA_BREAKPOINTS) - 2,
        )
        ia = max(ia, 0)
        ia1 = ia + 1

        # Find surrounding indices for heel
        jh = min(
            int((heel - HEEL_MIN) / HEEL_STEP),
            len(HEEL_BREAKPOINTS) - 2,
        )
        jh = max(jh, 0)
        jh1 = jh + 1

        # Fractional positions
        ta = (awa - AWA_BREAKPOINTS[ia]) / AWA_STEP
        ta = max(0.0, min(1.0, ta))
        th = (heel - HEEL_BREAKPOINTS[jh]) / HEEL_STEP
        th = max(0.0, min(1.0, th))

        # Bilinear
        v00 = self.offsets[ia][jh]
        v01 = self.offsets[ia][jh1]
        v10 = self.offsets[ia1][jh]
        v11 = self.offsets[ia1][jh1]

        v0 = _lerp(v00, v01, th)
        v1 = _lerp(v10, v11, th)
        return _lerp(v0, v1, ta)

    # ── learning ────────────────────────────────────────────────────

    def update_nearest(
        self,
        awa_deg: float,
        heel_deg: float,
        residual: float,
        learning_rate: float,
    ) -> None:
        """Nudge the nearest grid cell by ``learning_rate * residual``."""
        awa = abs(awa_deg)
        heel = abs(heel_deg)

        # Snap to nearest AWA index
        ia = round((max(AWA_MIN, min(AWA_MAX, awa)) - AWA_MIN) / AWA_STEP)
        ia = max(0, min(len(AWA_BREAKPOINTS) - 1, ia))

        # Snap to nearest heel index
        jh = round((max(HEEL_MIN, min(HEEL_MAX, heel)) - HEEL_MIN) / HEEL_STEP)
        jh = max(0, min(len(HEEL_BREAKPOINTS) - 1, jh))

        self.offsets[ia][jh] += learning_rate * residual
        self.observations[ia][jh] += 1

    # ── serialization ───────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "offsets": [row[:] for row in self.offsets],
            "observations": [row[:] for row in self.observations],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> UpwashTable:
        tbl = cls()
        tbl.offsets = [row[:] for row in d["offsets"]]
        tbl.observations = [row[:] for row in d["observations"]]
        return tbl


# ── UpwashTableSet ───────────────────────────────────────────────────

class UpwashTableSet:
    """Collection of UpwashTable instances, one per sail configuration."""

    __slots__ = ("tables",)

    def __init__(self) -> None:
        self.tables: dict[str, UpwashTable] = {}

    @classmethod
    def with_initial_values(cls) -> UpwashTableSet:
        ts = cls()
        for key in SAIL_CONFIG_KEYS:
            ts.tables[key] = UpwashTable.with_initial_values()
        return ts

    def get_table(self, key: str) -> UpwashTable | None:
        return self.tables.get(key)

    # ── persistence ─────────────────────────────────────────────────

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {key: tbl.to_dict() for key, tbl in self.tables.items()}
        p.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: str | Path) -> UpwashTableSet:
        """Load from JSON.  Returns initial values if file doesn't exist."""
        p = Path(path)
        if not p.exists():
            return cls.with_initial_values()
        data = json.loads(p.read_text())
        ts = cls()
        for key, d in data.items():
            ts.tables[key] = UpwashTable.from_dict(d)
        return ts
