"""Start line — capture, geometry, bias, and distance computation.

Pre-race workflow:
  1. Sail near RC boat  → log_rc(lat, lon)
  2. Sail near pin end  → log_pin(lat, lon)
  3. Point bow at mark  → sight_mark(heading_mag)

From these three captures we compute:
  - line_bearing:    bearing along the start line (RC → Pin)
  - line_length_m:   distance between RC and Pin in metres
  - line_bias_deg:   how far the line is biased from perpendicular to TWD
                     (positive = pin-end favored, negative = RC favored)
  - leg_bearing:     bearing from start midpoint toward the windward mark
  - course_offset:   leg_bearing − TWD (how rotated the course is)
  - dist_to_line_nm: shortest distance from boat to the start line
"""

import math
from dataclasses import dataclass
from typing import Optional, Tuple

from .navigation import bearing_to, haversine_distance


@dataclass
class StartLineState:
    """Captured start line + mark data."""

    rc_lat: Optional[float] = None
    rc_lon: Optional[float] = None
    pin_lat: Optional[float] = None
    pin_lon: Optional[float] = None
    mark_bearing: Optional[float] = None  # compass heading when sighting mark

    def is_line_set(self) -> bool:
        return (
            self.rc_lat is not None
            and self.rc_lon is not None
            and self.pin_lat is not None
            and self.pin_lon is not None
        )

    def is_mark_set(self) -> bool:
        return self.mark_bearing is not None

    def to_dict(self) -> dict:
        return {
            "rc": (
                {"lat": self.rc_lat, "lon": self.rc_lon}
                if self.rc_lat is not None
                else None
            ),
            "pin": (
                {"lat": self.pin_lat, "lon": self.pin_lon}
                if self.pin_lat is not None
                else None
            ),
            "mark_bearing": self.mark_bearing,
            "line_set": self.is_line_set(),
            "mark_set": self.is_mark_set(),
        }


class StartLine:
    """Manages start line capture and geometry."""

    def __init__(self) -> None:
        self.state = StartLineState()

    def log_rc(self, lat: float, lon: float) -> None:
        """Capture RC boat position."""
        self.state.rc_lat = lat
        self.state.rc_lon = lon

    def log_pin(self, lat: float, lon: float) -> None:
        """Capture pin end position."""
        self.state.pin_lat = lat
        self.state.pin_lon = lon

    def sight_mark(self, heading_mag: float) -> None:
        """Capture mark bearing from current heading."""
        self.state.mark_bearing = heading_mag % 360

    def reset(self) -> None:
        """Clear all captures."""
        self.state = StartLineState()

    # ── Geometry computations ──────────────────────────────────────

    def line_bearing(self) -> Optional[float]:
        """Bearing along the start line (RC → Pin), 0–360°."""
        if not self.state.is_line_set():
            return None
        return bearing_to(
            self.state.rc_lat, self.state.rc_lon,
            self.state.pin_lat, self.state.pin_lon,
        )

    def line_length_m(self) -> Optional[float]:
        """Start line length in metres."""
        if not self.state.is_line_set():
            return None
        nm = haversine_distance(
            self.state.rc_lat, self.state.rc_lon,
            self.state.pin_lat, self.state.pin_lon,
        )
        return nm * 1852.0

    def line_midpoint(self) -> Optional[Tuple[float, float]]:
        """Midpoint of the start line (lat, lon)."""
        if not self.state.is_line_set():
            return None
        return (
            (self.state.rc_lat + self.state.pin_lat) / 2.0,
            (self.state.rc_lon + self.state.pin_lon) / 2.0,
        )

    def line_bias_deg(self, twd: float) -> Optional[float]:
        """Line bias: how much the line favors one end.

        Positive = pin end is upwind (favored).
        Negative = RC end is upwind (favored).
        Zero = perfectly square to the wind.

        Computed as: how far the line perpendicular deviates from TWD.
        """
        lb = self.line_bearing()
        if lb is None:
            return None

        # Two perpendiculars to the line — pick the one closer to TWD
        perp_a = (lb + 90.0) % 360.0
        perp_b = (lb - 90.0) % 360.0
        if abs(_angle_diff(twd, perp_a)) <= abs(_angle_diff(twd, perp_b)):
            perp = perp_a
        else:
            perp = perp_b

        # Bias = difference between wind direction and line perpendicular
        # Positive means pin end is more upwind
        bias = _angle_diff(twd, perp)
        return bias

    def leg_bearing(self) -> Optional[float]:
        """Bearing from start line midpoint toward the sighted mark.

        This is the mark_bearing captured during sight_mark().
        When sighting, the helmsman points the bow at the mark,
        so the compass heading IS the bearing from boat to mark.
        Since sighting typically happens near the start line,
        this is a good approximation of the leg bearing.
        """
        return self.state.mark_bearing

    def course_offset_deg(self, twd: float) -> Optional[float]:
        """How much the course leg is rotated from the wind axis.

        course_offset = leg_bearing − TWD
        Positive = mark is right of the wind.
        Negative = mark is left of the wind.
        """
        lb = self.leg_bearing()
        if lb is None:
            return None
        return _angle_diff(lb, twd)

    def dist_to_line_nm(
        self, boat_lat: float, boat_lon: float
    ) -> Optional[float]:
        """Shortest distance from boat to the start line (NM).

        Uses the perpendicular distance from a point to a line
        segment defined by RC and Pin positions.
        """
        if not self.state.is_line_set():
            return None

        # Use cross-track distance formula:
        # d_xt = asin(sin(d13/R) * sin(θ13 − θ12)) * R
        d13 = haversine_distance(
            self.state.rc_lat, self.state.rc_lon,
            boat_lat, boat_lon,
        )
        brg13 = bearing_to(
            self.state.rc_lat, self.state.rc_lon,
            boat_lat, boat_lon,
        )
        brg12 = bearing_to(
            self.state.rc_lat, self.state.rc_lon,
            self.state.pin_lat, self.state.pin_lon,
        )

        # Cross-track distance (clamp arg for float safety)
        arg = (math.sin(d13 / EARTH_RADIUS_NM)
               * math.sin(math.radians(brg13 - brg12)))
        d_xt = math.asin(max(-1.0, min(1.0, arg))) * EARTH_RADIUS_NM

        return abs(d_xt)


# Earth radius for cross-track calc (same as navigation module)
EARTH_RADIUS_NM = 3440.065


def _angle_diff(a: float, b: float) -> float:
    """Signed angular difference a − b, result in [−180, 180]."""
    d = (a - b) % 360
    if d > 180:
        d -= 360
    return d
