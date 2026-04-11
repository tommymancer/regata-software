"""True wind calculation from calibrated apparent wind and boat speed.

Implements the wind triangle inversion from the Aquarela Njord CSV Spec:
  AWA + AWS + BSP → TWA + TWS + TWD

Sign convention: negative = port, positive = starboard (same for AWA and TWA).
TWD is 0–360, direction wind blows FROM.
"""

import math
from typing import Optional, Tuple

from .state import BoatState


def calc_true_wind(
    bsp_kt: float, awa_deg: float, aws_kt: float
) -> Tuple[float, float]:
    """Compute true wind from calibrated apparent wind and boat speed.

    Args:
        bsp_kt:  calibrated boat speed (knots)
        awa_deg: calibrated apparent wind angle (degrees, signed: −port +stbd)
        aws_kt:  apparent wind speed (knots)

    Returns:
        (twa_deg, tws_kt) — true wind angle (signed) and speed.
    """
    awa_rad = math.radians(awa_deg)
    # Apparent wind in boat-relative Cartesian
    aw_x = aws_kt * math.cos(awa_rad)   # along-boat component
    aw_y = aws_kt * math.sin(awa_rad)   # cross-boat component
    # Subtract boat speed to get true wind
    tw_x = aw_x - bsp_kt
    tw_y = aw_y
    tws = math.sqrt(tw_x ** 2 + tw_y ** 2)
    twa = math.degrees(math.atan2(tw_y, tw_x))
    return twa, tws


def calc_twd(twa_deg: float, heading_mag: float, mag_var: float) -> float:
    """Compute true wind direction (compass direction wind blows FROM).

    Args:
        twa_deg:     true wind angle (signed degrees)
        heading_mag: magnetic heading (degrees)
        mag_var:     magnetic variation (east positive, degrees)

    Returns:
        TWD in 0–360 degrees.
    """
    heading_true = heading_mag - mag_var
    twd = (heading_true + twa_deg) % 360
    return twd


def compute_true_wind(state: BoatState) -> None:
    """Mutate *state* in-place: compute TWA, TWS, TWD.

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
