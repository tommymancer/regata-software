"""Derived sailing calculations from calibrated + true wind data.

Computes:
  - VMG (velocity made good toward wind)
  - Leeway estimate from heel angle
  - Current set & drift from BSP/HDG vs SOG/COG vectors
"""

import math
from typing import Tuple

from .state import BoatState


def compute_vmg(state: BoatState) -> None:
    """VMG = BSP * cos(TWA).

    Positive VMG = making ground upwind, negative = downwind gain.
    Convention: we report VMG as always positive (absolute progress toward
    or away from wind axis), matching standard instrument display.
    """
    if state.bsp_kt is None or state.twa_deg is None:
        return
    state.vmg_kt = state.bsp_kt * math.cos(math.radians(state.twa_deg))


def compute_leeway(state: BoatState) -> None:
    """Estimate leeway angle from heel.

    Empirical model: leeway ≈ k * heel / BSP²
    k ≈ 10 for a typical sportboat (Nitro 80, ~1100 kg, deep keel).
    Clamped to ±15° for sanity.

    Leeway is in the same sign as heel (positive = stbd heel = stbd leeway).
    """
    if state.heel_deg is None or state.bsp_kt is None:
        return
    if state.bsp_kt < 0.5:
        state.leeway_deg = 0.0
        return

    k = 10.0
    leeway = k * state.heel_deg / (state.bsp_kt ** 2)
    state.leeway_deg = max(-15.0, min(15.0, leeway))


def compute_current(state: BoatState) -> None:
    """Estimate current set and drift from the difference between
    water track (BSP + heading) and ground track (SOG + COG).

    Current vector = ground_vector − water_vector.
    set_deg = direction current flows TO (0–360).
    drift_kt = current speed in knots.
    """
    if (
        state.bsp_kt is None
        or state.heading_mag is None
        or state.sog_kt is None
        or state.cog_deg is None
    ):
        return

    # Convert heading to true
    hdg_true = state.heading_mag - state.magnetic_variation

    # Water track vector (through-water motion)
    hdg_rad = math.radians(hdg_true)
    water_x = state.bsp_kt * math.sin(hdg_rad)
    water_y = state.bsp_kt * math.cos(hdg_rad)

    # Ground track vector
    cog_rad = math.radians(state.cog_deg)
    ground_x = state.sog_kt * math.sin(cog_rad)
    ground_y = state.sog_kt * math.cos(cog_rad)

    # Current = ground - water
    current_x = ground_x - water_x
    current_y = ground_y - water_y

    drift = math.sqrt(current_x ** 2 + current_y ** 2)
    if drift < 0.01:
        state.current_set_deg = 0.0
        state.current_drift_kt = 0.0
        return

    set_deg = math.degrees(math.atan2(current_x, current_y)) % 360

    state.current_set_deg = set_deg
    state.current_drift_kt = drift


def compute_derived(state: BoatState) -> None:
    """Run all derived calculations on *state* in-place."""
    compute_vmg(state)
    compute_leeway(state)
    compute_current(state)
