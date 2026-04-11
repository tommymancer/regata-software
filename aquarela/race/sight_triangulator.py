"""Sight-mark triangulation — compute mark position from multiple bearing sightings.

Each sighting records the boat's GPS position and compass heading when the
helmsman points the bow at the mark.  Two or more sightings from different
positions define intersecting bearing lines; their intersection is the
mark's estimated position.
"""

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple


# ── Validation thresholds ──────────────────────────────────────
MIN_BASELINE_M = 20.0     # sighting positions must be ≥ 20 m apart
MIN_ANGLE_DEG = 10.0      # bearing lines must differ by ≥ 10°
MIN_MARK_DIST_M = 20.0    # computed mark must be ≥ 20 m from sighting midpoint
MAX_MARK_DIST_M = 5000.0  # computed mark must be ≤ 5 km from sighting midpoint


@dataclass
class Sighting:
    """A single mark sighting."""

    lat: float
    lon: float
    bearing: float  # compass heading (degrees, 0–360)

    def to_dict(self) -> dict:
        return {"lat": self.lat, "lon": self.lon, "bearing": self.bearing}


class SightTriangulator:
    """Collects mark sightings and triangulates the mark position."""

    def __init__(self) -> None:
        self._sightings: List[Sighting] = []
        self._computed: Optional[Tuple[float, float]] = None

    def add_sighting(self, lat: float, lon: float, bearing: float) -> int:
        """Record a sighting.  Returns the total number of sightings."""
        self._sightings.append(Sighting(lat, lon, bearing % 360))
        if len(self._sightings) >= 2:
            result = self._triangulate()
            if result is not None:
                self._computed = result
            # If triangulation fails, keep previous computed mark (if any)
        return len(self._sightings)

    def triangulate(self) -> Optional[Tuple[float, float]]:
        """Return the computed mark position, or None if insufficient data."""
        return self._computed

    def computed_mark(self) -> Optional[dict]:
        """Return computed mark as dict {lat, lon} or None."""
        if self._computed is None:
            return None
        return {"lat": self._computed[0], "lon": self._computed[1]}

    def get_sightings(self) -> List[dict]:
        """Return all sightings for map display."""
        return [s.to_dict() for s in self._sightings]

    @property
    def count(self) -> int:
        return len(self._sightings)

    def reset(self) -> None:
        """Clear all sightings and computed mark."""
        self._sightings.clear()
        self._computed = None

    # ── Internal triangulation ─────────────────────────────────────

    def _triangulate(self) -> Optional[Tuple[float, float]]:
        """Intersect the two most recent bearing lines.

        Uses flat-earth local coordinates (metres) for the intersection,
        then converts back to lat/lon.  Accurate for distances < 2 km.

        Returns None if the geometry is poor (positions too close, bearings
        too similar, or result is unreasonable).
        """
        if len(self._sightings) < 2:
            return None

        s1 = self._sightings[-2]
        s2 = self._sightings[-1]

        # ── Check that bearings are sufficiently different ──────────
        angle_diff = abs(s1.bearing - s2.bearing) % 360
        if angle_diff > 180:
            angle_diff = 360 - angle_diff
        if angle_diff < MIN_ANGLE_DEG:
            return None  # nearly parallel — no reliable intersection

        # ── Reference point and local-metres conversion ─────────────
        ref_lat = (s1.lat + s2.lat) / 2.0
        ref_lon = (s1.lon + s2.lon) / 2.0
        m_per_deg_lat = 111_320.0
        m_per_deg_lon = 111_320.0 * math.cos(math.radians(ref_lat))

        x1 = (s1.lon - ref_lon) * m_per_deg_lon
        y1 = (s1.lat - ref_lat) * m_per_deg_lat
        x2 = (s2.lon - ref_lon) * m_per_deg_lon
        y2 = (s2.lat - ref_lat) * m_per_deg_lat

        # ── Check baseline distance ────────────────────────────────
        baseline = math.hypot(x2 - x1, y2 - y1)
        if baseline < MIN_BASELINE_M:
            return None  # sightings too close — intersection unreliable

        # ── Direction vectors from bearing (compass: 0=N, 90=E) ────
        dx1 = math.sin(math.radians(s1.bearing))
        dy1 = math.cos(math.radians(s1.bearing))
        dx2 = math.sin(math.radians(s2.bearing))
        dy2 = math.cos(math.radians(s2.bearing))

        # Solve: P1 + t1 * D1 = P2 + t2 * D2
        det = dx1 * (-dy2) - (-dx2) * dy1
        if abs(det) < 1e-10:
            return None  # parallel lines

        bx = x2 - x1
        by = y2 - y1

        t1 = (bx * (-dy2) - (-dx2) * by) / det
        t2 = (bx * dy1 - dx1 * by) / det

        # ── Mark must be ahead of at least one sighting ─────────────
        if t1 < 0 and t2 < 0:
            return None  # mark is behind both sighting positions

        # ── Intersection point (from line 1) ───────────────────────
        ix = x1 + t1 * dx1
        iy = y1 + t1 * dy1

        # ── Sanity: mark distance from midpoint ────────────────────
        mark_dist = math.hypot(ix, iy)
        if mark_dist < MIN_MARK_DIST_M or mark_dist > MAX_MARK_DIST_M:
            return None  # unreasonable distance

        # Convert back to lat/lon
        mark_lat = ref_lat + iy / m_per_deg_lat
        mark_lon = ref_lon + ix / m_per_deg_lon

        return (mark_lat, mark_lon)
