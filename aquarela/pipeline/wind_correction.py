"""Wind correction functions: heel geometry and upwash table lookup.

These corrections sit between calibration and true-wind computation:

    raw → calibrate → heel_correct → upwash_correct → true_wind
"""

from __future__ import annotations

import math
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .state import BoatState
    from .upwash_table import UpwashTable


def correct_heel(
    awa_deg: float,
    aws_kt: float,
    heel_deg: float,
) -> tuple[float, float]:
    """Geometric projection from tilted mast plane to horizontal.

    Returns (awa_corrected_deg, aws_corrected_kt).
    Uses abs(heel_deg) internally.  Returned AWA preserves the original sign.
    """
    heel = math.radians(abs(heel_deg))
    awa = math.radians(awa_deg)

    cos_heel = math.cos(heel)
    cos_awa = math.cos(awa)
    sin_awa = math.sin(awa)

    # Projected apparent wind angle
    awa_corr = math.atan2(sin_awa, cos_awa * cos_heel)

    # Projected apparent wind speed
    aws_corr = aws_kt * math.sqrt(
        cos_heel ** 2 * cos_awa ** 2 + sin_awa ** 2
    )

    return math.degrees(awa_corr), aws_corr


def correct_upwash(
    awa_deg: float,
    table: UpwashTable,
    heel_deg: float,
) -> tuple[float, float]:
    """Look up upwash offset and apply with sign matching AWA.

    Returns (awa_corrected_deg, upwash_offset_applied).
    """
    offset = table.lookup(abs(awa_deg), abs(heel_deg))
    sign = 1.0 if awa_deg >= 0 else -1.0
    awa_corrected = awa_deg + sign * offset
    return awa_corrected, offset


def apply_wind_correction(
    state: BoatState,
    table: Optional[UpwashTable] = None,
    heel_smoothed: Optional[float] = None,
) -> None:
    """Apply heel + upwash corrections to *state* in-place.

    Reads ``state.awa_deg`` and ``state.aws_kt``.  Uses *heel_smoothed*
    if provided, else ``state.heel_deg``, else 0.

    Writes:
        state.awa_corrected_deg
        state.aws_corrected_kt
        state.heel_correction_deg
        state.upwash_offset_deg
    """
    if state.awa_deg is None or state.aws_kt is None:
        return

    heel = heel_smoothed if heel_smoothed is not None else (state.heel_deg or 0.0)

    awa = state.awa_deg
    aws = state.aws_kt
    heel_corr_deg = 0.0

    # ── Heel correction ────────────────────────────────────────────
    if abs(heel) >= 0.5:
        awa_h, aws_h = correct_heel(awa, aws, heel)
        heel_corr_deg = awa_h - awa
        awa = awa_h
        aws = aws_h

    state.heel_correction_deg = heel_corr_deg
    state.aws_corrected_kt = aws

    # ── Upwash correction ──────────────────────────────────────────
    upwash_offset = 0.0
    if table is not None:
        awa, upwash_offset = correct_upwash(awa, table, heel)

    state.awa_corrected_deg = awa
    state.upwash_offset_deg = upwash_offset
