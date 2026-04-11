"""Mark navigation — haversine BTW / DTW / ETA."""

import math

from ..pipeline.state import BoatState

EARTH_RADIUS_NM = 3440.065  # nautical miles


def haversine_distance(lat1: float, lon1: float,
                       lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in nautical miles."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = (math.sin(dlat / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
    # Clamp to [0, 1] to guard against float rounding
    a = min(1.0, a)
    return 2 * EARTH_RADIUS_NM * math.asin(math.sqrt(a))


def bearing_to(lat1: float, lon1: float,
               lat2: float, lon2: float) -> float:
    """Initial bearing from point 1 → point 2, 0–360°."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = (math.cos(lat1) * math.sin(lat2)
         - math.sin(lat1) * math.cos(lat2) * math.cos(dlon))
    return math.degrees(math.atan2(x, y)) % 360


def compute_navigation(state: BoatState,
                       mark_lat: float, mark_lon: float,
                       mark_name: str) -> None:
    """Compute BTW and DTW to target mark.  Mutates *state* in-place."""
    state.next_mark_name = mark_name

    if state.lat is None or state.lon is None:
        state.btw_deg = None
        state.dtw_nm = None
        return

    state.btw_deg = bearing_to(state.lat, state.lon, mark_lat, mark_lon)
    state.dtw_nm = haversine_distance(state.lat, state.lon, mark_lat, mark_lon)
