"""Layline calculations — compute port/stbd layline bearings.

Laylines are the headings you need to sail to reach the windward mark
(upwind) or leeward mark (downwind) on a single tack/gybe.

layline_bearing = TWD ± (target_TWA + leeway) adjusted for current.
"""

import math
from typing import Optional, Tuple

from ..pipeline.state import BoatState
from ..race.navigation import bearing_to, haversine_distance
from .polar import PolarTable


def compute_laylines(state: BoatState, polar: PolarTable) -> Tuple[Optional[float], Optional[float]]:
    """Compute port and starboard layline bearings.

    Upwind/downwind is determined by the bearing to the active mark
    relative to the true wind direction — NOT by the boat's current TWA.
    This ensures correct laylines even when the boat is temporarily
    sailing away from the mark.

    Returns:
        (port_layline, stbd_layline) — compass bearings in 0–360°,
        or (None, None) if insufficient data.
    """
    if state.twd_deg is None or state.tws_kt is None:
        return None, None

    tws = state.tws_kt
    twd = state.twd_deg

    # Determine upwind/downwind from the mark bearing, not current TWA.
    # Angle between wind direction and bearing-to-mark:
    #   < 90° → mark is upwind,  ≥ 90° → mark is downwind.
    if state.btw_deg is not None:
        angle_to_mark = abs((state.btw_deg - twd + 180) % 360 - 180)
        is_upwind = angle_to_mark < 90
    else:
        # Fallback: use current TWA if no active mark
        abs_twa = abs(state.twa_deg) if state.twa_deg is not None else 45.0
        is_upwind = abs_twa < 90

    # Get target TWA from polar
    if is_upwind:
        target = polar.target_upwind(tws)
    else:
        target = polar.target_downwind(tws)

    if target is None:
        return None, None

    target_twa = target[0]  # optimal angle

    # Leeway correction (if available)
    leeway = abs(state.leeway_deg) if state.leeway_deg is not None else 0.0

    # Effective angle to lay (wider by leeway)
    effective_angle = target_twa + leeway

    # Current correction: shift laylines by current set relative to TWD
    current_correction = 0.0
    if (
        state.current_set_deg is not None
        and state.current_drift_kt is not None
        and state.current_drift_kt > 0.1
        and state.bsp_kt is not None
        and state.bsp_kt > 0.5
    ):
        # Approximate: shift laylines by arcsin(drift/BSP) in the
        # direction of current set relative to wind
        ratio = min(state.current_drift_kt / state.bsp_kt, 0.5)
        current_correction = math.degrees(math.asin(ratio))

    # Layline bearing = boat heading when sailing that layline toward the mark.
    # Same formula for upwind and downwind: target_TWA is the absolute angle
    # from bow to wind (≈45° upwind, ≈150° downwind). Convention: TWA is signed
    # with port negative, so stbd heading = TWD − TWA, port heading = TWD + TWA.
    #
    # Port layline: boat on port tack/gybe (wind on port/left side)
    port = (twd + effective_angle + current_correction) % 360
    # Starboard layline: boat on stbd tack/gybe (wind on stbd/right side)
    stbd = (twd - effective_angle - current_correction) % 360

    return port, stbd


def compute_layline_distances(
    state: BoatState,
    mark_lat: float,
    mark_lon: float,
    port_bearing: float,
    stbd_bearing: float,
) -> Tuple[Optional[float], Optional[float]]:
    """Perpendicular distance from boat to each layline through the mark.

    Each layline is a great-circle line from the mark at the given bearing.
    Cross-track distance = |mark_to_boat × sin(bearing_diff)|.

    Returns:
        (dist_to_port_nm, dist_to_stbd_nm) in nautical miles,
        or (None, None) if boat position is unavailable.
    """
    if state.lat is None or state.lon is None:
        return None, None

    dist_mark_to_boat = haversine_distance(mark_lat, mark_lon, state.lat, state.lon)
    brg_mark_to_boat = bearing_to(mark_lat, mark_lon, state.lat, state.lon)

    angle_port = math.radians(port_bearing - brg_mark_to_boat)
    dist_port = abs(dist_mark_to_boat * math.sin(angle_port))

    angle_stbd = math.radians(stbd_bearing - brg_mark_to_boat)
    dist_stbd = abs(dist_mark_to_boat * math.sin(angle_stbd))

    return dist_port, dist_stbd
