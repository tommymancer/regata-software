"""Auto-generate a race course from wind direction and start position.

Given TWD and a start position, creates:
  - Start line (RC + Pin) perpendicular to the wind, ~150 m apart
  - Windward mark ~0.4 NM directly upwind
"""

import math
from dataclasses import dataclass


@dataclass
class CourseSetup:
    """Generated race course positions."""

    rc_lat: float
    rc_lon: float
    pin_lat: float
    pin_lon: float
    windward_lat: float
    windward_lon: float
    twd: float  # wind direction used to generate

    def to_dict(self) -> dict:
        return {
            "rc": {"lat": self.rc_lat, "lon": self.rc_lon},
            "pin": {"lat": self.pin_lat, "lon": self.pin_lon},
            "windward": {"lat": self.windward_lat, "lon": self.windward_lon},
            "twd": self.twd,
        }


def _offset_position(
    lat: float, lon: float, bearing_deg: float, distance_m: float
) -> tuple[float, float]:
    """Offset a lat/lon position by distance (metres) along a bearing.

    Simple flat-earth approximation, accurate enough for < 2 km.
    """
    bearing_rad = math.radians(bearing_deg)
    d_north = distance_m * math.cos(bearing_rad)
    d_east = distance_m * math.sin(bearing_rad)

    # 1° lat ≈ 111_320 m, 1° lon ≈ 111_320 × cos(lat)
    new_lat = lat + d_north / 111_320.0
    new_lon = lon + d_east / (111_320.0 * math.cos(math.radians(lat)))
    return new_lat, new_lon


def generate_course(
    twd: float,
    start_lat: float,
    start_lon: float,
    line_length_m: float = 150.0,
    leg_length_m: float = 740.0,
) -> CourseSetup:
    """Generate a race course from wind direction and start position.

    Parameters
    ----------
    twd : float
        True wind direction (where wind comes FROM), 0–360°.
    start_lat, start_lon : float
        Center of the start line.
    line_length_m : float
        Distance between RC and Pin (default 150 m).
    leg_length_m : float
        Distance from start midpoint to windward mark (default 740 m ≈ 0.4 NM).

    Returns
    -------
    CourseSetup with all positions.
    """
    # Start line is perpendicular to the wind.
    # Line bearing = TWD + 90°  (RC to starboard side, Pin to port side
    # when looking upwind).
    line_brg = (twd + 90.0) % 360.0
    half = line_length_m / 2.0

    # RC is to the right (starboard) looking upwind = positive along line_brg
    rc_lat, rc_lon = _offset_position(start_lat, start_lon, line_brg, half)
    pin_lat, pin_lon = _offset_position(start_lat, start_lon, line_brg, -half)

    # Windward mark is directly upwind from start midpoint.
    # "Upwind" = toward where the wind comes from = TWD
    upwind_brg = twd % 360.0
    wm_lat, wm_lon = _offset_position(
        start_lat, start_lon, upwind_brg, leg_length_m
    )

    return CourseSetup(
        rc_lat=rc_lat,
        rc_lon=rc_lon,
        pin_lat=pin_lat,
        pin_lon=pin_lon,
        windward_lat=wm_lat,
        windward_lon=wm_lon,
        twd=twd,
    )
