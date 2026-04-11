"""Apply sensor calibration offsets to raw instrument values.

Pipeline order (from Aquarela Njord CSV Spec):
  1. Heading  — subtract compass offset
  2. BSP      — multiply by speed factor
  3. AWA      — subtract AWA offset
  4. Depth    — add depth offset (negative = keel depth below transducer)
  5. Pass through: SOG, COG, AWS, water_temp, lat, lon
"""

from .state import BoatState
from ..config import AquarelaConfig


def apply_calibration(state: BoatState, cfg: AquarelaConfig) -> None:
    """Mutate *state* in-place: copy raw_* fields into calibrated fields
    with offsets/factors from *cfg* applied.

    Fields that have no raw value (None) are left as None.
    """
    # 1. Heading: subtract compass offset
    if state.raw_heading_mag is not None:
        state.heading_mag = (state.raw_heading_mag - cfg.compass_offset) % 360

    # 2. BSP: multiply by speed factor
    if state.raw_bsp_kt is not None:
        state.bsp_kt = max(0.0, state.raw_bsp_kt * cfg.speed_factor)

    # 3. AWA: subtract AWA offset (keep signed range)
    if state.raw_awa_deg is not None:
        awa = state.raw_awa_deg - cfg.awa_offset
        # Normalize to −180 … +180 (modular, safe for any input)
        awa = ((awa + 180) % 360) - 180
        state.awa_deg = awa

    # 4. AWS: pass through (no calibration offset for wind speed sensor)
    if state.raw_aws_kt is not None:
        state.aws_kt = state.raw_aws_kt

    # 5. Depth: add offset (offset is negative for keel depth)
    if state.raw_depth_m is not None:
        state.depth_m = max(0.0, state.raw_depth_m + cfg.depth_offset)

    # 6. Pass through GPS / navigation
    if state.raw_sog_kt is not None:
        state.sog_kt = state.raw_sog_kt
    if state.raw_cog_deg is not None:
        state.cog_deg = state.raw_cog_deg

    # 7. Water temp: pass through
    if state.raw_water_temp_c is not None:
        state.water_temp_c = state.raw_water_temp_c

    # 8. Magnetic variation: prefer PGN value, fallback to config
    # Note: 0.0 is valid (on the agonic line), so only fall back on None
    if state.magnetic_variation is None:
        state.magnetic_variation = cfg.magnetic_variation
