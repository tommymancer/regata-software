"""VMC — Velocity Made on Course.

When the course is rotated (windward mark not aligned with TWD),
VMC replaces VMG as the metric to optimise.

  VMC = BSP × cos(HDG − leg_bearing)

Per-tack optimal TWA:
  On a rotated course, the optimal TWA differs between tacks.
  The favored tack (heading toward the mark) should be sailed wider
  (foot off for speed), the unfavored tack tighter (pinch to minimise
  time on the bad side).

  When mark is right of wind (offset > 0):
    Port tack is favored  → wider  → target + offset
    Starboard is unfavored → tighter → target − offset
  Clamped to avoid going below minimum polar TWA or above 90° upwind.
"""

import math
from typing import Optional, Tuple

from ..pipeline.state import BoatState
from .polar import PolarTable


def compute_vmc(
    bsp: float,
    heading: float,
    leg_bearing: float,
) -> float:
    """VMC = BSP × cos(heading − leg_bearing).

    Positive = making ground toward the mark.
    """
    angle = math.radians(heading - leg_bearing)
    return bsp * math.cos(angle)


def compute_vmc_targets(
    state: BoatState,
    polar: PolarTable,
    course_offset: float,
) -> None:
    """Compute VMC-optimised per-tack targets. Mutates *state* in-place.

    course_offset = leg_bearing − TWD (degrees, signed).
    Positive = mark is right of the wind.

    This adjusts the target TWA on each tack:
    - Starboard tack (TWA > 0): target_twa = polar_target − course_offset
    - Port tack (TWA < 0):      target_twa = polar_target + course_offset

    When offset > 0 (mark right of wind): port is favored (wider),
    starboard is unfavored (tighter). The favored tack foots off
    for speed; the unfavored tack pinches to cross over quickly.
    """
    if (
        state.twa_deg is None
        or state.tws_kt is None
        or state.bsp_kt is None
    ):
        return

    twa = state.twa_deg
    tws = state.tws_kt
    abs_twa = abs(twa)
    is_upwind = abs_twa < 90

    # Get polar VMG-optimal target
    if is_upwind:
        target = polar.target_upwind(tws)
    else:
        target = polar.target_downwind(tws)

    if target is None:
        return

    polar_target_twa, _, _ = target

    # Adjust target TWA for course rotation
    # On starboard (TWA > 0): if mark is right of wind (offset > 0),
    #   starboard is unfavored → sail tighter (subtract offset)
    # On port (TWA < 0): if mark is right of wind (offset > 0),
    #   port is favored → sail wider (add offset)
    if twa > 0:
        # Starboard tack
        adjusted_twa = polar_target_twa - course_offset
    else:
        # Port tack
        adjusted_twa = polar_target_twa + course_offset

    # Clamp: don't go below minimum polar TWA or create nonsensical angles
    min_twa = 25.0  # absolute minimum for any sailboat
    if is_upwind:
        adjusted_twa = max(min_twa, min(adjusted_twa, 85.0))
    else:
        adjusted_twa = max(95.0, min(adjusted_twa, 175.0))

    # Apply sign back
    state.target_twa_vmc_deg = math.copysign(adjusted_twa, twa) if twa != 0 else adjusted_twa

    # Compute VMC (use true heading, since leg_bearing is a true bearing from GPS)
    if state.heading_mag is not None and state.bsp_kt is not None:
        leg_brg = state.leg_bearing_deg
        if leg_brg is not None:
            heading_true = state.heading_mag - state.magnetic_variation
            state.vmc_kt = compute_vmc(
                state.bsp_kt, heading_true, leg_brg
            )

    # VMC from target for comparison
    # The target VMC is the component of target BSP projected onto the leg bearing.
    # For the current tack, the angle between heading and leg bearing is:
    #   adjusted_twa - course_offset (preserving sign for correct tack geometry)
    target_bsp_at_adjusted = polar.bsp(adjusted_twa, tws)
    if target_bsp_at_adjusted is not None and target_bsp_at_adjusted > 0:
        state.target_vmc_kt = target_bsp_at_adjusted * math.cos(
            math.radians(adjusted_twa - course_offset)
        )
